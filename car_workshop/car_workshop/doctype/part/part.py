from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from typing import Optional


class Part(Document):
    """
    Part DocType controller.
    
    This DocType represents automotive parts with compatibility information
    for specific vehicle brands and models.
    """
    
    def validate(self) -> None:
        """
        Validate Part document before saving.
        
        Checks:
        - Vehicle model belongs to specified brand in compatibility table
        - Year ranges are valid (start <= end)
        """
        self.validate_compatibility()
        
    def validate_compatibility(self) -> None:
        """
        Validate compatibility entries.
        
        Ensures:
        1. Vehicle models belong to their specified brands
        2. Year ranges are valid (start year <= end year)
        
        Raises:
            frappe.ValidationError: If validation fails
        """
        for entry in self.compatibility:
            if entry.vehicle_model and entry.vehicle_brand:
                # Check if model belongs to the specified brand
                brand = frappe.db.get_value(
                    "Vehicle Model", entry.vehicle_model, "brand"
                )
                if brand != entry.vehicle_brand:
                    frappe.throw(
                        _(
                            "Model {0} does not belong to brand {1}"
                        ).format(entry.vehicle_model, entry.vehicle_brand)
                    )
                    
            # Validate year range
            if entry.year_start and entry.year_end and entry.year_start > entry.year_end:
                frappe.throw(
                    _("Year start cannot be greater than year end for {0}").format(
                        entry.vehicle_model or _("this compatibility entry")
                    )
                )


@frappe.whitelist()
def create_item_from_part(docname: str) -> str:
    """
    Create an Item from a Part document.
    
    Args:
        docname: Name of the Part document
        
    Returns:
        str: Name of the created or existing Item
        
    Raises:
        frappe.ValidationError: If part_number is not set
        frappe.PermissionError: If user doesn't have permission to create Items
    """
    # Check permission to create Item
    if not frappe.has_permission("Item", "create"):
        frappe.throw(
            _("You don't have permission to create Items"),
            frappe.PermissionError
        )
    
    # Load Part document
    part = frappe.get_doc("Part", docname)
    
    # Validate part_number exists
    if not part.part_number:
        frappe.throw(_("Part Number is required to create an Item"))
    
    # Check if Item already exists
    existing_item = frappe.db.exists("Item", part.part_number)
    if existing_item:
        return existing_item
    
    # Get default UOM from Stock Settings
    default_uom = get_default_uom()
    
    # Create new Item
    item = frappe.new_doc("Item")
    item.update({
        "item_code": part.part_number,
        "item_name": part.part_name,
        "brand": part.brand,
        "item_group": "Spare Part",
        "is_stock_item": 1,
        "stock_uom": default_uom,
    })
    
    item.insert()
    
    return item.name


def get_default_uom() -> str:
    """
    Get default UOM from Stock Settings.
    
    Returns:
        str: Default stock UOM or "Nos" if not set
    """
    default_uom: Optional[str] = frappe.db.get_single_value(
        "Stock Settings", "stock_uom"
    )
    return default_uom or "Nos"