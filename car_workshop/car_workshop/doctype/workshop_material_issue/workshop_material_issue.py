# Copyright (c) 2025, Danny Audian and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, nowdate, nowtime
from erpnext.stock.doctype.stock_entry.stock_entry import get_uom_details

class WorkshopMaterialIssue(Document):
    def validate(self):
        """
        Validate the document before saving
        - Check all required fields
        - Validate items
        - Check for duplicates
        - Validate stock availability
        - Validate warehouse status
        """
        self.validate_mandatory_fields()
        self.validate_warehouse()
        self.validate_items()
        self.check_duplicate_parts()
        self.check_for_duplicates()
        self.validate_stock_availability()
        self.calculate_totals()
    
    def on_submit(self):
        """
        On document submission:
        - Create Stock Entry of type 'Material Issue'
        - Update consumed qty in Work Order
        """
        self.status = "Submitted"
        self.create_stock_entry()
        self.update_work_order()
    
    def on_cancel(self):
        """
        On document cancellation:
        - Check document status
        - Reverse the Stock Entry if it exists and is submitted
        - Revert consumed qty in Work Order
        - Log cancellation for audit
        """
        # Verify current status is "Submitted" before proceeding
        if self.status != "Submitted":
            frappe.throw(_("Only submitted documents can be cancelled"))
        
        # Update status first to prevent double cancellation attempts
        self.status = "Cancelled"
        
        # Cancel linked Stock Entry
        self.cancel_stock_entry()
        
        # Update Work Order consumed quantities
        self.update_work_order(cancel=True)
        
        # Log the cancellation
        self.log_cancellation()
    
    def cancel_stock_entry(self):
        """
        Cancel the associated Stock Entry if it exists and is submitted
        """
        # First check if we have a stored reference
        stock_entry_name = self.get("stock_entry")
        
        # If not, try to find it through a query
        if not stock_entry_name:
            stock_entry_name = frappe.db.get_value(
                "Stock Entry", 
                {"workshop_material_issue": self.name, "docstatus": 1}, 
                "name"
            )
        
        if not stock_entry_name:
            frappe.msgprint(_("No submitted Stock Entry found linked to this document"))
            return
        
        try:
            # Get the Stock Entry document
            stock_entry = frappe.get_doc("Stock Entry", stock_entry_name)
            
            # Verify it's not already cancelled
            if stock_entry.docstatus == 2:
                frappe.msgprint(_("Linked Stock Entry {0} is already cancelled").format(
                    frappe.get_desk_link("Stock Entry", stock_entry_name)))
                return
            
            # Only cancel if it's submitted (docstatus=1)
            if stock_entry.docstatus == 1:
                frappe.msgprint(_("Cancelling linked Stock Entry {0}").format(
                    frappe.get_desk_link("Stock Entry", stock_entry_name)))
                
                # Add a comment in the Stock Entry before cancellation
                stock_entry.add_comment(
                    'Comment', 
                    text=_("Cancelled due to cancellation of Workshop Material Issue: {0}").format(self.name)
                )
                
                # Cancel the Stock Entry
                stock_entry.flags.ignore_permissions = True
                stock_entry.cancel()
                
                frappe.msgprint(_("Stock Entry {0} cancelled successfully").format(
                    frappe.get_desk_link("Stock Entry", stock_entry_name)))
                
                # Record the cancellation in this document
                self.db_set("cancellation_date", nowdate())
                self.db_set("cancellation_time", nowtime())
                
        except Exception as e:
            frappe.log_error(
                message=f"Failed to cancel Stock Entry {stock_entry_name}: {str(e)}\n{frappe.get_traceback()}", 
                title=f"Stock Entry Cancellation Failed - {self.name}"
            )
            frappe.throw(_("Failed to cancel Stock Entry: {0}").format(str(e)))
    
    def validate_mandatory_fields(self):
        """Validate that all required fields are filled"""
        if not self.work_order:
            frappe.throw(_("Work Order is mandatory"))
        
        if not self.set_warehouse:
            frappe.throw(_("Source Warehouse is mandatory"))
        
        if not self.posting_date:
            self.posting_date = getdate(nowdate())
        
        if not self.items or len(self.items) == 0:
            frappe.throw(_("At least one item is required"))
    
    def validate_warehouse(self):
        """
        Validate the source warehouse:
        - Ensure it exists
        - Ensure it is enabled
        - Ensure it is a stock warehouse
        """
        if not self.set_warehouse:
            return
        
        warehouse_details = frappe.db.get_value("Warehouse", 
            self.set_warehouse, 
            ["disabled", "is_group", "company"], 
            as_dict=1)
        
        if not warehouse_details:
            frappe.throw(_("Source Warehouse {0} does not exist").format(self.set_warehouse))
        
        if warehouse_details.disabled:
            frappe.throw(_("Source Warehouse {0} is disabled. Please select an active warehouse.").format(
                self.set_warehouse))
        
        if warehouse_details.is_group:
            frappe.throw(_("Source Warehouse {0} is a group warehouse. Please select a non-group warehouse.").format(
                self.set_warehouse))
        
        # Check if warehouse belongs to the right company
        company = frappe.db.get_single_value("Workshop Settings", "company") or frappe.defaults.get_user_default("Company")
        if warehouse_details.company != company:
            frappe.throw(_("Source Warehouse {0} belongs to company {1}, but the current company is {2}").format(
                self.set_warehouse, warehouse_details.company, company))
    
    def validate_items(self):
        """Validate items table and auto-populate details from Part"""
        for i, item in enumerate(self.items):
            if not item.part:
                frappe.throw(_("Part is mandatory at row {0}").format(i+1))
            
            # Validate quantity
            if not item.qty or flt(item.qty) <= 0:
                frappe.throw(_("Quantity must be greater than zero for part {0} at row {1}").format(
                    item.part, i+1))
            
            # Auto-fetch item_code and description from Part if not already set
            if not item.item_code or not item.description:
                part_details = frappe.db.get_value("Part", item.part, ["item", "description"], as_dict=1)
                
                if not part_details:
                    frappe.throw(_("Part {0} does not exist").format(item.part))
                
                if not part_details.item:
                    frappe.throw(_("Part {0} is not linked to any Item. Please link an Item to this Part first.").format(
                        item.part))
                
                item.item_code = part_details.item
                item.description = part_details.description
            
            # Validate the Item exists and is a stock item
            item_details = frappe.db.get_value("Item", 
                item.item_code, ["is_stock_item", "disabled"], as_dict=1)
            
            if not item_details:
                frappe.throw(_("Item Code {0} for Part {1} does not exist").format(
                    item.item_code, item.part))
            
            if item_details.disabled:
                frappe.throw(_("Item {0} for Part {1} is disabled").format(
                    item.item_code, item.part))
            
            if not item_details.is_stock_item:
                frappe.throw(_("Item {0} for Part {1} is not a stock item").format(
                    item.item_code, item.part))
            
            # Get UOM if not set
            if not item.uom and item.item_code:
                item.uom = frappe.db.get_value("Item", item.item_code, "stock_uom")
            
            # Calculate rate and amount
            valuation_rate = self.get_item_valuation_rate(item.item_code)
            item.rate = valuation_rate
            item.amount = flt(item.qty) * flt(item.rate)
    
    def check_duplicate_parts(self):
        """Check for duplicate parts in the items table"""
        parts = []
        for i, item in enumerate(self.items):
            if item.part in parts:
                frappe.throw(_("Duplicate Part {0} found at row {1}. Please combine quantities in a single row.").format(
                    item.part, i+1))
            parts.append(item.part)
    
    def get_item_valuation_rate(self, item_code):
        """Get valuation rate for an item from the specified warehouse"""
        if not item_code or not self.set_warehouse:
            return 0
        
        bin_data = frappe.db.get_value("Bin", 
            {"item_code": item_code, "warehouse": self.set_warehouse},
            "valuation_rate",
            as_dict=1)
        
        if bin_data and bin_data.valuation_rate:
            return flt(bin_data.valuation_rate)
        
        # Fall back to item's valuation rate if bin doesn't exist
        return frappe.db.get_value("Item", item_code, "valuation_rate") or 0
    
    def check_for_duplicates(self):
        """Check for duplicate issues for the same Part in the same Work Order."""
        for item in self.items:
            query = """
                SELECT wmi.name, wmi.docstatus
                FROM `tabWorkshop Material Issue` wmi
                INNER JOIN `tabWorkshop Material Issue Item` wmii
                    ON wmii.parent = wmi.name
                WHERE wmii.part = %s
                    AND wmi.work_order = %s
                    AND wmi.docstatus < 2
            """
            params = [item.part, self.work_order]

            if not self.is_new():
                query += " AND wmi.name != %s"
                params.append(self.name)

            existing_issues = frappe.db.sql(query, params, as_dict=1)

            if existing_issues:
                duplicate = existing_issues[0]
                if duplicate.docstatus == 1:
                    frappe.throw(
                        _(
                            "Part {0} has already been issued for Work Order {1} in Material Issue {2}"
                        ).format(item.part, self.work_order, duplicate.name)
                    )
                else:
                    frappe.throw(
                        _(
                            "Part {0} already exists in draft Material Issue {1} for Work Order {2}"
                        ).format(item.part, duplicate.name, self.work_order)
                    )
    
    def validate_stock_availability(self):
        """Check if there is enough stock for all items in the set warehouse"""
        for item in self.items:
            bin_data = frappe.db.get_value("Bin", 
                {"item_code": item.item_code, "warehouse": self.set_warehouse},
                ["actual_qty", "reserved_qty"],
                as_dict=1) or {"actual_qty": 0, "reserved_qty": 0}
            
            available_qty = flt(bin_data.actual_qty) - flt(bin_data.reserved_qty)
            
            if flt(item.qty) > available_qty:
                frappe.throw(_("Insufficient stock for Part {0} (Item {1}) in {2}. Required: {3}, Available: {4}").format(
                    item.part, item.item_code, self.set_warehouse, item.qty, available_qty))
    
    def calculate_totals(self):
        """Calculate total quantity and amount"""
        self.total_qty = sum(flt(item.qty) for item in self.items)
        self.total_amount = sum(flt(item.amount) for item in self.items)
    
    def create_stock_entry(self):
        """Create a Stock Entry of type Material Issue"""
        try:
            stock_entry = frappe.new_doc("Stock Entry")
            stock_entry.stock_entry_type = "Material Issue"
            stock_entry.purpose = "Material Issue"
            stock_entry.posting_date = self.posting_date
            stock_entry.posting_time = nowtime()
            stock_entry.company = frappe.db.get_single_value("Workshop Settings", "company") or frappe.defaults.get_user_default("Company")
            stock_entry.from_warehouse = self.set_warehouse
            stock_entry.to_warehouse = None  # Material Issue doesn't need a target warehouse
            stock_entry.project = frappe.db.get_value("Work Order", self.work_order, "project")
            stock_entry.work_order = self.work_order
            
            # Add custom field reference
            # Note: Ensure a custom field 'workshop_material_issue' exists in Stock Entry doctype
            stock_entry.workshop_material_issue = self.name
            
            # Add remarks
            stock_entry.remarks = _("Material Issue for Workshop Material Issue: {0}").format(self.name)
            if self.remarks:
                stock_entry.remarks += "\n" + self.remarks
            
            # Add items to Stock Entry
            for item in self.items:
                stock_entry.append("items", {
                    "s_warehouse": self.set_warehouse,
                    "item_code": item.item_code,
                    "qty": item.qty,
                    "uom": item.uom,
                    "stock_uom": frappe.db.get_value("Item", item.item_code, "stock_uom"),
                    "conversion_factor": 1.0,
                    "valuation_rate": item.rate,
                    "serial_no": item.serial_no if item.serial_no else None,
                    "batch_no": item.batch_no if item.batch_no else None,
                    "basic_rate": item.rate,
                    "basic_amount": item.amount,
                    "transfer_qty": item.qty,
                    "description": item.description
                })
            
            # Save and submit the Stock Entry
            stock_entry.flags.ignore_permissions = True
            stock_entry.set_missing_values()
            stock_entry.save()
            stock_entry.submit()
            
            # Save the reference to the Stock Entry in this document
            self.db_set("stock_entry", stock_entry.name)
            
            frappe.msgprint(_("Stock Entry {0} created successfully").format(
                frappe.get_desk_link("Stock Entry", stock_entry.name)))
            
            # Update the status to reflect the stock movement
            self.status = "Submitted"
            
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), _("Stock Entry Creation Failed"))
            frappe.throw(_("Failed to create Stock Entry: {0}").format(str(e)))
    
    def update_work_order(self, cancel=False):
        """
        Update consumed qty in Work Order
        If cancel=True, reduce the consumed quantities
        """
        if not self.work_order:
            return
        
        try:
            work_order = frappe.get_doc("Work Order", self.work_order)
            
            # Track changes for logging
            changes_made = False
            updated_items = []
            
            for item in self.items:
                # Find the matching part in the Work Order
                for wo_item in work_order.part_detail:
                    if wo_item.item_code == item.item_code:
                        previous_qty = flt(getattr(wo_item, "consumed_qty", 0))

                        if cancel:
                            # Ensure we don't go below zero
                            wo_item.consumed_qty = max(0, previous_qty - flt(item.qty))
                        else:
                            wo_item.consumed_qty = previous_qty + flt(item.qty)

                        # Track if any change was made
                        if previous_qty != wo_item.consumed_qty:
                            changes_made = True
                            updated_items.append({
                                "item_code": wo_item.item_code,
                                "previous_qty": previous_qty,
                                "new_qty": wo_item.consumed_qty
                            })

                        break
            
            # Only update if changes were made
            if changes_made:
                # Update Work Order
                work_order.flags.ignore_validate_update_after_submit = True
                
                # Call calculate_total_consumed_qty if it exists
                if hasattr(work_order, 'calculate_total_consumed_qty'):
                    work_order.calculate_total_consumed_qty()
                
                # Save the changes
                work_order.save()
                
                # Add a comment in the Work Order for audit trail
                operation = "decreased" if cancel else "increased"
                comment_text = f"Material consumption {operation} due to {'cancellation of' if cancel else ''} Material Issue: {self.name}"
                work_order.add_comment('Comment', text=comment_text)
                
                # Update Work Order status if the method exists
                if hasattr(work_order, 'update_status'):
                    work_order.update_status()
                
                # Log the update with details
                item_details = ", ".join([
                    f"{item['item_code']}: {item['previous_qty']} → {item['new_qty']}" 
                    for item in updated_items
                ])
                
                frappe.msgprint(_("Consumed quantities updated in Work Order {0}. Items: {1}").format(
                    frappe.get_desk_link("Work Order", self.work_order),
                    item_details
                ))
                
        except Exception as e:
            frappe.log_error(
                message=f"Failed to update Work Order {self.work_order}: {str(e)}\n{frappe.get_traceback()}", 
                title=f"Work Order Update Failed - {self.name}"
            )
            frappe.throw(_("Failed to update Work Order: {0}").format(str(e)))

    def log_cancellation(self):
        """
        Create a log entry for the cancellation for audit purposes
        """
        try:
            # Log in system log
            log_message = f"""
            Workshop Material Issue {self.name} cancelled
            Work Order: {self.work_order}
            Warehouse: {self.set_warehouse}
            Items: {len(self.items)} items with total qty {self.total_qty}
            Cancelled by: {frappe.session.user}
            """
            
            frappe.log_error(
                message=log_message,
                title=f"Workshop Material Issue Cancelled - {self.name}"
            )
            
            # Add a comment in the Work Order for better visibility
            if self.work_order:
                try:
                    work_order = frappe.get_doc("Work Order", self.work_order)
                    work_order.add_comment(
                        'Comment', 
                        text=_("Material Issue {0} has been cancelled. {1} items returned to inventory.").format(
                            self.name, len(self.items)
                        )
                    )
                except Exception:
                    # Don't stop the process if commenting fails
                    pass
            
        except Exception as e:
            # Log the error but don't stop the cancellation process
            frappe.log_error(
                message=f"Failed to create cancellation log: {str(e)}",
                title=f"Cancellation Logging Failed - {self.name}"
            )

