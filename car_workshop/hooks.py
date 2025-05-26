app_name = "car_workshop"
app_title = "Car Workshop"
app_publisher = "PT. Innovasi Terbaik Bangsa"
app_description = "ERPNext module app for managing automotive workshop operations"
app_email = "danny.a.pratama@cao-group.co.id"
app_license = "MIT"

# Doctype JS (Client Scripts)
doctype_js = {
    "Customer Vehicle": "public/js/customer_vehicle.js",
    "Part": "public/js/part.js",
    "Service Package": "public/js/service_package.js",
    "Job Type": "public/js/job_type.js"
}

# After install
after_install = "car_workshop.setup.after_install"

# Document Events
doc_events = {
    "Customer Vehicle": {
        # validate method cukup di dalam class CustomerVehicle (Document)
        "on_update": "car_workshop.car_workshop.doctype.customer_vehicle.customer_vehicle.on_update",
        "after_insert": "car_workshop.car_workshop.doctype.customer_vehicle.customer_vehicle.create_vehicle_log",
    },
    "Vehicle Change Log": {
        "before_save": "car_workshop.car_workshop.doctype.vehicle_change_log.vehicle_change_log.before_save",
        "on_trash": "car_workshop.car_workshop.doctype.vehicle_change_log.vehicle_change_log.on_trash",
    }
}

# Fixtures
fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [
            ["module", "=", "Car Workshop"]
        ]
    },
    {
        "doctype": "Client Script",
        "filters": [
            ["module", "=", "Car Workshop"]
        ]
    },
    {
        "doctype": "Property Setter",
        "filters": [
            ["module", "=", "Car Workshop"]
        ]
    },
    {
        "doctype": "Role",
        "filters": [
            ["name", "in", ["Workshop Manager", "Technician"]]
        ]
    },
    {
        "doctype": "Workspace",
        "filters": [
            ["name", "=", "Car Workshop"]
        ]
    }
]

# Vehicle Master Data Setup Command
vehicle_master_data_setup = "car_workshop.config.load_vehicle_master_data.execute"
