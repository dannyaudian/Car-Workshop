import frappe
from frappe import _
from frappe.model.document import Document


class VehicleChangeLog(Document):
    def before_validate(self):
        """
        Automatically populate fields before validation
        - updated_by: Current user
        - change_date: Current timestamp
        - change_type: Based on fieldname
        """
        self._set_user_and_timestamp()
        self._set_change_type()
    
    def _set_user_and_timestamp(self):
        """Set the user and timestamp if not already set"""
        if not self.updated_by:
            self.updated_by = frappe.session.user
        if not self.change_date:
            self.change_date = frappe.utils.now()
    
    def _set_change_type(self):
        """Determine change_type based on fieldname with mapping fallback"""
        if not self.change_type and self.fieldname:
            mapping = {
                "plate_number": "Plate Change",
                "customer": "Owner Change",
                "brand": "Brand Change",
                "model": "Model Change",
                "year": "Year Change",
                "vin": "VIN Change",
                "creation": "Created",
            }
            self.change_type = mapping.get(
                self.fieldname, f"{self.fieldname.replace('_', ' ').title()} Change"
            )

    def validate(self):
        """
        Ensure immutability of existing logs
        - Prevent edits to existing records
        """
        self._prevent_edits()
    
    def _prevent_edits(self):
        """Prevent edits to existing change logs"""
        if not self.is_new():
            if not self._is_system_operation():
                frappe.throw(
                    _("Vehicle Change Logs cannot be edited after creation. Please create a new log instead."),
                    title=_("Edit Not Allowed")
                )

    def on_trash(self):
        """
        Ensure immutability of existing logs
        - Prevent deletions of records
        """
        if not self._is_system_operation():
            frappe.throw(
                _("Vehicle Change Logs cannot be deleted as they serve as an audit trail."),
                title=_("Deletion Not Allowed")
            )
    
    def _is_system_operation(self):
        """Check if operation is being done by system processes"""
        return any([
            frappe.flags.in_install,
            frappe.flags.in_patch,
            frappe.flags.in_migrate,
            frappe.flags.in_import
        ])

    def after_insert(self):
        """
        Execute actions after log entry is created
        - Notify relevant parties if needed
        """
        self.notify_change()

    def notify_change(self):
        """
        Hook for notifications or integrations
        Can be extended for email alerts, webhooks, etc.
        """
        if self._is_system_operation():
            return
            
        # Implementation can be added here based on notification requirements
        # Examples:
        # - Send email to vehicle owner
        # - Send webhook to external system
        # - Create notification in Frappe
        pass