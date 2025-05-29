import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, now_datetime
import json

class WorkshopPurchaseOrder(Document):
    def validate(self):
        """
        Validate the Workshop Purchase Order before saving
        """
        self.validate_dates()
        self.validate_items()
        self.validate_tax_settings()
        self.calculate_totals()
        
    def validate_dates(self):
        """
        Validate transaction date and expected delivery date
        """
        if self.expected_delivery and getdate(self.expected_delivery) < getdate(self.transaction_date):
            frappe.throw(_("Expected Delivery Date cannot be before Transaction Date"))
            
    def validate_items(self):
        """
        Validate that items table is not empty and all items have required fields
        """
        if not self.items:
            frappe.throw(_("Items cannot be empty"))
            
        for item in self.items:
            # Validate item has quantity and rate
            if flt(item.quantity) <= 0:
                frappe.throw(_("Row {0}: Quantity must be greater than zero").format(item.idx))
                
            if flt(item.rate) < 0:
                frappe.throw(_("Row {0}: Rate cannot be negative").format(item.idx))
                
            # Calculate amount if not set
            if not item.amount:
                item.amount = flt(item.quantity) * flt(item.rate)
                
            # Check reference based on item type
            if item.item_type == "Part" and not item.reference_doctype:
                frappe.throw(_("Row {0}: Part reference is required for Part items").format(item.idx))
                
            elif item.item_type == "OPL" and not item.reference_doctype:
                frappe.throw(_("Row {0}: Job Type reference is required for OPL items").format(item.idx))
                
            elif item.item_type == "Expense" and not item.reference_doctype:
                frappe.throw(_("Row {0}: Expense Type reference is required for Expense items").format(item.idx))
                
            # Validate work_order is set if item is billable
            if cint(item.billable) == 1 and not self.work_order:
                frappe.throw(_("Row {0}: Work Order is required for billable items").format(item.idx))
                
    def validate_tax_settings(self):
        """
        Validate tax settings and propagate default tax template if needed
        """
        # Apply default tax template to items if configured
        if hasattr(self, 'apply_default_tax_to_all_items') and cint(self.apply_default_tax_to_all_items) == 1:
            if not self.default_tax_template:
                frappe.throw(_("Default Tax Template must be specified when 'Apply Default Tax to All Items' is checked"))
                
            # Apply default tax to all items that use default tax
            for item in self.items:
                if hasattr(item, 'use_default_tax') and cint(item.use_default_tax) == 1:
                    item.tax_template = self.default_tax_template
        
        # Validate item-level tax settings
        for item in self.items:
            if hasattr(item, 'use_default_tax') and cint(item.use_default_tax) == 0:
                if not item.tax_template:
                    frappe.throw(_("Row {0}: Tax Template is required when 'Use Default Tax' is unchecked").format(item.idx))
    
    def calculate_totals(self):
        """
        Calculate total amount for the purchase order
        """
        self.total_amount = sum(flt(item.amount) for item in self.items)
        
        # Calculate billable amount
        self.billable_amount = sum(flt(item.amount) for item in self.items if cint(item.billable) == 1)
        
        # Calculate non-billable amount
        self.non_billable_amount = self.total_amount - self.billable_amount
        
        # Calculate tax totals
        tax_summary = self.get_tax_templates_summary()
        if hasattr(self, 'tax_summary'):
            self.tax_summary = json.dumps(tax_summary)
        
    def get_tax_templates_summary(self):
        """
        Calculate tax summary based on items and their tax templates
        
        Returns:
            dict: Summary of tax amounts by tax template
        """
        tax_summary = {}
        
        # Process each item
        for item in self.items:
            # Determine which tax template to use
            tax_template = None
            if hasattr(item, 'use_default_tax') and cint(item.use_default_tax) == 1:
                tax_template = self.default_tax_template
            elif hasattr(item, 'tax_template'):
                tax_template = item.tax_template
            
            if not tax_template:
                continue
                
            # Get tax template details if not already cached
            if tax_template not in tax_summary:
                tax_summary[tax_template] = {
                    "template_name": tax_template,
                    "tax_details": self._get_tax_template_details(tax_template),
                    "taxable_amount": 0,
                    "tax_amount": 0
                }
            
            # Add to taxable amount
            tax_summary[tax_template]["taxable_amount"] += flt(item.amount)
            
            # Calculate tax amount
            item_tax_amount = self._calculate_item_tax_amount(item.amount, tax_summary[tax_template]["tax_details"])
            tax_summary[tax_template]["tax_amount"] += item_tax_amount
        
        return tax_summary
    
    def _get_tax_template_details(self, tax_template):
        """
        Get tax rates and details from a tax template
        
        Args:
            tax_template (str): Name of the tax template
            
        Returns:
            list: List of tax details with rates and calculation methods
        """
        tax_details = []
        
        # Get tax template details from Purchase Taxes and Charges Template
        if tax_template:
            taxes = frappe.get_all(
                "Purchase Taxes and Charges",
                filters={"parent": tax_template},
                fields=["charge_type", "rate", "account_head", "description"],
                order_by="idx"
            )
            
            tax_details = taxes
        
        return tax_details
    
    def _calculate_item_tax_amount(self, amount, tax_details):
        """
        Calculate tax amount for an item based on tax details
        
        Args:
            amount (float): Item amount
            tax_details (list): List of tax details
            
        Returns:
            float: Total tax amount
        """
        total_tax = 0
        
        # Simple tax calculation based on rate - can be extended for more complex scenarios
        for tax in tax_details:
            if tax.get("charge_type") == "On Net Total":
                tax_amount = flt(amount) * flt(tax.get("rate", 0)) / 100
                total_tax += tax_amount
            
            # Add other charge types as needed
        
        return total_tax
        
    def before_submit(self):
        """
        Perform validations before submitting the document
        """
        # Validate source type and supplier
        if self.order_source == "Beli Baru" and not self.supplier:
            frappe.throw(_("Supplier is mandatory when Order Source is 'Beli Baru'"))
            
        # Validate work order exists if specified
        if self.work_order:
            if not frappe.db.exists("Work Order", self.work_order):
                frappe.throw(_("Work Order {0} does not exist").format(self.work_order))
                
        # Validate no duplicate items for the same work order
        self.validate_duplicate_items()
        
        # Set status to Submitted
        self.status = "Submitted"
        
        # Validate items match purchase type
        self.validate_items_match_purchase_type()
        
        # Validate tax settings before submission
        self.validate_tax_settings()
        
    def validate_items_match_purchase_type(self):
        """
        Validate that all items match the purchase type
        """
        if self.purchase_type == "Part":
            for item in self.items:
                if item.item_type != "Part":
                    frappe.throw(_("Row {0}: Item type must be 'Part' for Purchase Type 'Part'").format(item.idx))
                    
        elif self.purchase_type == "OPL":
            for item in self.items:
                if item.item_type != "OPL":
                    frappe.throw(_("Row {0}: Item type must be 'OPL' for Purchase Type 'OPL'").format(item.idx))
                    
        elif self.purchase_type == "Expense":
            for item in self.items:
                if item.item_type != "Expense":
                    frappe.throw(_("Row {0}: Item type must be 'Expense' for Purchase Type 'Expense'").format(item.idx))
    
    def validate_duplicate_items(self):
        """
        Ensure no active PO exists with same Work Order + reference_doctype + item_type + billable flag
        """
        if not self.work_order:
            return
            
        for item in self.items:
            # Check for duplicates only if reference is specified
            if not item.reference_doctype:
                continue
                
            # Construct filter conditions
            filters = {
                "docstatus": 1,  # Submitted
                "work_order": self.work_order,
                "status": ["!=", "Cancelled"]
            }
            
            # Check if there's another PO with the same work order and matching items
            duplicate_pos = frappe.get_all(
                "Workshop Purchase Order",
                filters=filters,
                fields=["name"]
            )
            
            if not duplicate_pos:
                continue
                
            # For each potential duplicate PO, check the items
            for po in duplicate_pos:
                if po.name == self.name:
                    continue  # Skip current document
                    
                # Get items from the potential duplicate PO
                duplicate_items = frappe.get_all(
                    "Workshop Purchase Order Item",
                    filters={
                        "parent": po.name,
                        "item_type": item.item_type,
                        "reference_doctype": item.reference_doctype,
                        "billable": item.billable
                    },
                    fields=["name", "parent"]
                )
                
                if duplicate_items:
                    frappe.throw(_(
                        "Duplicate item found in Purchase Order {0}. "
                        "Item Type: {1}, Reference: {2}, Billable: {3}"
                    ).format(
                        po.name,
                        item.item_type,
                        item.reference_doctype,
                        "Yes" if cint(item.billable) == 1 else "No"
                    ))
    
    def on_submit(self):
        """
        Actions to perform when the document is submitted
        """
        # Update the Work Order with PO information
        if self.work_order:
            self.update_work_order()
            
        # Auto-create Purchase Invoice if auto_invoice is enabled
        if hasattr(self, 'auto_invoice') and cint(self.auto_invoice) == 1:
            self.create_purchase_invoice()
            
        # Log submission for audit trail
        self.log_document_event("Submitted")
            
    def update_work_order(self):
        """
        Update the linked Work Order with PO information
        """
        if not self.work_order:
            return
            
        work_order = frappe.get_doc("Work Order", self.work_order)
        
        # Track if any updates were made
        updated = False
        
        if self.purchase_type == "Part":
            for po_item in self.items:
                if po_item.item_type == "Part" and po_item.reference_doctype:
                    for wo_part in work_order.part_detail:
                        if wo_part.part == po_item.reference_doctype and not wo_part.purchase_order:
                            wo_part.purchase_order = self.name
                            wo_part.po_rate = po_item.rate
                            updated = True
        
        elif self.purchase_type == "OPL":
            for po_item in self.items:
                if po_item.item_type == "OPL" and po_item.reference_doctype:
                    for wo_job in work_order.job_type_detail:
                        if wo_job.job_type == po_item.reference_doctype and wo_job.is_opl and not wo_job.purchase_order:
                            wo_job.purchase_order = self.name
                            wo_job.vendor_rate = po_item.rate
                            updated = True
        
        # Only save if updates were made
        if updated:
            work_order.save(ignore_permissions=True)
            frappe.msgprint(_("Work Order {0} has been updated with Purchase Order details").format(self.work_order))
    
    def create_purchase_invoice(self):
        """
        Queue creation of a draft Purchase Invoice for billable items
        """
        # Only proceed if we have billable items
        billable_items = [item for item in self.items if cint(item.billable) == 1]
        if not billable_items:
            return
            
        # Check if supplier is set
        if not self.supplier:
            frappe.msgprint(_("Cannot create Purchase Invoice without Supplier"))
            return
            
        # Create a background job to generate the invoice
        frappe.enqueue(
            method=self._create_purchase_invoice,
            queue="long",
            timeout=600,
            now=frappe.flags.in_test
        )
        
        frappe.msgprint(_("Purchase Invoice creation has been queued"))
    
    def _create_purchase_invoice(self):
        """
        Actual creation of Purchase Invoice (called via background job)
        """
        try:
            # Create a new Purchase Invoice
            invoice = frappe.new_doc("Purchase Invoice")
            invoice.supplier = self.supplier
            invoice.posting_date = getdate()
            invoice.due_date = self.expected_delivery or getdate()
            invoice.workshop_purchase_order = self.name
            
            # Add Work Order reference if available
            if self.work_order:
                invoice.work_order_reference = self.work_order
                
            # Set default tax template if available
            if hasattr(self, 'default_tax_template') and self.default_tax_template:
                invoice.taxes_and_charges = self.default_tax_template
            
            # Add items to the invoice
            for item in self.items:
                if cint(item.billable) != 1:
                    continue
                    
                # Get the Item Code based on the reference
                item_code = self._get_item_code_for_reference(item)
                if not item_code:
                    continue
                    
                # Add item to the invoice
                invoice_item = invoice.append("items", {
                    "item_code": item_code,
                    "qty": item.quantity,
                    "rate": item.rate,
                    "description": item.description or f"{item.item_type}: {item.reference_doctype}",
                    "uom": item.uom or "Nos",
                    "conversion_factor": 1.0,
                    "workshop_purchase_order": self.name,
                    "workshop_purchase_order_item": item.name
                })
                
                # Set item-specific tax template if different from default
                if hasattr(item, 'use_default_tax') and cint(item.use_default_tax) == 0 and hasattr(item, 'tax_template') and item.tax_template:
                    # Handle item-specific tax templates if Purchase Invoice supports this
                    # This might require custom fields on Purchase Invoice Item
                    if hasattr(invoice_item, 'item_tax_template'):
                        invoice_item.item_tax_template = item.tax_template
            
            # Add taxes if available
            if hasattr(self, 'default_tax_template') and self.default_tax_template:
                # This is a simplified approach. For complex scenarios with per-item tax templates,
                # you might need custom logic to merge tax templates or apply them differently
                tax_template_doc = frappe.get_doc("Purchase Taxes and Charges Template", self.default_tax_template)
                for tax in tax_template_doc.taxes:
                    invoice.append("taxes", {
                        "charge_type": tax.charge_type,
                        "account_head": tax.account_head,
                        "description": tax.description,
                        "rate": tax.rate
                    })
            
            # Save the invoice as draft
            invoice.flags.ignore_permissions = True
            invoice.save()
            
            frappe.msgprint(_("Purchase Invoice {0} has been created").format(invoice.name))
            
        except Exception as e:
            frappe.log_error(
                message=f"Error creating Purchase Invoice from Workshop Purchase Order {self.name}: {str(e)}",
                title="Purchase Invoice Creation Error"
            )
            
    def _get_item_code_for_reference(self, item):
        """
        Get the Item Code from the reference document
        """
        try:
            if item.item_type == "Part":
                # Get the item_code from Part
                return frappe.db.get_value("Part", item.reference_doctype, "item_code")
                
            elif item.item_type == "OPL":
                # For OPL, we might need a service item
                return frappe.db.get_value("Job Type", item.reference_doctype, "item_code") or "Service-OPL"
                
            elif item.item_type == "Expense":
                # For expense, use a default expense item
                return "Workshop-Expense"
                
        except Exception as e:
            frappe.log_error(
                message=f"Error getting item code for {item.item_type} reference {item.reference_doctype}: {str(e)}",
                title="Item Code Lookup Error"
            )
            
        return None
    
    def before_cancel(self):
        """
        Perform validations before canceling the document
        """
        # Check if the PO is already linked to a submitted Purchase Invoice
        pi_list = frappe.get_all(
            "Purchase Invoice",
            filters={
                "workshop_purchase_order": self.name,
                "docstatus": 1  # Submitted
            },
            fields=["name"]
        )
        
        if pi_list:
            pi_links = ", ".join([f'<a href="/app/purchase-invoice/{pi.name}">{pi.name}</a>' for pi in pi_list])
            frappe.throw(_(
                "Cannot cancel as this Purchase Order is linked to submitted Purchase Invoice(s): {0}"
            ).format(pi_links))
            
    def on_cancel(self):
        """
        Actions to perform when the document is cancelled
        """
        # Set status to Cancelled
        self.status = "Cancelled"
        
        # Remove links from Work Order
        if self.work_order:
            self.remove_from_work_order()
            
        # Unlink items from any pending invoice
        self.unlink_from_invoices()
        
        # Log cancellation for audit trail
        self.log_document_event("Cancelled")
    
    def remove_from_work_order(self):
        """
        Remove PO references from the linked Work Order
        """
        if not self.work_order:
            return
            
        work_order = frappe.get_doc("Work Order", self.work_order)
        
        # Track if any updates were made
        updated = False
        
        if self.purchase_type == "Part":
            for wo_part in work_order.part_detail:
                if wo_part.purchase_order == self.name:
                    wo_part.purchase_order = None
                    wo_part.po_rate = 0
                    updated = True
        
        elif self.purchase_type == "OPL":
            for wo_job in work_order.job_type_detail:
                if wo_job.purchase_order == self.name:
                    wo_job.purchase_order = None
                    wo_job.vendor_rate = 0
                    updated = True
        
        # Only save if updates were made
        if updated:
            work_order.save(ignore_permissions=True)
            frappe.msgprint(_("Work Order {0} has been updated").format(self.work_order))
    
    def unlink_from_invoices(self):
        """
        Unlink child items from any pending invoice
        """
        # Find draft Purchase Invoices linked to this PO
        draft_invoices = frappe.get_all(
            "Purchase Invoice",
            filters={
                "workshop_purchase_order": self.name,
                "docstatus": 0  # Draft
            },
            fields=["name"]
        )
        
        for invoice in draft_invoices:
            pi_doc = frappe.get_doc("Purchase Invoice", invoice.name)
            
            # Find items linked to this PO and remove them
            items_to_remove = []
            for i, item in enumerate(pi_doc.items):
                if getattr(item, "workshop_purchase_order", "") == self.name:
                    items_to_remove.append(item)
            
            # Remove the items
            for item in items_to_remove:
                pi_doc.remove(item)
            
            # If no items left, delete the invoice
            if not pi_doc.items:
                frappe.delete_doc("Purchase Invoice", pi_doc.name, ignore_permissions=True)
                frappe.msgprint(_("Empty Purchase Invoice {0} has been deleted").format(pi_doc.name))
            else:
                # Otherwise save the updated invoice
                pi_doc.save(ignore_permissions=True)
                frappe.msgprint(_("Purchase Invoice {0} has been updated").format(pi_doc.name))
    
    def log_document_event(self, event_type):
        """
        Log document events for audit trail
        """
        log_data = {
            "doctype": "Workshop Purchase Order",
            "document": self.name,
            "event": event_type,
            "timestamp": now_datetime(),
            "user": frappe.session.user,
            "data": json.dumps({
                "supplier": self.supplier,
                "work_order": self.work_order,
                "purchase_type": self.purchase_type,
                "total_amount": self.total_amount
            })
        }
        
        # If we have a custom DocType for activity logging
        if frappe.db.exists("DocType", "Workshop Activity Log"):
            frappe.get_doc({
                "doctype": "Workshop Activity Log",
                **log_data
            }).insert(ignore_permissions=True)
        else:
            # Otherwise use Frappe's built-in logging
            frappe.log_error(
                message=f"Workshop Purchase Order {self.name} - {event_type}",
                title=f"Workshop PO {event_type}"
            )

