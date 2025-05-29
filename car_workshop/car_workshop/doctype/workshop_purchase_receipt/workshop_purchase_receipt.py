import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, cint, getdate, nowdate

class WorkshopPurchaseReceipt(Document):
    def validate(self):
        """
        Validate the Workshop Purchase Receipt
        """
        self.set_supplier_from_po()
        self.validate_purchase_order()
        self.validate_items()
        self.calculate_totals()
    
    def before_submit(self):
        """
        Validations before submission
        """
        # Validate warehouse is set if parts are being received
        if any(item.item_type == "Part" for item in self.items) and not self.warehouse:
            frappe.throw(_("Warehouse is required when receiving parts"))
            
        # Set status to Submitted
        self.status = "Submitted"
    
    def on_submit(self):
        """
        Actions to perform on submission
        """
        self.mark_items_as_received()
        self.update_po_status()
        self.create_stock_entries_if_needed()
        self.add_comment_to_po("Submitted")
    
    def on_cancel(self):
        """
        Actions to perform on cancellation
        """
        self.unmark_items_as_received()
        self.update_po_status()
        self.cancel_linked_stock_entries()
        self.add_comment_to_po("Cancelled")
        
        # Set status to Cancelled
        self.status = "Cancelled"
    
    def set_supplier_from_po(self):
        """
        Set supplier from the selected Purchase Order
        """
        if self.purchase_order and not self.supplier:
            self.supplier = frappe.db.get_value("Workshop Purchase Order", self.purchase_order, "supplier")
    
    def validate_purchase_order(self):
        """
        Validate that the Purchase Order exists and is in the correct state
        """
        if not self.purchase_order:
            frappe.throw(_("Purchase Order is required"))
            
        po_doc = frappe.get_doc("Workshop Purchase Order", self.purchase_order)
        
        if po_doc.docstatus != 1:
            frappe.throw(_("Purchase Order {0} must be submitted before creating a receipt").format(self.purchase_order))
            
        if po_doc.status == "Cancelled":
            frappe.throw(_("Cannot create receipt against cancelled Purchase Order {0}").format(self.purchase_order))
    
    def validate_items(self):
        """
        Validate that items match Purchase Order and quantities are correct
        """
        if not self.items:
            frappe.throw(_("Items cannot be empty"))
            
        # Get all items from the Purchase Order
        po_items = frappe.get_all(
            "Workshop Purchase Order Item",
            filters={"parent": self.purchase_order},
            fields=["name", "item_type", "reference_doctype", "quantity", "rate"]
        )
        
        po_item_map = {item.name: item for item in po_items}
        
        # Get already received quantities for each PO item
        po_item_received_qty = self.get_previously_received_qty()
        
        for item in self.items:
            # Validate the PO item exists
            if not item.po_item or item.po_item not in po_item_map:
                frappe.throw(_("Row {0}: Item not found in Purchase Order {1}").format(
                    item.idx, self.purchase_order))
            
            po_item = po_item_map[item.po_item]
            
            # Set previously received quantity
            item.previously_received_qty = po_item_received_qty.get(item.po_item, 0)
            
            # Validate received quantity is positive
            if flt(item.received_qty) <= 0:
                frappe.throw(_("Row {0}: Received Quantity must be greater than zero").format(item.idx))
            
            # Validate total received quantity doesn't exceed ordered quantity
            total_received = flt(item.previously_received_qty) + flt(item.received_qty)
            if total_received > flt(po_item.quantity):
                frappe.throw(_("Row {0}: Total received quantity ({1}) cannot exceed ordered quantity ({2})").format(
                    item.idx, total_received, po_item.quantity))
            
            # Calculate amount
            item.amount = flt(item.received_qty) * flt(item.rate)
            
            # Set warehouse from parent if not specified
            if not item.warehouse and self.warehouse:
                item.warehouse = self.warehouse
    
    def calculate_totals(self):
        """
        Calculate total received amount
        """
        self.total_received_amount = sum(flt(item.amount) for item in self.items)
    
    def get_previously_received_qty(self):
        """
        Get quantities already received for each PO item
        """
        # Find all submitted receipts for this PO excluding the current one
        previous_receipts = frappe.get_all(
            "Workshop Purchase Receipt",
            filters={
                "purchase_order": self.purchase_order,
                "docstatus": 1,
                "name": ["!=", self.name or "new"]
            },
            fields=["name"]
        )
        
        # Initialize dict to store received quantities
        po_item_received_qty = {}
        
        # If there are previous receipts, sum up the quantities
        if previous_receipts:
            for receipt in previous_receipts:
                receipt_items = frappe.get_all(
                    "Workshop Purchase Receipt Item",
                    filters={"parent": receipt.name},
                    fields=["po_item", "received_qty"]
                )
                
                for item in receipt_items:
                    po_item_received_qty[item.po_item] = po_item_received_qty.get(item.po_item, 0) + flt(item.received_qty)
        
        return po_item_received_qty
    
    def mark_items_as_received(self):
        """
        Mark items as received in the Purchase Order
        """
        if not self.purchase_order:
            return
            
        po_doc = frappe.get_doc("Workshop Purchase Order", self.purchase_order)
        
        # Track if any updates were made
        updated = False
        
        for receipt_item in self.items:
            # Find the corresponding PO item
            for po_item in po_doc.items:
                if po_item.name == receipt_item.po_item:
                    # Update received flag or received_qty
                    if not hasattr(po_item, 'received_qty'):
                        po_item.received = 1
                    else:
                        # If there's a received_qty field, increment it
                        po_item.received_qty = flt(po_item.received_qty) + flt(receipt_item.received_qty)
                    
                    updated = True
                    break
        
        # Only save if updates were made
        if updated:
            po_doc.save(ignore_permissions=True)
    
    def unmark_items_as_received(self):
        """
        Unmark items as received in the Purchase Order when receipt is cancelled
        """
        if not self.purchase_order:
            return
            
        po_doc = frappe.get_doc("Workshop Purchase Order", self.purchase_order)
        
        # Track if any updates were made
        updated = False
        
        for receipt_item in self.items:
            # Find the corresponding PO item
            for po_item in po_doc.items:
                if po_item.name == receipt_item.po_item:
                    # Check if there are other receipts for this item
                    other_receipts = frappe.db.sql("""
                        SELECT SUM(wpri.received_qty)
                        FROM `tabWorkshop Purchase Receipt Item` wpri
                        INNER JOIN `tabWorkshop Purchase Receipt` wpr ON wpri.parent = wpr.name
                        WHERE wpr.purchase_order = %s
                        AND wpri.po_item = %s
                        AND wpr.docstatus = 1
                        AND wpr.name != %s
                    """, (self.purchase_order, receipt_item.po_item, self.name))
                    
                    other_qty = flt(other_receipts[0][0]) if other_receipts and other_receipts[0][0] else 0
                    
                    if not hasattr(po_item, 'received_qty'):
                        # For simple received flag
                        if other_qty == 0:
                            po_item.received = 0
                    else:
                        # For received_qty field
                        po_item.received_qty = other_qty
                    
                    updated = True
                    break
        
        # Only save if updates were made
        if updated:
            po_doc.save(ignore_permissions=True)
    
    def update_po_status(self):
        """
        Update the Purchase Order status based on receipt status
        """
        if not self.purchase_order:
            return
            
        po_doc = frappe.get_doc("Workshop Purchase Order", self.purchase_order)
        
        # Get total received quantities including this receipt
        po_item_received_qty = self.get_previously_received_qty()
        
        # If this is a submission, add quantities from this receipt
        if self.docstatus == 1:
            for item in self.items:
                po_item_received_qty[item.po_item] = po_item_received_qty.get(item.po_item, 0) + flt(item.received_qty)
        
        # Check if all PO items are fully received
        all_items_received = True
        for po_item in po_doc.items:
            received_qty = po_item_received_qty.get(po_item.name, 0)
            if received_qty < flt(po_item.quantity):
                all_items_received = False
                break
        
        # Update the PO status
        if all_items_received:
            po_doc.status = "Received"
        else:
            # Only change from Received to Submitted if this is a cancellation
            if self.docstatus == 2 and po_doc.status == "Received":
                po_doc.status = "Submitted"
        
        po_doc.save(ignore_permissions=True)
        frappe.msgprint(_("Purchase Order {0} status updated to {1}").format(
            self.purchase_order, po_doc.status))
    
    def create_stock_entries_if_needed(self):
        """
        Create stock entries for received parts if needed
        """
        # Only create entries if we have parts and a warehouse
        if not self.warehouse or not any(item.item_type == "Part" for item in self.items):
            return
        
        try:
            # Create a new Stock Entry
            stock_entry = frappe.new_doc("Stock Entry")
            stock_entry.stock_entry_type = "Material Receipt"
            stock_entry.posting_date = self.receipt_date
            stock_entry.set_posting_time = 1
            stock_entry.workshop_purchase_receipt = self.name
            stock_entry.workshop_purchase_order = self.purchase_order
            
            # Add items to the stock entry
            items_added = False
            
            for item in self.items:
                if item.item_type != "Part" or flt(item.received_qty) <= 0:
                    continue
                
                # Get the Item Code from the Part
                item_code = frappe.db.get_value("Part", item.reference_doctype, "item_code")
                if not item_code:
                    frappe.msgprint(_("Skipping Part {0} as it has no Item Code").format(item.reference_doctype))
                    continue
                
                # Add item to stock entry
                stock_entry.append("items", {
                    "item_code": item_code,
                    "qty": item.received_qty,
                    "t_warehouse": item.warehouse or self.warehouse,
                    "basic_rate": item.rate,
                    "valuation_rate": item.rate,
                    "basic_amount": item.amount,
                    "amount": item.amount,
                    "description": item.description or item.reference_doctype,
                    "workshop_purchase_receipt": self.name,
                    "workshop_purchase_receipt_item": item.name
                })
                
                items_added = True
            
            # Only save if there are items
            if items_added:
                stock_entry.save()
                stock_entry.submit()
                frappe.msgprint(_("Stock Entry {0} has been created").format(stock_entry.name))
        
        except Exception as e:
            frappe.log_error(
                message=f"Error creating Stock Entry from Workshop Purchase Receipt {self.name}: {str(e)}",
                title="Stock Entry Creation Error"
            )
            frappe.msgprint(_("Error creating Stock Entry. Please check the error log."))
    
    def cancel_linked_stock_entries(self):
        """
        Cancel any stock entries linked to this receipt
        """
        stock_entries = frappe.get_all(
            "Stock Entry",
            filters={
                "workshop_purchase_receipt": self.name,
                "docstatus": 1
            },
            fields=["name"]
        )
        
        for entry in stock_entries:
            try:
                stock_entry = frappe.get_doc("Stock Entry", entry.name)
                stock_entry.cancel()
                frappe.msgprint(_("Stock Entry {0} has been cancelled").format(entry.name))
            except Exception as e:
                frappe.log_error(
                    message=f"Error cancelling Stock Entry {entry.name}: {str(e)}",
                    title="Stock Entry Cancellation Error"
                )
                frappe.msgprint(_("Error cancelling Stock Entry {0}. Please check the error log.").format(entry.name))
    
    def add_comment_to_po(self, action):
        """
        Add a comment to the Purchase Order
        """
        if not self.purchase_order:
            return
        
        action_text = _("submitted") if action == "Submitted" else _("cancelled")
        
        comment_text = _("""
            Purchase Receipt {0} has been {1}.
            Receipt Date: {2}
            Total Received Amount: {3}
        """).format(
            f"<a href='/app/workshop-purchase-receipt/{self.name}'>{self.name}</a>",
            action_text,
            self.receipt_date,
            frappe.format(self.total_received_amount, {"fieldtype": "Currency"})
        )
        
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": "Workshop Purchase Order",
            "reference_name": self.purchase_order,
            "content": comment_text
        }).insert(ignore_permissions=True)


