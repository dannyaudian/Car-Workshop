import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

class ServicePriceList(Document):
    def validate(self):
        self.validate_dates()
        self.validate_duplicate()
        self.check_reference_exists()
    
    def validate_dates(self):
        """Validate that valid_from is before valid_upto"""
        if self.valid_from and self.valid_upto and getdate(self.valid_from) > getdate(self.valid_upto):
            frappe.throw("Valid From date cannot be after Valid Upto date")
    
    def validate_duplicate(self):
        """Check for duplicate active price list entry"""
        filters = {
            "reference_type": self.reference_type,
            "reference_name": self.reference_name,
            "price_list": self.price_list,
            "is_active": 1,
            "name": ["!=", self.name]  # Exclude current document
        }
        
        # Date-based filter conditions
        date_conditions = []
        today = nowdate()
        
        if self.valid_from and self.valid_upto:
            # This entry has a date range, check for overlaps
            date_conditions.extend([
                # Other entry with no dates (always valid)
                {"valid_from": ["is", "not set"], "valid_upto": ["is", "not set"]},
                
                # Other entry with only from date, check if it's before our upto
                {"valid_from": ["<=", self.valid_upto], "valid_upto": ["is", "not set"]},
                
                # Other entry with only upto date, check if it's after our from
                {"valid_from": ["is", "not set"], "valid_upto": [">=", self.valid_from]},
                
                # Other entry with both dates, check for any overlap
                {"valid_from": ["<=", self.valid_upto], "valid_upto": [">=", self.valid_from]}
            ])
        elif self.valid_from:
            # Only from date, valid from that date onwards
            date_conditions.extend([
                # Other entry with no dates
                {"valid_from": ["is", "not set"], "valid_upto": ["is", "not set"]},
                
                # Other entry with only from date
                {"valid_from": ["is", "not set"], "valid_upto": [">=", self.valid_from]},
                
                # Other entry with both dates, check if end date is after our from
                {"valid_from": ["is", "not set"], "valid_upto": [">=", self.valid_from]}
            ])
        elif self.valid_upto:
            # Only upto date, valid until that date
            date_conditions.extend([
                # Other entry with no dates
                {"valid_from": ["is", "not set"], "valid_upto": ["is", "not set"]},
                
                # Other entry with only upto date
                {"valid_from": ["<=", self.valid_upto], "valid_upto": ["is", "not set"]},
                
                # Other entry with both dates, check if start date is before our upto
                {"valid_from": ["<=", self.valid_upto], "valid_upto": ["is", "not set"]}
            ])
        else:
            # No dates, always valid
            # Any other entry with this reference and price list would conflict
            pass
        
        # Check for duplicates with date conditions
        duplicates = []
        if date_conditions:
            for condition in date_conditions:
                combined_filters = {**filters, **condition}
                duplicates.extend(frappe.get_all("Service Price List", filters=combined_filters))
        else:
            # No date conditions, simple duplicate check
            duplicates = frappe.get_all("Service Price List", filters=filters)
        
        if duplicates:
            frappe.throw(
                f"An active price already exists for {self.reference_type} '{self.reference_name}' "
                f"in Price List '{self.price_list}' with overlapping validity period."
            )
    
    def check_reference_exists(self):
        """Check if the referenced document exists"""
        if not frappe.db.exists(self.reference_type, self.reference_name):
            frappe.throw(f"The {self.reference_type} '{self.reference_name}' does not exist")
    
    def before_save(self):
        """Set defaults before saving"""
        if not self.currency:
            self.currency = "IDR"  # Default currency
        
        # If this is being activated, deactivate conflicting entries
        if self.is_active:
            self.deactivate_conflicting_entries()
    
    def deactivate_conflicting_entries(self):
        """Deactivate other entries that would conflict with this one"""
        # Similar to validate_duplicate but updates instead of throwing error
        filters = {
            "reference_type": self.reference_type,
            "reference_name": self.reference_name,
            "price_list": self.price_list,
            "is_active": 1,
            "name": ["!=", self.name]  # Exclude current document
        }
        
        # Date-based filter conditions
        date_conditions = []
        
        if self.valid_from and self.valid_upto:
            date_conditions.extend([
                {"valid_from": ["<=", self.valid_upto], "valid_upto": [">=", self.valid_from]}
            ])
        elif self.valid_from:
            date_conditions.extend([
                {"valid_upto": [">=", self.valid_from]}
            ])
        elif self.valid_upto:
            date_conditions.extend([
                {"valid_from": ["<=", self.valid_upto]}
            ])
        
        # Get conflicting entries
        conflicting_entries = []
        if date_conditions:
            for condition in date_conditions:
                combined_filters = {**filters, **condition}
                conflicting_entries.extend(frappe.get_all("Service Price List", filters=combined_filters))
        else:
            # No date conditions, all entries conflict
            conflicting_entries = frappe.get_all("Service Price List", filters=filters)
        
        # Deactivate conflicting entries
        for entry in conflicting_entries:
            frappe.db.set_value("Service Price List", entry.name, "is_active", 0)
    
    def on_trash(self):
        """Check if this is the only active price for the reference"""
        if self.is_active:
            active_prices = frappe.get_all(
                "Service Price List",
                filters={
                    "reference_type": self.reference_type,
                    "reference_name": self.reference_name,
                    "price_list": self.price_list,
                    "is_active": 1,
                    "name": ["!=", self.name]
                },
                limit=1
            )
            
            if not active_prices:
                frappe.msgprint(
                    f"Warning: This was the only active price for {self.reference_type} '{self.reference_name}' "
                    f"in Price List '{self.price_list}'. There will be no active price after deletion."
                )
