import frappe
from frappe.model.document import Document

class WorkOrderExpense(Document):
    def validate(self):
        # Add additional validations if needed
        pass