import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

class WorkshopPurchaseOrderItem(Document):
    def validate(self):
        self.set_reference_type()
        self.validate_reference()
        self.calculate_amount()
    
    def set_reference_type(self):
        """Set the item_reference_type based on the selected item_type"""
        reference_type_map = {
            "Part": "Part",
            "OPL": "Job Type",
            "Expense": "Expense Type"
        }
        self.item_reference_type = reference_type_map.get(self.item_type, "Part")
    
    def validate_reference(self):
        """Validate that the reference_doctype field is set properly based on item_type"""
        if self.item_type == "Part" and not self.reference_doctype:
            frappe.throw(_("Part reference is required for item type 'Part'"))
        elif self.item_type == "OPL" and not self.reference_doctype:
            frappe.throw(_("Job Type reference is required for item type 'OPL'"))
        elif self.item_type == "Expense" and not self.reference_doctype:
            frappe.throw(_("Expense Type reference is required for item type 'Expense'"))
    
    def calculate_amount(self):
        """Calculate amount based on quantity and rate"""
        self.amount = flt(self.quantity) * flt(self.rate)