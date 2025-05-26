import frappe
from frappe import _
from frappe.model.document import Document

class VehicleChangeLog(Document):
    def before_validate(self):
        """Set default values if not provided."""
        if not self.updated_by:
            self.updated_by = frappe.session.user

        if not self.change_date:
            self.change_date = frappe.utils.now()

        if not self.change_type and self.fieldname:
            self.set_change_type()

    def set_change_type(self):
        """Set change_type based on fieldname."""
        mapping = {
            "plate_number": "Plate Change",
            "customer": "Owner Change",
        }
        self.change_type = mapping.get(
            self.fieldname, f"{self.fieldname.replace('_', ' ').title()} Change"
        )

    def validate(self):
        """Block edits after creation (except during install/patch/migrate)."""
        if not self.is_new():
            if not (frappe.flags.in_install or frappe.flags.in_patch or frappe.flags.in_migrate):
                frappe.throw(
                    _("Vehicle Change Logs cannot be edited after creation. Please create a new log instead."),
                    title=_("Edit Not Allowed")
                )

    def before_save(self):
        """Reserved for future pre-save logic."""
        pass

    def on_trash(self):
        """Prevent deletion of vehicle change logs (except during install/patch/migrate)."""
        if not (frappe.flags.in_install or frappe.flags.in_patch or frappe.flags.in_migrate):
            frappe.throw(
                _("Vehicle Change Logs cannot be deleted as they serve as an audit trail."),
                title=_("Deletion Not Allowed")
            )

    def after_insert(self):
        """Trigger notifications or additional processing after insert."""
        self.notify_change()

    def notify_change(self):
        """Send notification if needed (stub, can be extended)."""
        if frappe.flags.in_install or frappe.flags.in_patch or frappe.flags.in_migrate or frappe.flags.in_import:
            return
        # Example: 
        # if self.change_type == "Owner Change":
        #     frappe.publish_realtime(
        #         'vehicle_owner_changed', 
        #         {'vehicle': self.vehicle, 'new_owner': self.new_value}
        #     )
