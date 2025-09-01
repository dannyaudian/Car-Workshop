import importlib
import sys
import types
from pathlib import Path


def setup_frappe_stub(item_price_result):
    """Create a minimal frappe stub for pricing tests."""
    frappe = types.ModuleType("frappe")
    frappe._ = lambda m: m

    def get_value(doctype, name, field):
        if doctype == "Part" and field == "item":
            return "ITEM-001"
        if doctype == "Item Tax Template Item":
            return "TAX-TEMPLATE"
        return None

    def get_all(doctype, **kwargs):
        if doctype == "Item Price":
            return item_price_result
        return []

    utils = types.ModuleType("frappe.utils")
    utils.flt = lambda x: float(x or 0)
    utils.getdate = lambda x: x
    utils.nowdate = lambda: "2024-01-01"
    utils.fmt_money = lambda value, precision, symbol="": f"{symbol}{value}"

    frappe.db = types.SimpleNamespace(get_value=get_value)
    frappe.get_all = get_all
    frappe.utils = utils
    frappe.whitelist = lambda *args, **kwargs: (lambda f: f)
    frappe.throw = lambda msg: (_ for _ in ()).throw(Exception(msg))

    sys.modules["frappe"] = frappe
    sys.modules["frappe.utils"] = utils
    return frappe


def import_pricing_module(item_price_result):
    setup_frappe_stub(item_price_result)
    importlib.invalidate_caches()
    sys.modules.pop("car_workshop", None)
    sys.modules.pop("car_workshop.utils", None)
    sys.modules.pop("car_workshop.utils.pricing", None)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    return importlib.import_module("car_workshop.utils.pricing")


def test_resolve_rate_from_item_price():
    module = import_pricing_module([
        types.SimpleNamespace(price_list_rate=150, currency="USD")
    ])
    called = False

    def fake_fallback(*args, **kwargs):
        nonlocal called
        called = True
        return None

    module.get_active_service_price = fake_fallback
    result = module.resolve_rate("Part", "PART-001", "Standard", "2024-01-01")

    assert result["rate"] == 150
    assert result["currency"] == "USD"
    assert result["source"] == "Item Price"
    assert called is False


def test_resolve_rate_falls_back_to_service_price_list():
    module = import_pricing_module([])
    called = False

    def fake_fallback(reference_type, reference_name, price_list, posting_date):
        nonlocal called
        called = True
        return {
            "rate": 300,
            "currency": "USD",
            "tax_template": None,
            "source": "Service Price List",
            "found": True,
        }

    module.get_active_service_price = fake_fallback
    result = module.resolve_rate("Part", "PART-001", "Standard", "2024-01-01")

    assert called is True
    assert result["rate"] == 300
    assert result["source"] == "Service Price List"
