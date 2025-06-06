# Copyright (c) 2025, Danny Audian and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, nowdate, nowtime
from frappe.utils.background_jobs import enqueue

class ReturnMaterial(Document):
    def validate(self):
        """
        Validate the Return Material document:
        - Check all required fields
        - Validate returned quantities against work order
        - Calculate total quantities and amounts
        """
        self.validate_required_fields()
        self.validate_qty_against_work_order()
        self.calculate_totals()
        self.set_status()
    
    def on_submit(self):
        """
        On document submission:
        - Create Stock Entry for material return
        - Update Work Order consumed quantities
        - Set document status
        """
        # Use background job if many items
        if len(self.items) > 10:
            enqueue(
                self.make_stock_entry_for_return,
                queue='short',
                timeout=600,
                event='make_stock_entry',
                return_document=self.name
            )
            frappe.msgprint(
                _("Stock Entry creation has been queued. It may take a few minutes to complete.")
            )
        else:
            self.make_stock_entry_for_return()
        
        self.set_status()
    
    def on_cancel(self):
        """
        On document cancellation:
        - Cancel the corresponding Stock Entry
        - Revert Work Order consumed quantities
        - Set document status
        """
        self.cancel_stock_entry_if_exists()
        self.set_status()
    
    def validate_required_fields(self):
        """Validate that all required fields are filled"""
        if not self.work_order:
            frappe.throw(_("Work Order is mandatory"))
        
        if not self.posting_date:
            self.posting_date = getdate(nowdate())
        
        if not self.posting_time:
            self.posting_time = nowtime()
        
        if not self.items or len(self.items) == 0:
            frappe.throw(_("At least one item is required"))
    
    def validate_qty_against_work_order(self):
        """
        Validate that each item's quantity does not exceed what was issued in Work Order
        """
        work_order = frappe.get_doc("Work Order", self.work_order)
        
        # Create a dictionary of consumed quantities from Work Order
        consumed_qty_dict = {}
        
        # Process work order parts to get consumed quantities
        for part in work_order.part_detail:
            if hasattr(part, 'consumed_qty') and part.item_code:
                consumed_qty_dict[part.item_code] = {
                    'consumed_qty': flt(part.consumed_qty),
                    'part': part.part if hasattr(part, 'part') else None,
                    'work_order_item': part.name
                }
        
        # Check if any other return material documents exist for the same work order
        other_returns = frappe.get_all(
            "Return Material",
            filters={
                "work_order": self.work_order,
                "docstatus": 1,
                "name": ["!=", self.name if not self.is_new() else ""]
            },
            fields=["name"]
        )
        
        # If other returns exist, reduce the available quantities
        if other_returns:
            for return_doc_name in other_returns:
                return_doc = frappe.get_doc("Return Material", return_doc_name.name)
                for item in return_doc.items:
                    if item.item_code in consumed_qty_dict:
                        consumed_qty_dict[item.item_code]['consumed_qty'] -= flt(item.qty)
        
        # Validate each item in this document
        for i, item in enumerate(self.items):
            if not item.item_code:
                # Auto-fetch item_code from part if not set
                if item.part:
                    item_code = frappe.db.get_value("Part", item.part, "item")
                    if not item_code:
                        frappe.throw(_("Part {0} at row {1} is not linked to any Item").format(
                            item.part, i+1))
                    item.item_code = item_code
                else:
                    frappe.throw(_("Item Code is required for row {0}").format(i+1))
            
            # Set work_order_item if not set but can be determined
            if not item.work_order_item and item.item_code in consumed_qty_dict:
                item.work_order_item = consumed_qty_dict[item.item_code]['work_order_item']
            
            # Check if item was issued in work order
            if item.item_code not in consumed_qty_dict:
                frappe.throw(_("Item {0} at row {1} was not issued in Work Order {2}").format(
                    item.item_code, i+1, self.work_order))
            
            # Check if return quantity exceeds consumed quantity
            available_qty = consumed_qty_dict[item.item_code]['consumed_qty']
            if flt(item.qty) > available_qty:
                frappe.throw(_("Return quantity {0} for Item {1} at row {2} exceeds available quantity {3}").format(
                    item.qty, item.item_code, i+1, available_qty))
            
            # Update consumed_qty_dict to reflect this return
            consumed_qty_dict[item.item_code]['consumed_qty'] -= flt(item.qty)
            
            # Calculate amount if not set
            if not item.amount:
                item.amount = flt(item.qty) * flt(item.valuation_rate)
    
    def calculate_totals(self):
        """Calculate total quantity and amount"""
        self.total_qty = sum(flt(item.qty) for item in self.items)
        self.total_amount = sum(flt(item.amount) for item in self.items)
    
    def set_status(self):
        """Set document status based on docstatus"""
        if self.docstatus == 0:
            self.status = "Draft"
        elif self.docstatus == 1:
            self.status = "Submitted"
        elif self.docstatus == 2:
            self.status = "Cancelled"
    
    def make_stock_entry_for_return(self):
        """
        Create a Stock Entry of type Material Receipt for the returned materials
        """
        # Check if stock entry already exists
        existing_entry = frappe.db.get_value("Stock Entry", {
            "reference_doctype": self.doctype,
            "reference_docname": self.name,
            "docstatus": 1
        })
        
        if existing_entry:
            frappe.msgprint(_("Stock Entry {0} already exists for this document").format(
                frappe.get_desk_link("Stock Entry", existing_entry)))
            return
        
        # Create new Stock Entry
        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.stock_entry_type = "Material Receipt"
        stock_entry.purpose = "Material Receipt"
        stock_entry.posting_date = self.posting_date
        stock_entry.posting_time = self.posting_time
        stock_entry.set_posting_time = 1
        
        # Set references
        stock_entry.reference_doctype = self.doctype
        stock_entry.reference_docname = self.name
        stock_entry.work_order = self.work_order
        
        # Set company (from warehouse or defaults)
        first_warehouse = self.items[0].warehouse if self.items else None
        if first_warehouse:
            stock_entry.company = frappe.db.get_value("Warehouse", first_warehouse, "company")
        else:
            stock_entry.company = frappe.defaults.get_user_default("Company")
        
        # Add remarks
        stock_entry.remarks = _("Materials returned from Work Order {0}").format(self.work_order)
        if self.remarks:
            stock_entry.remarks += "\n" + self.remarks
        
        # Add items to Stock Entry
        for item in self.items:
            stock_entry.append("items", {
                "s_warehouse": None,  # Material Receipt doesn't need source warehouse
                "t_warehouse": item.warehouse,
                "item_code": item.item_code,
                "qty": item.qty,
                "uom": item.uom,
                "stock_uom": frappe.db.get_value("Item", item.item_code, "stock_uom"),
                "conversion_factor": 1.0,
                "valuation_rate": item.valuation_rate,
                "serial_no": item.serial_no if hasattr(item, "serial_no") else None,
                "batch_no": item.batch_no if hasattr(item, "batch_no") else None,
                "basic_rate": item.valuation_rate,
                "basic_amount": item.amount,
                "transfer_qty": item.qty,
                "reference_doctype": "Work Order Part",
                "reference_docname": item.work_order_item
            })
        
        try:
            # Save and submit the Stock Entry
            stock_entry.flags.ignore_permissions = True
            stock_entry.save()
            stock_entry.submit()
            
            # Save the reference to Stock Entry
            self.db_set("stock_entry", stock_entry.name)
            
            # Update Work Order consumed quantities
            self.update_work_order_consumed_qty()
            
            frappe.msgprint(_("Stock Entry {0} created and submitted").format(
                frappe.get_desk_link("Stock Entry", stock_entry.name)))
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(_("Error creating Stock Entry for Return Material {0}: {1}").format(
                self.name, str(e)), "Return Material Error")
            frappe.throw(_("Error creating Stock Entry: {0}").format(str(e)))
    
    def update_work_order_consumed_qty(self):
        """Update consumed quantities in Work Order"""
        if not self.work_order:
            return
        
        work_order = frappe.get_doc("Work Order", self.work_order)
        updated = False
        
        for item in self.items:
            # Find the matching work order item
            for wo_item in work_order.part_detail:
                if (item.work_order_item and wo_item.name == item.work_order_item) or \
                   (not item.work_order_item and wo_item.item_code == item.item_code):
                    # Reduce consumed quantity by returned quantity
                    wo_item.consumed_qty = max(0, flt(wo_item.consumed_qty) - flt(item.qty))
                    updated = True
                    break
        
        if updated:
            # Save the work order with updated consumed quantities
            work_order.flags.ignore_validate_update_after_submit = True
            work_order.save()
            frappe.db.commit()
    
    def cancel_stock_entry_if_exists(self):
        """Cancel the corresponding Stock Entry if it exists"""
        stock_entry_name = self.stock_entry or frappe.db.get_value(
            "Stock Entry",
            {
                "reference_doctype": self.doctype,
                "reference_docname": self.name,
                "docstatus": 1
            }
        )
        
        if stock_entry_name:
            try:
                stock_entry = frappe.get_doc("Stock Entry", stock_entry_name)
                if stock_entry.docstatus == 1:
                    stock_entry.flags.ignore_permissions = True
                    stock_entry.cancel()
                    frappe.msgprint(_("Stock Entry {0} cancelled").format(
                        frappe.get_desk_link("Stock Entry", stock_entry_name)))
                    
                    # Restore Work Order consumed quantities
                    self.restore_work_order_consumed_qty()
            except Exception as e:
                frappe.log_error(_("Error cancelling Stock Entry {0} for Return Material {1}: {2}").format(
                    stock_entry_name, self.name, str(e)), "Return Material Error")
                frappe.throw(_("Error cancelling Stock Entry: {0}").format(str(e)))
    
    def restore_work_order_consumed_qty(self):
        """Restore consumed quantities in Work Order when return is cancelled"""
        if not self.work_order:
            return
        
        work_order = frappe.get_doc("Work Order", self.work_order)
        updated = False
        
        for item in self.items:
            # Find the matching work order item
            for wo_item in work_order.part_detail:
                if (item.work_order_item and wo_item.name == item.work_order_item) or \
                   (not item.work_order_item and wo_item.item_code == item.item_code):
                    # Add back the returned quantity to consumed_qty
                    wo_item.consumed_qty = flt(wo_item.consumed_qty) + flt(item.qty)
                    updated = True
                    break
        
        if updated:
            # Save the work order with restored consumed quantities
            work_order.flags.ignore_validate_update_after_submit = True
            work_order.save()
            frappe.db.commit()


