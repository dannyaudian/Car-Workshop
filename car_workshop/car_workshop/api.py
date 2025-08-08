import frappe
from frappe import _


@frappe.whitelist()
def get_latest_vehicle_log(customer_vehicle):
    """
    Mengambil log perubahan terakhir untuk kendaraan tertentu.

    Pengguna harus memiliki hak baca pada doctype "Vehicle Change Log" atau pada
    dokumen "Customer Vehicle" yang bersangkutan. Jika tidak, fungsi akan
    mengeluarkan `frappe.PermissionError`.

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

    customer_vehicle_doc = frappe.get_doc("Customer Vehicle", customer_vehicle)

    # Pastikan pengguna memiliki hak baca
    has_log_perm = frappe.has_permission("Vehicle Change Log", ptype="read")
    has_vehicle_perm = frappe.has_permission(
        "Customer Vehicle", doc=customer_vehicle_doc, ptype="read"
    )
    if not has_log_perm and not has_vehicle_perm:
        frappe.throw(
            _("Anda tidak memiliki izin untuk melihat log perubahan kendaraan ini."),
            frappe.PermissionError,
        )

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
    return logs[0] if logs else None
