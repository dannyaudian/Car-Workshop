frappe.ui.form.on('Job Type', {
    refresh: function(frm) {
        // Add custom field for current price if not exists
        if (!frm.custom_current_price_added) {
            frm.add_custom_button(__('Refresh Current Price'), function() {
                fetch_active_service_price(frm);
            });
            
            // Create a custom field to show current price without modifying the doctype
            frm.add_custom_field({
                fieldname: 'current_price_display',
                fieldtype: 'Currency',
                label: 'Current Price (from Price List)',
                read_only: 1,
                fieldgroup: 'Default Price', // Add it near the default price field
                insert_after: 'default_price',
                bold: 1,
                description: 'This price is fetched from the Service Price List and does not affect the default price'
            });
            
            frm.custom_current_price_added = true;
        }
        
        // Fetch active service price
        fetch_active_service_price(frm);
        
        // Recalculate item totals when form is refreshed
        calculate_item_totals(frm);
    },
    
    // When items are added or removed, recalculate totals
    items_add: function(frm, cdt, cdn) {
        calculate_item_totals(frm);
    },
    
    items_remove: function(frm, cdt, cdn) {
        calculate_item_totals(frm);
    }
});

// Helper function to fetch active service price
function fetch_active_service_price(frm) {
    if (frm.doc.name) {
        frappe.call({
            method: 'car_workshop.car_workshop.doctype.service_price_list.get_active_service_price.get_active_service_price',
            args: {
                reference_type: 'Job Type',
                reference_name: frm.doc.name,
                price_list: 'Retail Price List'
            },
            callback: function(r) {
                if (r.message && r.message.rate) {
                    // Update the custom field with the active price
                    frm.set_value('current_price_display', r.message.rate);
                    
                    // Show a flash message with the price information
                    frappe.show_alert({
                        message: __('Current price from Retail Price List: {0}', [
                            format_currency(r.message.rate, frappe.defaults.get_default('currency'))
                        ]),
                        indicator: 'green'
                    }, 5);
                } else {
                    // If no price found in Service Price List, show default price
                    frm.set_value('current_price_display', frm.doc.default_price);
                    
                    if (frm.doc.default_price) {
                        frappe.show_alert({
                            message: __('No price found in Service Price List. Using default price: {0}', [
                                format_currency(frm.doc.default_price, frappe.defaults.get_default('currency'))
                            ]),
                            indicator: 'blue'
                        }, 5);
                    } else {
                        frappe.show_alert({
                            message: __('No price defined for this job type.'),
                            indicator: 'orange'
                        }, 5);
                    }
                }
            }
        });
    }
}

// Helper function to calculate item totals
function calculate_item_totals(frm) {
    let total_amount = 0;
    
    // Loop through items and calculate amount
    $.each(frm.doc.items || [], function(i, item) {
        let amount = flt(item.qty) * flt(item.rate);
        frappe.model.set_value(item.doctype, item.name, 'amount', amount);
        total_amount += amount;
    });
    
    // If no default price is set, use the calculated total as suggestion
    if (!frm.doc.default_price && total_amount > 0) {
        frm.set_df_property('default_price', 'description', 
            __('Suggested price based on items: {0}', [
                format_currency(total_amount, frappe.defaults.get_default('currency'))
            ])
        );
    }
}

// Add behavior to Job Type Item child table
frappe.ui.form.on('Job Type Item', {
    qty: function(frm, cdt, cdn) {
        update_item_amount(frm, cdt, cdn);
    },
    
    rate: function(frm, cdt, cdn) {
        update_item_amount(frm, cdt, cdn);
    },
    
    item: function(frm, cdt, cdn) {
        // When item is selected, fetch its price
        var row = locals[cdt][cdn];
        if (row.item) {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Item',
                    filters: { name: row.item },
                    fieldname: ['standard_rate']
                },
                callback: function(r) {
                    if (r.message && r.message.standard_rate) {
                        frappe.model.set_value(cdt, cdn, 'rate', r.message.standard_rate);
                    }
                }
            });
        }
    }
});

// Helper function to update amount for a row
function update_item_amount(frm, cdt, cdn) {
    var row = locals[cdt][cdn];
    var amount = flt(row.qty) * flt(row.rate);
    frappe.model.set_value(cdt, cdn, 'amount', amount);
    calculate_item_totals(frm);
}