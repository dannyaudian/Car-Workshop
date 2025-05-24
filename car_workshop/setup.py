import frappe

def after_install():
    """
    Runs after the app is installed.
    """
    try:
        # Import and execute the vehicle master data setup
        from car_workshop.config.load_vehicle_master_data import execute
        
        frappe.logger().info("Starting setup process for Car Workshop app...")
        
        # Create default roles if they don't exist
        create_roles()
        
        # Load vehicle master data
        frappe.logger().info("Loading vehicle master data...")
        execute()
        
        frappe.logger().info("Car Workshop app setup completed successfully")
    except Exception as e:
        frappe.log_error(f"Error during Car Workshop app setup: {str(e)}", 
                         "Car Workshop Setup Error")
        frappe.logger().error(f"Car Workshop app setup failed: {str(e)}")

def create_roles():
    """
    Create default roles required by the app.
    """
    roles = ["Workshop Manager", "Technician"]
    
    for role in roles:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({
                "doctype": "Role",
                "role_name": role,
                "desk_access": 1,
                "is_custom": 1
            }).insert(ignore_permissions=True)
            frappe.logger().info(f"Created role: {role}")
        else:
            frappe.logger().debug(f"Role already exists: {role}")