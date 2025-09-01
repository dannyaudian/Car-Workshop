# Copyright (c) 2023, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

from typing import Optional

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class WorkOrderBillingJobType(Document):
    """
    Child DocType for Job Type items in Work Order Billing.
    This represents a billable service with hours and rate.
    """
    
    def validate(self) -> None:
        """Validate required fields and values."""
        if not self.job_type:
            frappe.throw(_("Job Type is required"))
            
        if flt(self.hours) <= 0:
            frappe.throw(_("Hours must be greater than zero"))
            
        if flt(self.rate) <= 0:
            # Try to get default rate if not specified
            self.rate = self.get_default_rate() or 0
            if flt(self.rate) <= 0:
                frappe.throw(_("Rate must be greater than zero"))
    
    def before_save(self) -> None:
        """Calculate amount before saving."""
        self.amount = flt(self.hours) * flt(self.rate)
    
    def get_default_rate(self, price_list: Optional[str] = None, date: Optional[str] = None) -> float:
        """
        Get the default rate for the job type from Item Price or Service Price List.
        
        Args:
            price_list: Optional price list to check. If not provided, uses default.
            date: Optional date for price validity. If not provided, uses current date.
            
        Returns:
            float: The rate found or 0 if not found
        """
        if not self.job_type:
            return 0
            
        # Get the item linked to the job type
        item_code = frappe.db.get_value("Job Type", self.job_type, "item")
        if not item_code:
            return 0
            
        if not price_list:
            price_list = frappe.db.get_single_value(
                "Selling Settings", "selling_price_list"
            ) or "Standard Selling"
        
        # First try standard Item Price
        filters = {
            "item_code": item_code,
            "price_list": price_list
        }
        
        if date:
            filters["valid_from"] = ["<=", date]
        
        item_prices = frappe.get_all(
            "Item Price",
            filters=filters,
            fields=["price_list_rate"],
            order_by="valid_from desc",
            limit=1
        )
        
        if item_prices:
            return flt(item_prices[0].price_list_rate)
        
        # Fallback to Service Price List if it exists
        if frappe.db.exists("DocType", "Service Price List"):
            service_prices = frappe.get_all(
                "Service Price List",
                filters={
                    "item": item_code,
                    "price_list": price_list
                },
                fields=["rate"],
                limit=1
            )
            if service_prices:
                return flt(service_prices[0].rate)
        
        # Last resort, return item standard rate or job type rate
        return (
            frappe.db.get_value("Item", item_code, "standard_rate") or
            frappe.db.get_value("Job Type", self.job_type, "rate") or
            0
        )