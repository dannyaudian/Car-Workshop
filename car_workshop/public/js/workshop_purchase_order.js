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
        
        // For submitted documents, show status-related buttons
        if (frm.doc.docstatus === 1) {
            if (frm.doc.status === "Submitted") {
                frm.add_custom_button(__('Mark as Received'), function() {
                    mark_as_received(frm);
                }).addClass('btn-primary');
            }
        }
        
        // Update dashboard information if available
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
    },
    
    onload: function(frm) {
        // Set up queries and filters for lookup fields
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
                    filters: {
                        "docstatus": 1
                    }
                };
            } else if (row.item_type === "OPL") {
                return {
                    filters: {
                        "is_opl": 1
                    }
                };
            }
            
            return {};
        });
        
        // Initialize calculated fields on load
        calculate_totals(frm);
    },
    
    validate: function(frm) {
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
        if (has_billable_items(frm) && !frm.doc.work_order) {
            frappe.validated = false;
            frappe.throw(__("Work Order is mandatory when there are billable items"));
        }
        
        // Calculate totals before submission
        calculate_totals(frm);
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
    // New handler for default_tax_template
    default_tax_template: function(frm) {
        // If apply_default_tax_to_all_items is checked, update all items
        if (frm.doc.apply_default_tax_to_all_items) {
            (frm.doc.items || []).forEach(item => {
                if (item.use_default_tax) {
                    frappe.model.set_value('Workshop Purchase Order Item', item.name, 'tax_template', frm.doc.default_tax_template);
                }
            });
            frm.refresh_field('items');
            
            // Show notification to user
            frappe.show_alert({
                message: __('Tax template updated for all items using default tax'),
                indicator: 'green'
            }, 3);
        }
    },
    
    // New handler for apply_default_tax_to_all_items
    apply_default_tax_to_all_items: function(frm) {
        if (frm.doc.apply_default_tax_to_all_items && frm.doc.default_tax_template) {
            (frm.doc.items || []).forEach(item => {
                if (item.use_default_tax) {
                    frappe.model.set_value('Workshop Purchase Order Item', item.name, 'tax_template', frm.doc.default_tax_template);
                }
            });
            frm.refresh_field('items');
        }
    }
});

// Child table (Workshop Purchase Order Item) events
frappe.ui.form.on('Workshop Purchase Order Item', {
    item_type: function(frm, cdt, cdn) {
        // Clear reference field when item type changes
        let row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, 'reference_doctype', '');
        
        // Update the reference field label based on item type
        let label = row.item_type === 'Part' ? 'Part' : 
                   (row.item_type === 'OPL' ? 'Job Type' : 'Expense Type');
        
        frm.fields_dict.items.grid.update_docfield_property(
            'reference_doctype', 'label', label
        );
    },
    
    reference_doctype: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        if (!row.reference_doctype) return;
        
        // Check if this item already has a purchase order
        if (frm.doc.work_order) {
            check_duplicate_po(frm, row);
        }
        
        // Fetch details based on reference type
        fetch_reference_details(frm, row, cdt, cdn);
    },
    
    quantity: function(frm, cdt, cdn) {
        calculate_item_amount(frm, cdt, cdn);
    },
    
    rate: function(frm, cdt, cdn) {
        calculate_item_amount(frm, cdt, cdn);
    },
    
    billable: function(frm, cdt, cdn) {
        calculate_totals(frm);
        
        // If billable is checked, ensure work_order is required
        if (has_billable_items(frm)) {
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
    },
    
    items_add: function(frm, cdt, cdn) {
        // Set defaults for new rows
        let row = locals[cdt][cdn];
        frappe.model.set_value(cdt, cdn, 'quantity', 1);
        frappe.model.set_value(cdt, cdn, 'billable', 1);
        
        if (frm.doc.work_order) {
            frappe.model.set_value(cdt, cdn, 'work_order', frm.doc.work_order);
        }
    },
    
    items_remove: function(frm, cdt, cdn) {
        calculate_totals(frm);
    }
    // New handler for use_default_tax
    use_default_tax: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.use_default_tax) {
            frappe.model.set_value(cdt, cdn, 'tax_template', frm.doc.default_tax_template);
        } else if (!row.tax_template) {
            // Show warning if tax_template is empty and use_default_tax is unchecked
            frappe.show_alert({
                message: __('Warning: No tax template specified for this item'),
                indicator: 'orange'
            }, 5);
        }
    },
    
    // New handler for tax_template
    tax_template: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.use_default_tax && !row.tax_template) {
            // Show warning if tax_template is empty and use_default_tax is unchecked
            frappe.show_alert({
                message: __('Warning: No tax template specified for this item'),
                indicator: 'orange'
            }, 5);
        }
    },
    
    form_render: function(frm, cdt, cdn) {
        // Add description to tax_template field when form is rendered
        frm.fields_dict.items.grid.update_docfield_property(
            'tax_template', 'description', 'Override default tax if needed'
        );
    }
});


