/**
 * Car Workshop Module - Workshop Purchase Order
 * 
 * Handles client-side logic for Workshop Purchase Order DocType
 */

// Load utilities
frappe.require('/assets/car_workshop/js/item_utils.js');

frappe.ui.form.on('Workshop Purchase Order', {
    refresh: function(frm) {
        // Only show custom buttons for Draft documents
        if (frm.doc.docstatus === 0) {
            // Add "Fetch Items from Work Order" button
            frm.add_custom_button(__('Fetch Items from Work Order'), function() {
                show_fetch_dialog(frm);
            }).addClass('btn-primary');
            
            // Add "Add Item Manually" button
            frm.add_custom_button(__('Add Item Manually'), function() {
                show_add_item_dialog(frm);
            });
        }
        
        // For submitted documents, show action buttons
        if (frm.doc.docstatus === 1) {
            // Only show Mark as Received button if status is Submitted
            if (frm.doc.status === "Submitted") {
                frm.add_custom_button(__('Mark as Received'), function() {
                    mark_as_received(frm);
                }).addClass('btn-primary');
            }
            
            // Add Generate Receipt button for submitted POs
            frm.add_custom_button(__('Generate Receipt'), function() {
                car_workshop.utils.generate_receipt(frm);
            }, __('Create'));
        }
        
        // Update dashboard information if available
        update_dashboard(frm);
    },
    
    onload: function(frm) {
        // Set up queries and filters for lookup fields
        setup_queries(frm);
        
        // Initialize calculated fields on load
        car_workshop.utils.calculate_totals(frm);
    },
    
    validate: function(frm) {
        validate_form(frm);
    },
    
    work_order: function(frm) {
        if (frm.doc.work_order) {
            // Ask user if they want to fetch items from the work order
            frappe.confirm(
                __('Do you want to fetch items from this Work Order?'),
                function() {
                    // If user confirms, show the fetch dialog
                    show_fetch_dialog(frm);
                }
            );
        }
    },
    
    order_source: function(frm) {
        // Set supplier as mandatory based on order source
        frm.set_df_property('supplier', 'reqd', frm.doc.order_source === 'Beli Baru');
        
        // Show alert if supplier is required but not set
        if (frm.doc.order_source === 'Beli Baru' && !frm.doc.supplier) {
            frappe.show_alert({
                message: __('Please select a Supplier - required for "Beli Baru" source'),
                indicator: 'orange'
            }, 5);
        }
    }
});

// Child table (Workshop Purchase Order Item) events
frappe.ui.form.on('Workshop Purchase Order Item', {
    item_type: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Clear reference field when item type changes
        frappe.model.set_value(cdt, cdn, 'reference_doctype', '');
        
        // Update the reference field label based on item type
        update_reference_label(frm, row);
        
        // Handle tax template if use_default_tax is checked
        if (row.use_default_tax) {
            car_workshop.utils.set_tax_template(frm, row);
        }
    },
    
    reference_doctype: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        if (!row.reference_doctype) return;
        
        // Check if this item already has a purchase order
        if (frm.doc.work_order) {
            car_workshop.utils.check_duplicate_po(frm, row);
        }
        
        // Fetch details based on reference type
        car_workshop.utils.fetch_reference_details(frm, row, cdt, cdn);
    },
    
    use_default_tax: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        car_workshop.utils.set_tax_template(frm, row);
    },
    
    quantity: function(frm, cdt, cdn) {
        car_workshop.utils.calculate_item_amount(frm, cdt, cdn);
    },
    
    rate: function(frm, cdt, cdn) {
        car_workshop.utils.calculate_item_amount(frm, cdt, cdn);
    },
    
    billable: function(frm, cdt, cdn) {
        car_workshop.utils.calculate_totals(frm);
        
        // If billable is checked, ensure work_order is required
        update_work_order_requirement(frm);
    },
    
    items_add: function(frm, cdt, cdn) {
        // Set defaults for new rows
        let row = locals[cdt][cdn];
        set_new_row_defaults(frm, row);
    },
    
    items_remove: function(frm, cdt, cdn) {
        car_workshop.utils.calculate_totals(frm);
        update_work_order_requirement(frm);
    }
});

