# Copyright (c) 2023, PT. Innovasi Terbaik Bangsa and contributors
# For license information, please see license.txt

from typing import Dict, Optional, Union, Any
from datetime import date

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, flt


class ServicePriceList(Document):
    def validate(self):
        self.validate_dates()
        self.validate_rate()
        self.validate_duplicate()
        self.check_reference_exists()
    
    def validate_dates(self) -> None:
        """Validate that valid_from is before valid_upto"""
        if self.valid_from and self.valid_upto and getdate(self.valid_from) > getdate(self.valid_upto):
            frappe.throw(_("Valid From date cannot be after Valid Upto date"))
    
    def validate_rate(self) -> None:
        """Validate rate value is positive if entry is active"""
        if self.is_active and flt(self.rate) <= 0:
            frappe.throw(_("Rate must be greater than zero for active price entries"))
    
    def validate_duplicate(self) -> None:
        """Check for duplicate active price list entry"""
        start = self.valid_from or "1000-01-01"
        end = self.valid_upto or "9999-12-31"

        duplicates = frappe.db.sql(
            """
            SELECT name FROM `tabService Price List`
            WHERE reference_type = %(reference_type)s
              AND reference_name = %(reference_name)s
              AND price_list = %(price_list)s
              AND is_active = 1
              AND name != %(name)s
              AND IFNULL(valid_from, '1000-01-01') <= %(end)s
              AND IFNULL(valid_upto, '9999-12-31') >= %(start)s
            """,
            {
                "reference_type": self.reference_type,
                "reference_name": self.reference_name,
                "price_list": self.price_list,
                "name": self.name or "new-service-price-list",
                "start": start,
                "end": end,
            },
            as_dict=True,
        )

        if duplicates:
            frappe.throw(
                _("An active price already exists for {0} '{1}' in Price List '{2}' with overlapping validity period.").format(
                    self.reference_type, self.reference_name, self.price_list
                )
            )
    
    def check_reference_exists(self) -> None:
        """Check if the referenced document exists"""
        if not frappe.db.exists(self.reference_type, self.reference_name):
            frappe.throw(_("The {0} '{1}' does not exist").format(
                self.reference_type, self.reference_name
            ))
    
    def before_save(self) -> None:
        """Set defaults before saving"""
        if not self.currency:
            self.currency = frappe.db.get_single_value("Selling Settings", "currency") or "IDR"
        
        # If this is being activated, deactivate conflicting entries
        if self.is_active:
            self.deactivate_conflicting_entries()
    
    def deactivate_conflicting_entries(self) -> None:
        """Deactivate other entries that would conflict with this one"""
        start = self.valid_from or "1000-01-01"
        end = self.valid_upto or "9999-12-31"
        
        # Find conflicting entries with overlapping date ranges
        conflicting_entries = frappe.db.sql(
            """
            SELECT name FROM `tabService Price List`
            WHERE reference_type = %(reference_type)s
              AND reference_name = %(reference_name)s
              AND price_list = %(price_list)s
              AND is_active = 1
              AND name != %(name)s
              AND IFNULL(valid_from, '1000-01-01') <= %(end)s
              AND IFNULL(valid_upto, '9999-12-31') >= %(start)s
            """,
            {
                "reference_type": self.reference_type,
                "reference_name": self.reference_name,
                "price_list": self.price_list,
                "name": self.name or "new-service-price-list",
                "start": start,
                "end": end,
            },
            as_dict=True,
        )
        
        # Deactivate conflicting entries
        for entry in conflicting_entries:
            frappe.db.set_value("Service Price List", entry.name, "is_active", 0)
            frappe.msgprint(
                _("Deactivated conflicting price entry: {0}").format(entry.name),
                alert=True
            )
    
    def on_trash(self) -> None:
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
                    _("Warning: This was the only active price for {0} '{1}' in Price List '{2}'. "
                      "There will be no active price after deletion.").format(
                        self.reference_type, self.reference_name, self.price_list
                    ),
                    indicator="orange",
                    alert=True
                )

    @classmethod
    def get_active_rate(
        cls,
        reference_type: str,
        reference_name: str,
        price_list: str,
        posting_date: Optional[Union[str, date]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the active rate for a service, part, or job type.
        
        Args:
            reference_type: The type of reference (Job Type, Part, Service Package)
            reference_name: The name of the reference
            price_list: The price list to check
            posting_date: The date for which to check validity (defaults to today)
            
        Returns:
            Optional[Dict]: Dictionary containing rate, currency, and tax_template, or None if not found
        """
        if not posting_date:
            posting_date = nowdate()
        
        # Convert to string date if it's a date object
        if isinstance(posting_date, date):
            posting_date = posting_date.strftime("%Y-%m-%d")
            
        # Get the latest active price for the given date
        price_record = frappe.db.sql(
            """
            SELECT rate, currency, tax_template
            FROM `tabService Price List`
            WHERE reference_type = %(reference_type)s
              AND reference_name = %(reference_name)s
              AND price_list = %(price_list)s
              AND is_active = 1
              AND (valid_from IS NULL OR valid_from <= %(posting_date)s)
              AND (valid_upto IS NULL OR valid_upto >= %(posting_date)s)
            ORDER BY IFNULL(valid_from, '1000-01-01') DESC, creation DESC
            LIMIT 1
            """,
            {
                "reference_type": reference_type,
                "reference_name": reference_name,
                "price_list": price_list,
                "posting_date": posting_date,
            },
            as_dict=True,
        )
        
        if price_record:
            return {
                "rate": flt(price_record[0].rate),
                "currency": price_record[0].currency,
                "tax_template": price_record[0].tax_template
            }
        
        return None


def get_active_rate(
    reference_type: str,
    reference_name: str,
    price_list: str,
    posting_date: Optional[Union[str, date]] = None
) -> Optional[Dict[str, Any]]:
    """
    Module-level function to get the active rate for a service, part, or job type.
    
    Args:
        reference_type: The type of reference (Job Type, Part, Service Package)
        reference_name: The name of the reference
        price_list: The price list to check
        posting_date: The date for which to check validity (defaults to today)
        
    Returns:
        Optional[Dict]: Dictionary containing rate, currency, and tax_template, or None if not found
    """
    return ServicePriceList.get_active_rate(
        reference_type, reference_name, price_list, posting_date
    )