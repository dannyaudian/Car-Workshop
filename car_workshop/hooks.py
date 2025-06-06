app_name = "car_workshop"
app_title = "Car Workshop"
app_publisher = "PT. Innovasi Terbaik Bangsa"
app_description = "ERPNext module app for managing automotive workshop operations"
app_email = "danny.a.pratama@cao-group.co.id"
app_license = "MIT"

# JavaScript customizations
doctype_js = {
    "Customer Vehicle": "public/js/customer_vehicle.js",
    "Part": "public/js/part.js",
    "Service Package": "public/js/service_package.js",
    "Job Type": "public/js/job_type.js",
    "Work Order": ["public/js/work_order.js", "public/js/work_order_material_issue_button.js"],
    "Workshop Purchase Order": "public/js/workshop_purchase_order.js",
    "Workshop Purchase Receipt": "public/js/workshop_purchase_receipt.js",
    "Workshop Purchase Invoice": "public/js/workshop_purchase_invoice.js",
    "Workshop Material Issue": "public/js/workshop_material_issue.js",
    "Return Material": "public/js/return_material.js",
    "Part Stock Opname": "public/js/part_stock_opname.js",  # Added Part Stock Opname JS
    "Part Stock Adjustment": "public/js/part_stock_adjustment.js"  # Added Part Stock Adjustment JS
}

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
        # Note: on_update is handled directly in CustomerVehicle.on_update()
    },
    # Removed the problematic Work Order entries as they are already in the WorkOrder class
    "Work Order Part": {
        "validate": "car_workshop.car_workshop.doctype.work_order_part.work_order_part.validate"
    },
    "Work Order Job Type": {
        "validate": "car_workshop.car_workshop.doctype.work_order_job_type.work_order_job_type.validate"
    },
    "Work Order Service Package": {
        "validate": "car_workshop.car_workshop.doctype.work_order_service_package.work_order_service_package.validate"
    },
    # Added Workshop Purchase Order events if needed
    "Workshop Purchase Order": {
        "validate": "car_workshop.car_workshop.doctype.workshop_purchase_order.workshop_purchase_order.validate",
        "before_submit": "car_workshop.car_workshop.doctype.workshop_purchase_order.workshop_purchase_order.before_submit"
    },
    # Add Workshop Purchase Receipt events
    "Workshop Purchase Receipt": {
        "validate": "car_workshop.car_workshop.doctype.workshop_purchase_receipt.workshop_purchase_receipt.validate",
        "before_submit": "car_workshop.car_workshop.doctype.workshop_purchase_receipt.workshop_purchase_receipt.before_submit",
        "on_submit": "car_workshop.car_workshop.doctype.workshop_purchase_receipt.workshop_purchase_receipt.on_submit",
        "on_cancel": "car_workshop.car_workshop.doctype.workshop_purchase_receipt.workshop_purchase_receipt.on_cancel"
    },
    # Add Workshop Purchase Receipt Item events
    "Workshop Purchase Receipt Item": {
        "validate": "car_workshop.car_workshop.doctype.workshop_purchase_receipt_item.workshop_purchase_receipt_item.validate"
    },
    # Add Workshop Purchase Invoice events
    "Workshop Purchase Invoice": {
        "validate": "car_workshop.car_workshop.doctype.workshop_purchase_invoice.workshop_purchase_invoice.validate",
        "on_submit": "car_workshop.car_workshop.doctype.workshop_purchase_invoice.workshop_purchase_invoice.on_submit",
        "on_cancel": "car_workshop.car_workshop.doctype.workshop_purchase_invoice.workshop_purchase_invoice.on_cancel",
        "on_update_after_submit": "car_workshop.car_workshop.doctype.workshop_purchase_invoice.workshop_purchase_invoice.on_update_after_submit"
    },
    # Add Workshop Purchase Invoice Item events
    "Workshop Purchase Invoice Item": {
        "validate": "car_workshop.car_workshop.doctype.workshop_purchase_invoice_item.workshop_purchase_invoice_item.validate",
        "on_update": "car_workshop.car_workshop.doctype.workshop_purchase_invoice_item.workshop_purchase_invoice_item.on_update"
    },
    # Add Workshop Material Issue events
    "Workshop Material Issue": {
        "validate": "car_workshop.car_workshop.doctype.workshop_material_issue.workshop_material_issue.validate",
        "on_submit": "car_workshop.car_workshop.doctype.workshop_material_issue.workshop_material_issue.on_submit",
        "on_cancel": "car_workshop.car_workshop.doctype.workshop_material_issue.workshop_material_issue.on_cancel"
    },
    # Add Workshop Material Issue Item events
    "Workshop Material Issue Item": {
        "validate": "car_workshop.car_workshop.doctype.workshop_material_issue_item.workshop_material_issue_item.validate"
    },
    # Add Return Material events
    "Return Material": {
        "validate": "car_workshop.car_workshop.doctype.return_material.return_material.validate",
        "on_submit": "car_workshop.car_workshop.doctype.return_material.return_material.on_submit",
        "on_cancel": "car_workshop.car_workshop.doctype.return_material.return_material.on_cancel"
    },
    # Add Return Material Item events
    "Return Material Item": {
        "validate": "car_workshop.car_workshop.doctype.return_material_item.return_material_item.validate"
    },
    # Add Part Stock Opname events
    "Part Stock Opname": {
        "validate": "car_workshop.car_workshop.doctype.part_stock_opname.part_stock_opname.validate",
        "on_submit": "car_workshop.car_workshop.doctype.part_stock_opname.part_stock_opname.on_submit",
        "on_cancel": "car_workshop.car_workshop.doctype.part_stock_opname.part_stock_opname.on_cancel"
    },
    # Add Part Stock Opname Item events
    "Part Stock Opname Item": {
        "validate": "car_workshop.car_workshop.doctype.part_stock_opname_item.part_stock_opname_item.validate",
        "on_update": "car_workshop.car_workshop.doctype.part_stock_opname_item.part_stock_opname_item.on_update"
    },
    # Add Part Stock Adjustment events
    "Part Stock Adjustment": {
        "validate": "car_workshop.car_workshop.doctype.part_stock_adjustment.part_stock_adjustment.validate",
        "on_submit": "car_workshop.car_workshop.doctype.part_stock_adjustment.part_stock_adjustment.on_submit",
        "on_cancel": "car_workshop.car_workshop.doctype.part_stock_adjustment.part_stock_adjustment.on_cancel"
    },
    # Add Part Stock Adjustment Item events
    "Part Stock Adjustment Item": {
        "validate": "car_workshop.car_workshop.doctype.part_stock_adjustment_item.part_stock_adjustment_item.validate"
    },
    # Add Payment Entry events to handle cancellation
    "Payment Entry": {
        "on_cancel": "car_workshop.car_workshop.doctype.payment_entry.payment_entry_hooks.update_workshop_purchase_invoices_on_cancel"
    },
    # Add Stock Entry events for linking with Workshop Material Issue and Return Material
    "Stock Entry": {
        "on_cancel": "car_workshop.car_workshop.doctype.workshop_material_issue.workshop_material_issue.on_stock_entry_cancel"
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
    "Part Stock Opname": "car_workshop.car_workshop.doctype.part_stock_opname.part_stock_opname.get_dashboard_data",  # Added dashboard data for Part Stock Opname
    "Part Stock Adjustment": "car_workshop.car_workshop.doctype.part_stock_adjustment.part_stock_adjustment.get_dashboard_data"  # Added dashboard data for Part Stock Adjustment
}

