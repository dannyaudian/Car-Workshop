// Copyright (c) 2025, Danny Audian and contributors
// For license information, please see license.txt

frappe.ui.form.on('Return Material', {
    refresh: function(frm) {
        // Set up queries
        setup_queries(frm);
        
        // Add custom buttons
        if (frm.doc.docstatus === 1) {
            // Add button to view Stock Entry if created
            if (frm.doc.stock_entry) {
                frm.add_custom_button(__('Stock Entry'), function() {
                    frappe.set_route("Form", "Stock Entry", frm.doc.stock_entry);
                }, __("View"));
            }
            
            // Add button to view Work Order
            frm.add_custom_button(__('Work Order'), function() {
                frappe.set_route("Form", "Work Order", frm.doc.work_order);
            }, __("View"));
        }
        
        // Add button to fetch returnable items for draft documents
        if (frm.doc.docstatus === 0 && frm.doc.work_order) {
            frm.add_custom_button(__('Fetch Returnable Items'), function() {
                fetch_returnable_items(frm);
            }, __("Tools"));
        }
        
        // Add information message for mobile users
        if (frappe.dom.is_touchscreen()) {
            frm.set_intro(__('Swipe left/right to view all columns in the items table'), 'blue');
        }
    },
    
    onload: function(frm) {
        // Set default values for new documents
        if (frm.doc.__islocal) {
            frm.set_value('posting_date', frappe.datetime.get_today());
            frm.set_value('posting_time', frappe.datetime.now_time());
        }
    },
    
    work_order: function(frm) {
        if (frm.doc.work_order) {
            // Prompt to fetch returnable items if empty
            if (!frm.doc.items || frm.doc.items.length === 0) {
                frappe.confirm(
                    __('Do you want to fetch returnable items from this Work Order?'),
                    function() {
                        fetch_returnable_items(frm);
                    }
                );
            }
        }
    },
    
    validate: function(frm) {
        // Calculate totals before saving
        calculate_totals(frm);
    }
});

frappe.ui.form.on('Return Material Item', {
    part: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.part) {
            // Get item code from Part
            frappe.db.get_value('Part', row.part, 'item')
                .then(r => {
                    if (r.message && r.message.item) {
                        frappe.model.set_value(cdt, cdn, 'item_code', r.message.item);
                        
                        // Get item details
                        frappe.db.get_value('Item', r.message.item, ['stock_uom', 'valuation_rate'])
                            .then(r => {
                                if (r.message) {
                                    frappe.model.set_value(cdt, cdn, 'uom', r.message.stock_uom);
                                    
                                    // Only set valuation_rate if not already set
                                    if (!row.valuation_rate) {
                                        frappe.model.set_value(cdt, cdn, 'valuation_rate', r.message.valuation_rate);
                                    }
                                    
                                    // Calculate amount
                                    calculate_amount(cdt, cdn);
                                }
                            });
                    } else {
                        frappe.msgprint(__('No item linked to Part {0}', [row.part]));
                    }
                });
        }
    },
    
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.item_code) {
            // Get item details
            frappe.db.get_value('Item', row.item_code, ['stock_uom', 'valuation_rate'])
                .then(r => {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, 'uom', r.message.stock_uom);
                        
                        // Only set valuation_rate if not already set
                        if (!row.valuation_rate) {
                            frappe.model.set_value(cdt, cdn, 'valuation_rate', r.message.valuation_rate);
                        }
                        
                        // Calculate amount
                        calculate_amount(cdt, cdn);
                    }
                });
        }
    },
    
    qty: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Calculate amount
        calculate_amount(cdt, cdn);
        
        // Validate against Work Order issued qty
        validate_qty_against_work_order(frm, row);
        
        // Update totals
        calculate_totals(frm);
    },
    
    valuation_rate: function(frm, cdt, cdn) {
        // Calculate amount
        calculate_amount(cdt, cdn);
        
        // Update totals
        calculate_totals(frm);
    },
    
    items_add: function(frm, cdt, cdn) {
        // Set default warehouse from parent
        let row = locals[cdt][cdn];
        if (frm.doc.default_warehouse && !row.warehouse) {
            frappe.model.set_value(cdt, cdn, 'warehouse', frm.doc.default_warehouse);
        }
        
        calculate_totals(frm);
    },
    
    items_remove: function(frm) {
        calculate_totals(frm);
    }
});

