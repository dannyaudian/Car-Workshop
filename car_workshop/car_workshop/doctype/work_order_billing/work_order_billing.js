// Copyright (c) 2023, PT. Innovasi Terbaik Bangsa and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Order Billing', {
    setup: function(frm) {
        frm.set_query('work_order', function() {
            return {
                filters: {
                    status: ['in', ['Completed', 'Closed']],
                    billing_status: 'Unbilled'
                }
            };
        });
        
        frm.set_query('cost_center', function() {
            return {
                filters: {
                    company: frm.doc.company
                }
            };
        });
        
        frm.set_query('taxes_and_charges', function() {
            return {
                filters: {
                    company: frm.doc.company
                }
            };
        });
        
        // Set query for payment accounts
        frm.set_query('payment_account', 'payment_details', function() {
            return {
                filters: {
                    is_group: 0,
                    company: frm.doc.company,
                    account_type: ['in', ['Bank', 'Cash']]
                }
            };
        });
    },
    
    refresh: function(frm) {
        // Add custom buttons
        if (frm.doc.docstatus === 1) {
            if (!frm.doc.sales_invoice) {
                frm.add_custom_button(__('Sales Invoice'), function() {
                    frappe.model.open_mapped_doc({
                        method: "car_workshop.car_workshop.doctype.work_order_billing.work_order_billing.make_sales_invoice",
                        frm: frm
                    });
                }, __('Create'));
            } else {
                frm.add_custom_button(__('Sales Invoice'), function() {
                    frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice);
                }, __('View'));
            }
        }
        
        // Add action to fetch data from Work Order
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Fetch from Work Order'), function() {
                fetch_work_order_details(frm);
            });
        }
    },
    
    work_order: function(frm) {
        if (frm.doc.work_order) {
            fetch_work_order_details(frm);
        }
    },
    
    validate: function(frm) {
        calculate_totals(frm);
    },
    
    payment_method: function(frm) {
        if (frm.doc.payment_method === 'Multiple') {
            // Clear existing payment details if coming from single mode
            if (frm.doc.payment_details && frm.doc.payment_details.length === 1) {
                frm.clear_table('payment_details');
                frm.refresh_field('payment_details');
            }
        } else {
            // Set single payment with the selected method
            frm.clear_table('payment_details');
            let payment = frm.add_child('payment_details');
            payment.payment_method = frm.doc.payment_method;
            
            // Try to set a default account based on payment method
            if (frm.doc.company) {
                let account_promise;
                if (frm.doc.payment_method === 'Cash') {
                    account_promise = frappe.db.get_value('Company', frm.doc.company, 'default_cash_account');
                } else if (frm.doc.payment_method === 'Bank Transfer') {
                    account_promise = frappe.db.get_value('Company', frm.doc.company, 'default_bank_account');
                }
                
                if (account_promise) {
                    account_promise.then(r => {
                        if (r.message) {
                            let account = r.message.default_cash_account || r.message.default_bank_account;
                            if (account) {
                                payment.payment_account = account;
                                frm.refresh_field('payment_details');
                            }
                        }
                    });
                }
            }
            
            payment.amount = frm.doc.grand_total || 0;
            frm.refresh_field('payment_details');
        }
    },
    
    // Trigger calculation on amount changes
    total_services_amount: function(frm) { calculate_totals(frm); },
    total_parts_amount: function(frm) { calculate_totals(frm); },
    total_external_services_amount: function(frm) { calculate_totals(frm); },
    taxes_and_charges: function(frm) { calculate_tax(frm); },
    discount_amount: function(frm) { calculate_totals(frm); }
});

