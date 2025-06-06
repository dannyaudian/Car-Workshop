import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import flt


class WorkOrder(Document):
    def autoname(self):
        # Set document name with format "WO-.YYYY.-.####"
        self.name = make_autoname("WO-.YYYY.-.####")
    
    def validate(self):
        # Validate purchase orders for parts with "Beli Baru" source
        self.validate_part_purchase_orders()
        
        # Validate vendors for OPL job types
        self.validate_opl_vendors()
        
        # Calculate total amount
        self.calculate_total_amount()
    
    def validate_part_purchase_orders(self):
        """Validate purchase orders for parts with 'Beli Baru' source"""
        if not self.part_detail:
            return
            
        for idx, part in enumerate(self.part_detail):
            if part.source == "Beli Baru" and not part.purchase_order:
                frappe.throw(_(
                    "Row #{0}: Purchase Order is mandatory for Part '{1}' when Source is 'Beli Baru'"
                ).format(idx + 1, part.part_name or part.part))
    
    def validate_opl_vendors(self):
        """Validate vendors for OPL job types"""
        if not self.job_type_detail:
            return
            
        for idx, job in enumerate(self.job_type_detail):
            if job.is_opl == 1 and not job.vendor:
                frappe.throw(_(
                    "Row #{0}: Vendor is mandatory for OPL Job Type '{1}'"
                ).format(idx + 1, job.job_type))
    
    def calculate_total_amount(self):
        """Calculate total amount of the work order"""
        total = 0
        
        # Sum part amounts
        total += self.calculate_part_total()
        
        # Sum job type prices
        total += self.calculate_job_type_total()
        
        # Sum service package total prices
        total += self.calculate_service_package_total()
        
        # Sum expense amounts
        total += self.calculate_expense_total()
        
        self.total_amount = total
    
    def calculate_part_total(self):
        """Calculate total amount for parts"""
        total = 0
        if self.part_detail:
            for part in self.part_detail:
                total += flt(part.amount)
        return total
    
    def calculate_job_type_total(self):
        """Calculate total amount for job types"""
        total = 0
        if self.job_type_detail:
            for job in self.job_type_detail:
                total += flt(job.price)
        return total
    
    def calculate_service_package_total(self):
        """Calculate total amount for service packages"""
        total = 0
        if self.service_package_detail:
            for service in self.service_package_detail:
                total += flt(service.total_price)
        return total
    
    def calculate_expense_total(self):
        """Calculate total amount for external expenses"""
        total = 0
        if self.external_expense:
            for expense in self.external_expense:
                total += flt(expense.amount)
        return total
    
    def before_submit(self):
        # Validate all important fields are filled before submitting
        self.validate_important_fields()
        
        # Validate part details before submission
        self.validate_part_details_before_submit()
    
    def validate_important_fields(self):
        """Validate mandatory fields before submission"""
        # List of mandatory fields to check before submission
        mandatory_fields = [
            {"fieldname": "customer", "label": "Customer"},
            {"fieldname": "customer_vehicle", "label": "Customer Vehicle"},
            {"fieldname": "service_date", "label": "Service Date"},
            {"fieldname": "service_advisor", "label": "Service Advisor"},
            {"fieldname": "status", "label": "Status"}
        ]
        
        # Check if any mandatory field is empty
        for field in mandatory_fields:
            if not self.get(field["fieldname"]):
                frappe.throw(_("{0} is mandatory before submitting").format(field["label"]))
        
        # Check if there are any details in the Work Order
        if not (self.job_type_detail or self.service_package_detail or self.part_detail):
            frappe.throw(_("Work Order must have at least one Job Type, Service Package, or Part detail before submitting"))
    
    def validate_part_details_before_submit(self):
        """Validate part details before submission"""
        if not self.part_detail:
            return
            
        for idx, part in enumerate(self.part_detail):
            # Check for purchase order for "Beli Baru" parts
            if part.source == "Beli Baru" and not part.purchase_order:
                frappe.throw(_(
                    "Row #{0}: Purchase Order is mandatory for Part '{1}' with 'Beli Baru' source before submitting"
                ).format(idx + 1, part.part_name or part.part))
            
            # Check for complete part information
            if not part.quantity or not part.rate or not part.amount:
                frappe.throw(_(
                    "Row #{0}: Quantity, Rate, and Amount are mandatory for Part '{1}' before submitting"
                ).format(idx + 1, part.part_name or part.part))
    
    def validate_job_types_before_submit(self):
        """Validate job types before submission"""
        if not self.job_type_detail:
            return
            
        for idx, job in enumerate(self.job_type_detail):
            if not job.price:
                frappe.throw(_(
                    "Row #{0}: Price is mandatory for Job Type '{1}' before submitting"
                ).format(idx + 1, job.job_type))
    
    def validate_service_packages_before_submit(self):
        """Validate service packages before submission"""
        if not self.service_package_detail:
            return
            
        for idx, service in enumerate(self.service_package_detail):
            if not service.total_price:
                frappe.throw(_(
                    "Row #{0}: Total Price is mandatory for Service Package '{1}' before submitting"
                ).format(idx + 1, service.service_package))
    
    def validate_expenses_before_submit(self):
        """Validate external expenses before submission"""
        if not self.external_expense:
            return
            
        for idx, expense in enumerate(self.external_expense):
            if not expense.amount:
                frappe.throw(_(
                    "Row #{0}: Amount is mandatory for Expense '{1}' before submitting"
                ).format(idx + 1, expense.expense_type))

@frappe.whitelist()
def make_material_issue(source_name, target_doc=None):
    """
    Create a new Workshop Material Issue from a Work Order
    
    Args:
        source_name: Work Order name
        target_doc: Target doc if provided
        
    Returns:
        Workshop Material Issue doc
    """
    def set_missing_values(source, target):
        # Set default values if missing
        target.posting_date = frappe.utils.getdate()
        
        # Set issued_by as the current user's Employee record if exists
        employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
        if employee:
            target.issued_by = employee
            
        # Add any remarks
        target.remarks = _("Material Issue created from Work Order {0}").format(source_name)
        
    def update_item(source_obj, target_obj, source_parent):
        # Find corresponding Part for this item
        parts = frappe.get_all("Part", 
            filters={"item": source_obj.item_code},
            fields=["name", "description"])
            
        if parts:
            # Set the Part and related fields
            target_obj.part = parts[0].name
            target_obj.description = parts[0].description
            
            # Get stock information for rate calculation
            bin_data = frappe.db.get_value("Bin", 
                {"item_code": source_obj.item_code, "warehouse": source_parent.source_warehouse}, 
                ["valuation_rate"], as_dict=1) or {"valuation_rate": 0}
                
            target_obj.rate = bin_data.valuation_rate
            target_obj.amount = flt(target_obj.qty) * flt(target_obj.rate)
    
    # Get the source document
    doc = frappe.get_doc("Work Order", source_name)
    
    # Create the target document using mapped doc
    target_doc = get_mapped_doc("Work Order", source_name, {
        "Work Order": {
            "doctype": "Workshop Material Issue",
            "field_map": {
                "name": "work_order",
                "source_warehouse": "set_warehouse"
            },
            "validation": {
                "docstatus": ["=", 1]  # Only allow if Work Order is submitted
            }
        },
        "Work Order Item": {  # Assuming this is the name of your required_items table
            "doctype": "Workshop Material Issue Item",
            "field_map": {
                "item_code": "item_code",
                "required_qty": "qty",
                "stock_uom": "uom"
            },
            "postprocess": update_item
        }
    }, target_doc, set_missing_values)
    
    return target_doc