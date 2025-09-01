from __future__ import annotations

from typing import Any, Dict, List

import frappe
from frappe import _

from utils.pricing import resolve_rate


@frappe.whitelist()
def get_work_order_billing_source(work_order: str) -> Dict[str, List[Dict[str, Any]]]:
    """Return billable items from a Work Order.

    Args:
        work_order: Name of the Work Order to inspect.
    """
    if not work_order:
        frappe.throw(_("Work Order is required"))

    doc = frappe.get_doc("Work Order", work_order)
    doc.check_permission("read")

    if not frappe.has_permission("Sales Invoice", "create"):
        frappe.throw(_("Not permitted to create Sales Invoice"), frappe.PermissionError)

    if doc.status not in ["Completed", "Closed"]:
        frappe.throw(_("Work Order must be 'Completed' or 'Closed' before billing"))

    if doc.billing_status == "Billed":
        frappe.throw(_("Work Order is already billed"))

    price_list = frappe.db.get_value("Selling Settings", None, "selling_price_list") or "Standard Selling"

    result: Dict[str, List[Dict[str, Any]]] = {
        "job_types": [],
        "service_packages": [],
        "parts": [],
        "external_services": [],
    }

    job_types = frappe.get_all(
        "Work Order Job Type",
        filters={"parent": work_order},
        fields=["job_type", "job_type_name", "hours", "rate"],
    )
    for job in job_types:
        item_code = frappe.db.get_value("Job Type", job.job_type, "item")
        if not item_code:
            continue
        rate = job.rate or resolve_rate(item_code=item_code, price_list=price_list)
        amount = (job.hours or 0) * rate
        result["job_types"].append(
            {
                "job_type": job.job_type,
                "job_type_name": job.job_type_name,
                "hours": job.hours,
                "rate": rate,
                "amount": amount,
            }
        )

    service_packages = frappe.get_all(
        "Work Order Service Package",
        filters={"parent": work_order},
        fields=["service_package", "service_package_name", "quantity", "rate"],
    )
    for package in service_packages:
        item_code = frappe.db.get_value("Service Package", package.service_package, "item")
        if not item_code:
            continue
        rate = package.rate or resolve_rate(item_code=item_code, price_list=price_list)
        amount = (package.quantity or 0) * rate
        result["service_packages"].append(
            {
                "service_package": package.service_package,
                "service_package_name": package.service_package_name,
                "quantity": package.quantity,
                "rate": rate,
                "amount": amount,
            }
        )

    parts = frappe.get_all(
        "Work Order Part",
        filters={"parent": work_order},
        fields=["part", "part_name", "quantity", "rate"],
    )
    for part in parts:
        item_code = frappe.db.get_value("Part", part.part, "item")
        if not item_code:
            continue
        rate = part.rate or resolve_rate(item_code=item_code, price_list=price_list)
        amount = (part.quantity or 0) * rate
        result["parts"].append(
            {
                "part": part.part,
                "part_name": part.part_name,
                "quantity": part.quantity,
                "rate": rate,
                "amount": amount,
            }
        )

    external_services = frappe.get_all(
        "Work Order External Service",
        filters={"parent": work_order},
        fields=["service_name", "provider", "rate"],
    )
    for service in external_services:
        amount = service.rate or 0
        result["external_services"].append(
            {
                "service_name": service.service_name,
                "provider": service.provider,
                "rate": service.rate,
                "amount": amount,
            }
        )

    return result
