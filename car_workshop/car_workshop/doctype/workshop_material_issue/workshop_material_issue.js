// Copyright (c) 2025, Danny Audian and contributors
// For license information, please see license.txt

frappe.ui.form.on('Workshop Material Issue', {
    refresh: function(frm) {
        // Set up queries and field settings
        setup_queries(frm);
        
        // Add custom buttons
        setup_custom_buttons(frm);
        
        // Calculate totals
        calculate_totals(frm);
        
        // Disable Save button if no items
        check_items_table(frm);
        
        // Show indicator for submission status
        if (frm.doc.docstatus === 1) {
            frm.dashboard.add_indicator(__("Submitted"), "green");
        } else if (frm.doc.docstatus === 2) {
            frm.dashboard.add_indicator(__("Cancelled"), "red");
        } else {
            frm.dashboard.add_indicator(__("Draft"), "orange");
        }
        
        // Add custom CSS for warnings
        frm.layout.wrapper.find('.insufficient-stock').css('color', 'red');
    },
    
    onload: function(frm) {
        // Set default values for new documents
        if (frm.doc.__islocal) {
            frm.set_value('posting_date', frappe.datetime.get_today());
            
            // Check if we are coming from a Work Order
            if (frappe.route_options && frappe.route_options.work_order) {
                frm.set_value('work_order', frappe.route_options.work_order);
            }
        }
    },
    
    work_order: function(frm) {
        if (frm.doc.work_order) {
            // Get Work Order details
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Work Order',
                    name: frm.doc.work_order
                },
                callback: function(r) {
                    if (r.message) {
                        // Set warehouse from Work Order if empty
                        if (!frm.doc.set_warehouse) {
                            frm.set_value('set_warehouse', r.message.source_warehouse);
                        }
                        
                        // Ask user if they want to fetch required parts
                        if (!frm.doc.items || frm.doc.items.length === 0) {
                            frappe.confirm(
                                __('Do you want to fetch the required parts from this Work Order?'),
                                function() {
                                    // Yes - fetch parts
                                    fetch_work_order_parts(frm);
                                },
                                function() {
                                    // No - do nothing
                                }
                            );
                        }
                    }
                }
            });
        }
    },
    
    set_warehouse: function(frm) {
        // Update rates and stock availability for all items
        if (frm.doc.items && frm.doc.items.length > 0 && frm.doc.set_warehouse) {
            $.each(frm.doc.items || [], function(i, item) {
                check_stock_availability(frm, item.doctype, item.name);
                update_item_rate(frm, item.doctype, item.name);
            });
        }
    },
    
    validate: function(frm) {
        calculate_totals(frm);
        
        // Disable submission if no items
        if (!frm.doc.items || frm.doc.items.length === 0) {
            frappe.throw(__('Please add at least one item to issue'));
            frappe.validated = false;
        }
    },
    
    before_save: function(frm) {
        if (!frm.doc.items || frm.doc.items.length === 0) {
            frappe.throw(__('Please add at least one item to issue'));
            return false;
        }
        return true;
    }
});

