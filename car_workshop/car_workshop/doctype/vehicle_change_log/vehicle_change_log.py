import frappe
from frappe import _
from frappe.model.document import Document

class VehicleChangeLog(Document):
    def before_validate(self):
        if not self.updated_by:
            self.updated_by = frappe.session.user
        if not self.change_date:
            self.change_date = frappe.utils.now()
        if not self.change_type and self.fieldname:
            self.set_change_type()

    def set_change_type(self):
        mapping = {
            "plate_number": "Plate Change",
            "customer": "Owner Change",
        }
        self.change_type = mapping.get(
            self.fieldname, f"{self.fieldname.replace('_', ' ').title()} Change"
        )

    def validate(self):
        if not self.is_new():
            if not (frappe.flags.in_install or frappe.flags.in_patch or frappe.flags.in_migrate):
                frappe.throw(
                    _("Vehicle Change Logs cannot be edited after creation. Please create a new log instead."),
                    title=_("Edit Not Allowed")
                )

    def before_save(self):
        pass

    def on_trash(self):
        if not (frappe.flags.in_install or frappe.flags.in_patch or frappe.flags.in_migrate):
            frappe.throw(
                _("Vehicle Change Logs cannot be deleted as they serve as an audit trail."),
                title=_("Deletion Not Allowed")
            )

    def after_insert(self):
        self.notify_change()

    def notify_change(self):
        if frappe.flags.in_install or frappe.flags.in_patch or frappe.flags.in_migrate or frappe.flags.in_import:
            return
        # Add notification logic here if needed
