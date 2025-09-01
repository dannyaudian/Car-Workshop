// Copyright (c) 2023, PT. Innovasi Terbaik Bangsa and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Order Billing Payment', {
    // Validate and update on amount change
    amount: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        
        // Prevent negative amounts
        if (row.amount && flt(row.amount) < 0) {
            frappe.model.set_value(cdt, cdn, 'amount', 0);
            frappe.msgprint(__('Amount cannot be negative'));
            return;
        }
        
        // If amount > 0, ensure payment account is selected
        if (flt(row.amount) > 0 && !row.payment_account) {
            frappe.msgprint(__('Please select a Payment Account'), __('Account Required'));
        }
        
        // Update parent form totals
        updateParentTotals(frm);
    },
    
    // Validate payment account when selected/changed
    payment_account: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        
        // If amount > 0, ensure payment account is selected
        if (flt(row.amount) > 0 && !row.payment_account) {
            frappe.msgprint(__('Please select a Payment Account'), __('Account Required'));
        }
    },
    
    // Update totals when a payment row is removed
    payment_method: function(frm, cdt, cdn) {
        updateParentTotals(frm);
    },
    
    // Update totals when any field changes that might affect presentation
    reference_number: function(frm, cdt, cdn) {
        // Optional validation for reference number format if needed
        const row = locals[cdt][cdn];
        if (row.reference_number && row.reference_number.trim() === '') {
            frappe.model.set_value(cdt, cdn, 'reference_number', null);
        }
    }
});

/**
 * Update payment totals on the parent form
 * This is called whenever any payment detail changes
 * 
 * @param {Object} frm - The parent form
 */
function updateParentTotals(frm) {
    // Find the parent form's recalculation function and call it
    if (frm.doc.parenttype === 'Work Order Billing' && frm.doc.parent) {
        const parentForm = frappe.get_doc('Work Order Billing', frm.doc.parent);
        
        // Try to access parent form's calculatePaymentTotal function
        if (parentForm && parentForm.parent_frm) {
            // First try the standard function name
            if (typeof parentForm.parent_frm.calculatePaymentTotal === 'function') {
                parentForm.parent_frm.calculatePaymentTotal();
            } 
            // Then try alternative name
            else if (typeof parentForm.parent_frm.calculate_payment_total === 'function') {
                parentForm.parent_frm.calculate_payment_total();
            }
            // Fallback: try to trigger a field update to recalculate totals
            else {
                frappe.model.set_value(
                    'Work Order Billing', 
                    frm.doc.parent, 
                    'payment_amount',
                    getPaymentTotal(frm.doc.parent)
                );
            }
        }
    } else {
        // For standalone use or testing, try to find a global function
        if (typeof calculate_payment_total === 'function') {
            calculate_payment_total(frm);
        }
    }
}

/**
 * Calculate the total payment amount for a Work Order Billing document
 * This is a helper function when direct access to parent methods isn't available
 * 
 * @param {string} parent_name - The name of the parent Work Order Billing document
 * @returns {number} - The total payment amount
 */
async function getPaymentTotal(parent_name) {
    try {
        const result = await frappe.db.get_list('Work Order Billing Payment', {
            filters: { parent: parent_name },
            fields: ['amount']
        });
        
        return result.reduce((total, row) => total + flt(row.amount), 0);
    } catch (error) {
        console.error('Error calculating payment total:', error);
        return 0;
    }
}