// Copyright (c) 2025, Danny Audian and contributors
// For license information, please see license.txt

frappe.ui.form.on('Part Stock Opname', {
    refresh: function(frm) {
        // Set up queries
        setup_queries(frm);
        
        // Add custom buttons
        if (frm.doc.docstatus === 1 && frm.doc.status !== "Adjusted") {
            // Add button to create adjustment
            frm.add_custom_button(__('Create Stock Adjustment'), function() {
                create_stock_adjustment(frm);
            }, __("Actions")).addClass('btn-primary');
        }
        
        // If adjustment exists, show a button to view it
        if (frm.doc.docstatus === 1 && frm.doc.status === "Adjusted") {
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Part Stock Adjustment',
                    filters: {
                        'reference_opname': frm.doc.name,
                        'docstatus': ['!=', 2]
                    },
                    fields: ['name', 'docstatus']
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        var adjustment = r.message[0];
                        frm.add_custom_button(__('View Stock Adjustment'), function() {
                            frappe.set_route("Form", "Part Stock Adjustment", adjustment.name);
                        }, __("Actions"));
                    }
                }
            });
        }
        
        // Add barcode scan button in header
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Scan Barcode'), function() {
                scan_barcode(frm);
            }, __("Actions")).addClass('btn-primary');
            
            // Add clear button
            frm.add_custom_button(__('Clear Items'), function() {
                frappe.confirm(
                    __('Are you sure you want to clear all items?'),
                    function() {
                        frm.clear_table('opname_items');
                        frm.refresh_field('opname_items');
                    }
                );
            }, __("Actions"));
            
            // Add manual barcode entry
            frm.add_custom_button(__('Enter Barcode Manually'), function() {
                show_barcode_input_dialog(frm);
            }, __("Actions"));
        }
        
        // Add information message based on device
        if (frappe.dom.is_touchscreen()) {
            frm.set_intro(__('Tap "Scan Barcode" to count items using camera'), 'blue');
        } else {
            frm.set_intro(__('Click "Scan Barcode" to count items or use "Enter Barcode Manually" if scanner unavailable'), 'blue');
        }
    },
    
    onload: function(frm) {
        // Set default values for new documents
        if (frm.doc.__islocal) {
            frm.set_value('posting_date', frappe.datetime.get_today());
            frm.set_value('posting_time', frappe.datetime.now_time());
        }
    },
    
    validate: function(frm) {
        // Ensure all items have quantity > 0
        let items_with_zero_qty = [];
        
        $.each(frm.doc.opname_items || [], function(i, item) {
            if (flt(item.qty_counted) <= 0) {
                items_with_zero_qty.push(item.part || `Row #${i+1}`);
            }
        });
        
        if (items_with_zero_qty.length > 0) {
            frappe.msgprint({
                title: __('Zero Quantities Found'),
                indicator: 'red',
                message: __('The following items have zero or negative quantities: {0}', 
                    [items_with_zero_qty.join(', ')])
            });
            frappe.validated = false;
        }
    }
});

frappe.ui.form.on('Part Stock Opname Item', {
    barcode: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.barcode) {
            process_barcode(frm, row.barcode, row);
        }
    },
    
    scan_barcode: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        scan_barcode_for_row(frm, row);
    },
    
    part: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.part) {
            // Get part details
            frappe.db.get_value('Part', row.part, ['part_name', 'uom'])
                .then(r => {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, 'part_name', r.message.part_name);
                        
                        // Set UOM if not already set
                        if (!row.uom) {
                            frappe.model.set_value(cdt, cdn, 'uom', r.message.uom || 'Pcs');
                        }
                    }
                });
        }
    },
    
    qty_counted: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        
        // Ensure quantity is not negative
        if (flt(row.qty_counted) < 0) {
            frappe.model.set_value(cdt, cdn, 'qty_counted', 0);
            frappe.show_alert({
                message: __('Quantity cannot be negative'),
                indicator: 'red'
            }, 3);
        }
    },
    
    opname_items_add: function(frm, cdt, cdn) {
        // Set focus to barcode field on desktop
        if (!frappe.dom.is_touchscreen()) {
            setTimeout(() => {
                let row = locals[cdt][cdn];
                if (frm.fields_dict.opname_items.grid.grid_rows_by_docname[row.name]) {
                    frm.fields_dict.opname_items.grid.grid_rows_by_docname[row.name].columns.barcode.focus();
                }
            }, 100);
        }
    }
});