// Calculate totals for job type items
frappe.ui.form.on('Work Order Billing Job Type', {
    hours: function(frm, cdt, cdn) {
        calculate_job_type_amount(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculate_job_type_amount(frm, cdt, cdn);
    },
    job_type_items_remove: function(frm) {
        calculate_services_total(frm);
    }
});

// Calculate totals for service package items
frappe.ui.form.on('Work Order Billing Service Package', {
    quantity: function(frm, cdt, cdn) {
        calculate_service_package_amount(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculate_service_package_amount(frm, cdt, cdn);
    },
    service_package_items_remove: function(frm) {
        calculate_services_total(frm);
    }
});

// Calculate totals for part items
frappe.ui.form.on('Work Order Billing Part', {
    quantity: function(frm, cdt, cdn) {
        calculate_part_amount(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculate_part_amount(frm, cdt, cdn);
    },
    part_items_remove: function(frm) {
        calculate_parts_total(frm);
    }
});

// Calculate totals for external service items
frappe.ui.form.on('Work Order Billing External Service', {
    rate: function(frm, cdt, cdn) {
        calculate_external_service_amount(frm, cdt, cdn);
    },
    external_service_items_remove: function(frm) {
        calculate_external_services_total(frm);
    }
});

// Calculate totals for payment details
frappe.ui.form.on('Work Order Billing Payment', {
    amount: function(frm) {
        calculate_payment_total(frm);
    },
    payment_details_remove: function(frm) {
        calculate_payment_total(frm);
    }
});

// Helper functions
function fetch_work_order_details(frm) {
    if (!frm.doc.work_order) {
        frappe.msgprint(__('Please select a Work Order first'));
        return;
    }
    
    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Work Order',
            name: frm.doc.work_order
        },
        callback: function(r) {
            if (r.message) {
                let work_order = r.message;
                
                // Set basic details
                frm.set_value('customer', work_order.customer);
                frm.set_value('customer_vehicle', work_order.customer_vehicle);
                frm.set_value('company', work_order.company);
                
                // Fetch job types
                frappe.call({
                    method: 'frappe.client.get_list',
                    args: {
                        doctype: 'Work Order Job Type',
                        filters: { parent: work_order.name },
                        fields: ['job_type', 'hours', 'rate', 'amount', 'name']
                    },
                    callback: function(r) {
                        if (r.message && r.message.length > 0) {
                            frm.clear_table('job_type_items');
                            r.message.forEach(function(job) {
                                let child = frm.add_child('job_type_items');
                                child.job_type = job.job_type;
                                child.hours = job.hours;
                                child.rate = job.rate;
                                child.amount = job.amount;
                                child.from_work_order = 1;
                                child.work_order_job_type = job.name;
                            });
                            frm.refresh_field('job_type_items');
                            calculate_services_total(frm);
                        }
                    }
                });
                
                // Fetch service packages
                frappe.call({
                    method: 'frappe.client.get_list',
                    args: {
                        doctype: 'Work Order Service Package',
                        filters: { parent: work_order.name },
                        fields: ['service_package', 'quantity', 'rate', 'amount', 'name']
                    },
                    callback: function(r) {
                        if (r.message && r.message.length > 0) {
                            frm.clear_table('service_package_items');
                            r.message.forEach(function(pkg) {
                                let child = frm.add_child('service_package_items');
                                child.service_package = pkg.service_package;
                                child.quantity = pkg.quantity;
                                child.rate = pkg.rate;
                                child.amount = pkg.amount;
                                child.from_work_order = 1;
                                child.work_order_service_package = pkg.name;
                            });
                            frm.refresh_field('service_package_items');
                            calculate_services_total(frm);
                        }
                    }
                });
                
                // Fetch parts
                frappe.call({
                    method: 'frappe.client.get_list',
                    args: {
                        doctype: 'Work Order Part',
                        filters: { parent: work_order.name },
                        fields: ['part', 'warehouse', 'quantity', 'uom', 'rate', 'amount', 'name']
                    },
                    callback: function(r) {
                        if (r.message && r.message.length > 0) {
                            frm.clear_table('part_items');
                            r.message.forEach(function(part) {
                                let child = frm.add_child('part_items');
                                child.part = part.part;
                                child.warehouse = part.warehouse;
                                child.quantity = part.quantity;
                                child.uom = part.uom;
                                child.rate = part.rate;
                                child.amount = part.amount;
                                child.from_work_order = 1;
                                child.work_order_part = part.name;
                            });
                            frm.refresh_field('part_items');
                            calculate_parts_total(frm);
                        }
                    }
                });
                
                // Calculate totals after fetching data
                setTimeout(function() {
                    calculate_totals(frm);
                }, 1000);
            }
        }
    });
}

function calculate_job_type_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = flt(row.hours) * flt(row.rate);
    refresh_field('amount', cdn, 'job_type_items');
    calculate_services_total(frm);
}

function calculate_service_package_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = flt(row.quantity) * flt(row.rate);
    refresh_field('amount', cdn, 'service_package_items');
    calculate_services_total(frm);
}

