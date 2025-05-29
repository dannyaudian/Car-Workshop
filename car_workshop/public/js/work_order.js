frappe.ui.form.on('Work Order', {
    refresh: function(frm) {
        // Add "Lihat Semua PO Terkait" button if there are related POs
        frm.add_custom_button(__('Lihat Semua PO Terkait'), function() {
            show_related_purchase_orders(frm);
        }).addClass('btn-primary');
        
        // Update field requirements based on source
        set_purchase_order_requirements(frm);
    },
    
    validate: function(frm) {
        // Validate purchase order requirement based on source
        if (frm.doc.source === "Beli Baru" && !frm.doc.purchase_order) {
            frappe.validated = false;
            frappe.throw(__("Purchase Order is mandatory when Source is 'Beli Baru'"));
        }
    },
    
    source: function(frm) {
        // Update field requirements when source changes
        set_purchase_order_requirements(frm);
    },
    
    setup: function(frm) {
        // Set up event handlers for child tables
        setup_child_table_events(frm);
    },
    
    // Event handlers for each field that affects total_amount
    purchase_order: function(frm) {
        // Optional: You can add additional logic here when purchase_order changes
    }
});

// Setup event handlers for all child tables
function setup_child_table_events(frm) {
    // Job Type child table events
    frappe.ui.form.on('Work Order Job Type', {
        job_type: function(frm, cdt, cdn) {
            var row = locals[cdt][cdn];
            // Check if job_type has is_opl flag and update row
            if (row.job_type) {
                frappe.db.get_value('Job Type', row.job_type, 'is_opl', function(r) {
                    if (r && r.is_opl !== undefined) {
                        frappe.model.set_value(cdt, cdn, 'is_opl', r.is_opl);
                    }
                });
            }
        },
        
        is_opl: function(frm, cdt, cdn) {
            var row = locals[cdt][cdn];
            // Clear vendor if is_opl is unchecked
            if (!row.is_opl) {
                frappe.model.set_value(cdt, cdn, 'vendor', '');
            }
        },
        
        vendor: function(frm, cdt, cdn) {
            // You can add additional logic here when vendor changes
        },
        
        price: function(frm, cdt, cdn) {
            calculate_total_amount(frm);
        },
        
        job_type_detail_remove: function(frm) {
            calculate_total_amount(frm);
        }
    });
    
    // Service Package child table events
    frappe.ui.form.on('Work Order Service Package', {
        service_package: function(frm, cdt, cdn) {
            var row = locals[cdt][cdn];
            if (row.service_package) {
                frappe.db.get_value('Service Package', row.service_package, 'price', function(r) {
                    if (r && r.price) {
                        frappe.model.set_value(cdt, cdn, 'total_price', r.price);
                        calculate_total_amount(frm);
                    }
                });
            }
        },
        
        total_price: function(frm, cdt, cdn) {
            calculate_total_amount(frm);
        },
        
        service_package_detail_remove: function(frm) {
            calculate_total_amount(frm);
        }
    });
    
    // Part child table events
    frappe.ui.form.on('Work Order Part', {
        part: function(frm, cdt, cdn) {
            var row = locals[cdt][cdn];
            if (row.part) {
                frappe.db.get_value('Part', row.part, 'price', function(r) {
                    if (r && r.price) {
                        frappe.model.set_value(cdt, cdn, 'rate', r.price);
                        calculate_part_amount(cdt, cdn);
                        calculate_total_amount(frm);
                    }
                });
            }
        },
        
        quantity: function(frm, cdt, cdn) {
            calculate_part_amount(cdt, cdn);
            calculate_total_amount(frm);
        },
        
        rate: function(frm, cdt, cdn) {
            calculate_part_amount(cdt, cdn);
            calculate_total_amount(frm);
        },
        
        amount: function(frm, cdt, cdn) {
            calculate_total_amount(frm);
        },
        
        part_detail_remove: function(frm) {
            calculate_total_amount(frm);
        }
    });
    
    // Expense child table events
    frappe.ui.form.on('Work Order Expense', {
        expense_type: function(frm, cdt, cdn) {
            // You can add additional logic here when expense_type changes
        },
        
        amount: function(frm, cdt, cdn) {
            calculate_total_amount(frm);
        },
        
        external_expense_remove: function(frm) {
            calculate_total_amount(frm);
        }
    });
}

// Function to calculate part amount (quantity * rate)
function calculate_part_amount(cdt, cdn) {
    var row = locals[cdt][cdn];
    var amount = flt(row.quantity) * flt(row.rate);
    frappe.model.set_value(cdt, cdn, 'amount', amount);
}

// Function to calculate total amount
function calculate_total_amount(frm) {
    var total_amount = 0;
    
    // Calculate from job types
    $.each(frm.doc.job_type_detail || [], function(i, d) {
        total_amount += flt(d.price);
    });
    
    // Calculate from service packages
    $.each(frm.doc.service_package_detail || [], function(i, d) {
        total_amount += flt(d.total_price);
    });
    
    // Calculate from parts
    $.each(frm.doc.part_detail || [], function(i, d) {
        total_amount += flt(d.amount);
    });
    
    // Calculate from expenses
    $.each(frm.doc.external_expense || [], function(i, d) {
        total_amount += flt(d.amount);
    });
    
    frm.set_value('total_amount', total_amount);
}

