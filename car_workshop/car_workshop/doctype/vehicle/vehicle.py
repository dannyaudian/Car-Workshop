import re
import frappe
from frappe import _
from frappe.model.document import Document


class Vehicle(Document):
    def validate(self):
        self.validate_plate_number()
        self.update_fuel_type()
    
    def validate_plate_number(self):
        """
        Validasi plat nomor kendaraan menggunakan format standar Indonesia.
        Format yang valid:
        - B 1234 CD (dengan spasi)
        - D1234 (tanpa spasi)
        - F 1234 (dengan spasi, tanpa huruf belakang)
        - Z 123 (dengan angka 3 digit)
        - B 1234 (dengan spasi, tanpa huruf belakang)
        """
        if not self.plate_number:
            return
        
        # Bersihkan plat nomor (hapus spasi berlebih dan konversi ke uppercase)
        self.plate_number = self.plate_number.strip().upper()
        
        # Regex untuk validasi format plat nomor Indonesia
        plate_pattern = r'^[A-Z]{1,2}\s?\d{1,4}(\s?[A-Z]{1,3})?$'
        
        if not re.match(plate_pattern, self.plate_number):
            frappe.throw(_(
                "Format plat nomor tidak valid. Format yang benar: 'B 1234 CD', 'D1234', "
                "'F 1234', 'Z 123', atau 'B 1234'. Huruf depan wajib, angka wajib, huruf belakang opsional."
            ))
    
    def update_fuel_type(self):
        """
        Update fuel type otomatis berdasarkan model kendaraan
        """
        if self.model:
            model_doc = frappe.get_doc("Vehicle Model", self.model)
            self.fuel_type = model_doc.fuel_type
    
    def on_update(self):
        """
        Update informasi terakhir seperti odometer dari riwayat servis
        """
        self.update_last_service_info()

    def update_last_service_info(self):
        """
        Update informasi terakhir seperti odometer dan tanggal servis
        dari riwayat servis kendaraan
        """
        if not self.service_history:
            return
            
        # Ambil entri terakhir dari service history yang sudah selesai
        completed_services = [
            service for service in self.service_history 
            if service.status == "Completed" and service.service_date and service.odometer
        ]
        
        if not completed_services:
            return
            
        # Urutkan berdasarkan tanggal servis terbaru
        completed_services.sort(key=lambda x: x.service_date, reverse=True)
        latest_service = completed_services[0]
        
        # Update informasi terakhir
        self.db_set('last_service_date', latest_service.service_date)
        self.db_set('last_odometer', latest_service.odometer)

def create_vehicle_log(doc, method=None):
    """
    Mencatat pembuatan kendaraan baru dalam Vehicle Change Log
    """
    frappe.get_doc({
        "doctype": "Vehicle Change Log",
        "vehicle": doc.name,
        "change_date": frappe.utils.now(),
        "fieldname": "creation",
        "new_value": doc.name,
        "change_type": "Created",
        "doctype_reference": "Vehicle",
        "reference": doc.name,
        "updated_by": frappe.session.user,
        "remarks": "Vehicle created"
    }).insert(ignore_permissions=True)

def log_vehicle_updates(doc, method=None):
    """
    Mencatat perubahan pada kendaraan dalam Vehicle Change Log
    """
    if not doc.get_doc_before_save():
        return
        
    old_doc = doc.get_doc_before_save()
    
    # Fields to track changes
    tracked_fields = ["plate_number", "vin", "brand", "model", "year", "customer"]
    
    for field in tracked_fields:
        old_value = old_doc.get(field)
        new_value = doc.get(field)
        
        if old_value != new_value:
            frappe.get_doc({
                "doctype": "Vehicle Change Log",
                "vehicle": doc.name,
                "change_date": frappe.utils.now(),
                "fieldname": field,
                "old_value": old_value,
                "new_value": new_value,
                "change_type": "Updated",
                "doctype_reference": "Vehicle",
                "reference": doc.name,
                "updated_by": frappe.session.user,
                "remarks": f"Field '{field}' updated"
            }).insert(ignore_permissions=True)