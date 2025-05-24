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
    },
    
    // When part changes, fetch its price
    part: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (row.part) {
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