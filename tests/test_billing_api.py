import sys
import types
from pathlib import Path
import pytest

# Ensure package root on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def identity_decorator(*args, **kwargs):
    def wrapper(fn):
        return fn
    return wrapper


def build_frappe_stub():
    PermissionError = type("PermissionError", (Exception,), {})

    utils = types.SimpleNamespace(flt=float, nowdate=lambda: "2024-01-01")

    def throw(msg, exc=None):
        raise (exc or Exception)(msg)

    frappe_stub = types.SimpleNamespace(
        db=types.SimpleNamespace(get_value=lambda *a, **k: None),
        get_all=lambda *a, **k: [],
        get_doc=lambda *a, **k: types.SimpleNamespace(),
        has_permission=lambda *a, **k: True,
        whitelist=identity_decorator,
        _=lambda m: m,
        throw=throw,
        PermissionError=PermissionError,
        utils=utils,
    )
    return frappe_stub


def setup_module(module):
    frappe_stub = build_frappe_stub()
    sys.modules['frappe'] = frappe_stub
    module.frappe_stub = frappe_stub

    from car_workshop.api import billing_api

    module.api = billing_api


def test_get_work_order_billing_source_returns_items():
    class WorkOrderDoc:
        status = "Completed"
        billing_status = "Unbilled"
        posting_date = "2024-03-01"

        def check_permission(self, perm):
            return None

    frappe_stub.get_doc = lambda *a, **k: WorkOrderDoc()
    frappe_stub.has_permission = lambda *a, **k: True

    def db_get_value(doctype, name, fieldname=None):
        if doctype == "Selling Settings":
            return "Standard Selling"
        return "ITEM-001"

    frappe_stub.db.get_value = db_get_value

    frappe_stub.get_all = lambda doctype, *a, **k: {
        "Work Order Job Type": [types.SimpleNamespace(job_type="JT", job_type_name="Job", hours=2, rate=100, amount=0)],
        "Work Order Service Package": [types.SimpleNamespace(service_package="SP", service_package_name="Pack", quantity=1, rate=200, amount=0)],
        "Work Order Part": [types.SimpleNamespace(part="PT", part_name="Part", quantity=2, rate=50, amount=0)],
        "Work Order External Service": [types.SimpleNamespace(service_name="Cleaning", provider="Vendor", rate=30, amount=0)],
    }[doctype]

    data = api.get_work_order_billing_source("WO-1")
    assert set(data.keys()) == {"job_types", "service_packages", "parts", "external_services"}
    assert data["job_types"][0].amount == 200
    assert data["service_packages"][0].amount == 200
    assert data["parts"][0].amount == 100
    assert data["external_services"][0].amount == 30


def test_get_work_order_billing_source_requires_sales_invoice_create_permission():
    frappe_stub.has_permission = lambda doctype, *a, **k: False if doctype == "Sales Invoice" else True

    with pytest.raises(frappe_stub.PermissionError):
        api.get_work_order_billing_source("WO-1")


def test_get_work_order_billing_source_requires_work_order_read_permission():
    class WorkOrderDoc:
        status = "Completed"
        billing_status = "Unbilled"
        posting_date = "2024-03-01"

        def check_permission(self, perm):
            raise frappe_stub.PermissionError("no read")

    frappe_stub.get_doc = lambda *a, **k: WorkOrderDoc()
    frappe_stub.has_permission = lambda *a, **k: True

    with pytest.raises(frappe_stub.PermissionError):
        api.get_work_order_billing_source("WO-1")
