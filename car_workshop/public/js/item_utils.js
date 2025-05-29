/**
 * Car Workshop Module - Item Utilities
 * 
 * Contains helper functions for Workshop Purchase Order and related doctypes
 */

frappe.provide('car_workshop.utils');

car_workshop.utils = {
    // Check if any items are marked as billable
    has_billable_items: function(doc) {
        if (!doc.items || doc.items.length === 0) return false;
        return doc.items.some(item => item.billable);
    },
    
    // Calculate amount for a single item
    calculate_item_amount: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        let amount = flt(row.quantity) * flt(row.rate);
        frappe.model.set_value(cdt, cdn, 'amount', amount);
        
        // Recalculate totals
        this.calculate_totals(frm);
    },
    
    // Calculate total amounts for the form
    calculate_totals: function(frm) {
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
    },
    
    // Fetch details for a reference item
    fetch_reference_details: function(frm, row, cdt, cdn) {
        if (row.item_type === 'Part') {
            frappe.db.get_value('Part', row.reference_doctype, 
                ['part_name', 'current_price', 'item_code'], 
                function(r) {
                    if (r) {
                        frappe.model.set_value(cdt, cdn, 'description', r.part_name);
                        frappe.model.set_value(cdt, cdn, 'rate', r.current_price);
                        car_workshop.utils.calculate_item_amount(frm, cdt, cdn);
                    } else {
                        // Fallback warning if reference not found
                        frappe.show_alert({
                            message: __(`Part '${row.reference_doctype}' details not found`),
                            indicator: 'orange'
                        });
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
                        car_workshop.utils.calculate_item_amount(frm, cdt, cdn);
                    } else {
                        // Fallback warning if reference not found
                        frappe.show_alert({
                            message: __(`Job Type '${row.reference_doctype}' details not found`),
                            indicator: 'orange'
                        });
                    }
                }
            );
        } else if (row.item_type === 'Expense') {
            // For expense types, we might need custom handling
            frappe.db.get_value('Expense Type', row.reference_doctype, 
                ['description', 'default_rate'], 
                function(r) {
                    if (r) {
                        frappe.model.set_value(cdt, cdn, 'description', r.description || row.reference_doctype);
                        frappe.model.set_value(cdt, cdn, 'rate', r.default_rate || 0);
                        car_workshop.utils.calculate_item_amount(frm, cdt, cdn);
                    } else {
                        // If no description found, use reference name as fallback
                        frappe.model.set_value(cdt, cdn, 'description', row.reference_doctype);
                        frappe.show_alert({
                            message: __(`Expense Type '${row.reference_doctype}' details not found`),
                            indicator: 'orange'
                        });
                    }
                }
            );
        }
    },
    
    // Check for duplicate purchase orders
    check_duplicate_po: function(frm, row) {
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
    },
    
    // Helper function to set tax template based on settings
    set_tax_template: function(frm, row) {
        // Only auto-populate tax template if use_default_tax is checked
        if (row.use_default_tax) {
            // Get default tax template based on item type
            if (row.item_type === 'Part') {
                frappe.db.get_single_value('Car Workshop Settings', 'default_part_tax_template')
                    .then(tax_template => {
                        if (tax_template) {
                            frappe.model.set_value(row.doctype, row.name, 'tax_template', tax_template);
                        }
                    });
            } else if (row.item_type === 'OPL') {
                frappe.db.get_single_value('Car Workshop Settings', 'default_service_tax_template')
                    .then(tax_template => {
                        if (tax_template) {
                            frappe.model.set_value(row.doctype, row.name, 'tax_template', tax_template);
                        }
                    });
            } else if (row.item_type === 'Expense') {
                frappe.db.get_single_value('Car Workshop Settings', 'default_expense_tax_template')
                    .then(tax_template => {
                        if (tax_template) {
                            frappe.model.set_value(row.doctype, row.name, 'tax_template', tax_template);
                        }
                    });
            }
        } else {
            // If use_default_tax is unchecked, clear tax_template
            frappe.model.set_value(row.doctype, row.name, 'tax_template', '');
        }
    },
    
    // Fetch items from work order based on selected options
    fetch_work_order_items: function(frm, values) {
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
                            
                            // Set use_default_tax to true by default
                            item.use_default_tax = 1;
                            
                            // Populate tax template if enabled
                            if (item.use_default_tax) {
                                car_workshop.utils.set_tax_template(frm, item);
                            }
                            
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
                            
                            // Set use_default_tax to true by default
                            item.use_default_tax = 1;
                            
                            // Populate tax template if enabled
                            if (item.use_default_tax) {
                                car_workshop.utils.set_tax_template(frm, item);
                            }
                            
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
                            
                            // Set use_default_tax to true by default
                            item.use_default_tax = 1;
                            
                            // Populate tax template if enabled
                            if (item.use_default_tax) {
                                car_workshop.utils.set_tax_template(frm, item);
                            }
                            
                            added_count++;
                        });
                    }
                    
                    if (added_count > 0) {
                        frm.refresh_field('items');
                        car_workshop.utils.calculate_totals(frm);
                        
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
    },
    
    // Function to handle receipt generation
    generate_receipt: function(frm) {
        if (frm.doc.docstatus !== 1) {
            frappe.throw(__("Purchase Order must be submitted before generating a receipt"));
            return;
        }
        
        frappe.call({
            method: 'car_workshop.car_workshop.doctype.workshop_purchase_order.workshop_purchase_order.generate_receipt',
            args: {
                purchase_order: frm.doc.name
            },
            freeze: true,
            freeze_message: __('Generating Purchase Receipt...'),
            callback: function(r) {
                if (r.message) {
                    frappe.show_alert({
                        message: __(`Purchase Receipt ${r.message} has been created`),
                        indicator: 'green'
                    });
                    
                    // Open the created receipt
                    frappe.set_route('Form', 'Workshop Purchase Receipt', r.message);
                }
            }
        });
    }
};