frappe.ui.form.on('Workshop Purchase Receipt', {
    refresh: function(frm) {
        // Add custom buttons based on document state
        if (frm.doc.docstatus === 0) {
            // For draft documents
            frm.add_custom_button(__('Get Items from Purchase Order'), function() {
                get_po_items(frm);
            }).addClass('btn-primary');
        }
        
        // Update dashboard information if available
        if (frm.doc.total_received_amount) {
            let dashboard_html = `
                <div class="row">
                    <div class="col-sm-6">
                        <div class="stat-label">${__('Total Received Amount')}</div>
                        <div class="stat-value">${format_currency(frm.doc.total_received_amount)}</div>
                    </div>
                    <div class="col-sm-6">
                        <div class="stat-label">${__('Purchase Order')}</div>
                        <div class="stat-value">
                            <a href="/app/workshop-purchase-order/${frm.doc.purchase_order}">${frm.doc.purchase_order}</a>
                        </div>
                    </div>
                </div>
            `;
            
            $(frm.fields_dict.dashboard_html.wrapper).html(dashboard_html);
        }
    },
    
    onload: function(frm) {
        // Set up query filters
        frm.set_query("purchase_order", function() {
            return {
                filters: {
                    "docstatus": 1,
                    "status": ["in", ["Submitted", "Received"]]
                }
            };
        });
        
        frm.set_query("warehouse", function() {
            return {
                filters: {
                    "is_group": 0
                }
            };
        });
        
        frm.set_query("po_item", "items", function(doc, cdt, cdn) {
            return {
                filters: {
                    "parent": doc.purchase_order
                }
            };
        });
        
        // Set default warehouse if not set
        if (!frm.doc.warehouse && frm.doc.__islocal) {
            frappe.db.get_single_value("Stock Settings", "default_warehouse")
                .then(warehouse => {
                    if (warehouse) {
                        frm.set_value("warehouse", warehouse);
                    }
                });
        }
    },
    
    purchase_order: function(frm) {
        if (frm.doc.purchase_order) {
            // Clear existing items
            frm.clear_table('items');
            frm.refresh_field('items');
            
            // Get purchase order details
            frappe.db.get_doc("Workshop Purchase Order", frm.doc.purchase_order)
                .then(po_doc => {
                    frm.set_value("supplier", po_doc.supplier);
                    
                    // Ask if user wants to fetch items
                    frappe.confirm(
                        __('Do you want to fetch items from this Purchase Order?'),
                        function() {
                            // Yes - fetch items
                            get_po_items(frm);
                        }
                    );
                });
        }
    },
    
    validate: function(frm) {
        // Calculate totals
        calculate_total_amount(frm);
    }
});

frappe.ui.form.on('Workshop Purchase Receipt Item', {
    received_qty: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Validate received quantity
        if (flt(row.received_qty) <= 0) {
            frappe.show_alert({
                message: __('Received quantity must be greater than zero'),
                indicator: 'orange'
            });
        }
        
        // Validate total received quantity doesn't exceed ordered quantity
        let total_received = flt(row.previously_received_qty) + flt(row.received_qty);
        if (total_received > flt(row.ordered_qty)) {
            frappe.show_alert({
                message: __('Total received quantity ({0}) cannot exceed ordered quantity ({1})', 
                          [total_received, row.ordered_qty]),
                indicator: 'red'
            });
        }
        
        // Calculate amount
        calculate_item_amount(frm, cdt, cdn);
    },
    
    rate: function(frm, cdt, cdn) {
        calculate_item_amount(frm, cdt, cdn);
    },
    
    po_item: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        if (row.po_item) {
            // Fetch details from PO item
            frappe.db.get_doc("Workshop Purchase Order Item", row.po_item)
                .then(po_item => {
                    // Set reference fields
                    frappe.model.set_value(cdt, cdn, 'item_type', po_item.item_type);
                    frappe.model.set_value(cdt, cdn, 'reference_doctype', po_item.reference_doctype);
                    frappe.model.set_value(cdt, cdn, 'description', po_item.description);
                    frappe.model.set_value(cdt, cdn, 'ordered_qty', po_item.quantity);
                    frappe.model.set_value(cdt, cdn, 'rate', po_item.rate);
                    frappe.model.set_value(cdt, cdn, 'uom', po_item.uom);
                    
                    // Set reference type based on item type
                    let reference_type = 'Part';
                    if (po_item.item_type === 'OPL') {
                        reference_type = 'Job Type';
                    } else if (po_item.item_type === 'Expense') {
                        reference_type = 'Expense Type';
                    }
                    frappe.model.set_value(cdt, cdn, 'item_reference_type', reference_type);
                    
                    // Get previously received quantity
                    get_previously_received_qty(frm, row);
                });
        }
    },
    
    items_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Set warehouse from parent if not set
        if (!row.warehouse && frm.doc.warehouse) {
            frappe.model.set_value(cdt, cdn, 'warehouse', frm.doc.warehouse);
        }
    }
});

// Helper functions

function calculate_item_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let amount = flt(row.received_qty) * flt(row.rate);
    frappe.model.set_value(cdt, cdn, 'amount', amount);
    
    // Recalculate total
    calculate_total_amount(frm);
}

function calculate_total_amount(frm) {
    let total_amount = 0;
    
    // Sum amounts from all items
    (frm.doc.items || []).forEach(item => {
        total_amount += flt(item.amount);
    });
    
    frm.set_value('total_received_amount', total_amount);
}

function get_previously_received_qty(frm, row) {
    if (!frm.doc.purchase_order || !row.po_item) return;
    
    frappe.call({
        method: "frappe.client.get_value",
        args: {
            doctype: "Workshop Purchase Receipt Item",
            filters: {
                "po_item": row.po_item,
                "docstatus": 1
            },
            fieldname: ["SUM(received_qty) as received_qty"]
        },
        callback: function(r) {
            if (r.message) {
                let previously_received = flt(r.message.received_qty);
                frappe.model.set_value(row.doctype, row.name, 'previously_received_qty', previously_received);
                
                // Set default received quantity to remaining
                let remaining = flt(row.ordered_qty) - previously_received;
                if (remaining > 0 && !row.received_qty) {
                    frappe.model.set_value(row.doctype, row.name, 'received_qty', remaining);
                }
            }
        }
    });
}

function get_po_items(frm) {
    if (!frm.doc.purchase_order) {
        frappe.throw(__("Please select a Purchase Order first"));
        return;
    }
    
    frappe.call({
        method: "car_workshop.car_workshop.doctype.workshop_purchase_receipt.workshop_purchase_receipt.make_purchase_receipt",
        args: {
            source_name: frm.doc.purchase_order
        },
        callback: function(r) {
            if (r.message) {
                // Create a new doc with the returned values
                let new_doc = frappe.model.sync(r.message)[0];
                
                // Update current doc with values from new doc
                frm.clear_table('items');
                
                new_doc.items.forEach(item => {
                    let new_row = frm.add_child('items');
                    Object.keys(item).forEach(key => {
                        new_row[key] = item[key];
                    });
                });
                
                frm.refresh_field('items');
                calculate_total_amount(frm);
                
                frappe.show_alert({
                    message: __('Items fetched from Purchase Order'),
                    indicator: 'green'
                });
            }
        }
    });
}