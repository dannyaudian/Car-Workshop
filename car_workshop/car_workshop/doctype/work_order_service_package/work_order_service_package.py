import frappe
from frappe.model.document import Document

class WorkOrderServicePackage(Document):
    def validate(self):
        # Fetch missing values from Service Package if not already set
        if self.service_package:
            if not self.description or not self.total_price or not self.currency:
                service_package = frappe.get_doc("Service Package", self.service_package)
                
                if not self.description:
                    self.description = service_package.description
                
                if not self.total_price:
                    self.total_price = service_package.price
                
                if not self.currency:
                    self.currency = service_package.currency