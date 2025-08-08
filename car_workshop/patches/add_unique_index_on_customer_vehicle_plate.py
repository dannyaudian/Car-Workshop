import frappe

def execute():
    """Ensure plate_number on Customer Vehicle has a unique index"""
    frappe.db.add_index("Customer Vehicle", "plate_number", unique=True)