// Function to set purchase_order field as mandatory based on source
function set_purchase_order_requirements(frm) {
    if (frm.doc.source === "Beli Baru") {
        frm.set_df_property("purchase_order", "reqd", 1);
    } else {
        frm.set_df_property("purchase_order", "reqd", 0);
    }
}

// Function to show related purchase orders in a dialog
function show_related_purchase_orders(frm) {
    // Collect all purchase orders from job types with is_opl=1 and expenses
    var related_pos = [];
    
    // Add the main purchase order if it exists
    if (frm.doc.purchase_order) {
        related_pos.push({
            purchase_order: frm.doc.purchase_order,
            source: "Main",
            reference: frm.doc.name
        });
    }
    
    // Add purchase orders from job types with is_opl=1
    $.each(frm.doc.job_type_detail || [], function(i, job) {
        if (job.is_opl && job.vendor) {
            // Check if there's a purchase order for this vendor in the system
            frappe.db.get_list('Purchase Order', {
                filters: {
                    'supplier': job.vendor,
                    'docstatus': ['!=', 2]  // Not cancelled
                },
                fields: ['name', 'supplier', 'status']
            }).then(function(pos) {
                if (pos && pos.length > 0) {
                    $.each(pos, function(j, po) {
                        related_pos.push({
                            purchase_order: po.name,
                            source: "Job Type: " + job.job_type,
                            vendor: job.vendor,
                            status: po.status
                        });
                    });
                    
                    // If POs were found, refresh the dialog if it's open
                    refresh_po_dialog(frm, related_pos);
                }
            });
        }
    });
    
    // Add purchase orders from expenses
    $.each(frm.doc.external_expense || [], function(i, expense) {
        if (expense.purchase_order) {
            related_pos.push({
                purchase_order: expense.purchase_order,
                source: "Expense: " + expense.expense_type,
                reference: expense.name
            });
        } else if (expense.supplier) {
            // Check if there's a purchase order for this supplier in the system
            frappe.db.get_list('Purchase Order', {
                filters: {
                    'supplier': expense.supplier,
                    'docstatus': ['!=', 2]  // Not cancelled
                },
                fields: ['name', 'supplier', 'status']
            }).then(function(pos) {
                if (pos && pos.length > 0) {
                    $.each(pos, function(j, po) {
                        related_pos.push({
                            purchase_order: po.name,
                            source: "Expense: " + expense.expense_type,
                            vendor: expense.supplier,
                            status: po.status
                        });
                    });
                    
                    // If POs were found, refresh the dialog if it's open
                    refresh_po_dialog(frm, related_pos);
                }
            });
        }
    });
    
    // Show dialog with the collected purchase orders
    show_po_dialog(frm, related_pos);
}

// Global variable to store the dialog reference
var po_dialog = null;

// Function to show purchase orders in a dialog
function show_po_dialog(frm, related_pos) {
    // Create fields for the dialog
    var fields = [
        {
            fieldtype: 'HTML',
            fieldname: 'po_html'
        }
    ];
    
    // Create the dialog
    po_dialog = new frappe.ui.Dialog({
        title: __('Related Purchase Orders'),
        fields: fields,
        size: 'large'
    });
    
    // Render the HTML content
    var $po_html = po_dialog.fields_dict.po_html.$wrapper;
    render_po_html($po_html, related_pos);
    
    // Show the dialog
    po_dialog.show();
}

// Function to refresh the PO dialog if it's open
function refresh_po_dialog(frm, related_pos) {
    if (po_dialog && po_dialog.display) {
        var $po_html = po_dialog.fields_dict.po_html.$wrapper;
        render_po_html($po_html, related_pos);
    }
}

// Function to render HTML content for the PO dialog
function render_po_html($wrapper, related_pos) {
    // Clear the wrapper
    $wrapper.empty();
    
    if (related_pos.length === 0) {
        $wrapper.append(`
            <div class="text-muted text-center">
                <p>${__('No related Purchase Orders found')}</p>
            </div>
        `);
        return;
    }
    
    // Create a table to display the purchase orders
    var html = `
        <div class="table-responsive">
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th>${__('Purchase Order')}</th>
                        <th>${__('Source')}</th>
                        <th>${__('Vendor/Supplier')}</th>
                        <th>${__('Status')}</th>
                        <th>${__('Actions')}</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    // Add rows for each purchase order
    related_pos.forEach(function(po) {
        html += `
            <tr>
                <td>${po.purchase_order}</td>
                <td>${po.source || ''}</td>
                <td>${po.vendor || ''}</td>
                <td>${po.status || ''}</td>
                <td>
                    <button class="btn btn-xs btn-default view-po" data-name="${po.purchase_order}">
                        ${__('View')}
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    // Append the HTML to the wrapper
    $wrapper.append(html);
    
    // Add event listeners for the view buttons
    $wrapper.find('.view-po').on('click', function() {
        var po_name = $(this).attr('data-name');
        frappe.set_route('Form', 'Purchase Order', po_name);
        po_dialog.hide();
    });
}