# Copyright (c) 2023, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class WorkOrderBillingPayment(Document):
    """
    Child DocType for Payment information in Work Order Billing.
    This is for information only - no Payment Entry is created.
    Actual payments will be processed through the Sales Invoice.
    """
    
    def validate(self) -> None:
        """Validate payment information."""
        # Ensure amount is not negative
        if flt(self.amount) < 0:
            frappe.throw(_("Payment amount cannot be negative"))
            
        # Require payment account if amount is provided
        if flt(self.amount) > 0 and not self.payment_account:
            frappe.throw(_("Payment Account is required when an amount is specified"))
            
        # Validate payment method is selected
        if not self.payment_method:
            frappe.throw(_("Payment Method is required"))
            
        # If reference number is provided, ensure it's properly formatted
        if self.reference_number:
            # Remove any leading/trailing whitespace
            self.reference_number = self.reference_number.strip()
            
        # If reference date is provided, ensure it's not in the future
        if self.reference_date and self.reference_date > frappe.utils.nowdate():
            frappe.msgprint(
                _("Reference Date is in the future. Please verify if this is correct."),
                indicator="orange",
                alert=True
            )