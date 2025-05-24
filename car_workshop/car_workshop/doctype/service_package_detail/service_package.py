import frappe
from frappe.model.document import Document

class ServicePackage(Document):
    def validate(self):
        self.validate_details()
        self.calculate_totals()
    
    def validate_details(self):
        """Validate that service package has at least one service detail"""
        if not self.details or len(self.details) == 0:
            frappe.throw("Service Package must have at least one service detail.")
    
    def calculate_totals(self):
        """Calculate totals for the service package"""
        total_amount = 0
        total_time = 0
        
        for detail in self.details:
            # Ensure each detail has an amount
            if not detail.amount:
                if detail.item_type == "Job":
                    rate = frappe.db.get_value("Job Type", detail.job_type, "standard_rate") or 0
                elif detail.item_type == "Part":
                    rate = frappe.db.get_value("Part", detail.part, "current_price") or 0
                else:
                    rate = 0
                
                detail.rate = rate
                detail.amount = (detail.quantity or 1) * rate
            
            total_amount += detail.amount
            
            # Add time if job type has duration
            if detail.item_type == "Job" and detail.job_type:
                time_minutes = frappe.db.get_value("Job Type", detail.job_type, "time_minutes") or 0
                total_time += time_minutes * (detail.quantity or 1)
        
        # Update package totals
        self.price = total_amount
        self.total_time_minutes = total_time
        
        # Convert time to hours and minutes for display
        hours = total_time // 60
        minutes = total_time % 60
        self.estimated_time = f"{hours} hr{'' if hours == 1 else 's'} {minutes} min{'' if minutes == 1 else 's'}"
    
    def before_save(self):
        """Set modified package flag"""
        if self.has_value_changed("price") or self.has_value_changed("details"):
            self.is_modified = 1
    
    def on_update(self):
        """Update linked price list item if specified"""
        if self.price_list:
            self.update_price_list_item()
    
    def update_price_list_item(self):
        """Update or create price list item for this service package"""
        # Check if price list item exists
        price_list_item = frappe.get_all(
            "Item Price",
            filters={
                "price_list": self.price_list,
                "item_code": self.name
            },
            fields=["name"]
        )
        
        if price_list_item:
            # Update existing price list item
            item_price = frappe.get_doc("Item Price", price_list_item[0].name)
            item_price.price_list_rate = self.price
            item_price.currency = self.currency
            item_price.save()
            frappe.msgprint(f"Price List item updated for {self.package_name}")
        else:
            # Create new price list item
            item_price = frappe.get_doc({
                "doctype": "Item Price",
                "price_list": self.price_list,
                "item_code": self.name,
                "price_list_rate": self.price,
                "currency": self.currency
            })
            item_price.insert()
            frappe.msgprint(f"New Price List item created for {self.package_name}")