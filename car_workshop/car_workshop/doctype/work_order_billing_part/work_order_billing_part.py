# Copyright (c) 2023, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

from typing import Optional

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class WorkOrderBillingPart(Document):
    """
    Child DocType for Part items in Work Order Billing.
    Represents a billable part with quantity and rate.
    """
    
    def validate(self) -> None:
        """Validate required fields and values."""
        if not self.part:
            frappe.throw(_("Part is required"))
            
        if not self.warehouse:
            frappe.throw(_("Warehouse is required"))
            
        if flt(self.quantity) <= 0:
            frappe.throw(_("Quantity must be greater than zero"))
            
        if flt(self.rate) <= 0:
            # Try to get default rate if not specified
            self.rate = self.get_default_rate() or 0
            if flt(self.rate) <= 0:
                frappe.throw(_("Rate must be greater than zero"))
        
        # Set the cost if not already set
        if not self.cost:
            self.set_part_cost()
    
    def before_save(self) -> None:
        """Calculate amount before saving."""
        self.amount = flt(self.quantity) * flt(self.rate)
    
    def set_part_cost(self) -> None:
        """Set the cost from Part or valuation rate."""
        if not self.part:
            return
            
        # Get the item linked to the part
        item_code = frappe.db.get_value("Part", self.part, "item")
        if not item_code:
            return
            
        # Try to get valuation rate from the item
        valuation_rate = frappe.db.get_value("Item", item_code, "valuation_rate") or 0
        
        # If warehouse is specified, try to get the stock valuation
        if self.warehouse and valuation_rate == 0:
            last_valuation_rate = frappe.db.get_value(
                "Stock Ledger Entry",
                {
                    "item_code": item_code,
                    "warehouse": self.warehouse
                },
                "valuation_rate",
                order_by="posting_date desc, posting_time desc, creation desc"
            )
            
            if last_valuation_rate:
                valuation_rate = last_valuation_rate
        
        # Set the cost
        self.cost = flt(valuation_rate) * flt(self.quantity)
    
    def get_default_rate(self, price_list: Optional[str] = None) -> float:
        """
        Get the default rate for the part from Item Price.
        
        Args:
            price_list: Optional price list to check. If not provided, uses default.
            
        Returns:
            float: The rate found or 0 if not found
        """
        if not self.part:
            return 0
            
        # Get the item linked to the part
        item_code = frappe.db.get_value("Part", self.part, "item")
        if not item_code:
            return 0
            
        if not price_list:
            price_list = frappe.db.get_single_value(
                "Selling Settings", "selling_price_list"
            ) or "Standard Selling"
        
        # Try standard Item Price
        item_prices = frappe.get_all(
            "Item Price",
            filters={
                "item_code": item_code,
                "price_list": price_list
            },
            fields=["price_list_rate"],
            order_by="valid_from desc",
            limit=1
        )
        
        if item_prices:
            return flt(item_prices[0].price_list_rate)
        
        # Last resort, return item standard rate
        return frappe.db.get_value("Item", item_code, "standard_rate") or 0