// Helper functions
function setup_queries(frm) {
    // Set query for warehouse
    frm.set_query('warehouse', function() {
        return {
            filters: {
                'is_group': 0,
                'company': frappe.defaults.get_user_default('Company')
            }
        };
    });
    
    // Set query for Part in items table
    frm.set_query('part', 'opname_items', function() {
        return {
            filters: {
                'disabled': 0
            }
        };
    });
}

function scan_barcode(frm) {
    // Detect if we're on mobile or desktop
    if (frappe.dom.is_touchscreen()) {
        // Use Frappe's built-in barcode scanner for mobile
        frappe.barcode.scan()
            .then(barcode => {
                if (barcode) {
                    process_barcode(frm, barcode);
                }
            })
            .catch(error => {
                console.error("Barcode scanning error:", error);
                frappe.show_alert({
                    message: __('Barcode scanning failed. Try entering manually.'),
                    indicator: 'red'
                });
                show_barcode_input_dialog(frm);
            });
    } else {
        // Use BarcodeDetector API for desktop if available
        if (window.BarcodeDetector) {
            show_barcode_detector_dialog(frm);
        } else {
            // Fallback to Frappe's scanner or manual entry
            try {
                const scanner = new frappe.ui.Scanner({
                    dialog: true,
                    multiple: false,
                    on_scan(data) {
                        if (data && data.length) {
                            process_barcode(frm, data);
                        }
                    }
                });
            } catch (e) {
                console.error("Scanner initialization error:", e);
                frappe.show_alert({
                    message: __('Camera access failed. Please enter barcode manually.'),
                    indicator: 'orange'
                });
                show_barcode_input_dialog(frm);
            }
        }
    }
}

function show_barcode_detector_dialog(frm) {
    // Create a dialog with video preview
    const dialog = new frappe.ui.Dialog({
        title: __('Scan Barcode'),
        fields: [
            {
                fieldname: 'video_container',
                fieldtype: 'HTML',
                options: `
                    <div style="position: relative;">
                        <video id="barcode-scanner" style="width: 100%; height: 300px; background: #000;"></video>
                        <div id="scanner-overlay" style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; border: 2px solid #4CAF50; box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.5);"></div>
                    </div>
                    <div class="text-muted text-center mt-2">
                        ${__('Position barcode within the green box')}
                    </div>
                `
            }
        ],
        primary_action_label: __('Cancel'),
        primary_action: () => {
            // Stop video stream and close
            if (videoStream) {
                videoStream.getTracks().forEach(track => track.stop());
            }
            dialog.hide();
        }
    });
    
    dialog.show();
    
    // Initialize video and barcode detection
    const video = document.getElementById('barcode-scanner');
    let videoStream;
    
    // Set up the Barcode Detector
    const barcodeDetector = new BarcodeDetector({
        formats: ['qr_code', 'code_39', 'code_128', 'ean_13', 'ean_8', 'upc_a', 'upc_e', 'itf']
    });
    
    // Access the camera
    navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: "environment" } 
    }).then(stream => {
        videoStream = stream;
        video.srcObject = stream;
        video.play();
        
        // Start detecting barcodes
        detectBarcode();
    }).catch(err => {
        console.error("Error accessing camera:", err);
        frappe.show_alert({
            message: __('Camera access failed. Please enter barcode manually.'),
            indicator: 'red'
        });
        dialog.hide();
        show_barcode_input_dialog(frm);
    });
    
    // Function to detect barcodes in video frames
    function detectBarcode() {
        if (dialog.$wrapper.is(':visible')) {
            barcodeDetector.detect(video)
                .then(barcodes => {
                    if (barcodes.length > 0) {
                        // Barcode detected
                        const barcode = barcodes[0].rawValue;
                        
                        // Provide visual feedback
                        document.getElementById('scanner-overlay').style.border = '4px solid yellow';
                        
                        // Stop video stream and close dialog
                        videoStream.getTracks().forEach(track => track.stop());
                        dialog.hide();
                        
                        // Process the detected barcode
                        process_barcode(frm, barcode);
                    }
                    
                    // Continue detecting if dialog is still open
                    setTimeout(() => detectBarcode(), 200);
                })
                .catch(err => {
                    console.error("Barcode detection error:", err);
                    setTimeout(() => detectBarcode(), 500);
                });
        }
    }
}

