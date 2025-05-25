frappe.ui.form.on('Part', {
    refresh: function(frm) {
        // Only fetch price if the document is not new (already saved)
        if (!frm.is_new()) {
            fetch_current_price(frm);
        }
        
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
                    },
                    error: function(err) {
                        // Handle errors gracefully
                        frappe.show_alert({
                            message: __('Error creating item: {0}', [err.message || 'Unknown error']),
                            indicator: 'red'
                        }, 5);
                    }
                });
            });
        }
        
        // Mobile barcode scanning button
        if (frappe.utils.is_mobile()) {
            frm.add_custom_button(__('Scan Barcode (Kamera)'), function() {
                // Check if the native barcode API is available
                if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                    // Create a simple camera interface
                    const d = new frappe.ui.Dialog({
                        title: __('Scan Barcode'),
                        fields: [{
                            fieldtype: 'HTML',
                            fieldname: 'camera_view',
                            label: '',
                            options: `
                                <div style="text-align: center;">
                                    <video id="scan_camera" style="width: 100%; max-height: 80vh;" autoplay playsinline></video>
                                    <div id="scan_status" style="margin-top: 10px;">Positioning barcode in view...</div>
                                </div>
                            `
                        }],
                        primary_action_label: __('Cancel'),
                        primary_action: () => {
                            // Stop camera stream
                            if (stream) {
                                stream.getTracks().forEach(track => {
                                    track.stop();
                                });
                            }
                            d.hide();
                        }
                    });

                    let stream;
                    let scanning = true;
                    
                    d.show();
                    
                    // Access the camera
                    navigator.mediaDevices.getUserMedia({ 
                        video: { 
                            facingMode: 'environment',  // Use back camera
                            width: { ideal: 1280 },
                            height: { ideal: 720 }
                        } 
                    })
                    .then(function(mediaStream) {
                        stream = mediaStream;
                        const video = document.getElementById('scan_camera');
                        video.srcObject = stream;
                        
                        // Create a canvas to capture frames for processing
                        const canvas = document.createElement('canvas');
                        const ctx = canvas.getContext('2d');
                        
                        // Start capturing frames
                        const interval = setInterval(() => {
                            if (!scanning) {
                                clearInterval(interval);
                                return;
                            }
                            
                            if (video.readyState === video.HAVE_ENOUGH_DATA) {
                                canvas.width = video.videoWidth;
                                canvas.height = video.videoHeight;
                                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                                
                                // Send frame to server for processing
                                canvas.toBlob(function(blob) {
                                    const formData = new FormData();
                                    formData.append('file', blob, 'barcode.png');
                                    
                                    fetch('/api/method/frappe.utils.image_processing.read_barcode', {
                                        method: 'POST',
                                        body: formData,
                                        headers: {
                                            'X-Frappe-CSRF-Token': frappe.csrf_token
                                        }
                                    })
                                    .then(response => response.json())
                                    .then(data => {
                                        if (data.message && data.message.barcode) {
                                            // Stop scanning
                                            scanning = false;
                                            clearInterval(interval);
                                            
                                            // Stop camera stream
                                            stream.getTracks().forEach(track => {
                                                track.stop();
                                            });
                                            
                                            // Close dialog
                                            d.hide();
                                            
                                            // Set the barcode value
                                            frm.set_value('part_number', data.message.barcode);
                                            
                                            // Show success message
                                            frappe.show_alert({
                                                message: __('Berhasil scan'),
                                                indicator: 'green'
                                            }, 3);
                                            
                                            // Trigger price fetch
                                            fetch_current_price(frm);
                                        }
                                    })
                                    .catch(error => {
                                        console.error('Error processing barcode:', error);
                                    });
                                }, 'image/png');
                            }
                        }, 500);
                    })
                    .catch(function(err) {
                        console.error('Error accessing camera:', err);
                        d.hide();
                        
                        // Fall back to file input method
                        fallback_to_file_input(frm);
                    });
                } else {
                    // Browser doesn't support camera access, use file input
                    fallback_to_file_input(frm);
                }
            }, __('Actions'));
        }
    },
    
    // When item_code changes, fetch price
    item_code: function(frm) {
        if (!frm.is_new()) {
            fetch_current_price(frm);
        }
    },
    
    // When part_number changes, fetch price
    part_number: function(frm) {
        if (!frm.is_new()) {
            fetch_current_price(frm);
            
            // Reset current_price to 0 if part_number is empty
            if (!frm.doc.part_number) {
                frm.set_value('current_price', 0);
                frm.refresh_field('current_price');
                frm.set_df_property('current_price', 'description', '');
            }
        }
    }
});

