# Copyright (c) 2025, Danny Audian and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry

# Override the on_cancel method of PaymentEntry
class CustomPaymentEntry(PaymentEntry):
    def on_cancel(self):
        # Call the original on_cancel method first
        super().on_cancel()
        
        # Now handle our custom logic for Workshop Purchase Invoice
        self.update_workshop_purchase_invoices()
    
    def update_workshop_purchase_invoices(self):
        """
        Update Workshop Purchase Invoices when Payment Entry is cancelled:
        - Clear payment_entry field
        - Reset paid_amount to zero
        - Set status back to "Submitted"
        """
        for ref in self.references:
            if ref.reference_doctype != "Workshop Purchase Invoice":
                continue
                
            try:
                # Get the invoice document
                invoice = frappe.get_doc("Workshop Purchase Invoice", ref.reference_name)
                
                # Only update if this payment entry is linked
                if invoice.payment_entry == self.name:
                    frappe.db.set_value("Workshop Purchase Invoice", invoice.name, {
                        "payment_entry": None,
                        "paid_amount": 0,
                        "status": "Submitted"
                    })
                    
                    frappe.msgprint(_("Workshop Purchase Invoice {0} updated").format(invoice.name))
                    
                    # Log the update for audit
                    frappe.log_error(
                        f"Payment Entry {self.name} cancelled - Reset payment fields for {invoice.name}",
                        "Workshop Purchase Invoice Payment Reset"
                    )
            except Exception as e:
                # Log error but don't stop the cancellation process
                frappe.log_error(
                    f"Error updating Workshop Purchase Invoice {ref.reference_name}: {str(e)}",
                    "Payment Entry Cancel Error"
                )