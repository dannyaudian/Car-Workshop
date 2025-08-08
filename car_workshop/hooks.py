app_name = "car_workshop"
app_title = "Car Workshop"
app_publisher = "PT. Innovasi Terbaik Bangsa"
app_description = "ERPNext module app for managing automotive workshop operations"
app_email = "danny.a.pratama@cao-group.co.id"
app_license = "MIT"

# JavaScript customizations
doctype_js = {}

# Include JS utility files
app_include_js = [
    "/assets/car_workshop/js/item_utils.js"  # Include item_utils.js as a common utility
]

# Setup function
after_install = "car_workshop.setup.after_install"

# Document events
doc_events = {
    "Customer Vehicle": {
        "after_insert": "car_workshop.car_workshop.doctype.customer_vehicle.customer_vehicle.create_vehicle_log"
    },
    "Work Order Part": {
        "validate": "car_workshop.car_workshop.doctype.work_order_part.work_order_part.validate"
    },
    "Work Order Job Type": {
        "validate": "car_workshop.car_workshop.doctype.work_order_job_type.work_order_job_type.validate"
    },
    "Work Order Service Package": {
        "validate": "car_workshop.car_workshop.doctype.work_order_service_package.work_order_service_package.validate"
    },
    "Workshop Purchase Order": {
        "validate": "car_workshop.car_workshop.doctype.workshop_purchase_order.workshop_purchase_order.validate",
        "before_submit": "car_workshop.car_workshop.doctype.workshop_purchase_order.workshop_purchase_order.before_submit"
    },
    "Workshop Purchase Receipt": {
        "validate": "car_workshop.car_workshop.doctype.workshop_purchase_receipt.workshop_purchase_receipt.validate",
        "before_submit": "car_workshop.car_workshop.doctype.workshop_purchase_receipt.workshop_purchase_receipt.before_submit",
        "on_submit": "car_workshop.car_workshop.doctype.workshop_purchase_receipt.workshop_purchase_receipt.on_submit",
        "on_cancel": "car_workshop.car_workshop.doctype.workshop_purchase_receipt.workshop_purchase_receipt.on_cancel"
    },
    "Workshop Purchase Receipt Item": {
        "validate": "car_workshop.car_workshop.doctype.workshop_purchase_receipt_item.workshop_purchase_receipt_item.validate"
    },
    "Workshop Purchase Invoice": {
        "validate": "car_workshop.car_workshop.doctype.workshop_purchase_invoice.workshop_purchase_invoice.validate",
        "on_submit": "car_workshop.car_workshop.doctype.workshop_purchase_invoice.workshop_purchase_invoice.on_submit",
        "on_cancel": "car_workshop.car_workshop.doctype.workshop_purchase_invoice.workshop_purchase_invoice.on_cancel",
        "on_update_after_submit": "car_workshop.car_workshop.doctype.workshop_purchase_invoice.workshop_purchase_invoice.on_update_after_submit"
    },
    "Workshop Purchase Invoice Item": {
        "validate": "car_workshop.car_workshop.doctype.workshop_purchase_invoice_item.workshop_purchase_invoice_item.validate",
        "on_update": "car_workshop.car_workshop.doctype.workshop_purchase_invoice_item.workshop_purchase_invoice_item.on_update"
    },
    "Workshop Material Issue": {
        "validate": "car_workshop.car_workshop.doctype.workshop_material_issue.workshop_material_issue.validate",
        "on_submit": "car_workshop.car_workshop.doctype.workshop_material_issue.workshop_material_issue.on_submit",
        "on_cancel": "car_workshop.car_workshop.doctype.workshop_material_issue.workshop_material_issue.on_cancel"
    },
    "Workshop Material Issue Item": {
        "validate": "car_workshop.car_workshop.doctype.workshop_material_issue_item.workshop_material_issue_item.validate"
    },
    "Return Material": {
        "validate": "car_workshop.car_workshop.doctype.return_material.return_material.validate",
        "on_submit": "car_workshop.car_workshop.doctype.return_material.return_material.on_submit",
        "on_cancel": "car_workshop.car_workshop.doctype.return_material.return_material.on_cancel"
    },
    "Return Material Item": {
        "validate": "car_workshop.car_workshop.doctype.return_material_item.return_material_item.validate"
    },
    "Part Stock Opname": {
        "validate": "car_workshop.car_workshop.doctype.part_stock_opname.part_stock_opname.validate",
        "on_submit": "car_workshop.car_workshop.doctype.part_stock_opname.part_stock_opname.on_submit",
        "on_cancel": "car_workshop.car_workshop.doctype.part_stock_opname.part_stock_opname.on_cancel"
    },
    "Part Stock Opname Item": {
        "validate": "car_workshop.car_workshop.doctype.part_stock_opname_item.part_stock_opname_item.validate",
        "on_update": "car_workshop.car_workshop.doctype.part_stock_opname_item.part_stock_opname_item.on_update"
    },
    "Part Stock Adjustment": {
        "validate": "car_workshop.car_workshop.doctype.part_stock_adjustment.part_stock_adjustment.validate",
        "on_submit": "car_workshop.car_workshop.doctype.part_stock_adjustment.part_stock_adjustment.on_submit",
        "on_cancel": "car_workshop.car_workshop.doctype.part_stock_adjustment.part_stock_adjustment.on_cancel"
    },
    "Part Stock Adjustment Item": {
        "validate": "car_workshop.car_workshop.doctype.part_stock_adjustment_item.part_stock_adjustment_item.validate"
    },
    "Payment Entry": {
        "on_cancel": "car_workshop.car_workshop.doctype.payment_entry.payment_entry_hooks.update_workshop_purchase_invoices_on_cancel"
    },
    "Stock Entry": {
        "on_cancel": "car_workshop.car_workshop.doctype.workshop_material_issue.workshop_material_issue.on_stock_entry_cancel"
    },
    "Work Order Billing": {
        "validate": "car_workshop.car_workshop.doctype.work_order_billing.work_order_billing.validate",
        "on_submit": [
            "car_workshop.car_workshop.doctype.work_order_billing.work_order_billing.on_submit",
            "car_workshop.incentive_utils.process_work_order_billing",
        ],
        "on_cancel": "car_workshop.car_workshop.doctype.work_order_billing.work_order_billing.on_cancel"
    }
}

