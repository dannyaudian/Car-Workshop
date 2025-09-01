# Copyright (c) 2023, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class WorkOrderBillingReturn(Document):
    """
    Child DocType for Return entries in Work Order Billing.
    Represents a returned part with a negative amount.
    No stock or GL posting happens here - returns will be handled
    during Sales Return/Credit Note creation from SI stage.
    """
    
    def validate(self) -> None:
        """Validate required fields and values."""
        if not self.part_item:
            frappe.throw(_("Part Item is required"))
            
        if flt(self.quantity) <= 0:
            frappe.throw(_("Return Quantity must be greater than zero"))
            
        if flt(self.rate) <= 0:
            frappe.throw(_("Rate must be greater than zero"))
            
        if not self.reason or not self.reason.strip():
            frappe.throw(_("Return Reason is required"))
            
        # Ensure the part_item exists and belongs to the parent document
        self.validate_part_item()
    
    def before_save(self) -> None:
        """Calculate amount as a negative value before saving."""
        # Store as negative amount to represent a return
        self.amount = -abs(flt(self.quantity) * flt(self.rate))
    
    def validate_part_item(self) -> None:
        """
        Validate that the referenced part_item exists and belongs to the parent document.
        """
        if not hasattr(self, 'parent') or not self.parent:
            return
            
        # Check if the part_item exists in parent's part_items table
        part_items = frappe.get_all(
            "Work Order Billing Part",
            filters={"parent": self.parent, "name": self.part_item},
            fields=["name", "quantity"]
        )
        
        if not part_items:
            frappe.throw(_("The selected Part Item does not belong to this Work Order Billing"))
            
        # Check if return quantity exceeds original quantity
        if part_items and flt(self.quantity) > flt(part_items[0].quantity):
            frappe.throw(
                _("Return Quantity ({0}) cannot exceed original quantity ({1})").format(
                    self.quantity, part_items[0].quantity
                )
            )