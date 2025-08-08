from frappe.model.document import Document
from frappe.utils import flt

class WorkOrderBillingReturn(Document):
    def validate(self):
        """Ensure amount reflects quantity and rate."""
        self.amount = flt(self.quantity) * flt(self.rate)
