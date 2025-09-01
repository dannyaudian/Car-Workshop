// Copyright (c) 2023, PT. Innovasi Terbaik Bangsa and contributors
// For license information, please see license.txt

frappe.ui.form.on('Work Order Billing', {
    setup: function(frm) {
        // Filter work orders to only show completed/closed ones that are unbilled
        frm.set_query('work_order', function() {
            return {
                filters: {
                    status: ['in', ['Completed', 'Closed']],
                    billing_status: 'Unbilled'
                }
            };
        });
        
        // Filter cost center by company
        frm.set_query('cost_center', function() {
            return {
                filters: {
                    company: frm.doc.company
                }
            };
        });
        
        // Filter taxes template by company
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
    
    refresh: async function(frm) {
        // Add fetch button for draft documents
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Fetch from Work Order'), async () => {
                await fetchWorkOrderDetails(frm);
            });
        }
        
        // Add buttons for submitted documents
        if (frm.doc.docstatus === 1) {
            if (!frm.doc.sales_invoice) {
                frm.add_custom_button(__('Create Sales Invoice'), async () => {
                    await createSalesInvoice(frm);
                }, __('Actions'));
            } else {
                frm.add_custom_button(__('View Sales Invoice'), () => {
                    frappe.set_route("Form", "Sales Invoice", frm.doc.sales_invoice);
                }, __('Actions'));
            }
        }
    },
    
    work_order: async function(frm) {
        if (frm.doc.work_order && frm.doc.docstatus === 0) {
            await fetchWorkOrderDetails(frm);
        }
    },
    
    validate: function(frm) {
        calculateTotals(frm);
    },
    
    payment_method: function(frm) {
        setupPaymentDetails(frm);
    },
    
    // Trigger calculation on amount changes
    discount_amount: function(frm) { 
        calculateTotals(frm); 
    },
    
    taxes_and_charges: function(frm) { 
        calculateTax(frm); 
    },
    
    down_payment_type: function(frm) {
        calculateDownPayment(frm);
    },
    
    down_payment_amount: function(frm) {
        calculateDownPayment(frm);
    }
});

