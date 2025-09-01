# Copyright (c) 2023, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

from typing import Dict, List, Optional, Any, Union

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, getdate, nowdate, add_days, get_datetime
from erpnext.controllers.accounts_controller import AccountsController
from car_workshop.utils.pricing import resolve_rate


class WorkOrderBilling(AccountsController):
    def validate(self):
        self.validate_work_order()
        self.validate_dates()
        self.calculate_totals()
        self.update_payment_status()
        self.set_status()
        self.validate_discount_approval()
        self.update_approval_fields()
        
    def on_submit(self):
        self.update_work_order_billing_status()
        self.record_status_history()
        
    def on_cancel(self):
        self.update_work_order_billing_status(cancel=True)
        self.cancel_linked_documents()
        self.record_status_history()

    def on_update(self):
        if self.has_value_changed("status"):
            self.record_status_history()

    def record_status_history(self) -> None:
        """Log status changes with user and timestamp"""
        timestamp = get_datetime()
        user = getattr(frappe.session, "user", "Unknown")
        message = _("Status changed to {0} by {1} on {2}").format(self.status, user, timestamp)
        self.add_comment("Info", message)

    def get_discount_threshold(self) -> float:
        """
        Fetch the discount threshold from settings
        
        Returns:
            float: The discount approval threshold amount
        """
        return flt(frappe.db.get_single_value("Car Workshop Settings", "discount_approval_threshold") or 0)

    def get_discount_approver_roles(self) -> List[str]:
        """
        Get the roles allowed to approve discounts
        
        Returns:
            List[str]: List of role names
        """
        roles = frappe.db.get_single_value("Car Workshop Settings", "discount_approver_roles") or "Accountant"
        return [r.strip() for r in roles.replace("\n", ",").split(",") if r.strip()]

    def validate_discount_approval(self) -> None:
        """Validate if the discount requires approval and if current user can approve"""
        threshold = self.get_discount_threshold()
        if flt(self.discount_amount) <= threshold:
            return

        approver_roles = self.get_discount_approver_roles()
        get_roles = getattr(frappe, "get_roles", lambda user=None: [])
        user_roles = set(get_roles(getattr(frappe.session, "user", None)))
        if not user_roles.intersection(set(approver_roles)):
            frappe.throw(
                _("Discount exceeds allowed threshold of {0}. Requires approval from roles: {1}").format(
                    threshold, ", ".join(approver_roles)
                )
            )
        if getattr(self, "approval_status", "Pending Approval") != "Approved":
            frappe.throw(_("Discount exceeds allowed threshold and needs approval."))
    
    def validate_work_order(self) -> None:
        """
        Validate that the Work Order exists, is in completed state,
        and has not been billed yet.
        """
        if not self.work_order:
            frappe.throw(_("Work Order is required"))
        
        work_order = frappe.get_doc("Work Order", self.work_order)
        if work_order.status not in ["Completed", "Closed"]:
            frappe.throw(_("Work Order must be 'Completed' or 'Closed' before billing"))
        
        # Check if the work order is already fully billed
        existing_billings = frappe.get_all(
            "Work Order Billing", 
            filters={
                "work_order": self.work_order, 
                "docstatus": 1,
                "name": ["!=", self.name]
            },
            fields=["name"]
        )
        
        if existing_billings and not self.is_return:
            frappe.throw(_("Work Order {0} is already billed in {1}").format(
                self.work_order, existing_billings[0].name))
    
    def validate_dates(self) -> None:
        """Set default dates and validate due date"""
        if not self.posting_date:
            self.posting_date = nowdate()
            
        if not self.due_date:
            self.due_date = add_days(self.posting_date, 30)  # Default 30 days due date
            
        if getdate(self.due_date) < getdate(self.posting_date):
            frappe.throw(_("Due Date cannot be before Posting Date"))
    
    def calculate_totals(self) -> None:
        """
        Calculate and update all total fields for the document.
        This serves as a preview - final calculations will be done in Sales Invoice.
        """
        # Calculate job type items total
        self.total_services_amount = 0
        for item in self.job_type_items:
            item.amount = flt(item.hours) * flt(item.rate)
            self.total_services_amount += flt(item.amount)
            
        # Calculate service package items total
        for item in self.service_package_items:
            item.amount = flt(item.quantity) * flt(item.rate)
            self.total_services_amount += flt(item.amount)
            
        # Calculate part items total
        self.total_parts_amount = 0
        for item in self.part_items:
            item.amount = flt(item.quantity) * flt(item.rate)
            self.total_parts_amount += flt(item.amount)
            
        # Calculate external service items total
        self.total_external_services_amount = 0
        for item in self.external_service_items:
            item.amount = flt(item.rate)
            self.total_external_services_amount += flt(item.amount)
            
        # Calculate subtotal
        self.subtotal = flt(self.total_services_amount) + flt(self.total_parts_amount) + flt(self.total_external_services_amount)
        
        # Calculate tax amount - preview only, final tax calculated in SI
        self.tax_amount = 0
        if self.taxes_and_charges:
            tax_template = frappe.get_doc("Sales Taxes and Charges Template", self.taxes_and_charges)
            for tax in tax_template.taxes:
                if tax.charge_type == "On Net Total":
                    self.tax_amount += flt(self.subtotal) * flt(tax.rate) / 100
                    
        # Calculate grand total
        self.grand_total = flt(self.subtotal) + flt(self.tax_amount) - flt(self.discount_amount)
        
        # Calculate rounded total
        self.rounded_total = round(self.grand_total)
        
        # Calculate payment amount total (for preview)
        self.payment_amount = 0
        for payment in self.payment_details:
            self.payment_amount += flt(payment.amount)

        # Preview of down payment and balance
        down_payment = self.get_down_payment_amount()
        self.remaining_balance = flt(self.grand_total) - down_payment
        self.balance_amount = flt(self.remaining_balance) - flt(self.payment_amount)
    
    def get_down_payment_amount(self) -> float:
        """
        Calculate down payment amount based on type and value
        
        Returns:
            float: Calculated down payment amount
        """
        amount = flt(self.down_payment_amount)
        if self.down_payment_type == "Percentage":
            return flt(self.grand_total) * amount / 100
        return amount
    
    def update_payment_status(self) -> None:
        """Update the payment status based on payment amounts"""
        total_paid = flt(self.payment_amount) + self.get_down_payment_amount()
        if total_paid <= 0:
            self.payment_status = "Unpaid"
        elif total_paid < flt(self.grand_total):
            self.payment_status = "Partially Paid"
        else:
            self.payment_status = "Paid"
    
    def set_status(self) -> None:
        """Set the document status based on various conditions"""
        if self.docstatus == 0:
            self.status = "Draft"
        elif self.docstatus == 2:
            self.status = "Cancelled"
        elif self.workflow_state == "Completed":
            self.status = "Completed"
        elif self.payment_status == "Paid":
            self.status = "Fully Paid"
        elif self.payment_status == "Partially Paid":
            self.status = "Partially Paid"
        elif getdate(self.due_date) < getdate(nowdate()):
            self.status = "Overdue"
        else:
            self.status = "Pending Payment"
    
    def update_work_order_billing_status(self, cancel: bool = False) -> None:
        """
        Update the billing status on the linked Work Order
        
        Args:
            cancel: Whether this is being called during cancellation
        """
        if not self.work_order:
            return
            
        status = "Unbilled" if cancel else "Billed"
        frappe.db.set_value("Work Order", self.work_order, "billing_status", status)
    
    def cancel_linked_documents(self) -> None:
        """Cancel linked Sales Invoice"""
        # Cancel Sales Invoice
        if self.sales_invoice:
            sinv = frappe.get_doc("Sales Invoice", self.sales_invoice)
            if sinv.docstatus == 1:
                sinv.flags.ignore_permissions = True
                sinv.cancel()

    def update_approval_fields(self) -> None:
        """Populate audit fields when approved"""
        if getattr(self, 'approval_status', None) == "Approved" and not getattr(self, 'approved_by', None):
            self.approved_by = frappe.session.user
            self.approved_on = get_datetime()

    def approve(self, approver: Optional[str] = None) -> None:
        """
        Convenience method to approve the billing document
        
        Args:
            approver: User who is approving the document
        """
        self.approval_status = "Approved"
        self.approved_by = approver or frappe.session.user
        self.approved_on = get_datetime()
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get dashboard data for this document
        
        Returns:
            Dict: Dashboard configuration for linked documents
        """
        return {
            'fieldname': 'work_order_billing',
            'non_standard_fieldnames': {
                'Sales Invoice': 'work_order_billing',
            },
            'transactions': [
                {
                    'label': _('References'),
                    'items': ['Work Order']
                },
                {
                    'label': _('Billing'),
                    'items': ['Sales Invoice']
                }
            ]
        }


@frappe.whitelist()
def get_work_order_billing_source(work_order: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get all billable items from a Work Order
    
    Args:
        work_order: Work Order document name
        
    Returns:
        Dict: Dictionary containing job_types, service_packages, parts, and external_services
    """
    if not work_order:
        frappe.throw(_("Work Order is required"))
    
    # Check permissions
    work_order_doc = frappe.get_doc("Work Order", work_order)
    work_order_doc.check_permission("read")
    
    if work_order_doc.status not in ["Completed", "Closed"]:
        frappe.throw(_("Work Order must be 'Completed' or 'Closed' before billing"))
    
    if work_order_doc.billing_status == "Billed":
        frappe.throw(_("Work Order is already billed"))

    # Get default price list
    default_price_list = frappe.db.get_value("Selling Settings", None, "selling_price_list") or "Standard Selling"
    posting_date = getattr(work_order_doc, "posting_date", nowdate())
    
    result = {
        "job_types": [],
        "service_packages": [],
        "parts": [],
        "external_services": []
    }
    
    # Get job types
    job_types = frappe.get_all(
        "Work Order Job Type",
        filters={"parent": work_order},
        fields=["job_type", "job_type_name", "hours", "rate", "amount"]
    )
    
    for job in job_types:
        item_code = frappe.db.get_value("Job Type", job.job_type, "item")
        if not item_code:
            continue

        if not job.rate:
            price_data = resolve_rate("Job Type", job.job_type, default_price_list, posting_date)
            if price_data:
                job.rate = price_data.get("rate")

        job.amount = flt(job.hours) * flt(job.rate)
        result["job_types"].append(job)
    
    # Get service packages
    service_packages = frappe.get_all(
        "Work Order Service Package",
        filters={"parent": work_order},
        fields=["service_package", "service_package_name", "quantity", "rate", "amount"]
    )
    
    for package in service_packages:
        item_code = frappe.db.get_value("Service Package", package.service_package, "item")
        if not item_code:
            continue

        if not package.rate:
            price_data = resolve_rate("Service Package", package.service_package, default_price_list, posting_date)
            if price_data:
                package.rate = price_data.get("rate")

        package.amount = flt(package.quantity) * flt(package.rate)
        result["service_packages"].append(package)
    
    # Get parts
    parts = frappe.get_all(
        "Work Order Part",
        filters={"parent": work_order},
        fields=["part", "part_name", "quantity", "rate", "amount"]
    )
    
    for part in parts:
        item_code = frappe.db.get_value("Part", part.part, "item")
        if not item_code:
            continue

        if not part.rate:
            price_data = resolve_rate("Part", part.part, default_price_list, posting_date)
            if price_data:
                part.rate = price_data.get("rate")

        part.amount = flt(part.quantity) * flt(part.rate)
        result["parts"].append(part)
    
    # Get external services
    external_services = frappe.get_all(
        "Work Order External Service",
        filters={"parent": work_order},
        fields=["service_name", "provider", "rate", "amount"]
    )
    
    for service in external_services:
        service.amount = flt(service.rate)
        result["external_services"].append(service)
    
    return result


