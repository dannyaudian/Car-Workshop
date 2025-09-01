import sys
import types
from pathlib import Path
import pytest


class WorkOrder:
    def __init__(self, allow_read=True):
        self.status = "Completed"
        self.billing_status = ""
        self.allow_read = allow_read

    def check_permission(self, perm):
        if perm == "read" and not self.allow_read:
            raise Exception("No read permission")


price_map = {
    "JOB-ITEM": 50,
    "PKG-ITEM": 60,
    "PART-ITEM": 70,
}


def install_stubs(allow_read=True, allow_create=True):
    def get_doc(doctype, name):
        return WorkOrder(allow_read=allow_read)

    def get_all(doctype, filters=None, fields=None, **kwargs):
        if doctype == "Work Order Job Type":
            return [types.SimpleNamespace(job_type="JT1", job_type_name="Job 1", hours=2, rate=0)]
        if doctype == "Work Order Service Package":
            return [
                types.SimpleNamespace(
                    service_package="SP1", service_package_name="Pkg 1", quantity=1, rate=None
                )
            ]
        if doctype == "Work Order Part":
            return [
                types.SimpleNamespace(part="PRT1", part_name="Part 1", quantity=3, rate=None)
            ]
        if doctype == "Work Order External Service":
            return [
                types.SimpleNamespace(service_name="Ext", provider="Vendor", rate=100)
            ]
        return []

    def db_get_value(doctype, name, field, *a, **k):
        if doctype == "Job Type" and field == "item":
            return "JOB-ITEM"
        if doctype == "Service Package" and field == "item":
            return "PKG-ITEM"
        if doctype == "Part" and field == "item":
            return "PART-ITEM"
        if doctype == "Selling Settings" and field == "selling_price_list":
            return "Retail"
        return None

    pricing_mod = types.ModuleType("utils.pricing")
    pricing_mod.resolve_rate = lambda **kwargs: price_map.get(kwargs.get("item_code"), 0)

    frappe_stub = types.SimpleNamespace(
        get_doc=get_doc,
        get_all=get_all,
        db=types.SimpleNamespace(get_value=db_get_value),
        _=lambda m: m,
        throw=lambda msg, *a, **k: (_ for _ in ()).throw(Exception(msg)),
        whitelist=lambda *a, **k: (lambda f: f),
        has_permission=lambda doctype, ptype: allow_create,
        PermissionError=Exception,
    )

    sys.modules["frappe"] = frappe_stub
    sys.modules["frappe.utils"] = types.SimpleNamespace()
    sys.modules["utils"] = types.ModuleType("utils")
    sys.modules["utils.pricing"] = pricing_mod

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_get_work_order_billing_source_shape():
    install_stubs()
    sys.modules.pop("car_workshop.api.billing_api", None)
    from car_workshop.api.billing_api import get_work_order_billing_source

    data = get_work_order_billing_source("WO-1")
    assert set(data) == {"job_types", "service_packages", "parts", "external_services"}
    assert data["job_types"][0]["rate"] == 50
    assert data["service_packages"][0]["rate"] == 60
    assert data["parts"][0]["rate"] == 70
    assert data["external_services"][0]["rate"] == 100


def test_requires_read_permission():
    install_stubs(allow_read=False)
    sys.modules.pop("car_workshop.api.billing_api", None)
    from car_workshop.api.billing_api import get_work_order_billing_source

    with pytest.raises(Exception):
        get_work_order_billing_source("WO-1")


def test_requires_sales_invoice_create():
    install_stubs(allow_create=False)
    sys.modules.pop("car_workshop.api.billing_api", None)
    from car_workshop.api.billing_api import get_work_order_billing_source

    with pytest.raises(Exception):
        get_work_order_billing_source("WO-1")
