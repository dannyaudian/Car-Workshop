"""Pricing helpers for Car Workshop"""

from __future__ import annotations

from typing import Any, Dict

import frappe
from frappe.utils import flt

from car_workshop.car_workshop.doctype.service_price_list.get_active_service_price import (
    get_active_service_price,
)


def resolve_rate(
    reference_type: str,
    reference_name: str,
    price_list: str,
    posting_date: str,
) -> Dict[str, Any] | None:
    """Resolve the rate for a reference using Item Price or Service Price List.

    Args:
        reference_type: DocType of the reference (e.g. "Part", "Job Type").
        reference_name: Name of the reference document.
        price_list: Selling price list to use for lookup.
        posting_date: Date on which price is applicable.

    Returns:
        A dictionary containing rate information or ``None`` if no price is found.
    """
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