frappe.ui.form.on('Workshop Material Issue Item', {
    part: function(frm, cdt, cdn) {
        var item = locals[cdt][cdn];
        if (item.part) {
            // Get part details
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Part',
                    name: item.part
                },
                callback: function(r) {
                    if (r.message) {
                        var part = r.message;
                        
                        // Auto-fetch item_code, description from Part
                        frappe.model.set_value(cdt, cdn, 'item_code', part.item);
                        frappe.model.set_value(cdt, cdn, 'description', part.description);
                        
                        // Get item details for UOM
                        if (part.item) {
                            frappe.call({
                                method: 'frappe.client.get',
                                args: {
                                    doctype: 'Item',
                                    name: part.item
                                },
                                callback: function(r) {
                                    if (r.message) {
                                        var item_doc = r.message;
                                        frappe.model.set_value(cdt, cdn, 'uom', item_doc.stock_uom);
                                        
                                        // Check stock availability and update rate
                                        check_stock_availability(frm, cdt, cdn);
                                        update_item_rate(frm, cdt, cdn);
                                    }
                                }
                            });
                        }
                    }
                }
            });
        }
    },
    
    item_code: function(frm, cdt, cdn) {
        var item = locals[cdt][cdn];
        if (item.item_code) {
            // Get item details for UOM
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Item',
                    name: item.item_code
                },
                callback: function(r) {
                    if (r.message) {
                        var item_doc = r.message;
                        frappe.model.set_value(cdt, cdn, 'uom', item_doc.stock_uom);
                        
                        // Check stock availability and update rate
                        check_stock_availability(frm, cdt, cdn);
                        update_item_rate(frm, cdt, cdn);
                    }
                }
            });
        }
    },
    
    qty: function(frm, cdt, cdn) {
        var item = locals[cdt][cdn];
        
        // Update amount
        frappe.model.set_value(cdt, cdn, 'amount', flt(item.qty) * flt(item.rate));
        
        // Check stock availability
        check_stock_availability(frm, cdt, cdn);
        
        // Calculate totals
        calculate_totals(frm);
    },
    
    rate: function(frm, cdt, cdn) {
        var item = locals[cdt][cdn];
        
        // Update amount
        frappe.model.set_value(cdt, cdn, 'amount', flt(item.qty) * flt(item.rate));
        
        // Calculate totals
        calculate_totals(frm);
    },
    
    items_add: function(frm, cdt, cdn) {
        calculate_totals(frm);
        check_items_table(frm);
    },
    
    items_remove: function(frm, cdt, cdn) {
        calculate_totals(frm);
        check_items_table(frm);
    }
});

// Helper functions
function setup_queries(frm) {
    // Filter warehouse to only show stock warehouses
    frm.set_query('set_warehouse', function() {
        return {
            filters: {
                'is_group': 0,
                'company': frappe.defaults.get_user_default('Company')
            }
        };
    });
    
    // Set Part query
    frm.set_query('part', 'items', function() {
        return {
            filters: {
                'disabled': 0
            }
        };
    });
    
    // Set UOM query
    frm.set_query('uom', 'items', function(doc, cdt, cdn) {
        var item = locals[cdt][cdn];
        return {
            filters: {
                'item': item.item_code
            }
        };
    });
    
    // Set query for work_order
    frm.set_query('work_order', function() {
        return {
            filters: {
                'docstatus': 1,
                'status': ['not in', ['Completed', 'Stopped', 'Closed']]
            }
        };
    });
}

function setup_custom_buttons(frm) {
    if (frm.doc.docstatus === 1) {
        // Add button to view Stock Entry
        if (frm.doc.stock_entry) {
            frm.add_custom_button(__('Stock Entry'), function() {
                frappe.set_route('Form', 'Stock Entry', frm.doc.stock_entry);
            }, __('View'));
        }
        
        // Add button to view Work Order
        frm.add_custom_button(__('Work Order'), function() {
            frappe.set_route('Form', 'Work Order', frm.doc.work_order);
        }, __('View'));
    } else if (frm.doc.docstatus === 0) {
        // Add button to fetch parts from Work Order
        if (frm.doc.work_order) {
            frm.add_custom_button(__('Fetch Parts from Work Order'), function() {
                fetch_work_order_parts(frm);
            });
        }
    }
}

function fetch_work_order_parts(frm) {
    if (!frm.doc.work_order) {
        frappe.msgprint(__('Please select a Work Order first'));
        return;
    }
    
    frappe.call({
        method: 'car_workshop.car_workshop.doctype.workshop_material_issue.workshop_material_issue.get_work_order_parts',
        args: {
            work_order: frm.doc.work_order
        },
        freeze: true,
        freeze_message: __('Fetching parts from Work Order...'),
        callback: function(r) {
            if (r.message && r.message.length) {
                // Clear existing items
                frm.clear_table('items');
                
                // Add new items
                $.each(r.message, function(i, part_data) {
                    var child = frm.add_child('items');
                    $.extend(child, part_data);
                });
                
                frm.refresh_field('items');
                calculate_totals(frm);
                frappe.show_alert(__('Parts fetched successfully'));
            } else {
                frappe.msgprint(__('No parts to issue for this Work Order'));
            }
        }
    });
}

