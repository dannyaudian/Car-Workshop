frappe.ui.form.on('Work Order Billing Return', {
    quantity(frm, cdt, cdn) {
        update_amount(frm, cdt, cdn);
    },
    rate(frm, cdt, cdn) {
        update_amount(frm, cdt, cdn);
    }
});

function update_amount(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const qty = flt(row.quantity);
    const rate = flt(row.rate);
    frappe.model.set_value(cdt, cdn, 'amount', qty * rate);

    // Refresh payment totals when returns affect billing
    if (typeof calculate_payment_total === 'function') {
        calculate_payment_total(frm);
    }
}

