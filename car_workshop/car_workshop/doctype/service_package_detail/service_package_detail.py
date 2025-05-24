from frappe.model.document import Document
import frappe

class ServicePackageDetail(Document):
    def validate(self):
        self.validate_item_selection()
        self.update_rate_and_amount()
    
    def validate_item_selection(self):
        """Validate that the correct field is filled based on item_type"""
        if self.item_type == "Job" and not self.job_type:
            frappe.throw("Job Type is required when Item Type is 'Job'")
        
        if self.item_type == "Part" and not self.part:
            frappe.throw("Part is required when Item Type is 'Part'")
        
        # Clear the other field based on selected type
        if self.item_type == "Job":
            self.part = None
        elif self.item_type == "Part":
            self.job_type = None
    
    def update_rate_and_amount(self):
        """Update rate and amount based on selected job_type or part"""
        # Default to 1 if quantity is not set
        if not self.quantity or self.quantity <= 0:
            self.quantity = 1
        
        # Get rate based on item type
        if self.item_type == "Job" and self.job_type:
            self.rate = self.get_job_type_rate()
        elif self.item_type == "Part" and self.part:
            self.rate = self.get_part_rate()
        
        # Calculate amount
        self.amount = self.quantity * (self.rate or 0)
    
    def get_job_type_rate(self):
        """Get standard rate from Job Type"""
        rate = frappe.db.get_value("Job Type", self.job_type, "standard_rate")
        return rate or 0
    
    def get_part_rate(self):
        """Get current price from Part"""
        rate = frappe.db.get_value("Part", self.part, "current_price")
        
        # If part has no price, try to get price from linked item
        if not rate:
            item_code = frappe.db.get_value("Part", self.part, "item_code")
            if item_code:
                # Try to get price from Item Price for the parent's price list
                parent = frappe.get_doc("Service Package", self.parent)
                if parent and parent.price_list:
                    rate = frappe.db.get_value("Item Price", 
                        {
                            "item_code": item_code,
                            "price_list": parent.price_list,
                            "selling": 1
                        }, 
                        "price_list_rate")
                
                # If still no price, try to get standard rate from Item
                if not rate:
                    rate = frappe.db.get_value("Item", item_code, "standard_rate")
        
        return rate or 0