function show_barcode_input_dialog(frm) {
    // Show dialog for manual barcode entry
    const dialog = new frappe.ui.Dialog({
        title: __('Enter Barcode'),
        fields: [
            {
                label: __('Barcode'),
                fieldname: 'barcode',
                fieldtype: 'Data',
                reqd: 1,
                description: __('Enter barcode manually or scan with a handheld scanner')
            },
            {
                label: __('Quantity'),
                fieldname: 'qty',
                fieldtype: 'Float',
                default: 1,
                reqd: 1
            },
            {
                fieldname: 'part_section',
                fieldtype: 'Section Break',
                label: __('Or Select Part Directly'),
                collapsible: 1,
                collapsed: 1
            },
            {
                label: __('Part'),
                fieldname: 'part',
                fieldtype: 'Link',
                options: 'Part'
            }
        ],
        primary_action_label: __('Add'),
        primary_action: (values) => {
            dialog.hide();
            
            if (values.part) {
                // If part is selected directly
                add_part_directly(frm, values.part, values.qty);
            } else if (values.barcode) {
                // Process barcode with specified quantity
                process_barcode(frm, values.barcode, null, values.qty);
            }
        }
    });
    
    // Set query for Part field
    dialog.fields_dict.part.get_query = function() {
        return {
            filters: {
                'disabled': 0
            }
        };
    };
    
    dialog.show();
    
    // Focus on barcode field
    dialog.fields_dict.barcode.input.focus();
    
    // Add support for handheld scanners (which typically send Enter key)
    dialog.$wrapper.find('input[data-fieldname="barcode"]').on('keydown', function(e) {
        if (e.keyCode === 13) {
            e.preventDefault();
            dialog.primary_action();
        }
    });
}

