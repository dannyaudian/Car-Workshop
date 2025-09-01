# Copyright (c) 2023, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class WorkOrderBillingCancellation(Document):
    """
    Child DocType for Cancellation entries in Work Order Billing.
    Represents a cancelled or adjusted item with a negative amount.
    """
    
    def validate(self) -> None:
        """Validate required fields and values."""
        if not self.linked_row_type:
            frappe.throw(_("Item Type is required"))
            
        if not self.linked_row_name:
            frappe.throw(_("Item Reference is required"))
            
        if flt(self.quantity) <= 0:
            frappe.throw(_("Quantity must be greater than zero"))
            
        if flt(self.rate) <= 0:
            frappe.throw(_("Rate must be greater than zero"))
            
        if not self.reason or not self.reason.strip():
            frappe.throw(_("Reason for cancellation is required"))
    
    def before_save(self) -> None:
        """Calculate amount as a negative value before saving."""
        # Store as negative amount to represent a deduction
        self.amount = -abs(flt(self.quantity) * flt(self.rate))
    
    def get_option_mapping(self) -> dict:
        """
        Get the mapping between linked_row_type options and actual doctypes.
        
        Returns:
            dict: Mapping of option values to doctype names
        """
        return {
            "Job Type": "Work Order Billing Job Type",
            "Service Package": "Work Order Billing Service Package",
            "Part": "Work Order Billing Part",
            "External Service": "Work Order Billing External Service"
        }