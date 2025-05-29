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