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
    "Work Order": ["public/js/work_order.js", "public/js/work_order_material_issue_button.js"],  # Added material issue button
    "Workshop Purchase Order": "public/js/workshop_purchase_order.js",
    "Workshop Purchase Receipt": "public/js/workshop_purchase_receipt.js",
    "Workshop Purchase Invoice": "public/js/workshop_purchase_invoice.js",
    "Workshop Material Issue": "public/js/workshop_material_issue.js"  # Added Workshop Material Issue JS
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
    # Add Payment Entry events to handle cancellation
    "Payment Entry": {
        "on_cancel": "car_workshop.car_workshop.doctype.payment_entry.payment_entry_hooks.update_workshop_purchase_invoices_on_cancel"
    },
    # Add Stock Entry events for linking with Workshop Material Issue
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
    "Workshop Material Issue": "car_workshop.car_workshop.doctype.workshop_material_issue.workshop_material_issue.get_dashboard_data"  # Added dashboard data for Workshop Material Issue
}

# Override calendar views
calendars = [
    "Work Order", 
    "Workshop Purchase Order", 
    "Workshop Purchase Receipt",
    "Workshop Purchase Invoice",
    "Workshop Material Issue"  # Added Workshop Material Issue to calendars
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
        {"doctype": "Workshop Material Issue"}  # Added Workshop Material Issue to global search
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
    {"doctype": "Workshop Material Issue", "print_format": "Workshop Material Issue"}
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
        }
    ]
}

# Define mapped document functions
doctype_mapped_functions = {
    "Work Order": "car_workshop.car_workshop.doctype.work_order.work_order.make_material_issue"
}

# Define override whitelisted methods
override_whitelisted_methods = {
    "frappe.desk.calendar.get_events": "car_workshop.car_workshop.utils.calendar.get_events"
}