# Override calendar views
calendars = [
    "Work Order", 
    "Workshop Purchase Order", 
    "Workshop Purchase Receipt",
    "Workshop Purchase Invoice",
    "Workshop Material Issue",
    "Return Material",
    "Part Stock Opname",  # Added Part Stock Opname to calendars
    "Part Stock Adjustment"  # Added Part Stock Adjustment to calendars
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
        {"doctype": "Part Stock Opname"},  # Added Part Stock Opname to global search
        {"doctype": "Part Stock Adjustment"}  # Added Part Stock Adjustment to global search
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
    {"doctype": "Part Stock Opname", "print_format": "Part Stock Opname"},  # Added Part Stock Opname print format
    {"doctype": "Part Stock Adjustment", "print_format": "Part Stock Adjustment"}  # Added Part Stock Adjustment print format
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
        "make_return_material": "car_workshop.car_workshop.doctype.work_order.work_order.make_return_material"
    },
    "Part Stock Opname": {
        "make_stock_adjustment": "car_workshop.car_workshop.doctype.part_stock_opname.part_stock_opname.make_stock_adjustment"  # Added make_stock_adjustment function
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
        "car_workshop.car_workshop.doctype.part_stock_opname.part_stock_opname.remind_pending_opnames"  # Added scheduled task for opname reminders
    ]
}

# Barcode API
barcode_handlers = {
    "Part": "car_workshop.car_workshop.doctype.part_stock_opname.part_stock_opname.get_part_from_barcode"
}