// Fallback to file input when camera API isn't available
function fallback_to_file_input(frm) {
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = 'image/*';
    fileInput.capture = 'environment'; // Use back camera when possible
    
    fileInput.onchange = function(e) {
        if (!e.target.files.length) return;
        
        const file = e.target.files[0];
        
        // Show processing indicator
        frappe.show_alert({
            message: __('Processing image...'),
            indicator: 'blue'
        }, 0);
        
        // Create form data
        const formData = new FormData();
        formData.append('file', file);
        
        // Send to server for processing
        fetch('/api/method/frappe.utils.image_processing.read_barcode', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Frappe-CSRF-Token': frappe.csrf_token
            }
        })
        .then(response => response.json())
        .then(data => {
            // Hide processing indicator
            $(".indicator-pill").remove();
            
            if (data.message && data.message.barcode) {
                // Set the barcode value
                frm.set_value('part_number', data.message.barcode);
                
                // Show success message
                frappe.show_alert({
                    message: __('Berhasil scan'),
                    indicator: 'green'
                }, 3);
                
                // Trigger price fetch
                fetch_current_price(frm);
            } else {
                // If barcode detection failed, prompt user to enter manually
                frappe.prompt({
                    label: __('Enter Barcode'),
                    fieldname: 'barcode',
                    fieldtype: 'Data'
                }, function(values) {
                    if (values.barcode) {
                        frm.set_value('part_number', values.barcode);
                        
                        frappe.show_alert({
                            message: __('Barcode entered manually'),
                            indicator: 'blue'
                        }, 3);
                        
                        fetch_current_price(frm);
                    }
                });
            }
        })
        .catch(error => {
            console.error('Error processing barcode:', error);
            
            // Hide processing indicator
            $(".indicator-pill").remove();
            
            // Show error and prompt for manual entry
            frappe.show_alert({
                message: __('Error processing barcode image'),
                indicator: 'red'
            }, 5);
            
            frappe.prompt({
                label: __('Enter Barcode'),
                fieldname: 'barcode',
                fieldtype: 'Data'
            }, function(values) {
                if (values.barcode) {
                    frm.set_value('part_number', values.barcode);
                    
                    frappe.show_alert({
                        message: __('Barcode entered manually'),
                        indicator: 'blue'
                    }, 3);
                    
                    fetch_current_price(frm);
                }
            });
        });
    };
    
    // Trigger the file input
    fileInput.click();
}

// Function to fetch and update current price
function fetch_current_price(frm) {
    if (!frm.doc.name || frm.is_new()) return;
    
    // Get default or standard price list
    let price_list = frappe.defaults.get_default('selling_price_list') || 'Retail Price List';
    
    // First try to get price from Service Price List
    frappe.call({
        method: 'car_workshop.car_workshop.doctype.service_price_list.get_active_service_price.get_active_service_price',
        args: {
            reference_type: 'Part',
            reference_name: frm.doc.name,
            price_list: price_list
        },
        callback: function(r) {
            if (r.message && r.message.rate) {
                // Set the current_price field with the price from Service Price List
                frm.set_value('current_price', r.message.rate);
                frm.refresh_field('current_price');
                
                // Show indicator of where the price came from
                frm.set_df_property('current_price', 'description', 
                    `Price from Service Price List (${price_list})`);
                
                // Show success message
                frappe.show_alert({
                    message: __('Price updated from Service Price List: {0}', [
                        format_currency(r.message.rate, frappe.defaults.get_default('currency'))
                    ]),
                    indicator: 'green'
                }, 3);
            } else {
                // If no price in Service Price List, try Item Price
                get_price_from_item_price(frm, price_list);
            }
        },
        error: function(err) {
            // Handle error gracefully
            console.error("Error fetching price from Service Price List:", err);
            // Still try the fallback
            get_price_from_item_price(frm, price_list);
        }
    });
}

// Fallback function to get price from Item Price
function get_price_from_item_price(frm, price_list) {
    if (!frm.doc.item_code) {
        // No item code, can't get price from Item Price
        frm.set_value('current_price', 0);
        frm.refresh_field('current_price');
        frm.set_df_property('current_price', 'description', 'No price available');
        
        // Show warning
        frappe.show_alert({
            message: __('No price found for this part'),
            indicator: 'orange'
        }, 3);
        
        return;
    }
    
    // Get price from Item Price
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Item Price',
            filters: {
                'item_code': frm.doc.item_code,
                'price_list': price_list,
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
                    `Price from Item Price (${price_list})`);
                
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
        },
        error: function(err) {
            console.error("Error fetching price from Item Price:", err);
            
            // Set defaults since we couldn't get a price
            frm.set_value('current_price', 0);
            frm.refresh_field('current_price');
            frm.set_df_property('current_price', 'description', 'Error fetching price');
            
            frappe.show_alert({
                message: __('Error fetching price information'),
                indicator: 'red'
            }, 3);
        }
    });
}