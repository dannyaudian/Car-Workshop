import frappe
from frappe.model.document import Document
from frappe.utils import flt

class WorkshopPurchaseReceiptItem(Document):
    def validate(self):
        """
        Validate the Workshop Purchase Receipt Item
        """
        self.set_item_reference_type()
        self.validate_received_quantity()
        self.calculate_amount()
        self.set_warehouse_from_parent()
    
    def set_item_reference_type(self):
        """
        Set the correct item_reference_type based on item_type
        """
        reference_type_map = {
            "Part": "Part",
            "OPL": "Job Type",
            "Expense": "Expense Type"
        }
        self.item_reference_type = reference_type_map.get(self.item_type, "Part")
    
    def validate_received_quantity(self):
        """
        Validate that received quantity is positive
        """
        if flt(self.quantity) <= 0:
            frappe.throw(frappe._("Quantity Received must be greater than zero"))
            
        # If we have PO reference and ordered quantity, validate against it
        if self.po_item and self.ordered_qty:
            total_received = flt(self.previously_received_qty) + flt(self.quantity)
            if total_received > flt(self.ordered_qty):
                frappe.throw(frappe._("Total received quantity ({0}) cannot exceed ordered quantity ({1})").format(
                    total_received, self.ordered_qty))
    
    def calculate_amount(self):
        """
        Calculate amount based on quantity and rate
        """
        self.amount = flt(self.quantity) * flt(self.rate)
    
    def set_warehouse_from_parent(self):
        """
        Set warehouse from parent if not specified and parent has warehouse
        """
        if not self.warehouse and hasattr(self, "parent") and self.parent:
            parent_warehouse = frappe.db.get_value("Workshop Purchase Receipt", self.parent, "warehouse")
            if parent_warehouse:
                self.warehouse = parent_warehouse