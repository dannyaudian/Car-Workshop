frappe.ui.form.on('Service Package', {
    refresh: function(frm) {
        // Additional refresh logic if needed
    },
    
    // Calculate totals when form values change
    details_add: function(frm, cdt, cdn) {
        calculate_total(frm);
    },
    details_remove: function(frm, cdt, cdn) {
        calculate_total(frm);
    }
});

frappe.ui.form.on('Service Package Detail', {
    // When item type changes, clear related fields
    item_type: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.item_type === 'Job') {
            frappe.model.set_value(cdt, cdn, 'part', '');
        } else if (row.item_type === 'Part') {
            frappe.model.set_value(cdt, cdn, 'job_type', '');
        }
        frappe.model.set_value(cdt, cdn, 'rate', 0);
        frappe.model.set_value(cdt, cdn, 'amount', 0);
    },
    
    // When job type changes, fetch its price
    job_type: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.job_type) {
            // Use the price_list from the parent document, or default to 'Retail Price List'
            var price_list = frm.doc.price_list || 'Retail Price List';
            
            // Call the get_active_service_price method
            frappe.call({
                method: 'car_workshop.car_workshop.doctype.service_price_list.get_active_service_price.get_active_service_price',
                args: {
                    reference_type: 'Job Type',
                    reference_name: row.job_type,
                    price_list: price_list
                },
                callback: function(r) {
                    if (r.message && r.message.rate) {
                        // Set the rate from the service price list
                        frappe.model.set_value(cdt, cdn, 'rate', r.message.rate);
                    } else {
                        // Fallback: try to get standard_rate from Job Type
                        frappe.call({
                            method: 'frappe.client.get_value',
                            args: {
                                doctype: 'Job Type',
                                filters: { name: row.job_type },
                                fieldname: ['standard_rate']
                            },
                            callback: function(r) {
                                if (r.message && r.message.standard_rate) {
                                    frappe.model.set_value(cdt, cdn, 'rate', r.message.standard_rate);
                                } else {
                                    frappe.model.set_value(cdt, cdn, 'rate', 0);
                                }
                            }
                        });
                    }
                }
            });
        }
    },
    
    // When part changes, fetch its price
    part: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.part) {
            // Use the price_list from the parent document, or default to 'Retail Price List'
            var price_list = frm.doc.price_list || 'Retail Price List';
            
            // Call the get_active_service_price method
            frappe.call({
                method: 'car_workshop.car_workshop.doctype.service_price_list.get_active_service_price.get_active_service_price',
                args: {
                    reference_type: 'Part',
                    reference_name: row.part,
                    price_list: price_list
                },
                callback: function(r) {
                    if (r.message && r.message.rate) {
                        // Set the rate from the service price list
                        frappe.model.set_value(cdt, cdn, 'rate', r.message.rate);
                    } else {
                        // Fallback: try to get current_price from Part
                        frappe.call({
                            method: 'frappe.client.get_value',
                            args: {
                                doctype: 'Part',
                                filters: { name: row.part },
                                fieldname: ['current_price']
                            },
                            callback: function(r) {
                                if (r.message && r.message.current_price) {
                                    frappe.model.set_value(cdt, cdn, 'rate', r.message.current_price);
                                } else {
                                    frappe.model.set_value(cdt, cdn, 'rate', 0);
                                }
                            }
                        });
                    }
                }
            });
        }
    },
    
    // When quantity or rate changes, calculate amount
    quantity: function(frm, cdt, cdn) {
        calculate_amount(cdt, cdn);
        calculate_total(frm);
    },
    
    rate: function(frm, cdt, cdn) {
        calculate_amount(cdt, cdn);
        calculate_total(frm);
    }
});

// Helper function to calculate amount for a row
function calculate_amount(cdt, cdn) {
    var row = locals[cdt][cdn];
    var amount = flt(row.quantity) * flt(row.rate);
    frappe.model.set_value(cdt, cdn, 'amount', amount);
}

// Helper function to calculate total package price
function calculate_total(frm) {
    var total = 0;
    $.each(frm.doc.details || [], function(i, d) {
        total += flt(d.amount);
    });
    frm.set_value('price', total);
}