// Helper Functions

// Check if any items are marked as billable
function has_billable_items(frm) {
    if (!frm.doc.items || frm.doc.items.length === 0) return false;
    
    return frm.doc.items.some(item => item.billable);
}

// Calculate amount for a single item
function calculate_item_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let amount = flt(row.quantity) * flt(row.rate);
    frappe.model.set_value(cdt, cdn, 'amount', amount);
    
    // Recalculate totals
    calculate_totals(frm);
}

// Calculate total amounts for the form
function calculate_totals(frm) {
    let total_amount = 0;
    let billable_amount = 0;
    let non_billable_amount = 0;
    
    (frm.doc.items || []).forEach(item => {
        let amount = flt(item.amount);
        total_amount += amount;
        
        if (item.billable) {
            billable_amount += amount;
        } else {
            non_billable_amount += amount;
        }
    });
    
    frm.set_value('total_amount', total_amount);
    
    // Set these values if they exist in the doctype
    if (frm.meta.fields.find(field => field.fieldname === 'billable_amount')) {
        frm.set_value('billable_amount', billable_amount);
    }
    
    if (frm.meta.fields.find(field => field.fieldname === 'non_billable_amount')) {
        frm.set_value('non_billable_amount', non_billable_amount);
    }
}

// Fetch details for a reference item
function fetch_reference_details(frm, row, cdt, cdn) {
    if (row.item_type === 'Part') {
        frappe.db.get_value('Part', row.reference_doctype, 
            ['part_name', 'current_price', 'item_code'], 
            function(r) {
                if (r) {
                    frappe.model.set_value(cdt, cdn, 'description', r.part_name);
                    frappe.model.set_value(cdt, cdn, 'rate', r.current_price);
                    calculate_item_amount(frm, cdt, cdn);
                }
            }
        );
    } else if (row.item_type === 'OPL') {
        frappe.db.get_value('Job Type', row.reference_doctype, 
            ['description', 'default_price'], 
            function(r) {
                if (r) {
                    frappe.model.set_value(cdt, cdn, 'description', r.description);
                    frappe.model.set_value(cdt, cdn, 'rate', r.default_price);
                    calculate_item_amount(frm, cdt, cdn);
                }
            }
        );
    } else if (row.item_type === 'Expense') {
        // For expense types, we might need custom handling
        // This could be expanded based on your specific requirements
        frappe.model.set_value(cdt, cdn, 'description', row.reference_doctype);
    }
}

// Check for duplicate purchase orders
function check_duplicate_po(frm, row) {
    if (!frm.doc.work_order || !row.reference_doctype || !row.item_type) return;
    
    frappe.call({
        method: 'car_workshop.car_workshop.doctype.workshop_purchase_order.workshop_purchase_order.check_duplicate_po',
        args: {
            work_order: frm.doc.work_order,
            item_type: row.item_type,
            reference_doctype: row.reference_doctype,
            current_po: frm.doc.name || "new"
        },
        callback: function(r) {
            if (r.message && r.message.exists) {
                frappe.show_alert({
                    message: __(`Warning: This item already has an active Purchase Order: ${r.message.po_number}`),
                    indicator: 'orange'
                }, 10);
            }
        }
    });
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
                label: __('Filter by Text')
            }
        ],
        primary_action_label: __('Fetch Items'),
        primary_action: function(values) {
            fetch_work_order_items(frm, values);
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
        }
    ];
    
    frappe.prompt(fields, function(values) {
        // Convert mobile selection to desktop format
        let desktop_values = {
            fetch_parts: values.item_type === 'Parts' || values.item_type === 'All',
            fetch_opl: values.item_type === 'OPL Jobs' || values.item_type === 'All',
            fetch_expenses: values.item_type === 'Expenses' || values.item_type === 'All',
            only_without_po: values.only_without_po,
            mark_billable: values.mark_billable
        };
        
        fetch_work_order_items(frm, desktop_values);
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
            
            if (frm.doc.work_order) {
                item.work_order = frm.doc.work_order;
            }
            
            frm.refresh_field('items');
            calculate_totals(frm);
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
                    }
                }
            );
        }
    };
    
    dialog.show();
    
    // Set initial reference type based on item type
    dialog.set_value('reference_type', 'Part');
}