@frappe.whitelist()
def make_purchase_invoice(source_name, target_doc=None):
    """
    Create a Purchase Invoice from Workshop Purchase Order
    """
    from frappe.model.mapper import get_mapped_doc
    
    def postprocess(source, target):
        target.supplier = source.supplier
        
        # Set supplier invoice details if available
        target.bill_no = ""
        target.bill_date = frappe.utils.today()
        
        # Only include billable items
        target.items = [item for item in target.items if item.billable]
        
        # Set default tax template if available
        if hasattr(source, 'default_tax_template') and source.default_tax_template:
            target.taxes_and_charges = source.default_tax_template
            
            # Copy taxes from template
            tax_template_doc = frappe.get_doc("Purchase Taxes and Charges Template", source.default_tax_template)
            for tax in tax_template_doc.taxes:
                target.append("taxes", {
                    "charge_type": tax.charge_type,
                    "account_head": tax.account_head,
                    "description": tax.description,
                    "rate": tax.rate
                })
        
        # Calculate totals
        for item in target.items:
            item.amount = item.qty * item.rate
            
    def update_item(source_doc, target_doc, source_parent):
        # Get the Item Code based on the reference
        item_code = get_item_code_for_reference(source_doc)
        if item_code:
            target_doc.item_code = item_code
            
        target_doc.qty = source_doc.quantity
        target_doc.rate = source_doc.rate
        target_doc.amount = source_doc.amount
        target_doc.workshop_purchase_order = source_parent.name
        target_doc.workshop_purchase_order_item = source_doc.name
        target_doc.description = source_doc.description or f"{source_doc.item_type}: {source_doc.reference_doctype}"
        
        # Handle item-specific tax template if available
        if hasattr(source_doc, 'use_default_tax') and hasattr(source_doc, 'tax_template'):
            if cint(source_doc.use_default_tax) == 0 and source_doc.tax_template:
                # Set item-specific tax template if Purchase Invoice Item supports it
                if hasattr(target_doc, 'item_tax_template'):
                    target_doc.item_tax_template = source_doc.tax_template
        
    def get_item_code_for_reference(item):
        """Get the Item Code from the reference document"""
        try:
            if item.item_type == "Part":
                # Get the item_code from Part
                return frappe.db.get_value("Part", item.reference_doctype, "item_code")
                
            elif item.item_type == "OPL":
                # For OPL, we might need a service item
                return frappe.db.get_value("Job Type", item.reference_doctype, "item_code") or "Service-OPL"
                
            elif item.item_type == "Expense":
                # For expense, use a default expense item
                return "Workshop-Expense"
                
        except Exception as e:
            frappe.log_error(
                message=f"Error getting item code for {item.item_type} reference {item.reference_doctype}: {str(e)}",
                title="Item Code Lookup Error"
            )
            
        return None
    
    doclist = get_mapped_doc("Workshop Purchase Order", source_name, {
        "Workshop Purchase Order": {
            "doctype": "Purchase Invoice",
            "field_map": {
                "name": "workshop_purchase_order",
                "work_order": "work_order_reference",
                "transaction_date": "posting_date",
                "default_tax_template": "taxes_and_charges"
            },
            "validation": {
                "docstatus": ["=", 1]  # Only submitted POs
            }
        },
        "Workshop Purchase Order Item": {
            "doctype": "Purchase Invoice Item",
            "field_map": {
                "name": "workshop_purchase_order_item",
                "reference_doctype": "workshop_reference_doctype",
                "item_type": "workshop_item_type",
                "tax_template": "item_tax_template"
            },
            "postprocess": update_item,
            "condition": lambda doc: doc.billable
        }
    }, target_doc, postprocess)
    
    return doclist

