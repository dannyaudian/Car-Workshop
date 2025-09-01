# Copyright (c) 2023, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

from typing import Dict, Optional, Any, Union

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt


def map_to_sales_invoice(wob_name: str) -> str:
    """
    Map Work Order Billing to Sales Invoice
    
    Args:
        wob_name: Work Order Billing document name
        
    Returns:
        str: The created Sales Invoice name
    """
    source_doc = frappe.get_doc("Work Order Billing", wob_name)
    
    # Validate the source document
    if source_doc.docstatus != 1:
        frappe.throw(_("Work Order Billing must be submitted before creating a Sales Invoice"))
        
    if source_doc.sales_invoice:
        frappe.throw(_("Sales Invoice {0} already exists for this Work Order Billing").format(
            source_doc.sales_invoice
        ))
    
    doc = get_mapped_doc(
        "Work Order Billing", 
        wob_name,
        {
            "Work Order Billing": {
                "doctype": "Sales Invoice",
                "field_map": {
                    "name": "work_order_billing",
                    "work_order": "work_order",
                    "customer_vehicle": "customer_vehicle",
                    "transaction_date": "posting_date",
                    "due_date": "due_date"
                },
                "validation": {
                    "docstatus": ["=", 1]
                },
                "postprocess": add_item_rows
            }
        }, 
        None, 
        set_missing_values
    )
    
    doc.save()
    
    # Update source document with Sales Invoice reference
    frappe.db.set_value("Work Order Billing", wob_name, "sales_invoice", doc.name)
    
    return doc.name


def set_missing_values(source: Dict, target: Dict) -> None:
    """
    Set missing values in the target document
    
    Args:
        source: Source document
        target: Target document
    """
    target.is_pos = 0
    target.ignore_pricing_rule = 1
    
    # Copy customer details
    if not target.customer:
        target.customer = source.customer
        target.customer_name = source.customer_name
    
    # Set due date if not set
    if not target.due_date and source.due_date:
        target.due_date = source.due_date
    
    # Set default values
    if hasattr(target, "set_missing_values"):
        target.run_method("set_missing_values")


def add_item_rows(source: Dict, target: Dict, source_parent: Dict) -> None:
    """
    Add all billable items to the Sales Invoice
    
    Args:
        source: Source document
        target: Target document
        source_parent: Parent document
    """
    # Add job type items
    for item in source_parent.get("job_type_items", []):
        item_code = frappe.db.get_value("Job Type", item.job_type, "item")
        if not item_code:
            continue
            
        si_item = target.append("items", {})
        si_item.item_code = item_code
        si_item.qty = item.hours
        si_item.rate = item.rate
        si_item.amount = item.amount
        si_item.description = f"Job: {item.job_type_name}"
        
    # Add service package items
    for item in source_parent.get("service_package_items", []):
        item_code = frappe.db.get_value("Service Package", item.service_package, "item")
        if not item_code:
            continue
            
        si_item = target.append("items", {})
        si_item.item_code = item_code
        si_item.qty = item.quantity
        si_item.rate = item.rate
        si_item.amount = item.amount
        si_item.description = f"Service Package: {item.service_package_name}"
        
    # Add part items
    for item in source_parent.get("part_items", []):
        item_code = frappe.db.get_value("Part", item.part, "item")
        if not item_code:
            continue
            
        si_item = target.append("items", {})
        si_item.item_code = item_code
        si_item.qty = item.quantity
        si_item.rate = item.rate
        si_item.amount = item.amount
        si_item.description = f"Part: {item.part_name}"
        
    # Add external service items
    for item in source_parent.get("external_service_items", []):
        default_service_item = frappe.db.get_single_value(
            "Car Workshop Settings", "default_external_service_item"
        )
        if not default_service_item:
            frappe.throw(_("Please set Default External Service Item in Car Workshop Settings"))
            
        si_item = target.append("items", {})
        si_item.item_code = default_service_item
        si_item.qty = 1
        si_item.rate = item.rate
        si_item.amount = item.amount
        si_item.description = f"External Service: {item.service_name}"
        
    # Add taxes if applicable
    if source_parent.taxes_and_charges:
        target.taxes_and_charges = source_parent.taxes_and_charges
        # Trigger taxes calculation
        if hasattr(target, "calculate_taxes_and_totals"):
            target.run_method("calculate_taxes_and_totals")
        
    # Apply discount if applicable
    if flt(source_parent.discount_amount) > 0:
        target.apply_discount_on = "Grand Total"
        target.discount_amount = source_parent.discount_amount