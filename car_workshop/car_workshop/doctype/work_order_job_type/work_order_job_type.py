import frappe
from frappe.model.document import Document

class WorkOrderJobType(Document):
    def validate(self):
        # Fetch missing values from Job Type if not already set
        if self.job_type:
            if not self.description or not self.price or self.is_opl is None:
                job_type = frappe.get_doc("Job Type", self.job_type)
                
                if not self.description:
                    self.description = job_type.description
                
                if not self.price:
                    self.price = job_type.default_price
                
                if self.is_opl is None:
                    self.is_opl = job_type.is_opl
            
            # If job is OPL, ensure vendor is set
            if self.is_opl and not self.vendor:
                # Try to fetch from job type
                job_type = frappe.get_doc("Job Type", self.job_type)
                if job_type.opl_vendor:
                    self.vendor = job_type.opl_vendor
                    self.vendor_item_code = job_type.opl_item_code
                    self.vendor_notes = job_type.opl_notes