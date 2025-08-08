import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field


def execute():
    fields = [
        {
            "dt": "Customer",
            "fieldname": "billing_preference",
            "label": "Billing Preference",
            "fieldtype": "Select",
            "options": "Separate\nConsolidate",
            "insert_after": "customer_name",
            "default": "Separate",
        },
        {
            "dt": "Sales Invoice",
            "fieldname": "consolidated_invoice",
            "label": "Consolidated Invoice",
            "fieldtype": "Check",
            "insert_after": "customer_name",
        },
    ]

    for df in fields:
        if not frappe.db.exists("Custom Field", {"dt": df["dt"], "fieldname": df["fieldname"]}):
            create_custom_field(df["dt"], df)
