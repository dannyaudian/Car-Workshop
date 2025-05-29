from frappe.model.document import Document
import frappe
from frappe import _

class JobType(Document):
    def validate(self):
        self.validate_opl_logic()
        self.calculate_item_amounts()
    
    def validate_opl_logic(self):
        """Validate OPL (Outsourced) job logic"""
        if self.is_opl:
            # Validations for OPL jobs
            if not self.opl_supplier:
                frappe.throw(_("OPL Supplier is required for outsourced jobs"))
            if not self.opl_item:
                frappe.throw(_("OPL Item is required for outsourced jobs"))
            if self.items and len(self.items) > 0:
                frappe.throw(_("Job Type Items should not be added for OPL jobs - use only OPL Item"))
            
            # Set default price based on OPL item if not already set
            if not self.default_price:
                opl_cost = self.get_opl_cost()
                if opl_cost:
                    self.default_price = opl_cost
        else:
            # Validations for internal jobs
            if not self.items or len(self.items) == 0:
                frappe.throw(_("Internal jobs must have at least one Job Type Item"))
    
    def get_opl_cost(self):
        """Get the cost from the linked OPL item"""
        if not self.opl_item:
            return 0
            
        try:
            # Try to get standard_rate from the item
            item_rate = frappe.db.get_value("Item", self.opl_item, "standard_rate")
            
            # If standard_rate is not set, try to get price from Item Price
            if not item_rate:
                item_prices = frappe.get_all(
                    "Item Price",
                    filters={
                        "item_code": self.opl_item,
                        "selling": 1
                    },
                    fields=["price_list_rate"],
                    order_by="valid_from desc",
                    limit=1
                )
                
                if item_prices:
                    item_rate = item_prices[0].price_list_rate
            
            return item_rate or 0
        except Exception as e:
            frappe.log_error(
                f"Error fetching OPL cost for {self.name}: {str(e)}",
                "JobType.get_opl_cost Error"
            )
            return 0
    
    def calculate_item_amounts(self):
        """Calculate amount for each item and update it"""
        if not self.is_opl and self.items:
            for item in self.items:
                item.amount = item.qty * (item.rate or 0)