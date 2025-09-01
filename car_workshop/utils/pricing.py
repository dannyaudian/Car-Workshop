# Copyright (c) 2023, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

from typing import Dict, Optional, Any, Union
from datetime import date
import frappe
from frappe.utils import flt, getdate

def resolve_rate(
    reference_type: str,
    reference_name: str,
    price_list: str,
    posting_date: Optional[Union[str, date]] = None
) -> Dict[str, Any]:
    """
    Resolve the rate for a reference item with the following priority:
    1. Item Price (for Parts linked to Items)
    2. Service Price List as a fallback

    Args:
        reference_type: Type of reference (Job Type, Part, Service Package)
        reference_name: Name of the reference
        price_list: Price list to check
        posting_date: Date for validity check (defaults to today)

    Returns:
        Dict: Dictionary with rate and other pricing details
    """
    from car_workshop.car_workshop.doctype.service_price_list.get_active_service_price import (
        get_active_service_price,
    )

    if not posting_date:
        posting_date = getdate()

    if not (reference_type and reference_name and price_list):
        return None

    # Try fetching Item Price for linked Item
    item_code = frappe.db.get_value(reference_type, reference_name, "item")
    if item_code:
        item_prices = frappe.get_all(
            "Item Price",
            filters={
                "item_code": item_code,
                "price_list": price_list,
                "selling": 1,
            },
            or_filters=[
                {"valid_from": ["<=", posting_date], "valid_upto": [">=", posting_date]},
                {"valid_from": ["<=", posting_date], "valid_upto": ["is", "null"]},
                {"valid_from": ["is", "null"], "valid_upto": [">=", posting_date]},
                {"valid_from": ["is", "null"], "valid_upto": ["is", "null"]},
            ],
            fields=["price_list_rate", "currency"],
            order_by="valid_from desc, creation desc",
            limit=1,
        )
        if item_prices:
            tax_template = frappe.db.get_value(
                "Item Tax Template Item",
                {"parent": item_code, "is_default": 1},
                "item_tax_template",
            ) or None
            return {
                "rate": flt(item_prices[0].price_list_rate),
                "currency": item_prices[0].currency,
                "tax_template": tax_template,
                "source": "Item Price",
            }

    # Fallback to Service Price List helper
    data = get_active_service_price(
        reference_type, reference_name, price_list, posting_date
    )
    if data and data.get("found"):
        return data

    return None

