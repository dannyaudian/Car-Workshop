# Copyright (c) 2025, Danny Audian and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class WorkshopPurchaseInvoiceItem(Document):
    """
    Workshop Purchase Invoice Item DocType controller.
    
    This DocType handles the line items for Workshop Purchase Invoices, including:
    - Parts: Items purchased from suppliers for a work order
    - OPL (Outside Processing Labor): External labor services
    - Expenses: Miscellaneous expenses related to a work order
    """
    
    def validate(self):
        """
        Validate the invoice item fields:
        - Ensure required fields based on item_type
        - Validate referenced documents
        - Set default values as needed
        """
        self.validate_required_fields()
        self.validate_referenced_documents()
        self.set_reference_doctype()
    
    def validate_required_fields(self):
        """
        Validate that required fields are set based on item_type
        """
        if not self.item_type:
            frappe.throw(frappe._("Item Type is required"))
            
        if not self.amount or self.amount <= 0:
            frappe.throw(frappe._("Amount must be greater than zero"))
            
        # For Expense items
        if self.item_type == "Expense":
            if not self.work_order:
                frappe.throw(frappe._("Work Order is required for Expense items"))
            
            # Expense items should not have PO or item reference
            if self.purchase_order:
                self.purchase_order = None
                
            if self.item_reference:
                self.item_reference = None
        
        # For Part and OPL items
        elif self.item_type in ["Part", "OPL"]:
            if not self.purchase_order:
                frappe.throw(frappe._("Purchase Order is required for {0} items").format(self.item_type))
                
            if not self.item_reference:
                frappe.throw(frappe._("Item Reference is required for {0} items").format(self.item_type))
    
    def validate_referenced_documents(self):
        """
        Validate that referenced documents exist and have correct status
        """
        # Validate Work Order if specified
        if self.work_order:
            if not frappe.db.exists("Work Order", self.work_order):
                frappe.throw(frappe._("Work Order {0} does not exist").format(self.work_order))
            
            wo_status = frappe.db.get_value("Work Order", self.work_order, "status")
            if wo_status in ["Cancelled", "Closed"]:
                frappe.throw(frappe._("Cannot reference a {0} Work Order").format(wo_status))
        
        # Validate Purchase Order if specified
        if self.purchase_order:
            if not frappe.db.exists("Workshop Purchase Order", self.purchase_order):
                frappe.throw(frappe._("Purchase Order {0} does not exist").format(self.purchase_order))
            
            po_status = frappe.db.get_value("Workshop Purchase Order", self.purchase_order, "status")
            if po_status in ["Cancelled", "Draft"]:
                frappe.throw(frappe._("Cannot reference a {0} Purchase Order").format(po_status))
        
        # Validate Item Reference if specified
        if self.item_reference and self.reference_doctype:
            if not frappe.db.exists(self.reference_doctype, self.item_reference):
                frappe.throw(frappe._("Item Reference {0} does not exist in {1}").format(
                    self.item_reference, self.reference_doctype))
            
            # For Part items, check if item belongs to the specified purchase order
            if self.item_type == "Part" and self.purchase_order:
                parent = frappe.db.get_value(self.reference_doctype, self.item_reference, "parent")
                if parent != self.purchase_order:
                    frappe.throw(frappe._("Item Reference {0} does not belong to Purchase Order {1}").format(
                        self.item_reference, self.purchase_order))
    
    def set_reference_doctype(self):
        """
        Set the reference_doctype field based on the item_type
        """
        if self.item_type == "Part":
            self.reference_doctype = "Workshop Purchase Order Item"
        elif self.item_type == "OPL":
            self.reference_doctype = "Job Type Item"
        else:
            self.reference_doctype = ""
    
    def fetch_details_from_reference(self):
        """
        Fetch details from the referenced document to populate fields
        """
        if not self.item_reference or not self.reference_doctype:
            return
            
        try:
            # Get the referenced document
            doc = frappe.get_doc(self.reference_doctype, self.item_reference)
            
            # Set description and amount based on item type
            if self.item_type == "Part":
                self.description = doc.description or doc.item_name or ""
                self.amount = doc.amount or 0
                
                # Get the work order from the purchase order if not set
                if not self.work_order and self.purchase_order:
                    self.work_order = frappe.db.get_value("Workshop Purchase Order", 
                                                          self.purchase_order, 
                                                          "work_order")
            
            elif self.item_type == "OPL":
                self.description = doc.description or doc.service_name or ""
                self.amount = doc.amount or doc.price or 0
                
                # Get the work order from the purchase order if not set
                if not self.work_order and self.purchase_order:
                    self.work_order = frappe.db.get_value("Workshop Purchase Order", 
                                                          self.purchase_order, 
                                                          "work_order")
        
        except Exception as e:
            frappe.log_error(f"Error fetching reference details: {str(e)}", 
                           "Workshop Purchase Invoice Item")
    
    def on_update(self):
        """
        Actions to perform when the document is updated
        """
        # If description is empty, try to get it from the item type or reference
        if not self.description:
            if self.item_type == "Expense" and self.work_order:
                wo_desc = frappe.db.get_value("Work Order", self.work_order, "description")
                self.description = f"Expense for WO: {wo_desc}" if wo_desc else "Expense"
            elif self.item_reference and self.reference_doctype:
                self.fetch_details_from_reference()