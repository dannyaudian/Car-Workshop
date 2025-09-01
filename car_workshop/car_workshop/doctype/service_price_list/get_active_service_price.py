# Copyright (c) 2023, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

from typing import Dict, Optional, Any, Union
from datetime import date

import frappe
from frappe import _
from frappe.utils import getdate, flt, nowdate


@frappe.whitelist()
def get_active_service_price(
    reference_type: str,
    reference_name: str,
    price_list: str,
    posting_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get active price for a service, part, or job type with the following priority:
    1. Item Price (for Parts linked to Items) based on price_list and posting_date
    2. Service Price List as a fallback
    
    Args:
        reference_type: Type of reference (Job Type, Part, Service Package)
        reference_name: Name of the reference item
        price_list: Name of the price list to check
        posting_date: Optional date for which to get the price (defaults to today)
        
    Returns:
        Dict: Dictionary with rate, currency, tax_template, and source information
    """
    # Validate input parameters
    if not reference_type or not reference_name or not price_list:
        frappe.throw(_("Reference type, reference name, and price list are required"))
    
    # Set default posting date if not provided
    if not posting_date:
        posting_date = nowdate()
    
    # For Part type, first try to get Item Price
    if reference_type == "Part":
        item_price_data = get_item_price_for_part(reference_name, price_list, posting_date)
        if item_price_data:
            return item_price_data
    
    # For all other types or if Item Price not found, fall back to Service Price List
    service_price_data = get_service_price_list(reference_type, reference_name, price_list, posting_date)
    if service_price_data:
        return service_price_data
    
    # If no price found, return a structured empty result
    return {
        "rate": 0,
        "currency": frappe.db.get_single_value("Selling Settings", "currency") or "INR",
        "source": "None",
        "tax_template": None,
        "found": False
    }


def get_item_price_for_part(
    part_name: str,
    price_list: str,
    posting_date: str
) -> Optional[Dict[str, Any]]:
    """
    Get Item Price for a Part by looking up its linked Item
    
    Args:
        part_name: Name of the Part
        price_list: Price list to check
        posting_date: Date for which to get the price
        
    Returns:
        Optional[Dict]: Dictionary with price details or None if not found
    """
    # Get the Item code for the Part
    item_code = frappe.db.get_value("Part", part_name, "item")
    
    if not item_code:
        return None
    
    # Try to get Item Price
    item_prices = frappe.get_all(
        "Item Price",
        filters={
            "item_code": item_code,
            "price_list": price_list,
            "selling": 1
        },
        or_filters=[
            {"valid_from": ["<=", posting_date], "valid_upto": [">=", posting_date]},
            {"valid_from": ["<=", posting_date], "valid_upto": ["is", "null"]},
            {"valid_from": ["is", "null"], "valid_upto": [">=", posting_date]},
            {"valid_from": ["is", "null"], "valid_upto": ["is", "null"]}
        ],
        fields=["price_list_rate", "currency"],
        order_by="valid_from desc, creation desc",
        limit=1
    )
    
    if not item_prices:
        return None
    
    # Get default tax template for the item if available
    tax_template = frappe.db.get_value(
        "Item Tax Template Item",
        {"parent": item_code, "is_default": 1},
        "item_tax_template"
    ) or None
    
    # Return structured result
    return {
        "rate": flt(item_prices[0].price_list_rate),
        "currency": item_prices[0].currency,
        "source": "Item Price",
        "tax_template": tax_template,
        "found": True
    }


def get_service_price_list(
    reference_type: str,
    reference_name: str,
    price_list: str,
    posting_date: str
) -> Optional[Dict[str, Any]]:
    """
    Get price from Service Price List
    
    Args:
        reference_type: Type of reference (Job Type, Part, Service Package)
        reference_name: Name of the reference item
        price_list: Price list to check
        posting_date: Date for which to get the price
        
    Returns:
        Optional[Dict]: Dictionary with price details or None if not found
    """
    # Query for active service price with date validation
    service_prices = frappe.get_all(
        "Service Price List",
        filters={
            "reference_type": reference_type,
            "reference_name": reference_name,
            "price_list": price_list,
            "is_active": 1
        },
        or_filters=[
            # No date restrictions
            {"valid_from": ["is", "null"], "valid_upto": ["is", "null"]},
            # Only valid_from set and it's before or equal to posting_date
            {"valid_from": ["<=", posting_date], "valid_upto": ["is", "null"]},
            # Only valid_upto set and it's after or equal to posting_date
            {"valid_from": ["is", "null"], "valid_upto": [">=", posting_date]},
            # Both dates set and posting_date is within range
            {"valid_from": ["<=", posting_date], "valid_upto": [">=", posting_date]}
        ],
        fields=["rate", "currency", "tax_template"],
        order_by="valid_from desc, creation desc",
        limit=1
    )
    
    if not service_prices:
        return None
    
    # Return structured result
    return {
        "rate": flt(service_prices[0].rate),
        "currency": service_prices[0].currency,
        "source": "Service Price List",
        "tax_template": service_prices[0].tax_template,
        "found": True
    }