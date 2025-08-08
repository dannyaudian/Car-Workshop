import frappe
from frappe.model.document import Document
from collections import defaultdict
import json
import hashlib

class ServicePackage(Document):
    def validate(self):
        self.validate_details()
        self.calculate_totals()
    
    def validate_details(self):
        """Validate that service package has at least one service detail"""
        if not self.details or len(self.details) == 0:
            frappe.throw("Service Package must have at least one service detail.")
    
    def calculate_totals(self):
        """Calculate totals for the service package"""
        total_amount = 0
        total_time = 0

        # Gather unique job types and parts for bulk lookup
        job_types = list({d.job_type for d in self.details if d.item_type == "Job" and d.job_type})
        part_names = list({d.part for d in self.details if d.item_type == "Part" and d.part})

        job_rates = {}
        job_durations = {}

        if job_types:
            job_data = frappe.get_all(
                "Job Type",
                filters={"name": ["in", job_types]},
                fields=["name", "default_price", "time_minutes"],
            )

            missing_rate = []
            for jd in job_data:
                job_rates[jd.name] = jd.default_price or 0
                job_durations[jd.name] = jd.time_minutes or 0
                if not jd.default_price:
                    missing_rate.append(jd.name)

            if missing_rate:
                item_data = frappe.get_all(
                    "Job Type Item",
                    filters={"parent": ["in", missing_rate]},
                    fields=["parent", "qty", "rate", "amount"],
                )
                totals = defaultdict(float)
                for item in item_data:
                    totals[item.parent] += item.amount or (item.qty * item.rate) or 0
                for jt in missing_rate:
                    job_rates[jt] = totals.get(jt, 0)

                    if not job_rates[jt] and self.price_list:
                        from car_workshop.car_workshop.doctype.service_price_list.get_active_service_price import (
                            get_active_service_price,
                        )

                        result = get_active_service_price("Job Type", jt, self.price_list)
                        if result and result.get("rate"):
                            job_rates[jt] = result.get("rate")

        part_prices = {}
        if part_names:
            part_data = frappe.get_all(
                "Part",
                filters={"name": ["in", part_names]},
                fields=["name", "current_price"],
            )
            for pd in part_data:
                part_prices[pd.name] = pd.current_price or 0

        for detail in self.details:
            # Ensure each detail has an amount
            if not detail.amount:
                if detail.item_type == "Job":
                    rate = job_rates.get(detail.job_type, 0)
                elif detail.item_type == "Part":
                    rate = part_prices.get(detail.part, 0)
                else:
                    rate = 0

                detail.rate = rate
                detail.amount = (detail.quantity or 1) * rate

            total_amount += detail.amount

            # Add time if job type has duration
            if detail.item_type == "Job" and detail.job_type:
                total_time += job_durations.get(detail.job_type, 0) * (detail.quantity or 1)
        
        # Update package totals
        self.price = total_amount
        self.total_time_minutes = total_time
        
        # Convert time to hours and minutes for display
        hours = total_time // 60
        minutes = total_time % 60
        self.estimated_time = f"{hours} hr{'' if hours == 1 else 's'} {minutes} min{'' if minutes == 1 else 's'}"
    
    def get_job_type_rate(self, job_type_name):
        """Get the rate from JobType based on its items structure"""
        # First check if the JobType has a field called 'default_price'
        rate = frappe.db.get_value("Job Type", job_type_name, "default_price")

        if rate:
            return rate

        # If no direct price field, calculate from items
        items = frappe.get_all(
            "Job Type Item",
            filters={"parent": job_type_name},
            fields=["qty", "rate", "amount"],
        )

        total_rate = 0
        if items:
            for item in items:
                total_rate += (item.amount or (item.qty * item.rate) or 0)

        if total_rate:
            return total_rate

        if self.price_list:
            from car_workshop.car_workshop.doctype.service_price_list.get_active_service_price import (
                get_active_service_price,
            )

            result = get_active_service_price("Job Type", job_type_name, self.price_list)
            if result and result.get("rate"):
                return result.get("rate")

        return 0
    
    def _details_have_changed(self):
        """Check if child table `details` has changed using a hash comparison"""
        previous_doc = self.get_doc_before_save()
        if not previous_doc:
            return False

        def serialize(details):
            return [
                d.as_dict() if hasattr(d, "as_dict") else getattr(d, "__dict__", {})
                for d in details or []
            ]

        current_details = serialize(self.get("details"))
        previous_details = serialize(previous_doc.get("details"))

        current_hash = hashlib.md5(
            json.dumps(current_details, sort_keys=True).encode()
        ).hexdigest()
        previous_hash = hashlib.md5(
            json.dumps(previous_details, sort_keys=True).encode()
        ).hexdigest()

        return current_hash != previous_hash

    def before_save(self):
        """Set modified package flag"""
        if self.has_value_changed("price") or self._details_have_changed():
            self.is_modified = 1
    
    def on_update(self):
        """Update linked price list item if specified"""
        if self.price_list:
            self.update_price_list_item()
    
    def update_price_list_item(self):
        """Update or create price list item for this service package"""
        # Check if price list item exists
        price_list_item = frappe.get_all(
            "Item Price",
            filters={
                "price_list": self.price_list,
                "item_code": self.name
            },
            fields=["name"]
        )
        
        if price_list_item:
            # Update existing price list item
            item_price = frappe.get_doc("Item Price", price_list_item[0].name)
            item_price.price_list_rate = self.price
            item_price.currency = self.currency
            item_price.save()
            frappe.msgprint(f"Price List item updated for {self.package_name}")
        else:
            # Create new price list item
            item_price = frappe.get_doc({
                "doctype": "Item Price",
                "price_list": self.price_list,
                "item_code": self.name,
                "price_list_rate": self.price,
                "currency": self.currency
            })
            item_price.insert()
            frappe.msgprint(f"New Price List item created for {self.package_name}")
