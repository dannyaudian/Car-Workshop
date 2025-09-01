"""Utility functions for the Car Workshop app."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import fmt_money


def format_currency_idr(value: float) -> str:
    """Format currency in Indonesian Rupiah."""
    return fmt_money(value, 0, "Rp")


def validate_mandatory_fields(doc, method: str | None = None) -> None:
    """Generic server-side validations applied to all DocTypes.

    - Ensures mandatory fields are not empty.
    - Prevents negative values for numeric fields.
    - Bumps the document version to help track changes.
    """

    for df in doc.meta.get("fields", []):
        value = doc.get(df.fieldname)

        if df.get("reqd") and (value is None or value == ""):
            frappe.throw(_("{0} is mandatory").format(df.label))

        if df.fieldtype in {"Currency", "Int", "Float"} and value is not None and float(value) < 0:
            frappe.throw(_("{0} cannot be negative").format(df.label))

    # Increment document version for change tracking
    current_version = frappe.utils.cint(doc.get("version"))
    doc.version = current_version + 1
