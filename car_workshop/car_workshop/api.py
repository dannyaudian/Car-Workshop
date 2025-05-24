import frappe
from frappe import _


@frappe.whitelist()
def get_latest_vehicle_log(customer_vehicle):
    """
    Mengambil log perubahan terakhir untuk kendaraan tertentu
    
    Args:
        customer_vehicle (str): Nama/ID kendaraan pelanggan
        
    Returns:
        dict: Data log perubahan terakhir atau None jika tidak ditemukan
    """
    if not customer_vehicle:
        return None
        
    # Cek apakah customer_vehicle tersebut ada
    if not frappe.db.exists("Customer Vehicle", customer_vehicle):
        frappe.throw(_("Kendaraan dengan ID {} tidak ditemukan").format(customer_vehicle))
    
    # Ambil log perubahan terakhir
    logs = frappe.get_all(
        "Vehicle Change Log",
        filters={"customer_vehicle": customer_vehicle},
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
    
    # Return data