// Helper Functions

// Update the dashboard display
function update_dashboard(frm) {
    if (frm.doc.total_amount) {
        let dashboard_html = `
            <div class="row">
                <div class="col-sm-4">
                    <div class="stat-label">${__('Total Amount')}</div>
                    <div class="stat-value">${format_currency(frm.doc.total_amount)}</div>
                </div>
                ${frm.doc.billable_amount ? `
                <div class="col-sm-4">
                    <div class="stat-label">${__('Billable Amount')}</div>
                    <div class="stat-value text-success">${format_currency(frm.doc.billable_amount)}</div>
                </div>
                ` : ''}
                ${frm.doc.non_billable_amount ? `
                <div class="col-sm-4">
                    <div class="stat-label">${__('Non-Billable Amount')}</div>
                    <div class="stat-value text-muted">${format_currency(frm.doc.non_billable_amount)}</div>
                </div>
                ` : ''}
            </div>
        `;
        
        $(frm.fields_dict.dashboard_html.wrapper).html(dashboard_html);
    }
}

// Setup queries for lookup fields
function setup_queries(frm) {
    frm.set_query("work_order", function() {
        return {
            filters: {
                "docstatus": 1,
                "status": ["!=", "Cancelled"]
            }
        };
    });
    
    // Set custom queries for items table
    frm.set_query("reference_doctype", "items", function(doc, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        if (row.item_type === "Part") {
            return {
                doctype: "Part",
                filters: {
                    "docstatus": 1
                }
            };
        } else if (row.item_type === "OPL") {
            return {
                doctype: "Job Type",
                filters: {
                    "is_opl": 1
                }
            };
        } else if (row.item_type === "Expense") {
            return {
                doctype: "Expense Type"
            };
        }
        
        return {};
    });
    
    // Setup tax template query
    frm.set_query("tax_template", "items", function() {
        return {
            doctype: "Purchase Taxes and Charges Template"
        };
    });
}

// Validate the form before saving
function validate_form(frm) {
    // Validate required fields based on conditional logic
    if (frm.doc.order_source === "Beli Baru" && !frm.doc.supplier) {
        frappe.validated = false;
        frappe.throw(__("Supplier is mandatory when Order Source is 'Beli Baru'"));
    }
    
    // Validate items exist
    if (!frm.doc.items || frm.doc.items.length === 0) {
        frappe.validated = false;
        frappe.throw(__("At least one item is required"));
    }
    
    // Validate all billable items have work order
    if (car_workshop.utils.has_billable_items(frm.doc) && !frm.doc.work_order) {
        frappe.validated = false;
        frappe.throw(__("Work Order is mandatory when there are billable items"));
    }
    
    // Calculate totals before submission
    car_workshop.utils.calculate_totals(frm);
}

// Update reference label based on item type
function update_reference_label(frm, row) {
    let label = 'Reference';
    
    if (row.item_type === 'Part') {
        label = 'Part';
    } else if (row.item_type === 'OPL') {
        label = 'Job Type';
    } else if (row.item_type === 'Expense') {
        label = 'Expense Type';
    }
    
    frm.fields_dict.items.grid.update_docfield_property(
        'reference_doctype', 'label', label
    );
}

// Update work order requirement based on billable items
function update_work_order_requirement(frm) {
    // If billable is checked, ensure work_order is required
    if (car_workshop.utils.has_billable_items(frm.doc)) {
        frm.set_df_property('work_order', 'reqd', true);
        
        // Alert if work_order not set
        if (!frm.doc.work_order) {
            frappe.show_alert({
                message: __('Please select a Work Order - required for billable items'),
                indicator: 'orange'
            }, 5);
        }
    } else {
        frm.set_df_property('work_order', 'reqd', false);
    }
}

