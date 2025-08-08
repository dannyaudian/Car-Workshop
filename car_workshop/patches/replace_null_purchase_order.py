import frappe


def execute():
    """Set empty string for missing purchase order values"""
    frappe.db.sql(
        """
        update `tabWork Order Part`
        set purchase_order = ''
        where purchase_order is null
        """
    )

