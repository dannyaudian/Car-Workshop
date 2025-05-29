def format_currency_idr(value):
    """Format currency in IDR format"""
    from frappe.utils import fmt_money
    return fmt_money(value, 0, "Rp")