function calculate_part_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = flt(row.quantity) * flt(row.rate);
    refresh_field('amount', cdn, 'part_items');
    calculate_parts_total(frm);
}

function calculate_external_service_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = flt(row.rate);
    refresh_field('amount', cdn, 'external_service_items');
    calculate_external_services_total(frm);
}

function calculate_services_total(frm) {
    let total_services = 0;
    
    // Add job type amounts
    if (frm.doc.job_type_items && frm.doc.job_type_items.length) {
        frm.doc.job_type_items.forEach(function(job) {
            total_services += flt(job.amount);
        });
    }
    
    // Add service package amounts
    if (frm.doc.service_package_items && frm.doc.service_package_items.length) {
        frm.doc.service_package_items.forEach(function(pkg) {
            total_services += flt(pkg.amount);
        });
    }
    
    frm.set_value('total_services_amount', total_services);
}

function calculate_parts_total(frm) {
    let total_parts = 0;
    
    if (frm.doc.part_items && frm.doc.part_items.length) {
        frm.doc.part_items.forEach(function(part) {
            total_parts += flt(part.amount);
        });
    }
    
    frm.set_value('total_parts_amount', total_parts);
}

function calculate_external_services_total(frm) {
    let total_external = 0;
    
    if (frm.doc.external_service_items && frm.doc.external_service_items.length) {
        frm.doc.external_service_items.forEach(function(svc) {
            total_external += flt(svc.amount);
        });
    }
    
    frm.set_value('total_external_services_amount', total_external);
}

function calculate_payment_total(frm) {
    let total_payment = 0;
    
    if (frm.doc.payment_details && frm.doc.payment_details.length) {
        frm.doc.payment_details.forEach(function(payment) {
            total_payment += flt(payment.amount);
        });
    }
    
    frm.set_value('payment_amount', total_payment);
    
    // Calculate balance
    let balance = flt(frm.doc.grand_total) - flt(total_payment);
    frm.set_value('balance_amount', balance);
    
    // Update payment status
    if (total_payment <= 0) {
        frm.set_value('payment_status', 'Unpaid');
    } else if (total_payment < frm.doc.grand_total) {
        frm.set_value('payment_status', 'Partially Paid');
    } else {
        frm.set_value('payment_status', 'Paid');
    }
}

function calculate_tax(frm) {
    if (!frm.doc.taxes_and_charges) {
        frm.set_value('tax_amount', 0);
        calculate_totals(frm);
        return;
    }
    
    frappe.call({
        method: 'frappe.client.get',
        args: {
            doctype: 'Sales Taxes and Charges Template',
            name: frm.doc.taxes_and_charges
        },
        callback: function(r) {
            if (r.message && r.message.taxes) {
                let tax_amount = 0;
                let subtotal = flt(frm.doc.total_services_amount) + 
                               flt(frm.doc.total_parts_amount) + 
                               flt(frm.doc.total_external_services_amount);
                
                r.message.taxes.forEach(function(tax) {
                    if (tax.charge_type === 'On Net Total') {
                        tax_amount += subtotal * flt(tax.rate) / 100;
                    }
                });
                
                frm.set_value('tax_amount', tax_amount);
                calculate_totals(frm);
            }
        }
    });
}

function calculate_totals(frm) {
    // Calculate subtotal
    let subtotal = flt(frm.doc.total_services_amount) + 
                   flt(frm.doc.total_parts_amount) + 
                   flt(frm.doc.total_external_services_amount);
    frm.set_value('subtotal', subtotal);
    
    // Calculate grand total
    let grand_total = subtotal + flt(frm.doc.tax_amount) - flt(frm.doc.discount_amount);
    frm.set_value('grand_total', grand_total);
    
    // Calculate rounded total
    let rounded_total = Math.round(grand_total);
    frm.set_value('rounded_total', rounded_total);
    
    // Update payment amounts if single payment method
    if (frm.doc.payment_method && frm.doc.payment_method !== 'Multiple') {
        if (frm.doc.payment_details && frm.doc.payment_details.length === 1) {
            frm.doc.payment_details[0].amount = grand_total;
            frm.refresh_field('payment_details');
        }
    }
    
    // Calculate balance amount
    calculate_payment_total(frm);
}