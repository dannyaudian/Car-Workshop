# Copyright (c) 2025, Danny Audian and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint, getdate, nowdate, now_datetime
from frappe.utils.background_jobs import enqueue
from typing import List, Optional, Dict, Any, Union
import json

class PartStockAdjustment(Document):
    def validate(self) -> None:
        """
        Validate the document:
        - Check all required fields
        - Validate items have differences
        - Calculate totals
        """
        self.validate_required_fields()
        self.validate_items_have_differences()
        self.calculate_totals()
        self.update_status()
    
    def on_submit(self) -> None:
        """
        On document submission:
        - Create Stock Entries for adjustments (one for receipt, one for issue)
        - Update document status
        """
        # Use background job if many items
        if len(self.adjustment_items) > 10:
            enqueue(
                self.make_stock_entries,
                queue='short',
                timeout=600,
                event='make_stock_entries',
                adjustment_document=self.name
            )
            frappe.msgprint(
                _("Stock Entry creation has been queued. It may take a few minutes to complete.")
            )
        else:
            self.make_stock_entries()
        
        self.update_status()
    
    def on_cancel(self) -> None:
        """
        On document cancellation:
        - Validate that all linked Stock Entries can be cancelled
        - Cancel Stock Entries
        - Update document status
        """
        # Check if all linked Stock Entries can be cancelled
        self.validate_stock_entries_cancellation()
        
        # Cancel all linked Stock Entries
        self.cancel_stock_entries()
        
        # Update document status
        self.update_status()
    
    def validate_required_fields(self) -> None:
        """Validate that all required fields are filled"""
        if not self.reference_opname:
            frappe.throw(_("Reference Stock Opname is mandatory"))
            
        if not self.warehouse:
            frappe.throw(_("Warehouse is mandatory"))
            
        if not self.posting_date:
            self.posting_date = getdate(nowdate())
            
        if not self.posting_time:
            self.posting_time = now_datetime().strftime('%H:%M:%S')
            
        if not self.adjustment_items or len(self.adjustment_items) == 0:
            frappe.throw(_("At least one adjustment item is required"))
    
    def validate_items_have_differences(self) -> None:
        """Validate that items have differences to adjust"""
        has_difference = False
        
        for item in self.adjustment_items:
            # Calculate difference if not set
            if item.difference == 0:
                difference = flt(item.counted_qty) - flt(item.actual_qty)
                item.difference = difference
            
            if item.difference != 0:
                has_difference = True
        
        if not has_difference:
            frappe.throw(_("No differences found to adjust. Please remove items with zero difference."))
    
    def calculate_totals(self) -> None:
        """Calculate total quantity and value differences"""
        total_qty_diff = 0
        total_value_diff = 0
        
        for item in self.adjustment_items:
            # Ensure difference is calculated
            difference = flt(item.counted_qty) - flt(item.actual_qty)
            item.difference = difference
            
            # Calculate adjustment amount if not set
            if not item.adjustment_amount:
                item.adjustment_amount = flt(item.difference) * flt(item.valuation_rate)
            
            # Sum up totals
            total_qty_diff += flt(item.difference)
            total_value_diff += flt(item.adjustment_amount)
        
        self.total_quantity_difference = total_qty_diff
        self.total_value_difference = total_value_diff
    
    def update_status(self) -> None:
        """Set document status based on docstatus"""
        if self.docstatus == 0:
            self.status = "Draft"
        elif self.docstatus == 1:
            self.status = "Submitted"
        elif self.docstatus == 2:
            self.status = "Cancelled"
    
    def validate_stock_entries_cancellation(self) -> None:
        """
        Validate if all linked Stock Entries can be cancelled
        - Check if all are in 'Submitted' status
        - Block cancellation if any Stock Entry cannot be cancelled
        """
        stock_entries_with_issues = []
        non_cancellable_entries = []
        
        # Check from stock_entry_logs
        if self.stock_entry_logs:
            for log in self.stock_entry_logs:
                if log.stock_entry:
                    se_status = self.check_stock_entry_status(log.stock_entry)
                    
                    if se_status.get('docstatus') == 2:
                        # Already cancelled, so skip
                        continue
                    elif not se_status.get('can_cancel'):
                        # Cannot be cancelled
                        non_cancellable_entries.append({
                            'name': log.stock_entry,
                            'reason': se_status.get('reason'),
                            'entry_type': log.entry_type
                        })
        else:
            # Fallback: Check linked Stock Entries via reference fields
            stock_entries = frappe.get_all("Stock Entry", 
                filters={
                    "reference_doctype": self.doctype,
                    "reference_docname": self.name,
                    "docstatus": 1
                },
                fields=["name", "stock_entry_type"]
            )
            
            for entry in stock_entries:
                se_status = self.check_stock_entry_status(entry.name)
                
                if not se_status.get('can_cancel'):
                    # Cannot be cancelled
                    non_cancellable_entries.append({
                        'name': entry.name,
                        'reason': se_status.get('reason'),
                        'entry_type': entry.stock_entry_type
                    })
        
        # If there are any issues, block cancellation
        if non_cancellable_entries:
            error_msg = _("Cannot cancel this Stock Adjustment because the following Stock Entries cannot be cancelled:")
            error_msg += "<ul>"
            
            for entry in non_cancellable_entries:
                error_msg += "<li><strong>{0}</strong> ({1}): {2}</li>".format(
                    entry['name'], entry['entry_type'], entry['reason'])
            
            error_msg += "</ul>"
            error_msg += _("Please resolve these issues before attempting to cancel this document.")
            
            frappe.throw(error_msg)
    
    def check_stock_entry_status(self, stock_entry_name):
        """
        Helper function to check if a Stock Entry can be cancelled
        
        Args:
            stock_entry_name: Name of the Stock Entry document
            
        Returns:
            dict: Contains status information
                - can_cancel: Boolean indicating if the Stock Entry can be cancelled
                - reason: Reason why it cannot be cancelled (if applicable)
                - docstatus: Current docstatus value
                - stock_entry_type: Type of the Stock Entry
        """
        try:
            stock_entry = frappe.get_doc("Stock Entry", stock_entry_name)
            result = {
                'can_cancel': True,
                'reason': "",
                'docstatus': stock_entry.docstatus,
                'stock_entry_type': stock_entry.stock_entry_type
            }
            
            # If already cancelled, it's fine
            if stock_entry.docstatus == 2:
                return result
            
            # Check if it's in submitted state
            if stock_entry.docstatus != 1:
                result['can_cancel'] = False
                result['reason'] = _("Not in submitted state")
                return result
            
            # Check for dependent documents that would prevent cancellation
            # 1. Check if any dependent GL Entries exist
            gl_entries = frappe.get_all("GL Entry", 
                filters={"voucher_type": "Stock Entry", "voucher_no": stock_entry_name},
                limit=1
            )
            
            if gl_entries:
                # Check if there are any linked payments or journal entries
                dependent_docs = frappe.get_all("Journal Entry Account", 
                    filters={"reference_type": "GL Entry", "reference_name": ["in", [e.name for e in gl_entries]]},
                    fields=["parent"],
                    limit=1
                )
                
                if dependent_docs:
                    result['can_cancel'] = False
                    result['reason'] = _("Has linked Journal Entries")
                    return result
            
            # 2. Check if this Stock Entry has subsequent inventory movements
            current_date = frappe.utils.now_datetime()
            subsequent_entries = frappe.get_all("Stock Ledger Entry",
                filters={
                    "item_code": ["in", [d.item_code for d in stock_entry.items]],
                    "warehouse": ["in", list(set([d.s_warehouse or d.t_warehouse for d in stock_entry.items]))],
                    "posting_date": [">", stock_entry.posting_date],
                    "creation": [">", stock_entry.creation],
                    "voucher_no": ["!=", stock_entry.name]
                },
                limit=1
            )
            
            if subsequent_entries:
                result['can_cancel'] = False
                result['reason'] = _("Has subsequent inventory movements")
                return result
            
            # 3. Check if created in a closed fiscal year
            from frappe.utils.jinja import get_jenv
            try:
                get_jenv().get_template('templates/includes/fiscal_year_controller.html')
                year_closed = frappe.db.get_value("Fiscal Year", {
                    "year_start_date": ["<=", stock_entry.posting_date],
                    "year_end_date": [">=", stock_entry.posting_date]
                }, "closed")
                
                if year_closed:
                    result['can_cancel'] = False
                    result['reason'] = _("Created in a closed fiscal year")
                    return result
            except Exception:
                # Fiscal year template not available, skip this check
                pass
            
            # 4. Check for any custom validations
            try:
                stock_entry.run_method("validate_cancellation")
            except Exception as e:
                result['can_cancel'] = False
                result['reason'] = str(e)
                return result
            
            return result
        except Exception as e:
            return {
                'can_cancel': False,
                'reason': str(e),
                'docstatus': 0,
                'stock_entry_type': "Unknown"
            }
    
    def make_stock_entries(self) -> None:
        """
        Create Stock Entries for the adjustments:
        - One Entry for positive adjustments (Material Receipt)
        - One Entry for negative adjustments (Material Issue)
        """
        positive_items = []
        negative_items = []
        
        # Group items by positive and negative differences
        for item in self.adjustment_items:
            if not item.item_code:
                # Get item code from part
                item_code = frappe.db.get_value("Part", item.part, "item")
                if not item_code:
                    frappe.throw(_("Item Code not found for Part {0}").format(item.part))
                item.item_code = item_code
            
            if flt(item.difference) > 0:
                positive_items.append(item)
            elif flt(item.difference) < 0:
                negative_items.append(item)
        
        stock_entries = []
        
        # Create Stock Entry for positive adjustments (Material Receipt)
        if positive_items:
            receipt_entry = self.create_stock_entry(positive_items, "Material Receipt")
            if receipt_entry:
                stock_entries.append(receipt_entry)
        
        # Create Stock Entry for negative adjustments (Material Issue)
        if negative_items:
            issue_entry = self.create_stock_entry(negative_items, "Material Issue")
            if issue_entry:
                stock_entries.append(issue_entry)
        
        # Store stock entry references
        if stock_entries:
            # Create a list to store stock entry logs
            if not hasattr(self, 'stock_entry_logs'):
                self.stock_entry_logs = []
            
            # Clear existing logs if any
            self.stock_entry_logs = []
            
            for entry in stock_entries:
                # Add to log list
                self.append('stock_entry_logs', {
                    'stock_entry': entry.name,
                    'entry_type': entry.stock_entry_type,
                    'posting_date': entry.posting_date,
                    'created_by': frappe.session.user,
                    'creation_date': now_datetime()
                })
            
            # Save to database
            self.db_update()
            
            # Update HTML field for display
            self.update_stock_entries_html(stock_entries)
            
            frappe.msgprint(_("Stock Entries created: {0}").format(
                ", ".join([entry.name for entry in stock_entries])))
    
    def update_stock_entries_html(self, stock_entries: List[Any]) -> None:
        """
        Update HTML field to show links to stock entries
        Args:
            stock_entries: List of stock entry documents
        """
        stock_entries_html = "<div class='stock-entries-container'>"
        stock_entries_html += "<h4>Stock Entries Created:</h4>"
        stock_entries_html += "<ul>"
        for entry in stock_entries:
            stock_entries_html += "<li><a href='/app/stock-entry/{0}'>{0}</a> ({1})</li>".format(
                entry.name, entry.stock_entry_type)
        
        stock_entries_html += "</ul></div>"
        
        self.db_set('stock_entries_html', stock_entries_html)

    def create_stock_entry(self, items: List[Any], entry_type: str) -> Optional[Any]:
        """
        Create a Stock Entry document for the given items
        Args:
            items: List of items to include in the Stock Entry
            entry_type: Type of Stock Entry (Material Receipt or Material Issue)
        Returns:
            Stock Entry document or None if creation fails
        """
        if not items:
            return None
        
        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.stock_entry_type = entry_type
        stock_entry.purpose = entry_type
        stock_entry.posting_date = self.posting_date
        stock_entry.posting_time = self.posting_time
        stock_entry.set_posting_time = 1
        
        # Set company from warehouse
        company = frappe.db.get_value("Warehouse", self.warehouse, "company")
        if not company:
            company = frappe.defaults.get_user_default("Company")
        stock_entry.company = company
        
        # Set references
        stock_entry.reference_doctype = self.doctype
        stock_entry.reference_docname = self.name
        
        # Add remarks
        stock_entry.remarks = _("Stock adjustment based on Stock Opname {0}").format(self.reference_opname)
        if self.remarks:
            stock_entry.remarks += "\n" + self.remarks
        
        # Add items to Stock Entry
        for item in items:
            se_item = stock_entry.append("items", {
                "item_code": item.item_code,
                "qty": abs(flt(item.difference)),
                "uom": item.uom,
                "stock_uom": item.uom,
                "conversion_factor": 1.0,
                "valuation_rate": item.valuation_rate,
                "basic_rate": item.valuation_rate,
                "basic_amount": abs(flt(item.difference)) * flt(item.valuation_rate),
                "transfer_qty": abs(flt(item.difference)),
                "allow_zero_valuation_rate": 1 if item.valuation_rate == 0 else 0
            })
            
            # Set warehouse based on entry type
            if entry_type == "Material Receipt":
                se_item.t_warehouse = self.warehouse
            else:  # Material Issue
                se_item.s_warehouse = self.warehouse

        try:
            # Save and submit the Stock Entry
            stock_entry.flags.ignore_permissions = True
            stock_entry.insert()
            stock_entry.submit()
            
            frappe.db.commit()
            return stock_entry
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(_("Error creating Stock Entry {0}: {1}").format(
                entry_type, str(e)), "Part Stock Adjustment Error")
            frappe.msgprint(_("Error creating Stock Entry of type {0}: {1}").format(
                entry_type, str(e)), raise_exception=True)
            return None

    def cancel_stock_entries(self) -> None:
        """Cancel all associated Stock Entries"""
        # Get stock entries from logs table
        if self.stock_entry_logs:
            for log in self.stock_entry_logs:
                if log.stock_entry:
                    try:
                        stock_entry = frappe.get_doc("Stock Entry", log.stock_entry)
                        if stock_entry.docstatus == 1:
                            stock_entry.flags.ignore_permissions = True
                            stock_entry.cancel()
                            frappe.msgprint(_("Stock Entry {0} cancelled").format(log.stock_entry))
                    except Exception as e:
                        frappe.log_error(
                            _("Error cancelling Stock Entry {0}: {1}").format(log.stock_entry, str(e)), 
                            "Stock Adjustment Error"
                        )
                        frappe.throw(_("Error cancelling Stock Entry {0}: {1}").format(
                            log.stock_entry, str(e)))
        else:
            # Fallback: Try to find stock entries using reference fields
            stock_entries = frappe.get_all("Stock Entry", 
                filters={
                    "reference_doctype": self.doctype,
                    "reference_docname": self.name,
                    "docstatus": 1
                },
                fields=["name"]
            )
            
            for entry in stock_entries:
                try:
                    stock_entry = frappe.get_doc("Stock Entry", entry.name)
                    stock_entry.flags.ignore_permissions = True
                    stock_entry.cancel()
                    frappe.msgprint(_("Stock Entry {0} cancelled").format(entry.name))
                except Exception as e:
                    frappe.log_error(
                        _("Error cancelling Stock Entry {0}: {1}").format(entry.name, str(e)), 
                        "Stock Adjustment Error"
                    )
                    frappe.throw(_("Error cancelling Stock Entry {0}: {1}").format(
                        entry.name, str(e)))

