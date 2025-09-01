frappe.ui.form.on('Part', {
    refresh: function(frm) {
        if (!frm.doc.item_code) {
            frm.add_custom_button(__('Create Item'), async () => {
                try {
                    frappe.dom.freeze(__('Creating Item...'));
                    if (frm.is_new()) {
                        await frm.save();
                    }
                    const item_code = await frappe.xcall('car_workshop.car_workshop.doctype.part.part.create_item_from_part', { docname: frm.doc.name });
                    frm.set_value('item_code', item_code);
                    await frm.save();
                            frappe.show_alert({
                        message: __('Item {0} created successfully', [ frappe.utils.escape_html(item_code) ]),
                                            indicator: 'green'
                    }, 5);
                    frm.reload_doc();
                } catch (error) {
                    frappe.show_alert({
                        message: __('Error creating item: {0}', [ frappe.utils.escape_html(error.message || 'Unknown error') ]),
                        indicator: 'red'
                    }, 5);
                    console.error('Error creating item:', error);
                } finally {
                    frappe.dom.unfreeze();
                }
            });
}
        if (!frm.is_new()) {
            fetch_current_price(frm);
        }
        frm.add_custom_button(__('Scan Barcode (Kamera)'), function() {
            scan_barcode_with_camera(frm);
        }, __('Actions'));
        },
    item_code: function(frm) {
        if (!frm.is_new()) {
            fetch_current_price(frm);
        }
        },
    service_price_list: function(frm) {
        if (!frm.is_new()) {
                fetch_current_price(frm);
            }
        }
});

function scan_barcode_with_camera(frm) {
    if (window.BarcodeDetector && window.isSecureContext) {
        desktop_camera_scan(frm).catch(error => {
            console.warn("Camera scanning failed:", error);
            fallback_prompt(frm);
        });
    } else {
        console.warn("BarcodeDetector API not available in this browser");
        fallback_prompt(frm);
    }
}

function desktop_camera_scan(frm) {
    return new Promise((resolve, reject) => {
        if (!window.isSecureContext) {
            reject(new Error("Camera access requires HTTPS"));
            return;
        }
        const d = new frappe.ui.Dialog({
            title: __('Scan Barcode'),
            fields: [{
                fieldtype: 'HTML',
                fieldname: 'camera_view',
                options: `<div style="text-align: center;"><video id="barcode_video" style="width: 100%; max-height: 80vh; border: 1px solid #ccc;" autoplay playsinline></video><div id="scan_status" style="margin-top: 10px; font-size: 14px; color: #8D99A6;">${__('Mendeteksi... Arahkan kamera ke barcode')}</div></div>`
            }],
            primary_action_label: __('Cancel'),
            primary_action: () => {
                if (stream) {
                    stream.getTracks().forEach(track => track.stop());
                }
                clearInterval(scanInterval);
                d.hide();
                reject(new Error("Scanning cancelled by user"));
            }
        });
        
        d.show();
        
        let stream;
        let scanInterval;

        BarcodeDetector.getSupportedFormats().then(supportedFormats => {
                console.log("Supported barcode formats:", supportedFormats);

                return navigator.mediaDevices.getUserMedia({
                    video: {
                        facingMode: 'environment',
                        width: { ideal: 1280 },
                        height: { ideal: 720 }
                    }
                });
        }).then(mediaStream => {
                stream = mediaStream;
                const video = document.getElementById('barcode_video');
                video.srcObject = stream;

                document.getElementById('scan_status').textContent = __('Kamera aktif, mendeteksi barcode...');

                video.play().catch(e => console.warn("Video play error:", e));

                const barcodeDetector = new BarcodeDetector({
                    formats: ['qr_code', 'code_39', 'code_128', 'ean_13', 'ean_8', 'upc_a', 'upc_e', 'itf', 'data_matrix']
                });

                scanInterval = setInterval(() => {
                    if (video.readyState === video.HAVE_ENOUGH_DATA) {
                    barcodeDetector.detect(video).then(barcodes => {
                        if (barcodes.length > 0) {
                            const barcode = barcodes[0].rawValue;
                                    document.getElementById('scan_status').textContent = __('Barcode terdeteksi!');

                                    clearInterval(scanInterval);

                                    stream.getTracks().forEach(track => track.stop());

                                    setTimeout(() => {
                                        d.hide();
                                        frm.set_value('part_number', barcode);
                                        frappe.show_alert({
                                            message: __('Berhasil scan'),
                                            indicator: 'green'
                }, 3);
                                        fetch_current_price(frm);
                                        resolve(barcode);
                                    }, 500);
            }
                    }).catch(err => {
                                console.warn("Barcode detection error:", err);
                                document.getElementById('scan_status').textContent = __('Error mendeteksi barcode, coba lagi...');
                            });
                    }
                }, 700);
        }).catch(err => {
                console.error("Camera access error:", err);
                d.hide();

                if (err.name === 'NotAllowedError') {
                    frappe.show_alert({
                        message: __('Camera access denied. Please allow camera access.'),
                        indicator: 'red'
                    }, 5);
                } else if (err.name === 'NotFoundError') {
                    frappe.show_alert({
                        message: __('No camera found on this device.'),
                        indicator: 'red'
                    }, 5);
                } else {
                        const errMsg = frappe.utils.escape_html(err.message || 'Unknown error');
                        frappe.show_alert({
                    message: __('Camera error: {0}', [ errMsg ]),
                            indicator: 'red'
                        }, 5);
        }

                reject(err);
    });
    });
}