# Data fixtures
fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [["module", "=", "Car Workshop"]]
    },
    {
        "doctype": "Client Script",
        "filters": [["module", "=", "Car Workshop"]]
    },
    {
        "doctype": "Property Setter",
        "filters": [["module", "=", "Car Workshop"]]
    },
    {
        "doctype": "Role",
        "filters": [["name", "in", ["Workshop Manager", "Technician", "Car Workshop Manager"]]]
    },
    {
        "doctype": "Workspace",
        "filters": [["name", "=", "Car Workshop"]]
    },
    {
        "doctype": "Print Format",
        "filters": [["module", "=", "Car Workshop"]]
    }
]

# Master data setup
vehicle_master_data_setup = "car_workshop.config.load_vehicle_master_data.execute"

# Dashboard links for Work Order
get_dashboard_data = {
    "Work Order": "car_workshop.car_workshop.doctype.work_order.work_order.get_dashboard_data",
    "Workshop Purchase Order": "car_workshop.car_workshop.doctype.workshop_purchase_order.workshop_purchase_order.get_dashboard_data",
    "Workshop Purchase Receipt": "car_workshop.car_workshop.doctype.workshop_purchase_receipt.workshop_purchase_receipt.get_dashboard_data",
    "Workshop Purchase Invoice": "car_workshop.car_workshop.doctype.workshop_purchase_invoice.workshop_purchase_invoice.get_dashboard_data",
    "Workshop Material Issue": "car_workshop.car_workshop.doctype.workshop_material_issue.workshop_material_issue.get_dashboard_data",
    "Return Material": "car_workshop.car_workshop.doctype.return_material.return_material.get_dashboard_data",
    "Part Stock Opname": "car_workshop.car_workshop.doctype.part_stock_opname.part_stock_opname.get_dashboard_data",
    "Part Stock Adjustment": "car_workshop.car_workshop.doctype.part_stock_adjustment.part_stock_adjustment.get_dashboard_data",
    "Work Order Billing": "car_workshop.car_workshop.doctype.work_order_billing.work_order_billing.get_dashboard_data"
}

