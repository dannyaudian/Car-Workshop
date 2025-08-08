import sys
import types
from pathlib import Path
import pytest


def setup_frappe_stub():
    frappe = types.ModuleType("frappe")
    frappe._ = lambda m: m
    def throw(msg):
        raise Exception(msg)
    frappe.throw = throw
    frappe.db = types.SimpleNamespace(exists=lambda *args, **kwargs: False)
    utils = types.ModuleType("frappe.utils")
    utils.flt = float
    utils.cint = int
    utils.getdate = lambda v: v
    utils.now_datetime = lambda: types.SimpleNamespace(strftime=lambda fmt: "00:00:00")
    frappe.utils = utils
    sys.modules["frappe"] = frappe
    sys.modules["frappe.utils"] = utils
    frappe.whitelist = lambda *args, **kwargs: (lambda f: f)
    model = types.ModuleType("frappe.model")
    document = types.ModuleType("frappe.model.document")
    class Document:
        pass
    document.Document = Document
    model.document = document
    sys.modules["frappe.model"] = model
    sys.modules["frappe.model.document"] = document
    return frappe


def import_doctype(module_name):
    sys.modules.pop(module_name, None)
    return __import__(module_name, fromlist=["*"])


@pytest.mark.parametrize("item_type, label", [
    ("Part", "Part"),
    ("OPL", "Job Type"),
    ("Expense", "Expense Type"),
])
def test_validate_items_invalid_reference(item_type, label):
    setup_frappe_stub()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    module = import_doctype(
        "car_workshop.car_workshop.doctype.workshop_purchase_order.workshop_purchase_order"
    )
    po = module.WorkshopPurchaseOrder()
    po.items = [
        types.SimpleNamespace(
            idx=1,
            item_type=item_type,
            reference_doctype="INVALID",
            quantity=1,
            rate=1,
            amount=1,
            billable=0,
        )
    ]
    with pytest.raises(Exception) as exc:
        po.validate_items()
    assert f"{label} INVALID does not exist" in str(exc.value)