function fallback_prompt(frm) {
    frappe.prompt({
        label: __('Enter Part Number'),
        fieldname: 'part_number',
        fieldtype: 'Data',
        reqd: true
    }, function(values) {
        if (values.part_number) {
            frm.set_value('part_number', values.part_number);
            frappe.show_alert({
                message: __('Part number entered manually'),
                indicator: 'blue'
            }, 3);
            fetch_current_price(frm);
        }
    }, __('Manual Entry'));
}

async function fetch_current_price(frm) {
    if (frm.is_new() || !frm.doc.item_code || !frm.doc.service_price_list) {
        if (!frm.doc.item_code) {
            frm.set_value('current_price', 0);
            frm.set_df_property('current_price', 'description', __('No item code specified'));
        } else if (!frm.doc.service_price_list) {
            frm.set_value('current_price', 0);
            frm.set_df_property('current_price', 'description', __('No price list selected'));
        }
        return;
    }

    try {
        frm.set_df_property('current_price', 'description', __('Fetching price...'));

        const price_list_response = await frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Item Price',
                filters: {
                    'item_code': frm.doc.item_code,
                    'price_list': frm.doc.service_price_list,
                    'selling': 1
                },
                fields: ['price_list_rate', 'valid_from'],
                order_by: 'valid_from desc',
                limit: 50
            }
        });

        const price_entries = price_list_response.message || [];

        if (price_entries.length > 0) {
            let selected_price;

            const entries_with_dates = price_entries.filter(entry => entry.valid_from);
            if (entries_with_dates.length > 0) {
                selected_price = entries_with_dates.reduce((latest, current) => {
                    return new Date(current.valid_from) > new Date(latest.valid_from) ? current : latest;
                }, entries_with_dates[0]);
            } else {
                selected_price = price_entries[0];
            }

            frm.set_value('current_price', selected_price.price_list_rate);
            frm.set_df_property(
                'current_price',
                'description',
                __('Price from {0}', [frappe.utils.escape_html(frm.doc.service_price_list)])
            );

            const formatted_price = format_currency(
                selected_price.price_list_rate,
                frappe.defaults.get_default('currency')
            );

            frappe.show_alert({
                message: __('Price updated: {0}', [
                    frappe.utils.escape_html(formatted_price)
                ]),
                indicator: 'green'
            }, 3);
        } else {
            frm.set_value('current_price', 0);
            frm.set_df_property(
                'current_price',
                'description',
                __('No Item Price found in {0}', [frappe.utils.escape_html(frm.doc.service_price_list)])
            );

            frappe.show_alert({
                message: __('No price found for this part in the selected price list'),
                indicator: 'orange'
            }, 3);
        }
    } catch (error) {
        console.error('Error fetching price:', error);

        frm.set_value('current_price', 0);
        frm.set_df_property('current_price', 'description', __('Error fetching price'));

        frappe.show_alert({
            message: __('Error fetching price information: {0}', [
                frappe.utils.escape_html(error.message || 'Unknown error')
            ]),
            indicator: 'red'
        }, 5);
    }
}

