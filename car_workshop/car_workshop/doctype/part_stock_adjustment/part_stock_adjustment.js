// Copyright (c) 2025, Danny Audian and contributors
// For license information, please see license.txt

frappe.ui.form.on('Part Stock Adjustment', {
    refresh: function(frm) {
        // Set up queries
        setup_queries(frm);
        
        // Add custom buttons for submitted document
        if (frm.doc.docstatus === 1) {
            // Add button to view stock entries if they exist
            if (frm.doc.stock_entry_logs && frm.doc.stock_entry_logs.length > 0) {
                $.each(frm.doc.stock_entry_logs, function(i, log) {
                    if (log.stock_entry) {
                        frm.add_custom_button(__(log.stock_entry), function() {
                            frappe.set_route("Form", "Stock Entry", log.stock_entry);
                        }, __("View Stock Entries"));
                    }
                });
            }
            
        // Add button to view stock opname
        frm.add_custom_button(__('Stock Opname'), function() {
            frappe.set_route("Form", "Part Stock Opname", frm.doc.reference_opname);
        }, __("View"));
    }
    
    // Add button to apply adjustments for draft document
    if (frm.doc.docstatus === 0) {
        frm.add_custom_button(__('Apply Adjustments'), function() {
            if (validate_has_differences(frm)) {
                frappe.confirm(
                    __('This will create stock entries to adjust inventory. Continue?'),
                    function() {
                        frm.save().then(() => frm.savesubmit());
                    }
                );
            }
        }).addClass('btn-primary');
    }
    
    // Add color-coding for differences
    highlight_differences(frm);
},
    
    onload: function(frm) {
        // Set default values for new documents
        if (frm.doc.__islocal) {
            frm.set_value('posting_date', frappe.datetime.get_today());
            frm.set_value('posting_time', frappe.datetime.now_time());
        }
    },
    
    reference_opname: function(frm) {
        if (frm.doc.reference_opname) {
            // Get stock opname details
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Part Stock Opname',
                    name: frm.doc.reference_opname
                },
                callback: function(r) {
                    if (r.message) {
                        var opname = r.message;
                        
                        // Set warehouse from opname
                        frm.set_value('warehouse', opname.warehouse);
                        
                        // Prompt to fetch adjustments
                        if (!frm.doc.adjustment_items || frm.doc.adjustment_items.length === 0) {
                            frappe.confirm(
                                __('Do you want to fetch adjustment items from this Stock Opname?'),
                                function() {
                                    fetch_adjustment_items(frm);
                                }
                            );
                        }
                    }
                }
            });
        }
    },
    
    validate: function(frm) {
        return validate_has_differences(frm);
    }
});

// Helper functions
function setup_queries(frm) {
    // Set query for reference opname
    frm.set_query('reference_opname', function() {
        return {
            filters: {
                'docstatus': 1,
                'status': ['!=', 'Adjusted']
            }
        };
    });
    
    // Set query for warehouse
    frm.set_query('warehouse', function() {
        return {
            filters: {
                'is_group': 0,
                'company': frappe.defaults.get_user_default('Company')
            }
        };
    });
}

function validate_has_differences(frm) {
    let has_difference = false;
    
    if (!frm.doc.adjustment_items || frm.doc.adjustment_items.length === 0) {
        frappe.msgprint(__('No adjustment items found'));
        return false;
    }
    
    $.each(frm.doc.adjustment_items, function(i, item) {
        if (flt(item.difference) !== 0) {
            has_difference = true;
            return false;  // Break the loop
        }
    });
    
    if (!has_difference) {
        frappe.msgprint(__('No differences found to adjust. Please remove items with zero difference.'));
        return false;
    }
    
    return true;
}

function highlight_differences(frm) {
    // Skip if the grid isn't rendered yet
    if (!frm.fields_dict.adjustment_items.grid.grid_rows) {
        return;
    }
    
    // Loop through items and highlight based on difference
    $.each(frm.doc.adjustment_items || [], function(i, item) {
        if (!frm.fields_dict.adjustment_items.grid.grid_rows_by_docname[item.name]) {
            return;
        }
        
        let row = frm.fields_dict.adjustment_items.grid.grid_rows_by_docname[item.name];
        
        // Remove existing highlights
        $(row.row).removeClass('text-danger text-success');
        
        // Add appropriate highlight
        if (flt(item.difference) < 0) {
            $(row.row).addClass('text-danger');
        } else if (flt(item.difference) > 0) {
            $(row.row).addClass('text-success');
        }
        
        // Add visual indicator for difference
        if (row.columns.difference) {
            let difference_cell = $(row.columns.difference.field_area);
            difference_cell.find('.difference-indicator').remove();
            
            if (flt(item.difference) < 0) {
                difference_cell.append('<i class="fa fa-arrow-down text-danger difference-indicator" style="margin-left: 5px;"></i>');
            } else if (flt(item.difference) > 0) {
                difference_cell.append('<i class="fa fa-arrow-up text-success difference-indicator" style="margin-left: 5px;"></i>');
            }
        }
    });
}

function fetch_adjustment_items(frm) {
    if (!frm.doc.reference_opname) {
        frappe.msgprint(__('Please select a Stock Opname first'));
        return;
    }
    
    frm.clear_table('adjustment_items');
    
    frappe.call({
        method: 'car_workshop.car_workshop.doctype.part_stock_adjustment.part_stock_adjustment.create_adjustment_from_opname',
        args: {
            opname_id: frm.doc.reference_opname
        },
        freeze: true,
        freeze_message: __('Fetching adjustment items...'),
        callback: function(r) {
            if (r.message) {
                // Redirect to the new adjustment document
                frappe.set_route("Form", "Part Stock Adjustment", r.message.name);
            } else {
                frappe.msgprint(__('No differences found between counted and system quantities'));
            }
        }
    });
}