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
    "Job Type": "public/js/job_type.js"
}

# Setup function
after_install = "car_workshop.setup.after_install"

# Document events
doc_events = {
    "Customer Vehicle": {
        "after_insert": "car_workshop.car_workshop.doctype.customer_vehicle.customer_vehicle.create_vehicle_log"
        # Note: on_update is handled directly in CustomerVehicle.on_update()
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
        "filters": [["name", "in", ["Workshop Manager", "Technician"]]]
    },
    {
        "doctype": "Workspace",
        "filters": [["name", "=", "Car Workshop"]]
    }
]

# Master data setup
vehicle_master_data_setup = "car_workshop.config.load_vehicle_master_data.execute"