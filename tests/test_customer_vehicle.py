import sys
import types
from pathlib import Path
import pytest

# Stub Document
class Document:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

# Frappe stub
frappe_stub = types.SimpleNamespace(
    db=types.SimpleNamespace(get_value=lambda *args, **kwargs: None),
    throw=lambda *args, **kwargs: (_ for _ in ()).throw(Exception(args[0] if args else "")),
    _=lambda msg: msg,
)
frappe_stub.model = types.SimpleNamespace(document=types.SimpleNamespace(Document=Document))

# Register stubs
sys.modules['frappe'] = frappe_stub
sys.modules['frappe.model'] = frappe_stub.model
sys.modules['frappe.model.document'] = frappe_stub.model.document

# Ensure package root on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_workshop.car_workshop.doctype.customer_vehicle.customer_vehicle import CustomerVehicle


def test_validate_rejects_duplicate_plate():
    frappe_stub.db.get_value = lambda doctype, filters, field: "OTHER-VEHICLE"
    vehicle = CustomerVehicle(name="CURRENT", plate_number="B 1234 CD", model=None)
    with pytest.raises(Exception):
        vehicle.validate()


def test_validate_allows_unique_plate():
    frappe_stub.db.get_value = lambda doctype, filters, field: None
    vehicle = CustomerVehicle(name="CV-001", plate_number="B 1234 CD", model=None)
    vehicle.validate()
