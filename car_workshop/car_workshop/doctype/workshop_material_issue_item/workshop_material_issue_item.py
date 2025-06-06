# Copyright (c) 2025, Danny Audian and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class WorkshopMaterialIssueItem(Document):
    """
    Workshop Material Issue Item DocType controller.
    
    This DocType handles the line items for Workshop Material Issues, representing
    parts/items issued from inventory to a Work Order.
    """
    
    def validate(self):
        """
        Validate the material issue item fields:
        - Ensure item code is linked to part
        - Set rate and amount based on valuation
        """
        self.validate_item_code()
        self.set_rate_and_amount()
    
    def validate_item_code(self):
        """Ensure item_code is correctly linked to the selected part"""
        if not self.part:
            return
            
        if not self.item_code:
            part_item = frappe.db.get_value("Part", self.part, "item")
            if not part_item:
                frappe.throw(frappe._("Part {0} is not linked to any Item").format(self.part))
            self.item_code = part_item
    
    def set_rate_and_amount(self):
        """Set rate based on warehouse valuation and calculate amount"""
        if not self.item_code or not self.qty:
            return
            
        if not self.rate:
            # Get parent document to find the warehouse
            parent_doc_name = self.parent
            if not parent_doc_name or parent_doc_name == "new-workshop-material-issue":
                return
                
            warehouse = frappe.db.get_value("Workshop Material Issue", parent_doc_name, "set_warehouse")
            if not warehouse:
                return
                
            # Get valuation rate from bin
            bin_data = frappe.db.get_value("Bin", 
                {"item_code": self.item_code, "warehouse": warehouse},
                "valuation_rate",
                as_dict=1)
                
            if bin_data and bin_data.valuation_rate:
                self.rate = bin_data.valuation_rate
            else:
                # Fallback to item's valuation rate
                self.rate = frappe.db.get_value("Item", self.item_code, "valuation_rate") or 0
        
        # Calculate amount
        self.amount = (self.qty or 0) * (self.rate or 0)