// Helper functions
function setup_queries(frm) {
    // Set query for warehouse in items table
    frm.set_query('warehouse', 'items', function() {
        return {
            filters: {
                'is_group': 0,
                'company': frappe.defaults.get_user_default('Company')
            }
        };
    });
    
    // Set query for Work Order
    frm.set_query('work_order', function() {
        return {
            filters: {
                'docstatus': 1,
                'status': ['not in', ['Cancelled']]
            }
        };
    });
    
    // Set query for Part in items table
    frm.set_query('part', 'items', function() {
        return {
            filters: {
                'disabled': 0
            }
        };
    });
    
    // Set query for work_order_item in items table
    frm.set_query('work_order_item', 'items', function(doc) {
        return {
            filters: {
                'parent': doc.work_order
            }
        };
    });
}

function calculate_amount(cdt, cdn) {
    let row = locals[cdt][cdn];
    let amount = flt(row.qty) * flt(row.valuation_rate);
    frappe.model.set_value(cdt, cdn, 'amount', amount);
}

function calculate_totals(frm) {
    let total_qty = 0;
    let total_amount = 0;
    
    $.each(frm.doc.items || [], function(i, item) {
        total_qty += flt(item.qty);
        total_amount += flt(item.amount);
    });
    
    frm.set_value('total_qty', total_qty);
    frm.set_value('total_amount', total_amount);
}

function validate_qty_against_work_order(frm, row) {
    if (!frm.doc.work_order || !row.item_code) {
        return;
    }
    
    // Get the Work Order
    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Work Order',
            name: frm.doc.work_order
        },
        callback: function(r) {
            if (!r.message) return;
            
            let work_order = r.message;
            let consumed_qty = 0;
            let item_found = false;
            
            // Find the consumed qty for this item in work order
            if (work_order.part_detail) {
                for (let part of work_order.part_detail) {
                    if ((row.work_order_item && part.name === row.work_order_item) || 
                        (!row.work_order_item && part.item_code === row.item_code)) {
                        consumed_qty = flt(part.consumed_qty);
                        item_found = true;
                        
                        // Set work_order_item if not already set
                        if (!row.work_order_item) {
                            frappe.model.set_value(row.doctype, row.name, 'work_order_item', part.name);
                        }
                        
                        break;
                    }
                }
            }
            
            // Check if this item was found in the work order
            if (!item_found) {
                frappe.show_alert({
                    message: __('Item {0} was not found in Work Order {1}', [row.item_code, frm.doc.work_order]),
                    indicator: 'red'
                }, 5);
                return;
            }
            
            // Get already returned qty from other returns
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Return Material',
                    filters: {
                        'work_order': frm.doc.work_order,
                        'docstatus': 1,
                        'name': ['!=', frm.docname || '']
                    },
                    fields: ['name']
                },
                callback: function(r) {
                    if (!r.message) {
                        check_qty(consumed_qty, 0);
                        return;
                    }
                    
                    // If other returns exist, get their quantities
                    let promises = [];
                    let already_returned = 0;
                    
                    r.message.forEach(ret => {
                        promises.push(new Promise(resolve => {
                            frappe.call({
                                method: 'frappe.client.get',
                                args: {
                                    doctype: 'Return Material',
                                    name: ret.name,
                                    filters: {
                                        'docstatus': 1
                                    }
                                },
                                callback: function(r) {
                                    if (r.message && r.message.items) {
                                        r.message.items.forEach(item => {
                                            if (item.item_code === row.item_code) {
                                                already_returned += flt(item.qty);
                                            }
                                        });
                                    }
                                    resolve();
                                }
                            });
                        }));
                    });
                    
                    // When all return documents are processed
                    Promise.all(promises).then(() => {
                        check_qty(consumed_qty, already_returned);
                    });
                }
            });
            
            // Function to check qty and show alerts
            function check_qty(consumed_qty, already_returned) {
                let available_qty = Math.max(0, consumed_qty - already_returned);
                
                if (flt(row.qty) > available_qty) {
                    frappe.show_alert({
                        message: __('Return quantity {0} exceeds available quantity {1} for item {2}', 
                            [row.qty, available_qty, row.item_code]),
                        indicator: 'red'
                    }, 7);
                    
                    // Add visual indicator to the row
                    let grid_row = frm.fields_dict.items.grid.grid_rows_by_docname[row.name];
                    $(grid_row.columns.qty.field_area).addClass('has-error');
                    
                    // Add warning icon if not already there
                    if (!$(grid_row.columns.qty.field_area).find('.qty-warning').length) {
                        let warning = $(`<i class="fa fa-exclamation-triangle qty-warning" 
                                          style="color: red; margin-left: 5px;" 
                                          title="Exceeds available quantity of ${available_qty}"></i>`);
                        $(grid_row.columns.qty.field_area).append(warning);
                    }
                } else {
                    // Remove error indicators if quantity is valid
                    let grid_row = frm.fields_dict.items.grid.grid_rows_by_docname[row.name];
                    $(grid_row.columns.qty.field_area).removeClass('has-error');
                    $(grid_row.columns.qty.field_area).find('.qty-warning').remove();
                    
                    // If qty is close to max, show informational message
                    if (flt(row.qty) > 0 && flt(row.qty) === available_qty) {
                        frappe.show_alert({
                            message: __('Using maximum available quantity for item {0}', [row.item_code]),
                            indicator: 'blue'
                        }, 4);
                    }
                }
            }
        }
    });
}