# Override calendar views
calendars = [
    "Work Order", 
    "Workshop Purchase Order", 
    "Workshop Purchase Receipt",
    "Workshop Purchase Invoice",
    "Workshop Material Issue",
    "Return Material",
    "Part Stock Opname",
    "Part Stock Adjustment",
    "Work Order Billing"
]

# Add DocTypes to global search
global_search_doctypes = {
    "Default": [
        {"doctype": "Work Order"},
        {"doctype": "Customer Vehicle"},
        {"doctype": "Part"},
        {"doctype": "Job Type"},
        {"doctype": "Service Package"},
        {"doctype": "Workshop Purchase Order"},
        {"doctype": "Workshop Purchase Receipt"},
        {"doctype": "Workshop Purchase Invoice"},
        {"doctype": "Workshop Material Issue"},
        {"doctype": "Return Material"},
        {"doctype": "Part Stock Opname"},
        {"doctype": "Part Stock Adjustment"},
        {"doctype": "Work Order Billing"}
    ]
}

# Jinja template filters
jinja = {
    "filters": [
        "car_workshop.utils.format_currency_idr"
    ]
}

# Add print formats
print_format = [
    {"doctype": "Workshop Material Issue", "print_format": "Workshop Material Issue"},
    {"doctype": "Return Material", "print_format": "Return Material"},
    {"doctype": "Part Stock Opname", "print_format": "Part Stock Opname"},
    {"doctype": "Part Stock Adjustment", "print_format": "Part Stock Adjustment"},
    {"doctype": "Work Order Billing", "print_format": "Work Order Billing"}
]

# Add custom fields to Stock Entry
doctype_custom_fields = {
    "Stock Entry": [
        {
            "fieldname": "workshop_material_issue",
            "label": "Workshop Material Issue",
            "fieldtype": "Link",
            "options": "Workshop Material Issue",
            "insert_after": "work_order",
            "read_only": 1
        },
        {
            "fieldname": "return_material",
            "label": "Return Material",
            "fieldtype": "Link",
            "options": "Return Material",
            "insert_after": "workshop_material_issue",
            "read_only": 1
        },
        {
            "fieldname": "reference_doctype",
            "label": "Reference DocType",
            "fieldtype": "Data",
            "insert_after": "return_material",
            "read_only": 1
        },
        {
            "fieldname": "reference_docname",
            "label": "Reference DocName",
            "fieldtype": "Data",
            "insert_after": "reference_doctype",
            "read_only": 1
        }
    ]
}

# Define mapped document functions
doctype_mapped_functions = {
    "Work Order": {
        "make_material_issue": "car_workshop.car_workshop.doctype.work_order.work_order.make_material_issue",
        "make_return_material": "car_workshop.car_workshop.doctype.work_order.work_order.make_return_material",
        "make_billing": "car_workshop.car_workshop.doctype.work_order.work_order.make_billing"
    },
    "Part Stock Opname": {
        "make_stock_adjustment": "car_workshop.car_workshop.doctype.part_stock_opname.part_stock_opname.make_stock_adjustment"
    }
}

# Define override whitelisted methods
override_whitelisted_methods = {
    "frappe.desk.calendar.get_events": "car_workshop.car_workshop.utils.calendar.get_events"
}

# Add scheduled tasks
scheduler_events = {
    "daily": [
        "car_workshop.car_workshop.doctype.return_material.return_material.process_pending_returns",
        "car_workshop.car_workshop.doctype.part_stock_opname.part_stock_opname.remind_pending_opnames"
    ]
}

# Barcode API
barcode_handlers = {
    "Part": "car_workshop.car_workshop.doctype.part_stock_opname.part_stock_opname.get_part_from_barcode"
}