@frappe.whitelist()
def make_sales_invoice(source_name: str, target_doc: Optional[Dict] = None) -> Union[Dict, str]:
    """
    Create Sales Invoice from Work Order Billing
    
    Args:
        source_name: Work Order Billing document name
        target_doc: Target document (optional)
        
    Returns:
        Union[Dict, str]: The created Sales Invoice document or its name
    """
    def set_missing_values(source: Document, target: Document) -> None:
        target.is_pos = 0
        target.ignore_pricing_rule = 1
        target.run_method("set_missing_values")
        
    def add_item_rows(source: Document, target: Document, source_parent: Document) -> None:
        """Add all billable items to the Sales Invoice"""
        # Add job type items
        for item in source_parent.job_type_items:
            item_code = frappe.db.get_value("Job Type", item.job_type, "item")
            if not item_code:
                continue
                
            si_item = target.append("items", {})
            si_item.item_code = item_code
            si_item.qty = item.hours
            si_item.rate = item.rate
            si_item.amount = item.amount
            si_item.description = f"Job: {item.job_type_name}"
            
        # Add service package items
        for item in source_parent.service_package_items:
            item_code = frappe.db.get_value("Service Package", item.service_package, "item")
            if not item_code:
                continue
                
            si_item = target.append("items", {})
            si_item.item_code = item_code
            si_item.qty = item.quantity
            si_item.rate = item.rate
            si_item.amount = item.amount
            si_item.description = f"Service Package: {item.service_package_name}"
            
        # Add part items
        for item in source_parent.part_items:
            item_code = frappe.db.get_value("Part", item.part, "item")
            if not item_code:
                continue
                
            si_item = target.append("items", {})
            si_item.item_code = item_code
            si_item.qty = item.quantity
            si_item.rate = item.rate
            si_item.amount = item.amount
            si_item.description = f"Part: {item.part_name}"
            
        # Add external service items
        for item in source_parent.external_service_items:
            default_service_item = frappe.db.get_single_value(
                "Car Workshop Settings", "default_external_service_item"
            )
            if not default_service_item:
                frappe.throw(_("Please set Default External Service Item in Car Workshop Settings"))
                
            si_item = target.append("items", {})
            si_item.item_code = default_service_item
            si_item.qty = 1
            si_item.rate = item.rate
            si_item.amount = item.amount
            si_item.description = f"External Service: {item.service_name}"
            
        # Add taxes if applicable
        if source_parent.taxes_and_charges:
            target.taxes_and_charges = source_parent.taxes_and_charges
            
        # Apply discount if applicable
        if flt(source_parent.discount_amount) > 0:
            target.apply_discount_on = "Grand Total"
            target.discount_amount = source_parent.discount_amount
    
    doc = get_mapped_doc(
        "Work Order Billing", 
        source_name,
        {
            "Work Order Billing": {
                "doctype": "Sales Invoice",
                "field_map": {
                    "name": "work_order_billing",
                    "work_order": "work_order",
                    "customer_vehicle": "customer_vehicle",
                    "posting_date": "posting_date",
                    "due_date": "due_date"
                },
                "validation": {
                    "docstatus": ["=", 1]
                },
                "postprocess": add_item_rows
            }
        }, 
        target_doc, 
        set_missing_values
    )
    
    doc.save()
    
    # Update source document with Sales Invoice reference
    frappe.db.set_value("Work Order Billing", source_name, "sales_invoice", doc.name)
    
    return doc.name if isinstance(doc, str) else doc