function process_barcode(frm, barcode, existing_row = null, qty = 1) {
    if (!barcode) return;
    
    // Check if the barcode already exists in the items table
    let exists = false;
    let existing_item = null;
    
    if (frm.doc.opname_items) {
        for (let item of frm.doc.opname_items) {
            if (item.barcode === barcode) {
                existing_item = item;
                exists = true;
                break;
            }
        }
    }
    
    if (exists && existing_item) {
        // Update quantity for existing barcode
        let row = locals[existing_item.doctype][existing_item.name];
        let new_qty = flt(row.qty_counted) + flt(qty);
        frappe.model.set_value(existing_item.doctype, existing_item.name, 'qty_counted', new_qty);
        
        frappe.show_alert({
            message: __('Quantity updated to {0} for barcode {1}', [new_qty, barcode]),
            indicator: 'green'
        }, 3);
        
        // Scroll to the row
        frm.fields_dict.opname_items.grid.scroll_to_row(row.idx - 1);
        highlight_row(frm, row.name);
    } else if (existing_row) {
        // Update the existing row that triggered this function
        frappe.model.set_value(existing_row.doctype, existing_row.name, 'barcode', barcode);
        
        // Get part from barcode
        frappe.call({
            method: 'car_workshop.car_workshop.doctype.part_stock_opname.part_stock_opname.get_part_from_barcode',
            args: {
                barcode: barcode
            },
            callback: function(r) {
                if (r.message && r.message.part) {
                    frappe.model.set_value(existing_row.doctype, existing_row.name, 'part', r.message.part);
                    frappe.model.set_value(existing_row.doctype, existing_row.name, 'part_name', r.message.part_name);
                    
                    // Set UOM if not already set
                    if (!existing_row.uom) {
                        frappe.model.set_value(existing_row.doctype, existing_row.name, 'uom', r.message.uom || 'Pcs');
                    }
                    
                    // Set qty_counted if not already set
                    if (!flt(existing_row.qty_counted)) {
                        frappe.model.set_value(existing_row.doctype, existing_row.name, 'qty_counted', flt(qty));
                    }
                    
                    highlight_row(frm, existing_row.name);
                } else {
                    // No part found for this barcode
                    frappe.show_alert({
                        message: __('No part found for barcode {0}', [barcode]),
                        indicator: 'red'
                    }, 5);
                }
            }
        });
    } else {
        // Get part from barcode and add new row
        frappe.call({
            method: 'car_workshop.car_workshop.doctype.part_stock_opname.part_stock_opname.get_part_from_barcode',
            args: {
                barcode: barcode
            },
            callback: function(r) {
                if (r.message && r.message.part) {
                    // Add new row with the part
                    let row = frm.add_child('opname_items');
                    row.barcode = barcode;
                    row.part = r.message.part;
                    row.part_name = r.message.part_name;
                    row.uom = r.message.uom || 'Pcs';
                    row.qty_counted = flt(qty);
                    
                    frm.refresh_field('opname_items');
                    
                    frappe.show_alert({
                        message: __('Added part {0} from barcode {1}', [r.message.part, barcode]),
                        indicator: 'green'
                    }, 3);
                    
                    // Scroll to and highlight the new row
                    setTimeout(() => {
                        if (frm.fields_dict.opname_items.grid.grid_rows.length > 0) {
                            frm.fields_dict.opname_items.grid.scroll_to_row(frm.fields_dict.opname_items.grid.grid_rows.length - 1);
                        }
                        highlight_row(frm, row.name);
                    }, 100);
                } else {
                    // No part found for this barcode
                    frappe.show_alert({
                        message: __('No part found for barcode {0}. Enter part manually.', [barcode]),
                        indicator: 'red'
                    }, 5);
                    
                    // Add empty row with just the barcode
                    let row = frm.add_child('opname_items');
                    row.barcode = barcode;
                    row.qty_counted = flt(qty);
                    
                    frm.refresh_field('opname_items');
                    
                    // Open manual selection dialog pre-filled with the barcode
                    setTimeout(() => {
                        let d = new frappe.ui.Dialog({
                            title: __('Select Part for Barcode'),
                            fields: [
                                {
                                    label: __('Barcode'),
                                    fieldname: 'barcode',
                                    fieldtype: 'Data',
                                    read_only: 1,
                                    default: barcode
                                },
                                {
                                    label: __('Part'),
                                    fieldname: 'part',
                                    fieldtype: 'Link',
                                    options: 'Part',
                                    reqd: 1,
                                    description: __('Select the part for this barcode')
                                }
                            ],
                            primary_action_label: __('Confirm'),
                            primary_action: (values) => {
                                frappe.model.set_value(row.doctype, row.name, 'part', values.part);
                                d.hide();
                            }
                        });
                        
                        d.show();
                    }, 1000);
                }
            }
        });
    }
}

