import frappe
from frappe import _

@frappe.whitelist()
def get_active_service_price(reference_type, reference_name, price_list):
    """
    Get active service price for a specific reference and price list
    
    Args:
        reference_type (str): Type of reference (Job Type, Part, Service Package)
        reference_name (str): Name of the reference item
        price_list (str): Name of the price list
        
    Returns:
        dict: Dictionary with rate and tax_template, or None if not found
    """
    # Validate input parameters
    if not reference_type or not reference_name or not price_list:
        frappe.throw(_("Reference type, reference name, and price list are required"))
    
    # Get current date for date validation
    current_date = frappe.utils.today()
    
    # Query for active service price with date validation
    service_price = frappe.get_all(
        "Service Price List",
        filters={
            "reference_type": reference_type,
            "reference_name": reference_name,
            "price_list": price_list,
            "is_active": 1
        },
        or_filters=[
            # No date restrictions
            {"valid_from": ["is", "not set"], "valid_upto": ["is", "not set"]},
            # Only valid_from set and it's before or equal to today
            {"valid_from": ["<=", current_date], "valid_upto": ["is", "not set"]},
            # Only valid_upto set and it's after or equal to today
            {"valid_from": ["is", "not set"], "valid_upto": [">=", current_date]},
            # Both dates set and today is within range
            {"valid_from": ["<=", current_date], "valid_upto": [">=", current_date]}
        ],
        fields=["rate", "tax_template"],
        order_by="valid_from desc",
        limit=1
    )
    
    # Return result or None
    if service_price:
        return {
            "rate": service_price[0].rate,
            "tax_template": service_price[0].tax_template
        }
    else:
        return None