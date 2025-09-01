# Copyright (c) 2023, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class WorkOrderBillingExternalService(Document):
    """
    Child DocType for External Service items in Work Order Billing.
    Represents an external service with quantity and rate.
    """
    
    def validate(self) -> None:
        """Validate required fields and values."""
        if not self.service_name:
            frappe.throw(_("Service Name is required"))
            
        if flt(self.quantity) <= 0:
            frappe.throw(_("Quantity must be greater than zero"))
            
        if flt(self.rate) <= 0:
            frappe.throw(_("Rate must be greater than zero"))
    
    def before_save(self) -> None:
        """Calculate amount before saving."""
        self.amount = flt(self.quantity) * flt(self.rate)
        
        # Set cost if supplier provided and cost not already set
        if self.supplier and not flt(self.cost):
            self.set_cost_from_supplier()
    
    def set_cost_from_supplier(self) -> None:
        """
        Set the cost from supplier rate if available.
        This is a placeholder method that could be implemented
        to fetch actual costs from supplier price lists or purchase orders.
        """
        # This is a placeholder implementation
        # In a real scenario, you might fetch this from supplier price lists,
        # purchase orders, or other sources
        
        # For now, we'll just use a simple approach for demonstration
        if hasattr(self, 'parent') and self.parent:
            # Try to find if there's a purchase order or supplier quotation for this service
            purchase_orders = frappe.get_all(
                "Purchase Order Item",
                filters={
                    "item_name": self.service_name,
                    "supplier": self.supplier
                },
                fields=["rate"],
                order_by="creation desc",
                limit=1
            )
            
            if purchase_orders:
                self.cost = flt(purchase_orders[0].rate) * flt(self.quantity)
                return
                
            # If not found in PO, maybe check supplier quotations or other sources
            # This is just a placeholder for demonstration
            
            # As a fallback, set cost to same as rate but this
            # would typically come from actual supplier costs
            if not self.cost:
                self.cost = flt(self.rate) * flt(self.quantity) * 0.8  # 80% of rate as a placeholder