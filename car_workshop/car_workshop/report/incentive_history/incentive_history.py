import frappe


def execute(filters=None):
    columns = [
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 150},
        {"label": "Work Order", "fieldname": "work_order", "fieldtype": "Link", "options": "Work Order", "width": 150},
        {"label": "Supplementary Of", "fieldname": "supplementary_of", "fieldtype": "Link", "options": "Work Order", "width": 150},
        {"label": "Work Order Billing", "fieldname": "work_order_billing", "fieldtype": "Link", "options": "Work Order Billing", "width": 180},
        {"label": "Salary Component", "fieldname": "salary_component", "fieldtype": "Link", "options": "Salary Component", "width": 150},
        {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 120},
    ]
    data = frappe.get_all(
        "Incentive History",
        fields=["employee", "work_order", "supplementary_of", "work_order_billing", "salary_component", "amount"],
    )
    return columns, data
