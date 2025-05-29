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
    "Work Order": "public/js/work_order.js",
    "Workshop Purchase Order": "public/js/workshop_purchase_order.js"  # Added Workshop Purchase Order JS
}

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
    "Workshop Purchase Order": "car_workshop.car_workshop.doctype.workshop_purchase_order.workshop_purchase_order.get_dashboard_data"  # Added dashboard data for Workshop Purchase Order
}

# Override calendar views
calendars = ["Work Order", "Workshop Purchase Order"]  # Added Workshop Purchase Order to calendars

# Add DocTypes to global search
global_search_doctypes = {
    "Default": [
        {"doctype": "Work Order"},
        {"doctype": "Customer Vehicle"},
        {"doctype": "Part"},
        {"doctype": "Job Type"},
        {"doctype": "Service Package"},
        {"doctype": "Workshop Purchase Order"}  # Added Workshop Purchase Order to global search
    ]
}

# Jinja template filters
jinja = {
    "filters": [
        "car_workshop.utils.format_currency_idr"
    ]
}