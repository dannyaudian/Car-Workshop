import frappe
from frappe import _
from frappe.model.document import Document


class VehicleChangeLog(Document):
    def before_validate(self):
        """
        Set default values if not provided
        """
        if not self.updated_by:
            self.updated_by = frappe.session.user
            
        if not self.change_date:
            self.change_date = frappe.utils.now()
            
        if not self.change_type and self.fieldname:
            self.set_change_type()
    
    def set_change_type(self):
        """
        Set change type based on fieldname
        """
        change_type_mapping = {
            "plate_number": "Plate Change",
            "customer": "Owner Change",
        }
        
        self.change_type = change_type_mapping.get(
            self.fieldname, f"{self.fieldname.replace('_', ' ').title()} Change"
        )
    
    def validate(self):
        """
        Validate if we're trying to update an existing document
        """
        if self.is_new():
            return
        
        if not frappe.flags.in_install and not frappe.flags.in_patch and not frappe.flags.in_migrate:
            # If document exists and we're trying to save changes, throw error
            frappe.throw(
                _("Vehicle Change Logs cannot be edited after creation. Please create a new log instead."),
                title=_("Edit Not Allowed")
            )
    
    def before_save(self):
        """
        Perform any necessary actions before saving the document
        """
        # This hook runs for both new and existing documents
        # Since we're blocking updates for existing docs in validate(),
        # we can use this for any pre-save operations on new docs
        pass
    
    def on_trash(self):
        """
        Prevent deletion of Vehicle Change Log records
        """
        if not frappe.flags.in_install and not frappe.flags.in_patch and not frappe.flags.in_migrate:
            frappe.throw(
                _("Vehicle Change Logs cannot be deleted as they serve as an audit trail."),
                title=_("Deletion Not Allowed")
            )
    
    def after_insert(self):
        """
        Actions after a new log is created
        """
        # Add notification or additional processing if needed
        self.notify_change()
    
    def notify_change(self):
        """
        Notify relevant users about the change
        """
        # Skip notification during data migrations, testing, etc.
        if frappe.flags.in_install or frappe.flags.in_patch or frappe.flags.in_migrate or frappe.flags.in_import:
            return
            
        # This is where you would add notification logic if required
        # For example:
        # if self.change_type == "Owner Change":
        #     frappe.publish_realtime(
        #         'vehicle_owner_changed', 
        #         {'vehicle': self.vehicle, 'new_owner': self.new_value}
        #     )