@frappe.whitelist()
def check_duplicate_po(work_order, item_type, reference_doctype, current_po=None):
    """
    Check if an item in a work order already has an active purchase order
    """
    # Skip for new POs with no name yet
    if current_po == "new":
        current_po = None
        
    # Construct filter conditions
    filters = {
        "docstatus": 1,  # Submitted
        "work_order": work_order,
        "status": ["!=", "Cancelled"]
    }
    
    if current_po:
        filters["name"] = ["!=", current_po]
    
    # Get all active POs for this work order
    purchase_orders = frappe.get_all(
        "Workshop Purchase Order",
        filters=filters,
        fields=["name"]
    )
    
    # If no POs found, no duplicates
    if not purchase_orders:
        return {"exists": False}
    
    # For each PO, check for matching items
    for po in purchase_orders:
        # Check for matching items
        item_filters = {
            "parent": po.name,
            "item_type": item_type,
            "reference_doctype": reference_doctype
        }
        
        duplicate_items = frappe.get_all(
            "Workshop Purchase Order Item",
            filters=item_filters,
            fields=["name", "parent"]
        )
        
        if duplicate_items:
            return {
                "exists": True,
                "po_number": po.name
            }
    
    return {"exists": False}

@frappe.whitelist()
def fetch_work_order_items(work_order, fetch_parts=0, fetch_opl=0, fetch_expenses=0, 
                          only_without_po=1, filter_text="", current_po=None):
    """
    Fetch items from a work order based on filter criteria
    """
    if not work_order:
        return {"error": "Work Order is required"}
    
    # Convert string arguments to boolean/integer
    fetch_parts = int(fetch_parts)
    fetch_opl = int(fetch_opl)
    fetch_expenses = int(fetch_expenses)
    only_without_po = int(only_without_po)
    
    # Get the work order document
    try:
        work_order_doc = frappe.get_doc("Work Order", work_order)
    except Exception as e:
        frappe.log_error(f"Error fetching Work Order {work_order}: {str(e)}")
        return {"error": f"Error fetching Work Order: {str(e)}"}
    
    result = {}
    
    # Fetch parts if requested
    if fetch_parts and hasattr(work_order_doc, "part_detail"):
        parts = []
        for part in work_order_doc.part_detail:
            # Skip if filtering by PO and part already has one
            if only_without_po and part.purchase_order and part.purchase_order != current_po:
                continue
                
            # Apply text filter if provided
            if filter_text and filter_text.lower() not in (part.part or "").lower() and filter_text.lower() not in (part.part_name or "").lower():
                continue
                
            parts.append({
                "part": part.part,
                "part_name": part.part_name,
                "quantity": part.quantity,
                "rate": part.rate,
                "amount": part.amount
            })
        
        result["parts"] = parts
    
    # Fetch OPL jobs if requested
    if fetch_opl and hasattr(work_order_doc, "job_type_detail"):
        opl_jobs = []
        for job in work_order_doc.job_type_detail:
            # Only include OPL jobs
            if not job.is_opl:
                continue
                
            # Skip if filtering by PO and job already has one
            if only_without_po and job.purchase_order and job.purchase_order != current_po:
                continue
                
            # Apply text filter if provided
            if filter_text and filter_text.lower() not in (job.job_type or "").lower() and filter_text.lower() not in (job.description or "").lower():
                continue
                
            opl_jobs.append({
                "job_type": job.job_type,
                "description": job.description,
                "price": job.price
            })
        
        result["opl_jobs"] = opl_jobs
    
    # Fetch expenses if requested
    if fetch_expenses and hasattr(work_order_doc, "external_expense"):
        expenses = []
        for expense in work_order_doc.external_expense:
            # Skip if filtering by PO and expense already has one
            if only_without_po and expense.purchase_order and expense.purchase_order != current_po:
                continue
                
            # Apply text filter if provided
            if filter_text and filter_text.lower() not in (expense.expense_type or "").lower() and filter_text.lower() not in (expense.description or "").lower():
                continue
                
            expenses.append({
                "expense_type": expense.expense_type,
                "description": expense.description,
                "amount": expense.amount
            })
        
        result["expenses"] = expenses
    
    return result

