from frappe.model.document import Document

class JobType(Document):
    def validate(self):
        self.calculate_item_amounts()
    
    def calculate_item_amounts(self):
        """Calculate amount for each item and update it"""
        for item in self.items:
            item.amount = item.qty * (item.rate or 0)