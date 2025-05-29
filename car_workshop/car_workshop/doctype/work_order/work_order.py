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
        # Validate purchase_order field if source is "Beli Baru"
        self.validate_purchase_order()
        
        # Validate vendors for OPL job types
        self.validate_opl_vendors()
        
        # Calculate total amount
        self.calculate_total_amount()
    
    def validate_purchase_order(self):
        if self.source == "Beli Baru" and not self.purchase_order:
            frappe.throw(_("Purchase Order is mandatory when Source is 'Beli Baru'"))
    
    def validate_opl_vendors(self):
        for job in self.job_type_detail:
            if job.is_opl == 1 and not job.vendor:
                frappe.throw(_("Vendor is mandatory for OPL Job Type: {0}").format(job.job_type))
    
    def calculate_total_amount(self):
        total = 0
        
        # Sum part amounts
        if self.part_detail:
            for part in self.part_detail:
                total += flt(part.amount)
        
        # Sum job type prices
        if self.job_type_detail:
            for job in self.job_type_detail:
                total += flt(job.price)
        
        # Sum service package total prices
        if self.service_package_detail:
            for service in self.service_package_detail:
                total += flt(service.total_price)
        
        # Sum expense amounts
        if self.external_expense:
            for expense in self.external_expense:
                total += flt(expense.amount)
        
        self.total_amount = total
    
    def before_submit(self):
        # Validate all important fields are filled before submitting
        self.validate_important_fields()
    
    def validate_important_fields(self):
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
        
        # Check for incomplete job types
        for job in self.job_type_detail:
            if not job.price:
                frappe.throw(_("Price is mandatory for Job Type: {0}").format(job.job_type))
        
        # Check for incomplete service packages
        for service in self.service_package_detail:
            if not service.total_price:
                frappe.throw(_("Total Price is mandatory for Service Package: {0}").format(service.service_package))
        
        # Check for incomplete parts
        for part in self.part_detail:
            if not part.quantity or not part.rate or not part.amount:
                frappe.throw(_("Quantity, Rate, and Amount are mandatory for Part: {0}").format(part.part))
        
        # Check for incomplete expenses
        for expense in self.external_expense:
            if not expense.amount:
                frappe.throw(_("Amount is mandatory for Expense: {0}").format(expense.expense_type))