@frappe.whitelist()
def generate_receipt(purchase_order):
    """
    Generate a Workshop Purchase Receipt document from a submitted Purchase Order.
    Only items with type 'Part' will be included in the receipt.
    
    Args:
        purchase_order (str): The name of the Workshop Purchase Order
        
    Returns:
        str: The name of the generated Workshop Purchase Receipt
        
    Raises:
        frappe.ValidationError: If the Purchase Order is not submitted
    """
    # Validate that purchase order exists and is submitted
    if not frappe.db.exists("Workshop Purchase Order", purchase_order):
        frappe.throw(_("Purchase Order {0} does not exist").format(purchase_order))
        
    po_doc = frappe.get_doc("Workshop Purchase Order", purchase_order)
    
    if po_doc.docstatus != 1:
        frappe.throw(_("Purchase Order {0} must be submitted to generate a receipt").format(purchase_order))
    
    # Get default warehouse from Stock Settings
    default_warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")
    
    # Create a new receipt
    receipt = frappe.new_doc("Workshop Purchase Receipt")
    receipt.purchase_order = purchase_order
    receipt.supplier = po_doc.supplier
    receipt.receipt_date = frappe.utils.nowdate()
    receipt.warehouse = default_warehouse
    
    # Add only Part items to the receipt
    part_count = 0
    for po_item in po_doc.items:
        if po_item.item_type == "Part":
            # Determine the reference type
            item_reference_type = "Part"
            
            # Add the item to the receipt
            receipt.append("items", {
                "item_type": po_item.item_type,
                "reference_doctype": po_item.reference_doctype,
                "description": po_item.description or po_item.reference_doctype,
                "quantity": po_item.quantity,
                "uom": po_item.uom or "Nos",
                "rate": po_item.rate,
                "amount": po_item.amount,
                "warehouse": default_warehouse,
                "po_item": po_item.name,
                "ordered_qty": po_item.quantity,
                "previously_received_qty": 0,
                "item_reference_type": item_reference_type
            })
            part_count += 1
    
    if part_count == 0:
        frappe.throw(_("No Part items found in Purchase Order {0}").format(purchase_order))
    
    # Save the receipt
    receipt.insert(ignore_permissions=True)
    
    frappe.msgprint(_("Workshop Purchase Receipt {0} has been created with {1} part items").format(
        receipt.name, part_count))
    
    return receipt.name

@frappe.whitelist()
def get_dashboard_data(data):
    """
    Get dashboard data for the Workshop Purchase Order
    """
    data = frappe._dict(data)
    data.transactions = [
        {
            'label': _('Related Documents'),
            'items': ['Workshop Purchase Receipt', 'Purchase Invoice', 'Stock Entry']
        }
    ]
    
    return data