import sys
import types
from pathlib import Path
import pytest

# Stub Frappe modules and Document class
class Document:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get(self, name):
        return getattr(self, name, None)

frappe_utils_stub = types.SimpleNamespace(
    flt=lambda x: float(x or 0),
    nowdate=lambda: "2024-01-01",
    add_days=lambda date, days: date,
)

frappe_stub = types.SimpleNamespace(
    _=lambda msg: msg,
    throw=lambda msg: (_ for _ in ()).throw(Exception(msg)),
    utils=frappe_utils_stub,
    whitelist=lambda *args, **kwargs: (lambda f: f),
)

# Setup model modules
model_document = types.SimpleNamespace(Document=Document)
model_mapper = types.SimpleNamespace(get_mapped_doc=lambda *args, **kwargs: None)
model_naming = types.SimpleNamespace(make_autoname=lambda pattern: pattern)

frappe_model = types.SimpleNamespace(
    document=model_document,
    mapper=model_mapper,
    naming=model_naming,
)

# Register stubs in sys.modules
sys.modules['frappe'] = frappe_stub
sys.modules['frappe.model'] = frappe_model
sys.modules['frappe.model.document'] = model_document
sys.modules['frappe.model.mapper'] = model_mapper
sys.modules['frappe.model.naming'] = model_naming
sys.modules['frappe.utils'] = frappe_utils_stub

# Ensure the package root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_workshop.car_workshop.doctype.work_order.work_order import WorkOrder


def create_work_order(**kwargs):
    defaults = dict(
        customer="CUST-001",
        customer_vehicle="VEH-001",
        service_date="2024-01-01",
        service_advisor="SA-001",
        status="Open",
        job_type_detail=None,
        service_package_detail=None,
        part_detail=None,
        external_expense=None,
    )
    defaults.update(kwargs)
    return WorkOrder(**defaults)


def test_validate_important_fields_passes_with_expense_only():
    wo = create_work_order(external_expense=[types.SimpleNamespace(amount=100)])
    # Should not raise
    wo.validate_important_fields()


def test_validate_important_fields_requires_detail():
    wo = create_work_order()
    with pytest.raises(Exception):
        wo.validate_important_fields()
