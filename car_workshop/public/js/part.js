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
        
        // Add Scan Barcode button for all devices (mobile and desktop)
        frm.add_custom_button(__('Scan Barcode (Kamera)'), function() {
            scan_barcode_multi_platform(frm);
        }, __('Actions'));
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
            if (!frm.doc.part_number) {
                // Reset current_price to 0 if part_number is empty
                frm.set_value('current_price', 0);
                frm.refresh_field('current_price');
                frm.set_df_property('current_price', 'description', '');
            } else {
                // Fetch price if part_number is set
                fetch_current_price(frm);
            }
        }
    }
});

// Multi-platform barcode scanning function
async function scan_barcode_multi_platform(frm) {
    try {
        // Try native Frappe barcode scanner first (for mobile devices)
        if (typeof frappe.barcode !== 'undefined' && typeof frappe.barcode.scan === 'function') {
            try {
                console.log("Trying Frappe native barcode scanner...");
                const barcode = await frappe.barcode.scan();
                
                if (barcode) {
                    // Success! Set the part_number
                    frm.set_value('part_number', barcode);
                    
                    // Show success message
                    frappe.show_alert({
                        message: __('Berhasil scan'),
                        indicator: 'green'
                    }, 3);
                    
                    // Trigger price fetch
                    fetch_current_price(frm);
                    return; // Exit function on success
                }
            } catch (err) {
                console.warn("Frappe barcode scanner failed:", err);
                // Continue to next method if this fails
            }
        }
        
        // If we reach here, try the BarcodeDetector API (for modern desktop browsers)
        if (window.BarcodeDetector && window.isSecureContext) {
            try {
                console.log("Trying BarcodeDetector API...");
                await desktop_camera_scan(frm);
                return; // Exit function on success
            } catch (err) {
                console.warn("BarcodeDetector scanning failed:", err);
                // Continue to next method if this fails
            }
        }
        
        // If we reach here, all automatic methods failed, use manual entry
        console.log("Falling back to manual entry...");
        fallback_prompt(frm);
        
    } catch (error) {
        console.error("Error in barcode scanning:", error);
        fallback_prompt(frm);
    }
}

// Desktop camera scanning with BarcodeDetector API
async function desktop_camera_scan(frm) {
    return new Promise((resolve, reject) => {
        // Check if we're on HTTPS (required for camera access)
        if (!window.isSecureContext) {
            reject(new Error("Camera access requires HTTPS"));
            return;
        }
        
        // Create dialog with video element
        const d = new frappe.ui.Dialog({
            title: __('Scan Barcode'),
            fields: [{
                fieldtype: 'HTML',
                fieldname: 'camera_view',
                options: `
                    <div style="text-align: center;">
                        <video id="barcode_video" style="width: 100%; max-height: 80vh; border: 1px solid #ccc;" autoplay playsinline></video>
                        <div style="margin-top: 10px; font-size: 14px; color: #8D99A6;">
                            ${__('Position barcode in view to scan automatically')}
                        </div>
                    </div>
                `
            }],
            primary_action_label: __('Cancel'),
            primary_action: () => {
                // Stop camera when dialog is closed
                if (stream) {
                    stream.getTracks().forEach(track => track.stop());
                }
                clearInterval(scanInterval);
                d.hide();
                reject(new Error("Scanning cancelled"));
            }
        });
        
        d.show();
        
        let stream;
        let scanInterval;
        
        // Access camera
        navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: 'environment', // Use back camera when available
                width: { ideal: 1280 },
                height: { ideal: 720 }
            }
        })
        .then(mediaStream => {
            stream = mediaStream;
            const video = document.getElementById('barcode_video');
            video.srcObject = stream;
            
            // Some browsers need explicit play() call
            video.play().catch(e => console.warn("Video play error:", e));
            
            // Initialize BarcodeDetector
            const barcodeDetector = new BarcodeDetector({
                // Common barcode formats
                formats: ['qr_code', 'code_39', 'code_128', 'ean_13', 'ean_8', 'upc_a', 'upc_e', 'itf', 'data_matrix']
            });
            
            // Start scanning
            scanInterval = setInterval(() => {
                if (video.readyState === video.HAVE_ENOUGH_DATA) {
                    barcodeDetector.detect(video)
                        .then(barcodes => {
                            if (barcodes.length > 0) {
                                // Barcode detected!
                                const barcode = barcodes[0].rawValue;
                                
                                // Stop scanning
                                clearInterval(scanInterval);
                                
                                // Stop camera
                                stream.getTracks().forEach(track => track.stop());
                                
                                // Close dialog
                                d.hide();
                                
                                // Set part number
                                frm.set_value('part_number', barcode);
                                
                                // Show success message
                                frappe.show_alert({
                                    message: __('Berhasil scan'),
                                    indicator: 'green'
                                }, 3);
                                
                                // Trigger price fetch
                                fetch_current_price(frm);
                                
                                // Resolve promise
                                resolve(barcode);
                            }
                        })
                        .catch(err => {
                            console.warn("Barcode detection error:", err);
                        });
                }
            }, 700); // Check every 700ms
        })
        .catch(err => {
            console.error("Camera access error:", err);
            d.hide();
            reject(err);
        });
    });
}

// Fallback to manual entry
function fallback_prompt(frm) {
    frappe.prompt({
        label: __('Enter Part Number'),
        fieldname: 'part_number',
        fieldtype: 'Data'
    }, function(values) {
        if (values.part_number) {
            frm.set_value('part_number', values.part_number);
            
            frappe.show_alert({
                message: __('Part number entered manually'),
                indicator: 'blue'
            }, 3);
            
            fetch_current_price(frm);
        }
    });
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