// Set defaults for new row
function set_new_row_defaults(frm, row) {
    frappe.model.set_value(row.doctype, row.name, 'quantity', 1);
    frappe.model.set_value(row.doctype, row.name, 'billable', 1);
    frappe.model.set_value(row.doctype, row.name, 'use_default_tax', 1);
    
    if (frm.doc.work_order) {
        frappe.model.set_value(row.doctype, row.name, 'work_order', frm.doc.work_order);
    }
}

// Show dialog to fetch items from work order
function show_fetch_dialog(frm) {
    if (!frm.doc.work_order) {
        frappe.throw(__("Please select a Work Order first"));
        return;
    }
    
    // Create a simplified dialog for mobile
    if (frappe.utils.is_mobile()) {
        show_mobile_fetch_dialog(frm);
        return;
    }
    
    // Full-featured dialog for desktop
    let dialog = new frappe.ui.Dialog({
        title: __('Fetch Items from Work Order'),
        fields: [
            {
                fieldname: 'work_order_display',
                fieldtype: 'HTML',
                options: `<div class="alert alert-info">
                    ${__('Selected Work Order')}: <strong>${frm.doc.work_order}</strong>
                </div>`
            },
            {
                fieldname: 'item_types_section',
                fieldtype: 'Section Break',
                label: __('Item Types to Fetch')
            },
            {
                fieldname: 'fetch_parts',
                fieldtype: 'Check',
                label: __('Fetch Parts'),
                default: 1
            },
            {
                fieldname: 'fetch_opl',
                fieldtype: 'Check',
                label: __('Fetch OPL Jobs'),
                default: 1
            },
            {
                fieldname: 'fetch_expenses',
                fieldtype: 'Check',
                label: __('Fetch Expenses'),
                default: 1
            },
            {
                fieldname: 'col_break1',
                fieldtype: 'Column Break'
            },
            {
                fieldname: 'only_without_po',
                fieldtype: 'Check',
                label: __('Only Items Without PO'),
                default: 1
            },
            {
                fieldname: 'mark_billable',
                fieldtype: 'Check',
                label: __('Mark as Billable'),
                default: 1
            },
            {
                fieldname: 'filter_section',
                fieldtype: 'Section Break',
                label: __('Additional Filters')
            },
            {
                fieldname: 'filter_by_text',
                fieldtype: 'Data',
                label: __('Filter by Text'),
                description: __('Filter items by name or description')
            }
        ],
        primary_action_label: __('Fetch Items'),
        primary_action: function(values) {
            car_workshop.utils.fetch_work_order_items(frm, values);
            dialog.hide();
        }
    });
    
    dialog.show();
}

// Simplified mobile dialog
function show_mobile_fetch_dialog(frm) {
    let fields = [
        {
            fieldname: 'item_type',
            fieldtype: 'Select',
            label: __('Item Type to Fetch'),
            options: 'Parts\nOPL Jobs\nExpenses\nAll',
            default: 'All',
            reqd: 1
        },
        {
            fieldname: 'only_without_po',
            fieldtype: 'Check',
            label: __('Only Items Without PO'),
            default: 1
        },
        {
            fieldname: 'mark_billable',
            fieldtype: 'Check',
            label: __('Mark as Billable'),
            default: 1
        },
        {
            fieldname: 'filter_by_text',
            fieldtype: 'Data',
            label: __('Filter Text (Optional)')
        }
    ];
    
    frappe.prompt(fields, function(values) {
        // Convert mobile selection to desktop format
        let desktop_values = {
            fetch_parts: values.item_type === 'Parts' || values.item_type === 'All',
            fetch_opl: values.item_type === 'OPL Jobs' || values.item_type === 'All',
            fetch_expenses: values.item_type === 'Expenses' || values.item_type === 'All',
            only_without_po: values.only_without_po,
            mark_billable: values.mark_billable,
            filter_by_text: values.filter_by_text
        };
        
        car_workshop.utils.fetch_work_order_items(frm, desktop_values);
    }, __('Fetch Items from Work Order'), __('Fetch'));
}

