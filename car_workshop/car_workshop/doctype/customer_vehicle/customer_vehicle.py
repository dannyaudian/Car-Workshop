import re
import frappe
from frappe import _
from frappe.model.document import Document


class CustomerVehicle(Document):
    def validate(self):
        """
        Run validation checks before document save
        """
        validate_plate_number(self)
        update_fuel_type(self)
    
    def on_update(self):
        """
        Actions to perform after document is updated
        """
        update_last_service_info(self)
        log_vehicle_updates(self)


# Validation Functions
def validate_plate_number(doc):
    """
    Validasi plat nomor kendaraan menggunakan format standar Indonesia.
    Format yang valid:
    - B 1234 CD (dengan spasi)
    - D1234 (tanpa spasi)
    - F 1234 (dengan spasi, tanpa huruf belakang)
    - Z 123 (dengan angka 3 digit)
    - B 1234 (dengan spasi, tanpa huruf belakang)
    """
    if not doc.plate_number:
        return
    
    # Bersihkan plat nomor (hapus spasi berlebih dan konversi ke uppercase)
    doc.plate_number = doc.plate_number.strip().upper()
    
    # Regex untuk validasi format plat nomor Indonesia
    plate_pattern = r'^[A-Z]{1,2}\s?\d{1,4}(\s?[A-Z]{1,3})?$'
    
    if not re.match(plate_pattern, doc.plate_number):
        frappe.throw(_(
            "Format plat nomor tidak valid. Format yang benar: 'B 1234 CD', 'D1234', "
            "'F 1234', 'Z 123', atau 'B 1234'. Huruf depan wajib, angka wajib, huruf belakang opsional."
        ))


def update_fuel_type(doc):
    """
    Update fuel type otomatis berdasarkan model kendaraan
    """
    if doc.model:
        model_doc = frappe.get_doc("Vehicle Model", doc.model)
        doc.fuel_type = model_doc.fuel_type


# Data Update Functions
def update_last_service_info(doc):
    """
    Update informasi terakhir seperti odometer dan tanggal servis
    dari riwayat servis kendaraan
    """
    if not doc.service_history:
        return
        
    # Ambil entri terakhir dari service history yang sudah selesai
    completed_services = [
        service for service in doc.service_history 
        if service.status == "Completed" and service.service_date and service.odometer
    ]
    
    if not completed_services:
        return
        
    # Urutkan berdasarkan tanggal servis terbaru
    completed_services.sort(key=lambda x: x.service_date, reverse=True)
    latest_service = completed_services[0]
    
    # Update informasi terakhir
    doc.db_set('last_service_date', latest_service.service_date)
    doc.db_set('last_odometer', latest_service.odometer)


# Logging Functions
def create_vehicle_log(doc, method=None):
    """
    Mencatat pembuatan kendaraan baru dalam Vehicle Change Log
    """
    if frappe.flags.in_install or frappe.flags.in_patch or frappe.flags.in_migrate or frappe.flags.in_import:
        return
        
    frappe.get_doc({
        "doctype": "Vehicle Change Log",
        "customer_vehicle": doc.name,
        "change_date": frappe.utils.now(),
        "fieldname": "creation",
        "new_value": doc.name,
        "change_type": "Created",
        "doctype_reference": "Customer Vehicle",
        "reference": doc.name,
        "updated_by": frappe.session.user,
        "remarks": "Customer Vehicle created"
    }).insert(ignore_permissions=True)


def log_vehicle_updates(doc, method=None):
    """
    Mencatat perubahan pada kendaraan dalam Vehicle Change Log
    """
    if frappe.flags.in_install or frappe.flags.in_patch or frappe.flags.in_migrate or frappe.flags.in_import:
        return
        
    old_doc = doc.get_doc_before_save()
    if not old_doc:
        return
    
    # Fields to track changes
    tracked_fields = ["plate_number", "vin", "brand", "model", "year", "customer"]
    
    for field in tracked_fields:
        old_value = old_doc.get(field)
        new_value = doc.get(field)
        
        if old_value != new_value:
            create_change_log_entry(
                doc.name, 
                field, 
                old_value, 
                new_value, 
                f"Field '{field}' updated"
            )


def create_change_log_entry(vehicle_name, field_name, old_value, new_value, remarks):
    """
    Helper function to create a change log entry
    """
    frappe.get_doc({
        "doctype": "Vehicle Change Log",
        "customer_vehicle": vehicle_name,
        "change_date": frappe.utils.now(),
        "fieldname": field_name,
        "old_value": old_value,
        "new_value": new_value,
        "change_type": "Updated",
        "doctype_reference": "Customer Vehicle",
        "reference": vehicle_name,
        "updated_by": frappe.session.user,
        "remarks": remarks
    }).insert(ignore_permissions=True)