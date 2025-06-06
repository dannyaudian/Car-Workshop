# Copyright (c) 2025, Danny Audian and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

class ReturnMaterialItem(Document):
    """
    Return Material Item DocType controller.
    
    This DocType handles the line items for Return Material documents, representing
    parts/items being returned from a Work Order back to inventory.
    """
    
    def validate(self):
        """
        Validate the return material item fields:
        - Ensure item code is linked to part
        - Validate quantity and warehouse
        - Calculate amount based on valuation rate
        """
        self.validate_part_item_link()
        self.validate_quantity()
        self.validate_warehouse()
        self.calculate_amount()
    
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
        
        # Verify the Item exists
        if not frappe.db.exists("Item", self.item_code):
            frappe.throw(_("Item {0} does not exist").format(self.item_code))
        
        # Get item name if not set
        if not self.item_name:
            self.item_name = frappe.db.get_value("Item", self.item_code, "item_name")
        
        # Get UOM if not set
        if not self.uom:
            self.uom = frappe.db.get_value("Item", self.item_code, "stock_uom")
    
    def validate_quantity(self):
        """Validate that quantity is positive"""
        if flt(self.qty) <= 0:
            frappe.throw(_("Quantity must be greater than zero for item {0}").format(self.item_code))
        
        # Check if this exceeds the consumed quantity in the Work Order
        # This is done at the parent level to consider other return documents
    
    def validate_warehouse(self):
        """Validate that warehouse exists and is valid"""
        if not self.warehouse:
            # Set default warehouse from parent if available
            parent_doc_name = self.parent
            if parent_doc_name and parent_doc_name != "new-return-material":
                return_to_warehouse = frappe.db.get_value("Return Material", 
                                                       parent_doc_name, 
                                                       "return_to_warehouse")
                if return_to_warehouse:
                    self.warehouse = return_to_warehouse
                    return
            
            frappe.throw(_("Warehouse is required for item {0}").format(self.item_code))
        
        # Verify warehouse exists
        if not frappe.db.exists("Warehouse", self.warehouse):
            frappe.throw(_("Warehouse {0} does not exist").format(self.warehouse))
        
        # Check if warehouse is enabled
        is_disabled = frappe.db.get_value("Warehouse", self.warehouse, "disabled")
        if is_disabled:
            frappe.throw(_("Warehouse {0} is disabled").format(self.warehouse))
    
    def calculate_amount(self):
        """Calculate amount based on quantity and valuation rate"""
        if not self.valuation_rate:
            # Get valuation rate from Item if not set
            self.valuation_rate = frappe.db.get_value("Item", self.item_code, "valuation_rate") or 0
        
        self.amount = flt(self.qty) * flt(self.valuation_rate)
    
    def on_update(self):
        """Actions to perform when the item is updated"""
        # Ensure work_order_item is set if available
        if not self.work_order_item and self.parent and self.item_code:
            # Get work order from parent
            work_order = frappe.db.get_value("Return Material", self.parent, "work_order")
            if work_order:
                # Find matching item in Work Order
                work_order_items = frappe.get_all(
                    "Work Order Part",
                    filters={
                        "parent": work_order,
                        "item_code": self.item_code
                    },
                    fields=["name"]
                )
                
                if work_order_items:
                    self.work_order_item = work_order_items[0].name
                    self.db_update()
    
    def validate_batch_serial(self):
        """Validate batch and serial numbers if provided"""
        if self.batch_no:
            # Check if batch exists
            if not frappe.db.exists("Batch", self.batch_no):
                frappe.throw(_("Batch {0} does not exist").format(self.batch_no))
            
            # Check if batch is for this item
            batch_item = frappe.db.get_value("Batch", self.batch_no, "item")
            if batch_item != self.item_code:
                frappe.throw(_("Batch {0} does not belong to item {1}").format(
                    self.batch_no, self.item_code))
        
        if self.serial_no:
            serial_nos = self.serial_no.strip().split('\n')
            if len(serial_nos) != int(self.qty):
                frappe.throw(_("Number of serial numbers ({0}) does not match quantity ({1})").format(
                    len(serial_nos), int(self.qty)))
            
            # Validate each serial number
            for serial_no in serial_nos:
                if not serial_no:
                    continue
                
                # Check if serial number exists
                if not frappe.db.exists("Serial No", serial_no):
                    frappe.throw(_("Serial No {0} does not exist").format(serial_no))
                
                # Check if serial belongs to this item
                sn_item = frappe.db.get_value("Serial No", serial_no, "item_code")
                if sn_item != self.item_code:
                    frappe.throw(_("Serial No {0} does not belong to item {1}").format(
                        serial_no, self.item_code))