// Copyright (c) 2025, Danny Audian and contributors
// For license information, please see license.txt

frappe.ui.form.on('Workshop Purchase Invoice', {
    refresh: function(frm) {
        // Set up field queries
        setup_field_queries(frm);
        
        // Set up custom buttons
        setup_custom_buttons(frm);
        
        // Calculate totals
        calculate_totals(frm);
        
        // Add Make Payment Entry button for submitted documents without payment
        if (frm.doc.docstatus === 1 && !frm.doc.payment_entry) {
            frm.add_custom_button(__('Make Payment Entry'), async function() {
                await make_payment_entry(frm);
            }).addClass('btn-primary');
        }
        
        // Display payment information if available
        if (frm.doc.payment_entry) {
            frm.set_intro(__(`Payment Entry: ${frm.doc.payment_entry}`), 'blue');
        }
    },
    
    onload: function(frm) {
        // Set default values when creating a new document
        if (frm.doc.__islocal) {
            frm.set_value('invoice_date', frappe.datetime.get_today());
        }
        
        // Initialize the dynamic link options in the items table
        frm.doc.items.forEach(function(item, i) {
            set_reference_doctype(frm, item);
        });
    },
    
    supplier: function(frm) {
        // Auto-fill credit_to account from supplier
        if (frm.doc.supplier) {
            frappe.db.get_value('Supplier', frm.doc.supplier, 'default_payable_account', function(r) {
                if (r && r.default_payable_account) {
                    frm.set_value('credit_to', r.default_payable_account);
                }
            });
        }
    },
    
    tax_amount: function(frm) {
        calculate_totals(frm);
    },
    
    validate: function(frm) {
        validate_items(frm);
        calculate_totals(frm);
    }
});

frappe.ui.form.on('Workshop Purchase Invoice Item', {
    item_type: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        // Reset fields based on type
        frappe.model.set_value(cdt, cdn, 'item_reference', null);
        frappe.model.set_value(cdt, cdn, 'purchase_order', null);
        
        // Set reference_doctype based on item_type
        set_reference_doctype(frm, row);
        
        // Set field properties based on item_type
        if (row.item_type === 'Expense') {
            // For Expense items
            frm.fields_dict.items.grid.update_docfield_property('work_order', 'reqd', 1);
            frm.fields_dict.items.grid.update_docfield_property('purchase_order', 'reqd', 0);
            frm.fields_dict.items.grid.update_docfield_property('purchase_order', 'hidden', 1);
            frm.fields_dict.items.grid.update_docfield_property('item_reference', 'reqd', 0);
            frm.fields_dict.items.grid.update_docfield_property('item_reference', 'hidden', 1);
        } else {
            // For Part or OPL items
            frm.fields_dict.items.grid.update_docfield_property('work_order', 'reqd', 0);
            frm.fields_dict.items.grid.update_docfield_property('purchase_order', 'reqd', 1);
            frm.fields_dict.items.grid.update_docfield_property('purchase_order', 'hidden', 0);
            frm.fields_dict.items.grid.update_docfield_property('item_reference', 'reqd', 1);
            frm.fields_dict.items.grid.update_docfield_property('item_reference', 'hidden', 0);
        }

        frm.refresh_field('items');
    },
    
    purchase_order: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        if (!row.purchase_order) {
            return;
        }
        
        // Auto-fill work_order from purchase_order
        frappe.db.get_value('Workshop Purchase Order', row.purchase_order, 'work_order', function(r) {
            if (r && r.work_order) {
                frappe.model.set_value(cdt, cdn, 'work_order', r.work_order);
            }
        });
        
        // Set query for item_reference based on purchase_order
        update_item_reference_query(frm, row);
    },
    
    item_reference: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        if (!row.item_reference || !row.reference_doctype) {
            return;
        }
        
        // Auto-fill details from item reference
        get_item_reference_details(frm, row, cdt, cdn);
    },
    
    work_order: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // For Expense items, generate a description if empty
        if (row.item_type === 'Expense' && row.work_order && !row.description) {
            frappe.db.get_value('Work Order', row.work_order, 'description', function(r) {
                if (r && r.description) {
                    frappe.model.set_value(cdt, cdn, 'description', 'Expense for WO: ' + r.description);
                }
            });
        }
    },
    
    amount: function(frm, cdt, cdn) {
        calculate_totals(frm);
    },
    
    items_add: function(frm, cdt, cdn) {
        // Set default values for new items
        let row = locals[cdt][cdn];
        set_reference_doctype(frm, row);
    },
    
    items_remove: function(frm, cdt, cdn) {
        calculate_totals(frm);
    }
});

// Helper Functions

/**
 * Create a Payment Entry for the invoice
 * @param {Object} frm - The form object
 * @returns {Promise} - Promise resolving to the payment entry name
 */
async function make_payment_entry(frm) {
    try {
        frappe.dom.freeze(__('Creating Payment Entry...'));
        
        const result = await frappe.call({
            method: 'make_payment_entry',
            doc: frm.doc,
            freeze: true
        });
        
        if (!result.exc) {
            const payment_entry = result.message;
            
            // Update form values
            frm.reload_doc();
            
            // Show success message
            frappe.show_alert({
                message: __('Payment Entry {0} created successfully', [
                    `<a href="/app/payment-entry/${payment_entry}">${payment_entry}</a>`
                ]),
                indicator: 'green'
            }, 5);
            
            return payment_entry;
        }
    } catch (error) {
        frappe.msgprint({
            title: __('Error Creating Payment'),
            indicator: 'red',
            message: __('Could not create Payment Entry: {0}', [error.message || error])
        });
    } finally {
        frappe.dom.unfreeze();
    }
}

