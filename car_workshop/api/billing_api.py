from __future__ import annotations

from typing import Any, Dict, List

import frappe
from frappe import _
from frappe.utils import flt, nowdate

from car_workshop.utils.pricing import resolve_rate


@frappe.whitelist()
def get_work_order_billing_source(work_order: str) -> Dict[str, List[Dict[str, Any]]]:
    """Collect billable items from a Work Order.

    Args:
        work_order: Work Order document name.

    Returns:
        A dictionary with job types, service packages, parts and external services.
    """
    if not work_order:
        frappe.throw(_("Work Order is required"))

    # Permission checks
    if not frappe.has_permission("Sales Invoice", "create"):
        raise frappe.PermissionError(_("Not permitted to create Sales Invoice"))

    work_order_doc = frappe.get_doc("Work Order", work_order)
    work_order_doc.check_permission("read")

    if work_order_doc.status not in ["Completed", "Closed"]:
        frappe.throw(_("Work Order must be 'Completed' or 'Closed' before billing"))

    if getattr(work_order_doc, "billing_status", None) == "Billed":
        frappe.throw(_("Work Order is already billed"))

    default_price_list = (
        frappe.db.get_value("Selling Settings", None, "selling_price_list")
        or "Standard Selling"
    )
    posting_date = getattr(work_order_doc, "posting_date", nowdate())

    result: Dict[str, List[Dict[str, Any]]] = {
        "job_types": [],
        "service_packages": [],
        "parts": [],
        "external_services": [],
    }

    job_types = frappe.get_all(
        "Work Order Job Type",
        filters={"parent": work_order},
        fields=["job_type", "job_type_name", "hours", "rate", "amount"],
    )
    for job in job_types:
        item_code = frappe.db.get_value("Job Type", job.job_type, "item")
        if not item_code:
            continue
        if not job.rate:
            price = resolve_rate("Job Type", job.job_type, default_price_list, posting_date)
            if price:
                job.rate = price.get("rate")
        job.amount = flt(job.hours) * flt(job.rate)
        result["job_types"].append(job)

    service_packages = frappe.get_all(
        "Work Order Service Package",
        filters={"parent": work_order},
        fields=["service_package", "service_package_name", "quantity", "rate", "amount"],
    )
    for package in service_packages:
        item_code = frappe.db.get_value("Service Package", package.service_package, "item")
        if not item_code:
            continue
        if not package.rate:
            price = resolve_rate(
                "Service Package", package.service_package, default_price_list, posting_date
            )
            if price:
                package.rate = price.get("rate")
        package.amount = flt(package.quantity) * flt(package.rate)
        result["service_packages"].append(package)

    parts = frappe.get_all(
        "Work Order Part",
        filters={"parent": work_order},
        fields=["part", "part_name", "quantity", "rate", "amount"],
    )
    for part in parts:
        item_code = frappe.db.get_value("Part", part.part, "item")
        if not item_code:
            continue
        if not part.rate:
            price = resolve_rate("Part", part.part, default_price_list, posting_date)
            if price:
                part.rate = price.get("rate")
        part.amount = flt(part.quantity) * flt(part.rate)
        result["parts"].append(part)

    external_services = frappe.get_all(
        "Work Order External Service",
        filters={"parent": work_order},
        fields=["service_name", "provider", "rate", "amount"],
    )
    for service in external_services:
        service.amount = flt(service.rate)
        result["external_services"].append(service)

    return result