@frappe.whitelist()
def get_returnable_items(work_order):
    """
    Get items that can be returned from a Work Order
    
    Args:
        work_order: Work Order name
        
    Returns:
        list: List of returnable items
    """
    if not work_order:
        return []
    
    work_order_doc = frappe.get_doc("Work Order", work_order)
    
    # Get all parts with consumed quantities
    returnable_items = []
    
    for part in work_order_doc.part_detail:
        if not hasattr(part, 'consumed_qty') or flt(part.consumed_qty) <= 0:
            continue
        
        # Check if this item has already been fully returned
        existing_returns = frappe.db.sql("""
            SELECT SUM(rmi.qty) as total_returned
            FROM `tabReturn Material Item` rmi
            INNER JOIN `tabReturn Material` rm ON rmi.parent = rm.name
            WHERE rm.work_order = %s
            AND rm.docstatus = 1
            AND rmi.item_code = %s
        """, (work_order, part.item_code), as_dict=1)
        
        total_returned = flt(existing_returns[0].total_returned) if existing_returns else 0
        available_to_return = max(0, flt(part.consumed_qty) - total_returned)
        
        if available_to_return <= 0:
            continue
        
        # Get item details
        item_details = frappe.db.get_value("Item", part.item_code, 
            ["item_name", "stock_uom", "valuation_rate"], as_dict=1)
        
        if not item_details:
            continue
        
        # Get part if available
        part_name = part.part if hasattr(part, 'part') else frappe.db.get_value(
            "Part", {"item": part.item_code}, "name")
        
        returnable_items.append({
            "part": part_name,
            "item_code": part.item_code,
            "item_name": item_details.item_name,
            "qty": available_to_return,
            "consumed_qty": part.consumed_qty,
            "already_returned": total_returned,
            "uom": item_details.stock_uom,
            "valuation_rate": item_details.valuation_rate or part.rate,
            "amount": (item_details.valuation_rate or part.rate) * available_to_return,
            "work_order_item": part.name
        })
    
    return returnable_items