// Calculate totals for job type items
frappe.ui.form.on('Work Order Billing Job Type', {
    hours: function(frm, cdt, cdn) {
        calculateJobTypeAmount(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculateJobTypeAmount(frm, cdt, cdn);
    },
    job_type_items_remove: function(frm) {
        calculateServiceTotal(frm);
    }
});

// Calculate totals for service package items
frappe.ui.form.on('Work Order Billing Service Package', {
    quantity: function(frm, cdt, cdn) {
        calculateServicePackageAmount(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculateServicePackageAmount(frm, cdt, cdn);
    },
    service_package_items_remove: function(frm) {
        calculateServiceTotal(frm);
    }
});

// Calculate totals for part items
frappe.ui.form.on('Work Order Billing Part', {
    quantity: function(frm, cdt, cdn) {
        calculatePartAmount(frm, cdt, cdn);
    },
    rate: function(frm, cdt, cdn) {
        calculatePartAmount(frm, cdt, cdn);
    },
    part_items_remove: function(frm) {
        calculatePartsTotal(frm);
    }
});

// Calculate totals for external service items
frappe.ui.form.on('Work Order Billing External Service', {
    rate: function(frm, cdt, cdn) {
        calculateExternalServiceAmount(frm, cdt, cdn);
    },
    external_service_items_remove: function(frm) {
        calculateExternalServicesTotal(frm);
    }
});

// Calculate totals for payment details
frappe.ui.form.on('Work Order Billing Payment', {
    amount: function(frm) {
        calculatePaymentTotal(frm);
    },
    payment_details_remove: function(frm) {
        calculatePaymentTotal(frm);
    }
});

// Helper functions
async function fetchWorkOrderDetails(frm) {
    if (!frm.doc.work_order) {
        frappe.msgprint(__('Please select a Work Order first'));
        return;
    }
    
    frappe.dom.freeze(__('Fetching Work Order details...'));
    
    try {
        // Get work order details using the aggregator function
        const data = await frappe.xcall(
            'car_workshop.api.billing_api.get_work_order_billing_source',
            {
                work_order: frm.doc.work_order
            }
        );
        
        // Get work order basic info
        const workOrder = await frappe.db.get_doc('Work Order', frm.doc.work_order);
        
        // Set basic details
        frm.set_value('customer', workOrder.customer);
        frm.set_value('customer_vehicle', workOrder.customer_vehicle);
        frm.set_value('company', workOrder.company);
        
        // Process job types
        if (data.job_types && data.job_types.length) {
            frm.clear_table('job_type_items');
            data.job_types.forEach(job => {
                let child = frm.add_child('job_type_items');
                child.job_type = job.job_type;
                child.job_type_name = job.job_type_name;
                child.hours = job.hours;
                child.rate = job.rate;
                child.amount = job.amount;
                child.from_work_order = 1;
            });
            frm.refresh_field('job_type_items');
        }
        
        // Process service packages
        if (data.service_packages && data.service_packages.length) {
            frm.clear_table('service_package_items');
            data.service_packages.forEach(pkg => {
                let child = frm.add_child('service_package_items');
                child.service_package = pkg.service_package;
                child.service_package_name = pkg.service_package_name;
                child.quantity = pkg.quantity;
                child.rate = pkg.rate;
                child.amount = pkg.amount;
                child.from_work_order = 1;
            });
            frm.refresh_field('service_package_items');
        }
        
        // Process parts
        if (data.parts && data.parts.length) {
            frm.clear_table('part_items');
            data.parts.forEach(part => {
                let child = frm.add_child('part_items');
                child.part = part.part;
                child.part_name = part.part_name;
                child.quantity = part.quantity;
                child.rate = part.rate;
                child.amount = part.amount;
                child.from_work_order = 1;
            });
            frm.refresh_field('part_items');
        }
        
        // Process external services
        if (data.external_services && data.external_services.length) {
            frm.clear_table('external_service_items');
            data.external_services.forEach(service => {
                let child = frm.add_child('external_service_items');
                child.service_name = service.service_name;
                child.provider = service.provider;
                child.rate = service.rate;
                child.amount = service.amount;
                child.from_work_order = 1;
            });
            frm.refresh_field('external_service_items');
        }
        
        // Calculate all totals
        calculateTotals(frm);
        
        frappe.show_alert({
            message: __('Work Order details fetched successfully'),
            indicator: 'green'
        });
    } catch (error) {
        console.error("Error fetching work order details:", error);
        frappe.msgprint({
            title: __('Error'),
            indicator: 'red',
            message: __('Failed to fetch Work Order details: {0}', [error.message || error])
        });
    } finally {
        frappe.dom.unfreeze();
    }
}

async function createSalesInvoice(frm) {
    frappe.dom.freeze(__('Creating Sales Invoice...'));
    
    try {
        const sales_invoice = await frappe.xcall(
            'car_workshop.car_workshop.doctype.work_order_billing.work_order_billing.make_sales_invoice',
            { 
                source_name: frm.doc.name 
            }
        );
        
        // Update the sales_invoice field and refresh
        frm.reload_doc();
        
        frappe.show_alert({
            message: __('Sales Invoice {0} created successfully', [sales_invoice]),
            indicator: 'green'
        });
        
        // Open the newly created Sales Invoice
        frappe.set_route("Form", "Sales Invoice", sales_invoice);
    } catch (error) {
        console.error("Error creating Sales Invoice:", error);
        frappe.msgprint({
            title: __('Error'),
            indicator: 'red',
            message: __('Failed to create Sales Invoice: {0}', [error.message || error])
        });
    } finally {
        frappe.dom.unfreeze();
    }
}

function calculateJobTypeAmount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = flt(row.hours) * flt(row.rate);
    frm.refresh_field('job_type_items');
    calculateServiceTotal(frm);
}

function calculateServicePackageAmount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = flt(row.quantity) * flt(row.rate);
    frm.refresh_field('service_package_items');
    calculateServiceTotal(frm);
}

function calculatePartAmount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = flt(row.quantity) * flt(row.rate);
    frm.refresh_field('part_items');
    calculatePartsTotal(frm);
}

function calculateExternalServiceAmount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    row.amount = flt(row.rate);
    frm.refresh_field('external_service_items');
    calculateExternalServicesTotal(frm);
}

function calculateServiceTotal(frm) {
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
    calculateTotals(frm);
}

function calculatePartsTotal(frm) {
    let total_parts = 0;
    
    if (frm.doc.part_items && frm.doc.part_items.length) {
        frm.doc.part_items.forEach(function(part) {
            total_parts += flt(part.amount);
        });
    }
    
    frm.set_value('total_parts_amount', total_parts);
    calculateTotals(frm);
}

function calculateExternalServicesTotal(frm) {
    let total_external = 0;
    
    if (frm.doc.external_service_items && frm.doc.external_service_items.length) {
        frm.doc.external_service_items.forEach(function(svc) {
            total_external += flt(svc.amount);
        });
    }
    
    frm.set_value('total_external_services_amount', total_external);
    calculateTotals(frm);
}

function calculatePaymentTotal(frm) {
    let total_payment = 0;
    
    if (frm.doc.payment_details && frm.doc.payment_details.length) {
        frm.doc.payment_details.forEach(function(payment) {
            total_payment += flt(payment.amount);
        });
    }
    
    frm.set_value('payment_amount', total_payment);
    
    // Calculate balance based on down payment
    calculateBalance(frm);
    
    // Update payment status
    updatePaymentStatus(frm);
}

