import frappe
from frappe.model.document import Document
from frappe.utils import flt

class WorkOrderPart(Document):
    def validate(self):
        # Fetch missing values from Part if not already set
        if self.part:
            part_fields = ["part_number", "part_name", "item_code", "brand", "category"]
            part_doc = frappe.get_doc("Part", self.part)
            
            for field in part_fields:
                if not self.get(field) and hasattr(part_doc, field):
                    self.set(field, part_doc.get(field))
            
            # Set rate from Part's current_price if not already set
            if not self.rate and part_doc.current_price:
                self.rate = part_doc.current_price
        
        # Calculate amount
        self.calculate_amount()
    
    def calculate_amount(self):
        if self.quantity and self.rate:
            self.amount = flt(self.quantity) * flt(self.rate)