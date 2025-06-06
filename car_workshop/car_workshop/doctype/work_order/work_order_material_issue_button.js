// Copyright (c) 2025, Danny Audian and contributors
// For license information, please see license.txt

// Add "Create Material Issue" button to Work Order
frappe.ui.form.on('Work Order', {
    refresh: function(frm) {
        // Add button only if the Work Order is submitted and not cancelled
        if (frm.doc.docstatus === 1 && frm.doc.status !== 'Cancelled') {
            frm.add_custom_button(__('Material Issue'), function() {
                // Call server method to create material issue
                frappe.model.open_mapped_doc({
                    method: 'car_workshop.car_workshop.doctype.work_order.work_order.make_material_issue',
                    frm: frm
                });
            }, __('Create'));
        }
    }
});