from frappe.model.document import Document
import frappe

class Part(Document):
    def validate(self):
        self.update_price_from_item()
        self.validate_compatibility()
        
    def update_price_from_item(self):
        """Update current price from linked Item"""
        if self.item_code:
            price = frappe.db.get_value("Item", self.item_code, "standard_rate")
            if price:
                self.current_price = price
                
    def validate_compatibility(self):
        """Validate that models belong to their brands"""
        for entry in self.compatibility:
            if entry.vehicle_model and entry.vehicle_brand:
                # Check if model belongs to the specified brand
                brand = frappe.db.get_value("Vehicle Model", entry.vehicle_model, "brand")
                if brand != entry.vehicle_brand:
                    frappe.throw(f"Model {entry.vehicle_model} does not belong to brand {entry.vehicle_brand}")
                    
            # Validate year range
            if entry.year_start and entry.year_end and entry.year_start > entry.year_end:
                frappe.throw(f"Year start cannot be greater than year end for {entry.vehicle_model}")