function calculateDownPayment(frm) {
    if (!frm.doc.down_payment_amount) return;
    
    calculateBalance(frm);
}

function calculateBalance(frm) {
    // Calculate down payment amount
    let down_payment = 0;
    if (frm.doc.down_payment_amount) {
        if (frm.doc.down_payment_type === "Percentage") {
            down_payment = flt(frm.doc.grand_total) * flt(frm.doc.down_payment_amount) / 100;
        } else {
            down_payment = flt(frm.doc.down_payment_amount);
        }
    }
    
    // Calculate remaining balance after down payment
    const remaining = flt(frm.doc.grand_total) - down_payment;
    frm.set_value('remaining_balance', remaining);
    
    // Calculate final balance
    const balance = remaining - flt(frm.doc.payment_amount);
    frm.set_value('balance_amount', balance);
}

function updatePaymentStatus(frm) {
    let total_paid = flt(frm.doc.payment_amount);
    
    // Add down payment to total paid
    if (frm.doc.down_payment_amount) {
        if (frm.doc.down_payment_type === "Percentage") {
            total_paid += flt(frm.doc.grand_total) * flt(frm.doc.down_payment_amount) / 100;
        } else {
            total_paid += flt(frm.doc.down_payment_amount);
        }
    }
    
    // Update payment status
    if (total_paid <= 0) {
        frm.set_value('payment_status', 'Unpaid');
    } else if (total_paid < frm.doc.grand_total) {
        frm.set_value('payment_status', 'Partially Paid');
    } else {
        frm.set_value('payment_status', 'Paid');
    }
}

async function calculateTax(frm) {
    if (!frm.doc.taxes_and_charges) {
        frm.set_value('tax_amount', 0);
        calculateTotals(frm);
        return;
    }
    
    try {
        const taxTemplate = await frappe.db.get_doc('Sales Taxes and Charges Template', frm.doc.taxes_and_charges);
        
        if (taxTemplate && taxTemplate.taxes) {
            let tax_amount = 0;
            const subtotal = flt(frm.doc.total_services_amount) + 
                           flt(frm.doc.total_parts_amount) + 
                           flt(frm.doc.total_external_services_amount);
            
            taxTemplate.taxes.forEach(function(tax) {
                if (tax.charge_type === 'On Net Total') {
                    tax_amount += subtotal * flt(tax.rate) / 100;
                }
            });
            
            frm.set_value('tax_amount', tax_amount);
        }
    } catch (error) {
        console.error("Error calculating tax:", error);
        frm.set_value('tax_amount', 0);
    } finally {
        calculateTotals(frm);
    }
}

function calculateTotals(frm) {
    // Calculate subtotal
    const subtotal = flt(frm.doc.total_services_amount) + 
                   flt(frm.doc.total_parts_amount) + 
                   flt(frm.doc.total_external_services_amount);
    frm.set_value('subtotal', subtotal);
    
    // Calculate grand total
    const grand_total = subtotal + flt(frm.doc.tax_amount) - flt(frm.doc.discount_amount);
    frm.set_value('grand_total', grand_total);
    
    // Calculate rounded total (simple rounding for preview)
    const rounded_total = Math.round(grand_total);
    frm.set_value('rounded_total', rounded_total);
    
    // Update balance calculations
    calculateBalance(frm);
    
    // Update payment status
    updatePaymentStatus(frm);
}

function setupPaymentDetails(frm) {
    if (frm.doc.payment_method === 'Multiple') {
        // If switching to multiple payment mode, keep existing entries
        if (!frm.doc.payment_details || frm.doc.payment_details.length === 0) {
            // Add a blank row if no entries exist
            let payment = frm.add_child('payment_details');
            frm.refresh_field('payment_details');
        }
    } else if (frm.doc.payment_method) {
        // Set single payment with the selected method
        frm.clear_table('payment_details');
        let payment = frm.add_child('payment_details');
        payment.payment_method = frm.doc.payment_method;
        
        // Try to set a default account based on payment method
        setDefaultPaymentAccount(frm, payment);
        
        payment.amount = frm.doc.grand_total || 0;
        frm.refresh_field('payment_details');
        calculatePaymentTotal(frm);
    }
}

async function setDefaultPaymentAccount(frm, payment) {
    if (!frm.doc.company) return;
    
    try {
        let account_field;
        
        if (frm.doc.payment_method === 'Cash') {
            account_field = 'default_cash_account';
        } else if (frm.doc.payment_method === 'Bank Transfer') {
            account_field = 'default_bank_account';
        }
        
        if (account_field) {
            const company = await frappe.db.get_value('Company', frm.doc.company, [account_field]);
            
            if (company && company.message && company.message[account_field]) {
                payment.payment_account = company.message[account_field];
                frm.refresh_field('payment_details');
            }
        }
    } catch (error) {
        console.error("Error setting default payment account:", error);
    }
}