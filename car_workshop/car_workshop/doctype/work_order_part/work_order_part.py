import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

class WorkOrderPart(Document):
    def validate(self):
        # Fetch missing values from Part if not already set
        self.fetch_part_details()
        
        # Validate source and purchase order
        self.validate_source_and_po()
        
        # Calculate amount
        self.calculate_amount()
    
    def fetch_part_details(self):
        """Fetch missing values from Part doctype"""
        if self.part:
            part_fields = ["part_number", "part_name", "item_code", "brand", "category"]
            part_doc = frappe.get_doc("Part", self.part)
            
            for field in part_fields:
                if not self.get(field) and hasattr(part_doc, field):
                    self.set(field, part_doc.get(field))
            
            # Set rate from Part's current_price if not already set
            if not self.rate and part_doc.current_price:
                self.rate = part_doc.current_price
    
    def validate_source_and_po(self):
        """Validate source and purchase order relationship"""
        # Ensure source is set
        if not self.source:
            self.source = "Dari Stok"  # Default to stock if not set
        
        # Validate purchase order for "Beli Baru" source
        if self.source == "Beli Baru":
            if not self.purchase_order:
                frappe.throw(_(
                    "Purchase Order is required for Part '{0}' when Source is 'Beli Baru'"
                ).format(self.part_name or self.part))
        else:
            # Clear purchase order if source is not "Beli Baru"
            if self.purchase_order:
                self.purchase_order = None
    
    def calculate_amount(self):
        """Calculate amount based on quantity and rate"""
        if self.quantity and self.rate:
            self.amount = flt(self.quantity) * flt(self.rate)
        else:
            # Ensure amount is 0 if either quantity or rate is missing
            self.amount = 0