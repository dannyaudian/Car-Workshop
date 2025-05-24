frappe.ui.form.on('Part', {
    refresh: function(frm) {
        // Check if item_code is not set
        if (!frm.doc.item_code) {
            // Add "Create Item" button
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
        
        // Get latest price for the item if item_code exists
        if (frm.doc.item_code) {
            get_latest_price(frm);
        }
    }
});

// Function to get the latest price from Item Price
function get_latest_price(frm) {
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
                // Set the current_price field with the latest price
                frm.set_value('current_price', response.message[0].price_list_rate);
                frm.refresh_field('current_price');
            } else {
                // No price found
                frm.set_value('current_price', 0);
                frm.refresh_field('current_price');
            }
        }
    });
}