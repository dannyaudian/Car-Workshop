import frappe
from frappe import _

@frappe.whitelist()
def create_item_from_part(part_name, part_number, brand, category):
    """
    Create a new Item from a Part
    
    Args:
        part_name (str): Name of the part
        part_number (str): Part number to be used as item_code
        brand (str): Brand of the part
        category (str): Category of the part
        
    Returns:
        str: Name of the created Item
    """
    # Validate if an item with the same item_code already exists
    if frappe.db.exists("Item", {"item_code": part_number}):
        frappe.throw(_("An Item with item_code {0} already exists").format(part_number))
    
    # Create a new Item
    item = frappe.new_doc("Item")
    item.item_code = part_number
    item.item_name = part_name
    item.brand = brand
    item.item_group = "Spare Part"
    item.is_stock_item = 1
    item.stock_uom = "Pcs"
    
    # Additional fields you might want to set based on the category
    if category:
        item.item_category = category
    
    # Insert the document
    item.insert()
    
    # Return the name of the created item
    return item.name