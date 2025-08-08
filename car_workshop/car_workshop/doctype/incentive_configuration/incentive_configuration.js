frappe.ui.form.on('Incentive Configuration', {
    incentive_type(frm) {
        // Show or hide rate field based on incentive type
        frm.toggle_display('rate', frm.doc.incentive_type !== 'Tiered');
        if (frm.doc.incentive_type !== 'Tiered') {
            frm.clear_table('tiers');
        }
    },
    rate(frm) {
        if (frm.doc.incentive_type === 'Percentage' && frm.doc.rate > 100) {
            frm.set_value('rate', 100);
            frappe.msgprint(__('Rate cannot exceed 100%'));
        }
    },
    refresh(frm) {
        frm.trigger('incentive_type');
    }
});

frappe.ui.form.on('Incentive Tier', {
    rate(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.rate && row.rate > 100) {
            frappe.model.set_value(cdt, cdn, 'rate', 100);
            frappe.msgprint(__('Rate cannot exceed 100%'));
        }
    }
});

