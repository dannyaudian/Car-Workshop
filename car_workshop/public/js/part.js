frappe.ui.form.on('Part', {
    refresh: function(frm) {
        // Fetch price on refresh
        fetch_current_price(frm);
        
        // If no item_code, show "Create Item" button
        if (!frm.doc.item_code) {
            frm.add_custom_button(__('Create Item'), function() {
                // Call the server-side method to create an item from the part
                frappe.call({
                    method: 'car_workshop.car_workshop.doctype.part.create_item_from_part.create_item_from_part',
                    args: {
                        part_name: frm.doc.part_name,
                        part_number: frm.doc.part_number,
                        brand: frm.doc.brand,
                        category: frm.doc.category
                    },
                    callback: function(response) {
                        if (response.message) {
                            // Update the item_code field with the new item's name
                            frm.set_value('item_code', response.message);
                            frm.save();
                            
                            // Show success message
                            frappe.show_alert({
                                message: __('Item {0} created successfully', [response.message]),
                                indicator: 'green'
                            }, 5);
                            
                            // Reload the form to refresh all fields
                            frm.reload_doc();
                        }
                    }
                });
            });
        }
        
        // Check if on mobile device
        if (frappe.is_mobile()) {
            // Add "Scan Part Number" button
            frm.add_custom_button(__('Scan Part Number'), function() {
                // Use barcode scanner
                frappe.barcode.scan().then(barcode_data => {
                    if (barcode_data) {
                        // Set the part_number field with the scanned value
                        frm.set_value('part_number', barcode_data);
                        
                        // Show success message
                        frappe.show_alert({
                            message: __('Part Number scanned successfully'),
                            indicator: 'green'
                        }, 3);
                    }
                }).catch(error => {
                    // Handle scanning errors
                    frappe.show_alert({
                        message: __('Error scanning barcode: {0}', [error.message]),
                        indicator: 'red'
                    }, 5);
                });
            });
        }
    },
    
    // When item_code changes, fetch price
    item_code: function(frm) {
        fetch_current_price(frm);
    }
});

// Function to fetch and update current price
function fetch_current_price(frm) {
    if (!frm.doc.name) return;
    
    // First try to get price from Service Price List
    frappe.call({
        method: 'car_workshop.car_workshop.doctype.service_price_list.get_active_service_price.get_active_service_price',
        args: {
            reference_type: 'Part',
            reference_name: frm.doc.name,
            price_list: 'Retail Price List'
        },
        callback: function(r) {
            if (r.message && r.message.rate) {
                // Set the current_price field with the price from Service Price List
                frm.set_value('current_price', r.message.rate);
                frm.refresh_field('current_price');
                
                // Show indicator of where the price came from
                frm.set_df_property('current_price', 'description', 
                    'Price from Service Price List (Retail Price List)');
                
                // Show success message
                frappe.show_alert({
                    message: __('Price updated from Service Price List: {0}', [
                        format_currency(r.message.rate, frappe.defaults.get_default('currency'))
                    ]),
                    indicator: 'green'
                }, 3);
            } else {
                // If no price in Service Price List, try Item Price
                get_price_from_item_price(frm);
            }
        }
    });
}

// Fallback function to get price from Item Price
function get_price_from_item_price(frm) {
    if (!frm.doc.item_code) {
        // No item code, can't get price from Item Price
        frm.set_value('current_price', 0);
        frm.refresh_field('current_price');
        frm.set_df_property('current_price', 'description', 'No price available');
        return;
    }
    
    // Get price from Item Price
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Item Price',
            filters: {
                'item_code': frm.doc.item_code,
                'price_list': 'Retail Price List',
                'selling': 1
            },
            fields: ['price_list_rate'],
            order_by: 'valid_from desc',
            limit: 1
        },
        callback: function(response) {
            if (response.message && response.message.length > 0) {
                // Set the current_price field with the latest price from Item Price
                frm.set_value('current_price', response.message[0].price_list_rate);
                frm.refresh_field('current_price');
                
                // Show indicator of where the price came from
                frm.set_df_property('current_price', 'description', 
                    'Price from Item Price (Retail Price List)');
                
                // Show info message
                frappe.show_alert({
                    message: __('Price updated from Item Price: {0}', [
                        format_currency(response.message[0].price_list_rate, 
                        frappe.defaults.get_default('currency'))
                    ]),
                    indicator: 'blue'
                }, 3);
            } else {
                // No price found in Item Price either
                frm.set_value('current_price', 0);
                frm.refresh_field('current_price');
                frm.set_df_property('current_price', 'description', 'No price available');
                
                // Show warning
                frappe.show_alert({
                    message: __('No price found for this part'),
                    indicator: 'orange'
                }, 3);
            }
        }
    });
}