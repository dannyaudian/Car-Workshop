from frappe.model.document import Document
import frappe
from frappe import _

class JobType(Document):
    def validate(self):
        self.validate_opl_logic()
        self.calculate_item_amounts()
    
    def validate_opl_logic(self):
        """Validate OPL (Outsourced) job logic"""
        if self.is_opl:
            # Validations for OPL jobs
            if not self.opl_vendor:
                frappe.throw(_("Wajib isi Vendor OPL jika pekerjaan dilakukan oleh vendor luar"))
            if not self.opl_item_code:
                frappe.throw(_("Wajib isi Item OPL yang akan digunakan untuk proses vendor"))
            if self.items and len(self.items) > 0:
                frappe.throw(_("Pekerjaan OPL tidak boleh mengisi Job Type Item — gunakan hanya Item OPL"))
        else:
            # Validations for internal jobs
            if not self.items or len(self.items) == 0:
                frappe.throw(_("Pekerjaan internal harus memiliki detail Job Type Item"))
    
    def calculate_item_amounts(self):
        """Calculate amount for each item and update it"""
        for item in self.items:
            item.amount = item.qty * (item.rate or 0)