# Copyright (c) 2023, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, nowdate, add_days, get_datetime
from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.accounts.utils import get_account_currency
from erpnext.accounts.party import get_party_account
from erpnext.controllers.accounts_controller import AccountsController

class WorkOrderBilling(AccountsController):
    def validate(self):
        self.validate_work_order()
        self.validate_dates()
        self.calculate_totals()
        self.update_payment_status()
        self.set_status()
        self.update_approval_fields()
        
    def on_submit(self):
        self.update_work_order_billing_status()
        self.make_gl_entries()
        self.create_sales_invoice()
        self.create_down_payment_entry()
        self.process_returns_and_cancellations()
        
    def on_cancel(self):
        self.update_work_order_billing_status(cancel=True)
        self.make_gl_entries(cancel=True)
        self.cancel_linked_documents()
        self.record_status_history()

    def on_update_after_submit(self):
        self.make_gl_entries(cancel=True)
        self.make_gl_entries()

    def on_update(self):
        if self.has_value_changed("status"):
            self.record_status_history()

    def record_status_history(self):
        """Log status changes with user and timestamp"""
        message = _("Status changed to {0}").format(self.status)
        self.add_comment("Info", message)
    
    def validate_work_order(self):
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
    
    def validate_dates(self):
        if not self.posting_date:
            self.posting_date = nowdate()
            
        if not self.due_date:
            self.due_date = add_days(self.posting_date, 30)  # Default 30 days due date
            
        if getdate(self.due_date) < getdate(self.posting_date):
            frappe.throw(_("Due Date cannot be before Posting Date"))
    
    def get_down_payment_amount(self):
        amount = flt(self.down_payment_amount)
        if self.down_payment_type == "Percentage":
            return flt(self.grand_total) * amount / 100
        return amount

    def calculate_totals(self):
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
        
        # Calculate tax amount
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
        
        # Calculate payment amount total
        self.payment_amount = 0
        for payment in self.payment_details:
            self.payment_amount += flt(payment.amount)

        down_payment = self.get_down_payment_amount()
        self.remaining_balance = flt(self.grand_total) - down_payment

        # Calculate balance amount
        self.balance_amount = flt(self.remaining_balance) - flt(self.payment_amount)
    
    def update_payment_status(self):
        total_paid = flt(self.payment_amount) + self.get_down_payment_amount()
        if total_paid <= 0:
            self.payment_status = "Unpaid"
        elif total_paid < flt(self.grand_total):
            self.payment_status = "Partially Paid"
        else:
            self.payment_status = "Paid"
    
    def set_status(self):
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
    
    def update_work_order_billing_status(self, cancel=False):
        if not self.work_order:
            return
            
        status = "Unbilled"
        if not cancel:
            status = "Billed"
            
        frappe.db.set_value("Work Order", self.work_order, "billing_status", status)
    
    def make_gl_entries(self, cancel=False):
        gl_entries = []
        
        # Revenue entry
        revenue_account = frappe.get_cached_value('Company', self.company, 'default_income_account')
        if not revenue_account:
            frappe.throw(_("Please set Default Income Account in Company settings"))
            
        # Customer receivable account
        receivable_account = get_party_account(
            party_type="Customer",
            party=self.customer,
            company=self.company
        )
        
        if not receivable_account:
            frappe.throw(_("Please set Receivable Account for customer {0}").format(self.customer))
        
        # Revenue GL Entry
        gl_entries.append(
            self.get_gl_dict({
                "account": revenue_account,
                "credit": self.subtotal,
                "credit_in_account_currency": self.subtotal,
                "against": self.customer,
                "cost_center": self.cost_center,
                "remarks": f"Revenue for Work Order {self.work_order}"
            })
        )
        
        # COGS and Inventory entries for parts
        if self.total_parts_amount > 0:
            inventory_account = frappe.get_cached_value('Company', self.company, 'default_inventory_account')
            cogs_account = frappe.get_cached_value('Company', self.company, 'default_expense_account')
            
            if not inventory_account:
                frappe.throw(_("Please set Default Inventory Account in Company settings"))
                
            if not cogs_account:
                frappe.throw(_("Please set Default Expense Account in Company settings"))
                
            # Inventory GL Entry
            gl_entries.append(
                self.get_gl_dict({
                    "account": inventory_account,
                    "credit": self.total_parts_amount,
                    "credit_in_account_currency": self.total_parts_amount,
                    "against": cogs_account,
                    "cost_center": self.cost_center,
                    "remarks": f"Inventory reduction for Work Order {self.work_order}"
                })
            )
            
            # COGS GL Entry
            gl_entries.append(
                self.get_gl_dict({
                    "account": cogs_account,
                    "debit": self.total_parts_amount,
                    "debit_in_account_currency": self.total_parts_amount,
                    "against": inventory_account,
                    "cost_center": self.cost_center,
                    "remarks": f"COGS for Work Order {self.work_order}"
                })
            )
        
        # Tax account entries
        if flt(self.tax_amount) > 0:
            tax_account = None
            if self.taxes_and_charges:
                tax_template = frappe.get_doc("Sales Taxes and Charges Template", self.taxes_and_charges)
                if tax_template.taxes:
                    tax_account = tax_template.taxes[0].account_head
            
            if not tax_account:
                tax_account = frappe.get_cached_value('Company', self.company, 'default_tax_account')
                
            if not tax_account:
                frappe.throw(_("Please set a Tax Account in the Taxes and Charges Template or Company settings"))
                
            # Tax GL Entry
            gl_entries.append(
                self.get_gl_dict({
                    "account": tax_account,
                    "credit": self.tax_amount,
                    "credit_in_account_currency": self.tax_amount,
                    "against": self.customer,
                    "cost_center": self.cost_center,
                    "remarks": f"Tax for Work Order {self.work_order}"
                })
            )
        
        # Discount account entries
        if flt(self.discount_amount) > 0:
            discount_account = frappe.get_cached_value('Company', self.company, 'discount_allowed_account')
            
            if not discount_account:
                frappe.throw(_("Please set Discount Allowed Account in Company settings"))
                
            # Discount GL Entry
            gl_entries.append(
                self.get_gl_dict({
                    "account": discount_account,
                    "debit": self.discount_amount,
                    "debit_in_account_currency": self.discount_amount,
                    "against": self.customer,
                    "cost_center": self.cost_center,
                    "remarks": f"Discount for Work Order {self.work_order}"
                })
            )
        
        # Customer receivable entry
        gl_entries.append(
            self.get_gl_dict({
                "account": receivable_account,
                "party_type": "Customer",
                "party": self.customer,
                "debit": self.grand_total,
                "debit_in_account_currency": self.grand_total,
                "against": revenue_account,
                "cost_center": self.cost_center,
                "remarks": f"Receivable for Work Order {self.work_order}"
            })
        )
        
        # Make payment entries if any
        if self.payment_amount > 0:
            for payment in self.payment_details:
                if payment.amount <= 0:
                    continue
                    
                # Payment GL Entry
                gl_entries.append(
                    self.get_gl_dict({
                        "account": payment.payment_account,
                        "debit": payment.amount,
                        "debit_in_account_currency": payment.amount,
                        "against": receivable_account,
                        "cost_center": self.cost_center,
                        "remarks": f"Payment for Work Order {self.work_order}"
                    })
                )
                
                # Reduce receivable
                gl_entries.append(
                    self.get_gl_dict({
                        "account": receivable_account,
                        "party_type": "Customer",
                        "party": self.customer,
                        "credit": payment.amount,
                        "credit_in_account_currency": payment.amount,
                        "against": payment.payment_account,
                        "cost_center": self.cost_center,
                        "remarks": f"Payment against receivable for Work Order {self.work_order}"
                    })
                )
        
        # Make GL entries
        if gl_entries:
            make_gl_entries(gl_entries, cancel=cancel)
    
    def create_sales_invoice(self):
        """Create a Sales Invoice from this billing document"""
        if self.sales_invoice:
            return

        if not self.company:
            frappe.throw(_("Company is required to create a Sales Invoice"))

        def append_items(sinv):
            for item in self.job_type_items:
                sinv_item = sinv.append("items", {})
                sinv_item.item_code = frappe.db.get_value("Job Type", item.job_type, "item")
                sinv_item.qty = item.hours
                sinv_item.rate = item.rate
                sinv_item.amount = item.amount
                sinv_item.description = f"Job: {item.job_type_name}"

            for item in self.service_package_items:
                sinv_item = sinv.append("items", {})
                sinv_item.item_code = frappe.db.get_value("Service Package", item.service_package, "item")
                sinv_item.qty = item.quantity
                sinv_item.rate = item.rate
                sinv_item.amount = item.amount
                sinv_item.description = f"Service Package: {item.service_package_name}"

            for item in self.part_items:
                sinv_item = sinv.append("items", {})
                sinv_item.item_code = frappe.db.get_value("Part", item.part, "item")
                sinv_item.qty = item.quantity
                sinv_item.rate = item.rate
                sinv_item.amount = item.amount
                sinv_item.description = f"Part: {item.part_name}"

            for item in self.external_service_items:
                sinv_item = sinv.append("items", {})
                default_service_item = frappe.db.get_single_value("Car Workshop Settings", "default_external_service_item")
                if not default_service_item:
                    frappe.throw(_("Please set Default External Service Item in Car Workshop Settings"))
                sinv_item.item_code = default_service_item
                sinv_item.qty = 1
                sinv_item.rate = item.rate
                sinv_item.amount = item.amount
                sinv_item.description = f"External Service: {item.service_name}"

            if self.taxes_and_charges:
                tax_template = frappe.get_doc("Sales Taxes and Charges Template", self.taxes_and_charges)
                for tax in tax_template.taxes:
                    sinv.append("taxes", {
                        "charge_type": tax.charge_type,
                        "account_head": tax.account_head,
                        "description": tax.description,
                        "rate": tax.rate
                    })

            if flt(self.discount_amount) > 0:
                sinv.apply_discount_on = "Grand Total"
                sinv.discount_amount = self.discount_amount

        pref = frappe.db.get_value("Customer", self.customer, "billing_preference") or "Separate"

        if pref == "Consolidate":
            sinv_name = frappe.db.get_value(
                "Sales Invoice",
                {"customer": self.customer, "docstatus": 0, "consolidated_invoice": 1},
                "name",
            )
            sinv = frappe.get_doc("Sales Invoice", sinv_name) if sinv_name else frappe.new_doc("Sales Invoice")
            if not sinv_name:
                sinv.customer = self.customer
                sinv.posting_date = self.posting_date
                sinv.due_date = self.due_date
                sinv.company = self.company
                sinv.cost_center = self.cost_center
                sinv.consolidated_invoice = 1
            append_items(sinv)
            sinv.flags.ignore_permissions = True
            sinv.save()
            self.db_set('sales_invoice', sinv.name)
        else:
            sinv = frappe.new_doc("Sales Invoice")
            sinv.customer = self.customer
            sinv.posting_date = self.posting_date
            sinv.due_date = self.due_date
            sinv.company = self.company
            sinv.cost_center = self.cost_center
            sinv.work_order_billing = self.name
            sinv.work_order = self.work_order
            sinv.customer_vehicle = self.customer_vehicle
            append_items(sinv)
            sinv.flags.ignore_permissions = True
            sinv.flags.ignore_mandatory = True
            sinv.insert()
            sinv.submit()
            self.db_set('sales_invoice', sinv.name)
            if self.payment_amount > 0:
                self.create_payment_entry(sinv.name)
    
    def create_payment_entry(self, sales_invoice):
        """Create a Payment Entry for the received payment"""
        from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
        
        if not self.payment_amount or self.payment_amount <= 0:
            return
            
        # For each payment method
        for payment_detail in self.payment_details:
            if payment_detail.amount <= 0:
                continue
                
            pe = get_payment_entry("Sales Invoice", sales_invoice, 
                                   party_amount=payment_detail.amount, 
                                   bank_account=payment_detail.payment_account)
            
            pe.reference_no = payment_detail.reference_number or self.name
            pe.reference_date = payment_detail.reference_date or self.posting_date
            pe.remarks = f"Payment for Work Order Billing {self.name}"
            pe.mode_of_payment = payment_detail.payment_method
            
            pe.flags.ignore_permissions = True
            pe.save()
            pe.submit()
            
            # Update payment_entry field for the first payment
            if not self.payment_entry:
                self.db_set('payment_entry', pe.name)
    
    def create_down_payment_entry(self):
        """Create advance Payment Entry for down payment"""
        advance_amount = self.get_down_payment_amount()
        if advance_amount <= 0:
            return
        if not self.payment_details:
            frappe.throw(_("Payment details are required for down payment"))
        payment_detail = self.payment_details[0]
        advance_account = frappe.get_cached_value('Company', self.company, 'default_customer_advance_account')
        if not advance_account:
            frappe.throw(_("Please set Default Customer Advance Account in Company settings"))
        pe = frappe.new_doc("Payment Entry")
        pe.payment_type = "Receive"
        pe.party_type = "Customer"
        pe.party = self.customer
        pe.company = self.company
        pe.posting_date = self.posting_date
        pe.mode_of_payment = payment_detail.payment_method
        pe.paid_from = advance_account
        pe.paid_to = payment_detail.payment_account
        pe.received_amount = advance_amount
        pe.paid_amount = advance_amount
        pe.is_advance = "Yes"
        pe.reference_no = self.name
        pe.reference_date = self.posting_date
        pe.remarks = f"Down payment for Work Order Billing {self.name}"
        if self.sales_invoice:
            pe.append("references", {
                "reference_doctype": "Sales Invoice",
                "reference_name": self.sales_invoice,
                "allocated_amount": advance_amount
            })
        pe.flags.ignore_permissions = True
        pe.insert()
        pe.submit()
        if not self.payment_entry:
            self.db_set('payment_entry', pe.name)

    def cancel_linked_documents(self):
        """Cancel linked Sales Invoice and Payment Entry"""
        # Cancel Sales Invoice
        if self.sales_invoice:
            sinv = frappe.get_doc("Sales Invoice", self.sales_invoice)
            if sinv.docstatus == 1:
                sinv.flags.ignore_permissions = True
                sinv.cancel()
                
        # Cancel Payment Entry
        if self.payment_entry:
            pe = frappe.get_doc("Payment Entry", self.payment_entry)
            if pe.docstatus == 1:
                pe.flags.ignore_permissions = True
                pe.cancel()

    def process_returns_and_cancellations(self):
        """Handle returns and cancellations after billing."""
        for item in getattr(self, 'return_items', []) or []:
            self.adjust_stock(item)
            self.issue_credit_note(item)
            self.process_refund(item)
            self.reverse_additional_salary(item)
        for item in getattr(self, 'cancellation_items', []) or []:
            self.issue_debit_note(item)
            self.process_refund(item)
            self.reverse_additional_salary(item)

    def adjust_stock(self, item):
        """Placeholder to adjust stock for returned parts."""
        item.stock_adjusted = True

    def issue_credit_note(self, item):
        item.credit_note_issued = True

    def issue_debit_note(self, item):
        item.debit_note_issued = True

    def process_refund(self, item):
        item.refund_processed = True

    def reverse_additional_salary(self, item):
        item.additional_salary_reversed = True

    def update_approval_fields(self):
        """Populate audit fields when approved."""
        if getattr(self, 'approval_status', None) == "Approved" and not getattr(self, 'approved_by', None):
            self.approved_by = frappe.session.user
            self.approved_on = get_datetime()

    def approve(self, approver=None):
        """Convenience method to approve the billing document."""
        self.approval_status = "Approved"
        self.approved_by = approver or frappe.session.user
        self.approved_on = get_datetime()
    
    def get_dashboard_data(self):
        """Get dashboard data for this document"""
        return {
            'fieldname': 'work_order_billing',
            'non_standard_fieldnames': {
                'Sales Invoice': 'work_order_billing',
                'Payment Entry': 'reference_name'
            },
            'transactions': [
                {
                    'label': _('References'),
                    'items': ['Work Order']
                },
                {
                    'label': _('Payments'),
                    'items': ['Sales Invoice', 'Payment Entry', 'Journal Entry']
                }
            ]
        }

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):
    """Create Sales Invoice from Work Order Billing"""
    from frappe.model.mapper import get_mapped_doc
    
    def set_missing_values(source, target):
        target.is_pos = 0
        target.ignore_pricing_rule = 1
        target.run_method("set_missing_values")
        
    doclist = get_mapped_doc("Work Order Billing", source_name, {
        "Work Order Billing": {
            "doctype": "Sales Invoice",
            "field_map": {
                "name": "work_order_billing",
                "work_order": "work_order",
                "customer_vehicle": "customer_vehicle"
            },
            "validation": {
                "docstatus": ["=", 1]
            }
        }
    }, target_doc, set_missing_values)
    
    return doclist