@frappe.whitelist()
def get_work_order_parts(work_order):
    """Get required parts from a Work Order using the part detail table"""
    if not work_order:
        return []

    wo = frappe.get_doc("Work Order", work_order)

    required_items = []
    for item in getattr(wo, "part_detail", []) or []:
        if not getattr(item, "item_code", None):
            continue

        # Get stock information
        bin_data = frappe.db.get_value(
            "Bin",
            {"item_code": item.item_code, "warehouse": wo.set_warehouse},
            ["actual_qty", "reserved_qty", "valuation_rate"],
            as_dict=1,
        ) or {"actual_qty": 0, "reserved_qty": 0, "valuation_rate": 0}

        consumed_qty = flt(getattr(item, "consumed_qty", 0))
        required_qty = flt(getattr(item, "quantity", 0))
        remaining_qty = required_qty - consumed_qty

        actual_qty = flt(bin_data.get("actual_qty"))
        reserved_qty = flt(bin_data.get("reserved_qty"))
        rate = flt(bin_data.get("valuation_rate"))
        available_qty = actual_qty - reserved_qty

        if remaining_qty > 0:
            issue_qty = min(remaining_qty, available_qty)
            required_items.append(
                {
                    "part": getattr(item, "part", None),
                    "item_code": item.item_code,
                    "description": getattr(item, "part_name", ""),
                    "qty": issue_qty,
                    "uom": frappe.db.get_value("Item", item.item_code, "stock_uom"),
                    "rate": rate,
                    "amount": rate * issue_qty,
                    "required_qty": required_qty,
                    "consumed_qty": consumed_qty,
                    "available_qty": available_qty,
                    "work_order_item": item.name,
                }
            )

    return required_items