function add_part_directly(frm, part_code, qty) {
    if (!part_code) return;
    
    // Check if the part already exists in the items table
    let exists = false;
    let existing_item = null;
    
    if (frm.doc.opname_items) {
        for (let item of frm.doc.opname_items) {
            if (item.part === part_code) {
                existing_item = item;
                exists = true;
                break;
            }
        }
    }
    
    if (exists && existing_item) {
        // Update quantity for existing part
        let row = locals[existing_item.doctype][existing_item.name];
        let new_qty = flt(row.qty_counted) + flt(qty);
        frappe.model.set_value(existing_item.doctype, existing_item.name, 'qty_counted', new_qty);
        
        frappe.show_alert({
            message: __('Quantity updated to {0} for part {1}', [new_qty, part_code]),
            indicator: 'green'
        }, 3);
        
        // Scroll to the row
        frm.fields_dict.opname_items.grid.scroll_to_row(row.idx - 1);
        highlight_row(frm, row.name);
    } else {
        // Get part details
        frappe.db.get_value('Part', part_code, ['part_name', 'uom'])
            .then(r => {
                if (r.message) {
                    // Add new row with the part
                    let row = frm.add_child('opname_items');
                    row.part = part_code;
                    row.part_name = r.message.part_name;
                    row.uom = r.message.uom || 'Pcs';
                    row.qty_counted = flt(qty);
                    
                    frm.refresh_field('opname_items');
                    
                    frappe.show_alert({
                        message: __('Added part {0}', [part_code]),
                        indicator: 'green'
                    }, 3);
                    
                    // Scroll to and highlight the new row
                    setTimeout(() => {
                        if (frm.fields_dict.opname_items.grid.grid_rows.length > 0) {
                            frm.fields_dict.opname_items.grid.scroll_to_row(frm.fields_dict.opname_items.grid.grid_rows.length - 1);
                        }
                        highlight_row(frm, row.name);
                    }, 100);
                }
            });
    }
}

function highlight_row(frm, row_name) {
    // Highlight the row briefly
    if (frm.fields_dict.opname_items.grid.grid_rows_by_docname[row_name]) {
        let $row = $(frm.fields_dict.opname_items.grid.grid_rows_by_docname[row_name].row);
        $row.addClass('highlight-row');
        
        setTimeout(() => {
            $row.removeClass('highlight-row');
        }, 1000);
    }
}

function scan_barcode_for_row(frm, row) {
    // Scan barcode specifically for a row
    if (frappe.dom.is_touchscreen()) {
        frappe.barcode.scan()
            .then(barcode => {
                if (barcode) {
                    process_barcode(frm, barcode, row);
                }
            })
            .catch(error => {
                console.error("Barcode scanning error:", error);
                frappe.show_alert({
                    message: __('Barcode scanning failed. Try entering manually.'),
                    indicator: 'red'
                });
            });
    } else {
        try {
            const scanner = new frappe.ui.Scanner({
                dialog: true,
                multiple: false,
                on_scan(data) {
                    if (data && data.length) {
                        process_barcode(frm, data, row);
                    }
                }
            });
        } catch (e) {
            console.error("Scanner initialization error:", e);
            frappe.show_alert({
                message: __('Camera access failed. Please enter barcode manually.'),
                indicator: 'orange'
            });
            
            // Show manual barcode input dialog
            let d = new frappe.ui.Dialog({
                title: __('Enter Barcode'),
                fields: [
                    {
                        label: __('Barcode'),
                        fieldname: 'barcode',
                        fieldtype: 'Data',
                        reqd: 1
                    }
                ],
                primary_action_label: __('OK'),
                primary_action: (values) => {
                    process_barcode(frm, values.barcode, row);
                    d.hide();
                }
            });
            
            d.show();
        }
    }
}

function create_stock_adjustment(frm) {
    frappe.call({
        method: 'car_workshop.car_workshop.doctype.part_stock_adjustment.part_stock_adjustment.create_adjustment_from_opname',
        args: {
            opname_id: frm.doc.name
        },
        freeze: true,
        freeze_message: __('Creating stock adjustment...'),
        callback: function(r) {
            if (r.message) {
                frappe.set_route("Form", "Part Stock Adjustment", r.message.name);
            } else {
                frappe.msgprint(__('No differences found between counted and system quantities'));
            }
        }
    });
}

// Add custom CSS
frappe.dom.set_style(`
    .highlight-row {
        animation: highlight-background 1s ease;
    }
    
    @keyframes highlight-background {
        0% { background-color: rgba(255, 255, 0, 0.3); }
        100% { background-color: transparent; }
    }
`);