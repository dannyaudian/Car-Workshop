# Copyright (c) 2025, Danny Audian and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

class PartStockOpnameItem(Document):
    """
    Part Stock Opname Item DocType controller.
    
    This DocType handles the line items for Part Stock Opname documents, representing
    parts/items being counted during physical inventory.
    """
    
    def validate(self):
        """
        Validate the stock opname item fields:
        - Ensure part is linked to an item
        - Validate quantity formats
        - Fetch system quantity if not set
        - Calculate variance
        """
        self.validate_part_item_link()
        self.validate_quantity()
        self.fetch_system_quantity()
        self.calculate_variance()
    
    def validate_part_item_link(self):
        """Ensure part is correctly linked to an item"""
        if not self.part:
            return
            
        if not self.item_code:
            # Get item code from Part
            item_code = frappe.db.get_value("Part", self.part, "item")
            if not item_code:
                frappe.throw(_("Part {0} is not linked to any Item").format(self.part))
            self.item_code = item_code
            
            # Get item name if not set
            if not self.item_name:
                self.item_name = frappe.db.get_value("Item", item_code, "item_name")
        
        # Verify the Item exists
        if not frappe.db.exists("Item", self.item_code):
            frappe.throw(_("Item {0} does not exist").format(self.item_code))
        
        # Get UOM if not set
        if not self.uom:
            self.uom = frappe.db.get_value("Item", self.item_code, "stock_uom")
    
    def validate_quantity(self):
        """Validate that counted quantity is properly formatted"""
        # Ensure qty_counted is numeric and not negative
        if self.qty_counted is not None and flt(self.qty_counted) < 0:
            frappe.throw(_("Counted quantity cannot be negative for part {0}").format(self.part))
        
        # Format to proper precision
        if self.qty_counted is not None:
            self.qty_counted = flt(self.qty_counted, precision=3)
    
    def fetch_system_quantity(self):
        """Fetch system quantity if not set"""
        # Skip if system quantity is already set and not in draft status
        parent_doc_name = self.parent
        if self.qty_system is not None and parent_doc_name and parent_doc_name != "new-part-stock-opname":
            parent_status = frappe.db.get_value("Part Stock Opname", parent_doc_name, "status")
            if parent_status != "Draft":
                return
            
        # Get warehouse from parent
        warehouse = None
        if parent_doc_name and parent_doc_name != "new-part-stock-opname":
            warehouse = frappe.db.get_value("Part Stock Opname", parent_doc_name, "warehouse")
        
        if not warehouse or not self.item_code:
            return
            
        # Get bin data
        bin_data = frappe.db.get_value(
            "Bin",
            {"item_code": self.item_code, "warehouse": warehouse},
            ["actual_qty", "valuation_rate"],
            as_dict=True
        )
        
        if bin_data:
            self.qty_system = flt(bin_data.actual_qty)
            self.valuation_rate = flt(bin_data.valuation_rate)
        else:
            self.qty_system = 0
            self.valuation_rate = frappe.db.get_value("Item", self.item_code, "valuation_rate") or 0
    
    def calculate_variance(self):
        """Calculate variance between system and counted quantities"""
        if self.qty_system is not None and self.qty_counted is not None:
            self.variance = flt(self.qty_counted) - flt(self.qty_system)
            
            # Calculate variance percentage
            if flt(self.qty_system) != 0:
                self.variance_percent = (flt(self.variance) / flt(self.qty_system)) * 100
            else:
                # If system quantity is zero, and there's a counted quantity, variance is 100%
                if flt(self.qty_counted) > 0:
                    self.variance_percent = 100
                else:
                    self.variance_percent = 0
                    
            # Calculate value impact
            self.value_impact = flt(self.variance) * flt(self.valuation_rate)
    
    def on_update(self):
        """Actions to perform when the item is updated"""
        # Update parent document's totals
        self.update_parent_totals()
    
    def update_parent_totals(self):
        """Update the parent document's total quantities and variances"""
        parent_name = self.parent
        if not parent_name or parent_name == "new-part-stock-opname":
            return
            
        # Check if parent exists and is in draft state
        parent_status = frappe.db.get_value("Part Stock Opname", parent_name, "status")
        if not parent_status or parent_status != "Draft":
            return
            
        try:
            # Get all items for this parent
            items = frappe.get_all("Part Stock Opname Item", 
                filters={"parent": parent_name},
                fields=["qty_system", "qty_counted", "variance", "value_impact"]
            )
            
            # Calculate totals
            total_system_qty = sum(flt(item.qty_system) for item in items if item.qty_system is not None)
            total_counted_qty = sum(flt(item.qty_counted) for item in items if item.qty_counted is not None)
            total_variance = sum(flt(item.variance) for item in items if item.variance is not None)
            total_value_impact = sum(flt(item.value_impact) for item in items if item.value_impact is not None)
            
            # Update parent
            frappe.db.set_value("Part Stock Opname", parent_name, {
                "total_system_qty": total_system_qty,
                "total_counted_qty": total_counted_qty,
                "total_variance": total_variance,
                "total_value_impact": total_value_impact
            })
            
        except Exception as e:
            frappe.log_error(f"Error updating parent totals: {str(e)}", 
                           "Part Stock Opname Item")