# Copyright (c) 2025, Danny Audian and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, now_datetime, nowdate
import json

class PartStockOpname(Document):
    def validate(self):
        """
        Validate the document:
        - Check all required fields
        - Validate items
        - Store system quantities for later comparison
        """
        self.validate_required_fields()
        self.validate_items()
        self.update_status()
        self.store_system_quantities()
    
    def on_submit(self):
        """
        On document submission:
        - Validate submission is allowed
        - Update document status
        """
        self.validate_submission()
        self.update_status()
    
    def on_cancel(self):
        """
        On document cancellation:
        - Validate cancellation is allowed
        - Update document status
        """
        self.validate_cancellation()
        self.update_status()
    
    def validate_required_fields(self):
        """Validate that all required fields are filled"""
        if not self.warehouse:
            frappe.throw(_("Warehouse is mandatory"))
            
        if not self.posting_date:
            self.posting_date = getdate(nowdate())
            
        if not self.posting_time:
            self.posting_time = now_datetime().strftime('%H:%M:%S')
            
        if not self.opname_items or len(self.opname_items) == 0:
            frappe.throw(_("At least one item is required for stock opname"))
    
    def validate_items(self):
        """
        Validate items:
        - Check for duplicate parts
        - Ensure counted quantity is valid and > 0
        """
        part_list = []
        for i, item in enumerate(self.opname_items):
            # Check for duplicate parts
            if item.part in part_list:
                frappe.throw(_("Duplicate Part {0} at row {1}").format(item.part, i+1))
            part_list.append(item.part)
            
            # Ensure counted quantity is valid and > 0
            if flt(item.qty_counted) <= 0:
                frappe.throw(_("Counted Quantity must be greater than zero for Part {0} at row {1}").format(
                    item.part, i+1))
    
    def validate_submission(self):
        """Validate that document can be submitted"""
        if self.status == "Adjusted":
            frappe.throw(_("Document cannot be submitted again as it has already been adjusted"))
    
    def validate_cancellation(self):
        """Validate that document can be cancelled"""
        if self.status == "Adjusted":
            frappe.throw(_("Document cannot be cancelled as it has already been adjusted"))
    
    def store_system_quantities(self):
        """
        Store system quantities as hidden cache for later comparison
        when creating adjustment
        """
        system_quantities = {}
        
        for item in self.opname_items:
            if not item.part:
                continue
                
            # Get the item_code linked to the part
            item_code = frappe.db.get_value("Part", item.part, "item")
            if not item_code:
                continue
                
            # Get system quantity from Bin
            bin_data = frappe.db.get_value(
                "Bin",
                {"item_code": item_code, "warehouse": self.warehouse},
                ["actual_qty", "valuation_rate"],
                as_dict=True
            )
            
            system_quantities[item.part] = {
                "item_code": item_code,
                "actual_qty": flt(bin_data.actual_qty) if bin_data else 0,
                "valuation_rate": flt(bin_data.valuation_rate) if bin_data else 0
            }
        
        # Store as JSON string in a hidden field
        self.system_quantities_cache = json.dumps(system_quantities)
    
    def update_status(self):
        """Set document status based on docstatus"""
        if self.docstatus == 0:
            self.status = "Draft"
        elif self.docstatus == 1:
            self.status = "Submitted"
        elif self.docstatus == 2:
            self.status = "Cancelled"

    def create_stock_adjustment(self):
        """
        Create a Part Stock Adjustment document with the differences
        between counted and actual quantities
        """
        if self.docstatus != 1:
            frappe.throw(_("Stock Adjustment can only be created for submitted documents"))
            
        if self.status == "Adjusted":
            frappe.throw(_("Stock Adjustment has already been created for this document"))
        
        # Retrieve system quantities from cache
        if not hasattr(self, 'system_quantities_cache') or not self.system_quantities_cache:
            frappe.throw(_("System quantities cache not found. Please refresh the document."))
            
        system_quantities = json.loads(self.system_quantities_cache)
        
        # Create Part Stock Adjustment
        adjustment = frappe.new_doc("Part Stock Adjustment")
        adjustment.posting_date = nowdate()
        adjustment.posting_time = now_datetime().strftime('%H:%M:%S')
        adjustment.warehouse = self.warehouse
        adjustment.reference_doctype = self.doctype
        adjustment.reference_docname = self.name
        adjustment.remarks = _("Created from Stock Opname {0}").format(self.name)
        
        # Add items with differences
        items_with_diff = 0
        
        for item in self.opname_items:
            if not item.part or item.part not in system_quantities:
                continue
                
            system_qty = system_quantities[item.part]["actual_qty"]
            difference = flt(item.qty_counted) - system_qty
            
            # Only add items with differences
            if difference != 0:
                adjustment.append("items", {
                    "part": item.part,
                    "item_code": system_quantities[item.part]["item_code"],
                    "system_qty": system_qty,
                    "counted_qty": item.qty_counted,
                    "difference_qty": difference,
                    "uom": item.uom,
                    "valuation_rate": system_quantities[item.part]["valuation_rate"],
                    "adjustment_amount": difference * system_quantities[item.part]["valuation_rate"]
                })
                items_with_diff += 1
        
        if items_with_diff == 0:
            frappe.msgprint(_("No differences found between counted and system quantities"))
            return None
        
        adjustment.insert(ignore_permissions=True)
        
        # Update status to Adjusted
        self.db_set('status', 'Adjusted')
        
        return adjustment

@frappe.whitelist()
def get_part_from_barcode(barcode):
    """
    Get part from barcode
    
    Args:
        barcode: Barcode of the part
        
    Returns:
        dict: Part details
    """
    if not barcode:
        return {}
    
    # Try to find the barcode in Item Barcode
    barcode_data = frappe.db.get_value(
        "Item Barcode",
        {"barcode": barcode},
        ["parent as item_code"],
        as_dict=True
    )
    
    if barcode_data and barcode_data.item_code:
        # Find the part linked to this item
        part_data = frappe.db.get_value(
            "Part",
            {"item": barcode_data.item_code},
            ["name", "part_name", "uom"],
            as_dict=True
        )
        
        if part_data:
            return {
                "part": part_data.name,
                "part_name": part_data.part_name,
                "uom": part_data.uom or "Pcs"
            }
    
    # If not found in Item Barcode, try to find directly in Part
    part_data = frappe.db.get_value(
        "Part",
        {"barcode": barcode},
        ["name", "part_name", "uom"],
        as_dict=True
    )
    
    if part_data:
        return {
            "part": part_data.name,
            "part_name": part_data.part_name,
            "uom": part_data.uom or "Pcs"
        }
    
    return {}

@frappe.whitelist()
def make_stock_adjustment(source_name, target_doc=None):
    """
    Create stock adjustment from stock opname
    
    Args:
        source_name: Name of the stock opname document
        target_doc: Target doc if provided
        
    Returns:
        Part Stock Adjustment doc
    """
    opname = frappe.get_doc("Part Stock Opname", source_name)
    return opname.create_stock_adjustment()