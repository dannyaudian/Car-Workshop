import frappe
from frappe import _


@frappe.whitelist()
def get_latest_vehicle_log(vehicle):
    """
    Mengambil log perubahan terakhir untuk kendaraan tertentu
    
    Args:
        vehicle (str): Nama/ID kendaraan
        
    Returns:
        dict: Data log perubahan terakhir atau None jika tidak ditemukan
    """
    if not vehicle:
        return None
        
    # Cek apakah vehicle tersebut ada
    if not frappe.db.exists("Vehicle", vehicle):
        frappe.throw(_("Kendaraan dengan ID {} tidak ditemukan").format(vehicle))
    
    # Ambil log perubahan terakhir
    logs = frappe.get_all(
        "Vehicle Change Log",
        filters={"vehicle": vehicle},
        fields=[
            "fieldname", 
            "old_value", 
            "new_value", 
            "change_date", 
            "updated_by", 
            "remarks",
            "change_type"
        ],
        order_by="creation desc",
        limit=1
    )
    
    # Return data log atau None jika tidak ada
    return logs[0] if logs else None


@frappe.whitelist()
def get_vehicle_logs(vehicle, limit=10):
    """
    Mengambil beberapa log perubahan terakhir untuk kendaraan tertentu
    
    Args:
        vehicle (str): Nama/ID kendaraan
        limit (int): Jumlah maksimum log yang diambil
        
    Returns:
        list: Data log perubahan atau list kosong jika tidak ditemukan
    """
    if not vehicle:
        return []
        
    # Cek apakah vehicle tersebut ada
    if not frappe.db.exists("Vehicle", vehicle):
        frappe.throw(_("Kendaraan dengan ID {} tidak ditemukan").format(vehicle))
    
    # Ambil log perubahan 
    logs = frappe.get_all(
        "Vehicle Change Log",
        filters={"vehicle": vehicle},
        fields=[
            "fieldname", 
            "old_value", 
            "new_value", 
            "change_date", 
            "updated_by", 
            "remarks",
            "change_type"
        ],
        order_by="creation desc",
        limit=limit
    )
    
    return logs