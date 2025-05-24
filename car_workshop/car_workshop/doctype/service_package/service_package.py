import frappe
from frappe.model.document import Document

class ServicePackage(Document):
    def validate(self):
        self.validate_price()
        self.validate_details()
    
    def validate_price(self):
        """Validate that price is greater than zero"""
        if self.price <= 0:
            frappe.throw("Package price must be greater than zero.")
    
    def validate_details(self):
        """Validate that service package has at least one service detail"""
        if not self.details or len(self.details) == 0:
            frappe.throw("Service Package must have at least one service detail.")
        
        # Calculate total estimated time
        total_time = 0
        for detail in self.details:
            if detail.time_minutes:
                total_time += detail.time_minutes
        
        # Store the total time in a custom field
        self.total_time_minutes = total_time
        
        # Convert to hours and minutes for display
        hours = total_time // 60
        minutes = total_time % 60
        self.estimated_time = f"{hours} hrs {minutes} mins"
    
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
    
    def get_total_cost(self):
        """Calculate the total cost of all services in the package"""
        total_cost = 0
        for detail in self.details:
            if detail.cost:
                total_cost += detail.cost
        return total_cost