@frappe.whitelist()
def create_adjustment_from_opname(opname_id: str) -> Optional[Any]:
    """
    Create a stock adjustment from a stock opname
    
    Args:
        opname_id: ID of the stock opname document
        
    Returns:
        Part Stock Adjustment doc or None if no differences found
    """
    if not opname_id:
        frappe.throw(_("Stock Opname ID is required"))
        
    opname = frappe.get_doc("Part Stock Opname", opname_id)
    
    if opname.docstatus != 1:
        frappe.throw(_("Stock Opname must be submitted to create adjustment"))
        
    if opname.status == "Adjusted":
        frappe.throw(_("Stock Adjustment has already been created for this Stock Opname"))
    
    # Create adjustment doc
    adjustment = frappe.new_doc("Part Stock Adjustment")
    adjustment.reference_opname = opname.name
    adjustment.posting_date = nowdate()
    adjustment.posting_time = now_datetime().strftime('%H:%M:%S')
    adjustment.warehouse = opname.warehouse
    adjustment.remarks = _("Created from Stock Opname {0}").format(opname.name)
    
    # Get system quantities and add items
    has_differences = False
    
    # Try to load system quantities from cache in opname
    if hasattr(opname, 'system_quantities_cache') and opname.system_quantities_cache:
        system_quantities = json.loads(opname.system_quantities_cache)
        
        for item in opname.opname_items:
            if not item.part:
                continue
                
            if item.part in system_quantities:
                system_qty = system_quantities[item.part]["actual_qty"]
                difference = flt(item.qty_counted) - system_qty
                
                # Only add items with differences
                if difference != 0:
                    adjustment.append("adjustment_items", {
                        "part": item.part,
                        "item_code": system_quantities[item.part]["item_code"],
                        "actual_qty": system_qty,
                        "counted_qty": item.qty_counted,
                        "difference": difference,
                        "uom": item.uom,
                        "valuation_rate": system_quantities[item.part]["valuation_rate"],
                        "adjustment_amount": difference * system_quantities[item.part]["valuation_rate"]
                    })
                    has_differences = True
    else:
        # Fallback: Query current quantities if cache not available
        for item in opname.opname_items:
            if not item.part:
                continue
                
            # Get item_code from part
            item_code = frappe.db.get_value("Part", item.part, "item")
            if not item_code:
                continue
                
            # Get system quantity
            bin_data = frappe.db.get_value(
                "Bin",
                {"item_code": item_code, "warehouse": opname.warehouse},
                ["actual_qty", "valuation_rate"],
                as_dict=True
            )
            
            system_qty = flt(bin_data.actual_qty) if bin_data else 0
            valuation_rate = flt(bin_data.valuation_rate) if bin_data else 0
            
            difference = flt(item.qty_counted) - system_qty
            
            # Only add items with differences
            if difference != 0:
                adjustment.append("adjustment_items", {
                    "part": item.part,
                    "item_code": item_code,
                    "actual_qty": system_qty,
                    "counted_qty": item.qty_counted,
                    "difference": difference,
                    "uom": item.uom,
                    "valuation_rate": valuation_rate,
                    "adjustment_amount": difference * valuation_rate
                })
                has_differences = True
    
    if not has_differences:
        frappe.msgprint(_("No differences found between counted and system quantities"))
        return None
    
    adjustment.insert(ignore_permissions=True)
    
    # Update stock opname status
    opname.db_set('status', 'Adjusted')

    return adjustment