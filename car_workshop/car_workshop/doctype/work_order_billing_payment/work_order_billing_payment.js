frappe.ui.form.on('Work Order Billing Payment', {
    amount(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.amount && row.amount < 0) {
            frappe.model.set_value(cdt, cdn, 'amount', 0);
            frappe.msgprint(__('Amount cannot be negative'));
        }

        // Recalculate totals on the parent document
        if (typeof calculate_payment_total === 'function') {
            calculate_payment_total(frm);
        }
    }
});

