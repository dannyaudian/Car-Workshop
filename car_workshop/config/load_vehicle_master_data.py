import json
import os
import frappe
from frappe import _

def load_vehicle_master_data():
    """
    Loads master data for Vehicle Brand, Fuel Type, and Vehicle Model
    from JSON files in the config directory.
    """
    try:
        frappe.logger().info("Starting to load vehicle master data...")
        
        # Load Vehicle Brands
        brands_loaded = load_vehicle_brands()
        frappe.logger().info(f"Loaded {brands_loaded} vehicle brands")
        
        # Load Fuel Types
        fuel_types_loaded = load_fuel_types()
        frappe.logger().info(f"Loaded {fuel_types_loaded} fuel types")
        
        # Load Vehicle Models (depends on brands and fuel types)
        models_loaded = load_vehicle_models()
        frappe.logger().info(f"Loaded {models_loaded} vehicle models")
        
        frappe.logger().info("Completed loading vehicle master data successfully")
        return True
    except Exception as e:
        frappe.log_error(f"Error loading vehicle master data: {str(e)}", 
                         "Vehicle Master Data Loading Error")
        frappe.logger().error(f"Failed to load vehicle master data: {str(e)}")
        return False

def load_vehicle_brands():
    """Load vehicle brands from JSON file"""
    brands_file = os.path.join(frappe.get_app_path("car_workshop", "config"), "vehicle_brand.json")
    
    try:
        with open(brands_file, 'r') as f:
            brands = json.load(f)
        
        count = 0
        for brand_name in brands:
            if not frappe.db.exists("Vehicle Brand", {"brand_name": brand_name}):
                brand = frappe.new_doc("Vehicle Brand")
                brand.brand_name = brand_name
                brand.insert(ignore_permissions=True)
                count += 1
                frappe.logger().info(f"Created Vehicle Brand: {brand_name}")
            else:
                frappe.logger().debug(f"Vehicle Brand already exists: {brand_name}")
        
        return count
    except Exception as e:
        frappe.log_error(f"Error loading vehicle brands: {str(e)}", 
                         "Vehicle Brands Loading Error")
        frappe.logger().error(f"Failed to load vehicle brands: {str(e)}")
        raise

def load_fuel_types():
    """Load fuel types from JSON file"""
    fuel_types_file = os.path.join(frappe.get_app_path("car_workshop", "config"), "fuel_type.json")
    
    try:
        with open(fuel_types_file, 'r') as f:
            fuel_types = json.load(f)
        
        count = 0
        for fuel_type_name in fuel_types:
            if not frappe.db.exists("Fuel Type", {"name1": fuel_type_name}):
                fuel_type = frappe.new_doc("Fuel Type")
                fuel_type.name1 = fuel_type_name
                fuel_type.insert(ignore_permissions=True)
                count += 1
                frappe.logger().info(f"Created Fuel Type: {fuel_type_name}")
            else:
                frappe.logger().debug(f"Fuel Type already exists: {fuel_type_name}")
        
        return count
    except Exception as e:
        frappe.log_error(f"Error loading fuel types: {str(e)}", 
                         "Fuel Types Loading Error")
        frappe.logger().error(f"Failed to load fuel types: {str(e)}")
        raise

def load_vehicle_models():
    """Load vehicle models from JSON file"""
    models_file = os.path.join(frappe.get_app_path("car_workshop", "config"), "vehicle_model.json")
    
    try:
        with open(models_file, 'r') as f:
            models = json.load(f)
        
        count = 0
        for model_data in models:
            brand = model_data.get('brand')
            model_name = model_data.get('model_name')
            fuel_type = model_data.get('fuel_type')
            
            # Check if all required data exists
            if not all([brand, model_name, fuel_type]):
                frappe.logger().warning(f"Skipping incomplete vehicle model data: {model_data}")
                continue
            
            # Check if brand exists
            if not frappe.db.exists("Vehicle Brand", {"brand_name": brand}):
                frappe.logger().warning(f"Brand not found, skipping model: {model_name} ({brand})")
                continue
            
            # Check if fuel type exists
            if not frappe.db.exists("Fuel Type", {"name1": fuel_type}):
                frappe.logger().warning(f"Fuel type not found, skipping model: {model_name} ({fuel_type})")
                continue
            
            # Check if the model already exists
            model_exists = frappe.db.exists("Vehicle Model", {
                "brand": brand,
                "model_name": model_name
            })
            
            if not model_exists:
                model = frappe.new_doc("Vehicle Model")
                model.brand = frappe.get_value("Vehicle Brand", {"brand_name": brand}, "name")
                model.model_name = model_name
                model.fuel_type = frappe.get_value("Fuel Type", {"name1": fuel_type}, "name")
                model.insert(ignore_permissions=True)
                count += 1
                frappe.logger().info(f"Created Vehicle Model: {model_name} ({brand})")
            else:
                frappe.logger().debug(f"Vehicle Model already exists: {model_name} ({brand})")
        
        return count
    except Exception as e:
        frappe.log_error(f"Error loading vehicle models: {str(e)}", 
                         "Vehicle Models Loading Error")
        frappe.logger().error(f"Failed to load vehicle models: {str(e)}")
        raise

def execute():
    """
    Execute the loading of vehicle master data.
    This function can be called from other scripts or scheduler jobs.
    """
    return load_vehicle_master_data()

if __name__ == "__main__":
    # This allows running the script directly for testing
    execute()