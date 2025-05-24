app_name = "car_workshop"
app_title = "Car Workshop"
app_publisher = "Your Company"
app_description = "ERPNext module app for managing automotive workshop operations"
app_email = "info@yourcompany.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/car_workshop/css/car_workshop.css"
# app_include_js = "/assets/car_workshop/js/car_workshop.js"

# include js, css files in header of web template
# web_include_css = "/assets/car_workshop/css/car_workshop.css"
# web_include_js = "/assets/car_workshop/js/car_workshop.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "car_workshop/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Customer Vehicle": "public/js/customer_vehicle.js",
    "Part": "public/js/part.js",
    "Service Package": "public/js/service_package.js"
}

# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "car_workshop.setup.before_install"
after_install = "car_workshop.setup.after_install"

# Uninstallation
# ------------

# before_uninstall = "car_workshop.uninstall.before_uninstall"
# after_uninstall = "car_workshop.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "car_workshop.utils.before_app_install"
# after_app_install = "car_workshop.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "car_workshop.utils.before_app_uninstall"
# after_app_uninstall = "car_workshop.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "car_workshop.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Customer Vehicle": {
        "on_update": "car_workshop.car_workshop.doctype.customer_vehicle.customer_vehicle.on_update",
        "after_insert": "car_workshop.car_workshop.doctype.customer_vehicle.customer_vehicle.create_vehicle_log",
        "validate": "car_workshop.car_workshop.doctype.customer_vehicle.customer_vehicle.validate",
    },
    "Vehicle Change Log": {
        "before_save": "car_workshop.car_workshop.doctype.vehicle_change_log.vehicle_change_log.before_save",
        "on_trash": "car_workshop.car_workshop.doctype.vehicle_change_log.vehicle_change_log.on_trash",
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
#	"all": [
#		"car_workshop.tasks.all"
#	],
#	"daily": [
#		"car_workshop.tasks.daily"
#	],
#	"hourly": [
#		"car_workshop.tasks.hourly"
#	],
#	"weekly": [
#		"car_workshop.tasks.weekly"
#	],
#	"monthly": [
#		"car_workshop.tasks.monthly"
#	],
# }

# Testing
# -------

# before_tests = "car_workshop.install.before_tests"

# Overriding Methods
# ------------------------------

# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "car_workshop.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "car_workshop.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo", "Note", "File"]

# Request Events
# ----------------
# before_request = ["car_workshop.utils.before_request"]
# after_request = ["car_workshop.utils.after_request"]

# Job Events
# ----------
# before_job = ["car_workshop.utils.before_job"]
# after_job = ["car_workshop.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
#	{
#		"doctype": "{doctype_1}",
#		"filter_by": "{filter_by}",
#		"redact_fields": ["{field_1}", "{field_2}"],
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_2}",
#		"filter_by": "{filter_by}",
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_3}",
#		"strict": False,
#	},
#	{
#		"doctype": "{doctype_4}"
#	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"car_workshop.auth.validate"
# ]


# Fixtures
# --------
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
# --------------------------------
vehicle_master_data_setup = "car_workshop.config.load_vehicle_master_data.execute"