function set_reference_doctype(frm, row) {
    // Set the reference_doctype based on item_type
    if (row.item_type === 'Part') {
        row.reference_doctype = 'Workshop Purchase Order Item';
    } else if (row.item_type === 'OPL') {
        row.reference_doctype = 'Job Type Item';
    } else {
        row.reference_doctype = '';
    }
    frm.refresh_field('items');
}

function update_item_reference_query(frm, row) {
    // Set query for item_reference based on item_type and purchase_order
    if (row.item_type === 'Part' && row.purchase_order) {
        frm.fields_dict.items.grid.get_field('item_reference').get_query = function() {
            return {
                filters: {
                    'parent': row.purchase_order,
                    'parenttype': 'Workshop Purchase Order'
                }
            };
        };
    } else if (row.item_type === 'OPL') {
        frm.fields_dict.items.grid.get_field('item_reference').get_query = function() {
            return {
                filters: {
                    'parenttype': 'Job Type'
                }
            };
        };
    }
}

function get_item_reference_details(frm, row, cdt, cdn) {
    // Get details from the referenced document
    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: row.reference_doctype,
            name: row.item_reference
        },
        callback: function(r) {
            if (r.message) {
                let doc = r.message;
                
                // Set description and amount based on the reference document
                if (row.item_type === 'Part') {
                    frappe.model.set_value(cdt, cdn, 'description', doc.description || doc.item_name || '');
                    frappe.model.set_value(cdt, cdn, 'amount', doc.amount || 0);
                } else if (row.item_type === 'OPL') {
                    frappe.model.set_value(cdt, cdn, 'description', doc.description || doc.service_name || '');
                    frappe.model.set_value(cdt, cdn, 'amount', doc.amount || doc.price || 0);
                }
                
                calculate_totals(frm);
            }
        }
    });
}

function calculate_totals(frm) {
    // Calculate bill_total from items
    let bill_total = 0;
    
    if (frm.doc.items && frm.doc.items.length) {
        frm.doc.items.forEach(function(item) {
            bill_total += flt(item.amount);
        });
    }
    
    frm.set_value('bill_total', bill_total);
    
    // Calculate grand_total
    let tax_amount = flt(frm.doc.tax_amount) || 0;
    frm.set_value('grand_total', bill_total + tax_amount);
}

function validate_items(frm) {
    // Validate items before saving
    if (!frm.doc.items || frm.doc.items.length === 0) {
        frappe.throw(__("Please add at least one item"));
        return false;
    }
    
    let valid = true;
    
    frm.doc.items.forEach(function(item, idx) {
        // Check amount is positive
        if (flt(item.amount) <= 0) {
            frappe.throw(__("Amount must be greater than zero for row #{0}", [idx + 1]));
            valid = false;
        }
        
        // Validate based on item_type
        if (item.item_type === 'Expense') {
            if (!item.work_order) {
                frappe.throw(__("Work Order is required for Expense item at row #{0}", [idx + 1]));
                valid = false;
            }
        } else {
            if (!item.purchase_order || !item.item_reference) {
                frappe.throw(__("Purchase Order and Item Reference are required for {0} item at row #{1}", 
                    [item.item_type, idx + 1]));
                valid = false;
            }
        }
    });
    
    return valid;
}

function setup_field_queries(frm) {
    // Set query for supplier
    frm.set_query('supplier', function() {
        return {
            filters: {
                'disabled': 0
            }
        };
    });
    
    // Set query for work_order
    frm.set_query('work_order', function() {
        return {
            filters: {
                'docstatus': 1
            }
        };
    });
    
    // Set query for work_order in items
    frm.set_query('work_order', 'items', function() {
        return {
            filters: {
                'docstatus': 1
            }
        };
    });
    
    // Set query for purchase_order in items
    frm.set_query('purchase_order', 'items', function(doc) {
        return {
            filters: {
                'supplier': doc.supplier,
                'docstatus': 1
            }
        };
    });
}

function setup_custom_buttons(frm) {
    // Add custom buttons based on document state
    if (!frm.doc.__islocal) {
        // Add buttons to view related documents
        
        // Get unique purchase orders
        let pos = Array.from(new Set(frm.doc.items
            .filter(item => item.purchase_order)
            .map(item => item.purchase_order)));
            
        if (pos.length > 0) {
            frm.add_custom_button(__('Purchase Orders'), function() {
                if (pos.length === 1) {
                    frappe.set_route('Form', 'Workshop Purchase Order', pos[0]);
                } else {
                    frappe.route_options = {
                        'name': ['in', pos]
                    };
                    frappe.set_route('List', 'Workshop Purchase Order');
                }
            }, __('View'));
        }
        
        // Get unique work orders
        let wos = Array.from(new Set(frm.doc.items
            .filter(item => item.work_order)
            .map(item => item.work_order)));
            
        if (wos.length === 1) {
            frm.add_custom_button(__('Work Order'), function() {
                frappe.set_route('Form', 'Work Order', wos[0]);
            }, __('View'));
        } else if (wos.length > 1) {
            frm.add_custom_button(__('Work Orders'), function() {
                frappe.route_options = {
                    'name': ['in', wos]
                };
                frappe.set_route('List', 'Work Order');
            }, __('View'));
        }
        
        // Add view Payment Entry button if it exists
        if (frm.doc.payment_entry) {
            frm.add_custom_button(__('Payment Entry'), function() {
                frappe.set_route('Form', 'Payment Entry', frm.doc.payment_entry);
            }, __('View'));
        }
    }
}