// Dialog for manually adding items
function show_add_item_dialog(frm) {
    // Create a dialog with fields for adding an item
    let fields = [
        {
            fieldname: 'item_type',
            fieldtype: 'Select',
            label: __('Item Type'),
            options: 'Part\nOPL\nExpense',
            reqd: 1
        },
        {
            fieldname: 'reference_doctype',
            fieldtype: 'Dynamic Link',
            label: __('Reference'),
            options: 'reference_type',
            reqd: 1,
            get_query: function() {
                let reference_type = dialog.fields_dict.reference_type.get_value();
                
                if (reference_type === 'Part') {
                    return {
                        filters: {
                            "docstatus": 1
                        }
                    };
                } else if (reference_type === 'Job Type') {
                    return {
                        filters: {
                            "is_opl": 1
                        }
                    };
                }
                
                return {};
            }
        },
        {
            fieldname: 'reference_type',
            fieldtype: 'Select',
            label: __('Reference Type'),
            options: 'Part\nJob Type\nExpense Type',
            default: 'Part',
            hidden: 1,
            onchange: function() {
                // Update the reference label
                let label = dialog.get_value('reference_type') === 'Part' ? 'Part' : 
                          (dialog.get_value('reference_type') === 'Job Type' ? 'Job Type' : 'Expense Type');
                
                dialog.set_df_property('reference_doctype', 'label', label);
            }
        },
        {
            fieldname: 'description',
            fieldtype: 'Small Text',
            label: __('Description')
        },
        {
            fieldname: 'qty_section',
            fieldtype: 'Section Break',
            label: __('Quantity and Rate')
        },
        {
            fieldname: 'quantity',
            fieldtype: 'Float',
            label: __('Quantity'),
            default: 1,
            reqd: 1
        },
        {
            fieldname: 'rate',
            fieldtype: 'Currency',
            label: __('Rate'),
            reqd: 1
        },
        {
            fieldname: 'col_break1',
            fieldtype: 'Column Break'
        },
        {
            fieldname: 'uom',
            fieldtype: 'Link',
            label: __('UOM'),
            options: 'UOM',
            default: 'Nos'
        },
        {
            fieldname: 'tax_section',
            fieldtype: 'Section Break',
            label: __('Tax and Billing')
        },
        {
            fieldname: 'use_default_tax',
            fieldtype: 'Check',
            label: __('Use Default Tax Template'),
            default: 1
        },
        {
            fieldname: 'tax_template',
            fieldtype: 'Link',
            label: __('Tax Template'),
            options: 'Purchase Taxes and Charges Template',
            depends_on: 'eval:!doc.use_default_tax'
        },
        {
            fieldname: 'col_break2',
            fieldtype: 'Column Break'
        },
        {
            fieldname: 'billable',
            fieldtype: 'Check',
            label: __('Billable to Customer'),
            default: 1
        }
    ];
    
    let dialog = new frappe.ui.Dialog({
        title: __('Add Item'),
        fields: fields,
        primary_action_label: __('Add'),
        primary_action: function(values) {
            // Handle item type and reference type mapping
            if (values.item_type === 'Part') {
                values.reference_type = 'Part';
            } else if (values.item_type === 'OPL') {
                values.reference_type = 'Job Type';
            } else if (values.item_type === 'Expense') {
                values.reference_type = 'Expense Type';
            }
            
            // Add the item to the child table
            let item = frm.add_child('items');
            item.item_type = values.item_type;
            item.reference_doctype = values.reference_doctype;
            item.description = values.description;
            item.quantity = values.quantity;
            item.rate = values.rate;
            item.amount = flt(values.quantity) * flt(values.rate);
            item.uom = values.uom;
            item.billable = values.billable;
            item.use_default_tax = values.use_default_tax;
            
            if (!values.use_default_tax && values.tax_template) {
                item.tax_template = values.tax_template;
            } else if (values.use_default_tax) {
                // Set tax template based on settings
                setTimeout(function() {
                    car_workshop.utils.set_tax_template(frm, item);
                }, 300);
            }
            
            if (frm.doc.work_order) {
                item.work_order = frm.doc.work_order;
            }
            
            frm.refresh_field('items');
            car_workshop.utils.calculate_totals(frm);
            dialog.hide();
            
            // Show a success message
            frappe.show_alert({
                message: __('Item added successfully'),
                indicator: 'green'
            }, 3);
        }
    });
    
    // Update reference type when item type changes
    dialog.fields_dict.item_type.df.onchange = function() {
        let item_type = dialog.get_value('item_type');
        let reference_type = 'Part';
        
        if (item_type === 'OPL') {
            reference_type = 'Job Type';
        } else if (item_type === 'Expense') {
            reference_type = 'Expense Type';
        }
        
        dialog.set_value('reference_type', reference_type);
    };
    
    // Handle tax template visibility based on use_default_tax
    dialog.fields_dict.use_default_tax.df.onchange = function() {
        let use_default = dialog.get_value('use_default_tax');
        dialog.set_df_property('tax_template', 'hidden', use_default);
        
        if (use_default) {
            dialog.set_value('tax_template', '');
        }
    };
    
    // Fetch details when reference is selected
    dialog.fields_dict.reference_doctype.df.onchange = function() {
        let reference = dialog.get_value('reference_doctype');
        let reference_type = dialog.get_value('reference_type');
        
        if (!reference) return;
        
        if (reference_type === 'Part') {
            frappe.db.get_value('Part', reference, 
                ['part_name', 'current_price'], 
                function(r) {
                    if (r) {
                        dialog.set_value('description', r.part_name);
                        dialog.set_value('rate', r.current_price);
                    } else {
                        frappe.show_alert({
                            message: __(`Part '${reference}' details not found`),
                            indicator: 'orange'
                        });
                    }
                }
            );
        } else if (reference_type === 'Job Type') {
            frappe.db.get_value('Job Type', reference, 
                ['description', 'default_price'], 
                function(r) {
                    if (r) {
                        dialog.set_value('description', r.description);
                        dialog.set_value('rate', r.default_price);
                    } else {
                        frappe.show_alert({
                            message: __(`Job Type '${reference}' details not found`),
                            indicator: 'orange'
                        });
                    }
                }
            );
        } else if (reference_type === 'Expense Type') {
            frappe.db.get_value('Expense Type', reference, 
                ['description', 'default_rate'], 
                function(r) {
                    if (r) {
                        dialog.set_value('description', r.description || reference);
                        dialog.set_value('rate', r.default_rate || 0);
                    } else {
                        dialog.set_value('description', reference);
                        frappe.show_alert({
                            message: __(`Expense Type '${reference}' details not found`),
                            indicator: 'orange'
                        });
                    }
                }
            );
        }
    };
    
    dialog.show();
    
    // Set initial reference type based on item type
    dialog.set_value('reference_type', 'Part');
}

// Mark Purchase Order as received
function mark_as_received(frm) {
    // Prevent duplicate updates - only allow if status is Submitted
    if (frm.doc.status !== "Submitted") {
        frappe.show_alert({
            message: __('This Purchase Order is already marked as ' + frm.doc.status),
            indicator: 'orange'
        });
        return;
    }
    
    frappe.confirm(
        __('Are you sure you want to mark this Purchase Order as received?'),
        function() {
            frm.call({
                method: "set_status",
                doc: frm.doc,
                args: {
                    status: "Received"
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frm.reload_doc();
                        frappe.show_alert({
                            message: __('Purchase Order marked as received'),
                            indicator: 'green'
                        }, 5);
                    }
                }
            });
        }
    );
}