@frappe.whitelist()
def make_purchase_receipt_from_po(source_name):
    """
    Create a Purchase Receipt from Workshop Purchase Order
    """
    po = frappe.get_doc("Workshop Purchase Order", source_name)
    
    if po.docstatus != 1:
        frappe.throw(_("Purchase Order must be submitted to create a receipt"))
    
    # Create a new receipt
    receipt = frappe.new_doc("Workshop Purchase Receipt")
    receipt.purchase_order = po.name
    receipt.supplier = po.supplier
    receipt.receipt_date = nowdate()
    receipt.warehouse = frappe.db.get_single_value("Stock Settings", "default_warehouse")
    
    # Get already received quantities
    po_item_received_qty = {}
    previous_receipts = frappe.get_all(
        "Workshop Purchase Receipt",
        filters={
            "purchase_order": po.name,
            "docstatus": 1
        },
        fields=["name"]
    )
    
    if previous_receipts:
        for receipt_doc in previous_receipts:
            receipt_items = frappe.get_all(
                "Workshop Purchase Receipt Item",
                filters={"parent": receipt_doc.name},
                fields=["po_item", "received_qty"]
            )
            
            for item in receipt_items:
                po_item_received_qty[item.po_item] = po_item_received_qty.get(item.po_item, 0) + flt(item.received_qty)
    
    # Add items with remaining quantities to receive
    for po_item in po.items:
        received_qty = po_item_received_qty.get(po_item.name, 0)
        remaining_qty = flt(po_item.quantity) - received_qty
        
        if remaining_qty > 0:
            # Determine reference type based on item type
            if po_item.item_type == "Part":
                item_reference_type = "Part"
            elif po_item.item_type == "OPL":
                item_reference_type = "Job Type"
            else:
                item_reference_type = "Expense Type"
            
            receipt.append("items", {
                "po_item": po_item.name,
                "item_type": po_item.item_type,
                "reference_doctype": po_item.reference_doctype,
                "item_reference_type": item_reference_type,
                "description": po_item.description,
                "ordered_qty": po_item.quantity,
                "previously_received_qty": received_qty,
                "received_qty": remaining_qty,
                "uom": po_item.uom,
                "rate": po_item.rate,
                "amount": flt(remaining_qty) * flt(po_item.rate),
                "warehouse": receipt.warehouse
            })
    
    return receipt

@frappe.whitelist()
def get_dashboard_data(data):
    """
    Get dashboard data for the Workshop Purchase Receipt
    """
    data = frappe._dict(data)
    data.transactions = [
        {
            'label': _('Related Documents'),
            'items': ['Stock Entry']
        },
        {
            'label': _('References'),
            'items': ['Workshop Purchase Order']
        }
    ]
    
    return data