function fetch_returnable_items(frm) {
    if (!frm.doc.work_order) {
        frappe.msgprint(__('Please select a Work Order first'));
        return;
    }
    
    frappe.call({
        method: 'car_workshop.car_workshop.doctype.return_material.return_material.get_returnable_items',
        args: {
            work_order: frm.doc.work_order
        },
        freeze: true,
        freeze_message: __('Fetching returnable items...'),
        callback: function(r) {
            if (r.message && r.message.length) {
                let d = new frappe.ui.Dialog({
                    title: __('Select Items to Return'),
                    fields: [
                        {
                            fieldname: 'items_html',
                            fieldtype: 'HTML'
                        }
                    ],
                    primary_action_label: __('Add Selected Items'),
                    primary_action: function() {
                        // Get selected items
                        let selected_items = [];
                        d.fields_dict.items_html.$wrapper.find(':checkbox:checked').each(function() {
                            let idx = $(this).data('idx');
                            if (idx !== undefined) {
                                selected_items.push(r.message[idx]);
                            }
                        });
                        
                        if (selected_items.length === 0) {
                            frappe.msgprint(__('Please select at least one item'));
                            return;
                        }
                        
                        // Add items to the table
                        if (frm.doc.items && frm.doc.items.length > 0) {
                            frappe.confirm(
                                __('Do you want to replace the existing items?'),
                                function() {
                                    // Yes - clear existing and add new
                                    frm.clear_table('items');
                                    add_items_to_table(frm, selected_items);
                                    d.hide();
                                },
                                function() {
                                    // No - add to existing
                                    add_items_to_table(frm, selected_items);
                                    d.hide();
                                }
                            );
                        } else {
                            // No existing items
                            add_items_to_table(frm, selected_items);
                            d.hide();
                        }
                    }
                });
                
                // Generate HTML for the items
                let items_html = `
                    <div class="returnable-items-container" style="max-height: 300px; overflow-y: auto; margin-bottom: 15px;">
                        <table class="table table-bordered">
                            <thead>
                                <tr>
                                    <th style="width: 30px;"><input type="checkbox" id="select-all" title="Select All"></th>
                                    <th>${__('Item')}</th>
                                    <th>${__('Available Qty')}</th>
                                    <th>${__('UOM')}</th>
                                    <th>${__('Valuation Rate')}</th>
                                </tr>
                            </thead>
                            <tbody>
                `;
                
                r.message.forEach((item, idx) => {
                    items_html += `
                        <tr>
                            <td><input type="checkbox" data-idx="${idx}" title="Select"></td>
                            <td>
                                <div><strong>${item.item_code}</strong></div>
                                <div class="text-muted small">${item.item_name || ''}</div>
                            </td>
                            <td>${item.qty}</td>
                            <td>${item.uom}</td>
                            <td>${format_currency(item.valuation_rate)}</td>
                        </tr>
                    `;
                });
                
                items_html += `
                            </tbody>
                        </table>
                    </div>
                    <div class="text-muted small">
                        ${__('Note: Available quantity is calculated as Consumed Qty minus Already Returned Qty')}
                    </div>
                `;
                
                d.fields_dict.items_html.$wrapper.html(items_html);
                
                // Handle select all checkbox
                d.fields_dict.items_html.$wrapper.find('#select-all').on('change', function() {
                    let is_checked = $(this).prop('checked');
                    d.fields_dict.items_html.$wrapper.find('tbody input[type="checkbox"]').prop('checked', is_checked);
                });
                
                d.show();
            } else {
                frappe.msgprint(__('No returnable items found for this Work Order'));
            }
        }
    });
}

function add_items_to_table(frm, items) {
    // Add items to the table
    items.forEach(item => {
        let row = frm.add_child('items');
        row.part = item.part;
        row.item_code = item.item_code;
        row.qty = item.qty;
        row.uom = item.uom;
        row.valuation_rate = item.valuation_rate;
        row.amount = item.amount;
        row.work_order_item = item.work_order_item;
        
        // Set warehouse if default is available
        if (frm.doc.default_warehouse) {
            row.warehouse = frm.doc.default_warehouse;
        }
    });
    
    frm.refresh_field('items');
    calculate_totals(frm);
    frappe.show_alert(__('Added {0} items', [items.length]), 3);
}