function check_stock_availability(frm, cdt, cdn) {
    var item = locals[cdt][cdn];
    if (!item.item_code || !frm.doc.set_warehouse) {
        return;
    }
    
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'Bin',
            filters: {
                item_code: item.item_code,
                warehouse: frm.doc.set_warehouse
            },
            fieldname: 'actual_qty'
        },
        callback: function(r) {
            if (r.message) {
                var available_qty = flt(r.message.actual_qty);
                
                // Check if qty exceeds available stock
                if (flt(item.qty) > available_qty) {
                    // Add warning indicator
                    var field = frm.fields_dict.items.grid.grid_rows_by_docname[cdn].columns.qty;
                    
                    // Add warning with specific class for styling
                    $(field.field_area).find('.control-value').addClass('insufficient-stock');
                    
                    // Show warning message
                    frappe.show_alert({
                        message: __('Warning: Available quantity of {0} is {1} in {2}', 
                            [item.item_code, available_qty, frm.doc.set_warehouse]),
                        indicator: 'orange'
                    }, 5);
                } else {
                    // Remove warning if previously added
                    var field = frm.fields_dict.items.grid.grid_rows_by_docname[cdn].columns.qty;
                    $(field.field_area).find('.control-value').removeClass('insufficient-stock');
                }
            }
        }
    });
}

function update_item_rate(frm, cdt, cdn) {
    var item = locals[cdt][cdn];
    if (!item.item_code || !frm.doc.set_warehouse) {
        return;
    }
    
    frappe.call({
        method: 'frappe.client.get_value',
        args: {
            doctype: 'Bin',
            filters: {
                item_code: item.item_code,
                warehouse: frm.doc.set_warehouse
            },
            fieldname: 'valuation_rate'
        },
        callback: function(r) {
            if (r.message && r.message.valuation_rate) {
                frappe.model.set_value(cdt, cdn, 'rate', r.message.valuation_rate);
            } else {
                // If no valuation rate in bin, get from item
                frappe.call({
                    method: 'frappe.client.get_value',
                    args: {
                        doctype: 'Item',
                        filters: {
                            name: item.item_code
                        },
                        fieldname: 'valuation_rate'
                    },
                    callback: function(r) {
                        if (r.message) {
                            frappe.model.set_value(cdt, cdn, 'rate', r.message.valuation_rate);
                        }
                    }
                });
            }
        }
    });
}

function calculate_totals(frm) {
    var total_qty = 0;
    var total_amount = 0;
    
    $.each(frm.doc.items || [], function(i, item) {
        total_qty += flt(item.qty);
        total_amount += flt(item.amount);
    });
    
    frm.set_value('total_qty', total_qty);
    frm.set_value('total_amount', total_amount);
}

function check_items_table(frm) {
    // Disable Save button if no items
    if (!frm.doc.items || frm.doc.items.length === 0) {
        frm.disable_save();
        frm.dashboard.add_comment(__('Please add at least one item to issue'), 'yellow');
    } else {
        frm.enable_save();
        // Remove warning if exists
        frm.dashboard.clear_comment();
    }
}

// Add custom button in Work Order to create Material Issue
frappe.ui.form.on('Work Order', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 1 && frm.doc.status !== 'Completed' && frm.doc.status !== 'Stopped') {
            frm.add_custom_button(__('Material Issue'), function() {
                frappe.model.open_mapped_doc({
                    method: 'car_workshop.car_workshop.doctype.work_order.work_order.make_material_issue',
                    frm: frm
                });
            }, __('Create'));
        }
    }
});

// Create a mapped document method for the Work Order
frappe.provide('car_workshop.car_workshop.doctype.work_order.work_order');

car_workshop.car_workshop.doctype.work_order.work_order.make_material_issue = function(frm) {
    frappe.route_options = {
        "work_order": frm.doc.name,
        "set_warehouse": frm.doc.source_warehouse
    };
    frappe.new_doc("Workshop Material Issue");
};