// Fetch items from work order based on selected options
function fetch_work_order_items(frm, values) {
    if (!frm.doc.work_order) {
        frappe.throw(__("Please select a Work Order first"));
        return;
    }
    
    frappe.call({
        method: 'car_workshop.car_workshop.doctype.workshop_purchase_order.workshop_purchase_order.fetch_work_order_items',
        args: {
            work_order: frm.doc.work_order,
            fetch_parts: values.fetch_parts || false,
            fetch_opl: values.fetch_opl || false,
            fetch_expenses: values.fetch_expenses || false,
            only_without_po: values.only_without_po || false,
            filter_text: values.filter_by_text || '',
            current_po: frm.doc.name || 'new'
        },
        freeze: true,
        freeze_message: __('Fetching items from Work Order...'),
        callback: function(r) {
            if (r.message) {
                let added_count = 0;
                
                // Process parts
                if (r.message.parts && r.message.parts.length > 0) {
                    r.message.parts.forEach(part => {
                        let item = frm.add_child('items');
                        item.item_type = 'Part';
                        item.reference_doctype = part.part;
                        item.description = part.part_name;
                        item.quantity = part.quantity;
                        item.rate = part.rate;
                        item.amount = part.amount;
                        item.uom = 'Nos';
                        item.billable = values.mark_billable;
                        item.work_order = frm.doc.work_order;
                        added_count++;
                    });
                }
                
                // Process OPL jobs
                if (r.message.opl_jobs && r.message.opl_jobs.length > 0) {
                    r.message.opl_jobs.forEach(job => {
                        let item = frm.add_child('items');
                        item.item_type = 'OPL';
                        item.reference_doctype = job.job_type;
                        item.description = job.description;
                        item.quantity = 1;
                        item.rate = job.price;
                        item.amount = job.price;
                        item.uom = 'Nos';
                        item.billable = values.mark_billable;
                        item.work_order = frm.doc.work_order;
                        added_count++;
                    });
                }
                
                // Process expenses
                if (r.message.expenses && r.message.expenses.length > 0) {
                    r.message.expenses.forEach(expense => {
                        let item = frm.add_child('items');
                        item.item_type = 'Expense';
                        item.reference_doctype = expense.expense_type;
                        item.description = expense.description;
                        item.quantity = 1;
                        item.rate = expense.amount;
                        item.amount = expense.amount;
                        item.uom = 'Nos';
                        item.billable = values.mark_billable;
                        item.work_order = frm.doc.work_order;
                        added_count++;
                    });
                }
                
                if (added_count > 0) {
                    frm.refresh_field('items');
                    calculate_totals(frm);
                    
                    frappe.show_alert({
                        message: __(`${added_count} items added from Work Order`),
                        indicator: 'green'
                    }, 5);
                } else {
                    frappe.show_alert({
                        message: __('No items found matching the criteria'),
                        indicator: 'blue'
                    }, 5);
                }
            }
        }
    });
}

// Mark Purchase Order as received
function mark_as_received(frm) {
    frappe.confirm(
        __('Are you sure you want to mark this Purchase Order as received?'),
        function() {
            frm.set_value('status', 'Received');
            frm.save();
            frappe.show_alert({
                message: __('Purchase Order marked as received'),
                indicator: 'green'
            }, 5);
        }
    );
}

if (frm.doc.docstatus === 1 && frm.doc.status !== "Cancelled") {
    frm.add_custom_button(__('Create Receipt'), function() {
        frappe.model.open_mapped_doc({
            method: "car_workshop.car_workshop.doctype.workshop_purchase_receipt.workshop_purchase_receipt.make_purchase_receipt",
            frm: frm
        });
    }).addClass('btn-primary');
}