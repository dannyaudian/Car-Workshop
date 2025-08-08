import sys
import types
import importlib
from pathlib import Path

# Ensure package root on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def setup_frappe_stub():
    frappe = types.ModuleType("frappe")
    frappe._ = lambda m: m

    class DB:
        def get_value(self, doctype, name=None, fieldname=None, as_dict=False, **kwargs):
            if doctype == "Bin":
                return {"actual_qty": 5, "reserved_qty": 1, "valuation_rate": 10}
            if doctype == "Item" and fieldname == "stock_uom":
                return "Nos"
            return None

    frappe.db = DB()

    def get_doc(doctype, name):
        if doctype == "Work Order":
            part = types.SimpleNamespace(
                part="PART-001",
                part_name="Test Part",
                item_code="ITEM-001",
                consumed_qty=1,
                quantity=3,
                name="WO_PART_1",
            )
            return types.SimpleNamespace(part_detail=[part], set_warehouse="WH")
        return types.SimpleNamespace()

    frappe.get_doc = get_doc
    frappe.get_all = lambda *args, **kwargs: []
    utils = types.ModuleType("frappe.utils")
    utils.flt = float
    utils.cint = int
    utils.getdate = lambda v: v
    utils.nowdate = lambda: "2024-01-01"
    utils.nowtime = lambda: "00:00:00"
    frappe.utils = utils
    frappe.whitelist = lambda *args, **kwargs: (lambda f: f)

    sys.modules["frappe"] = frappe
    sys.modules["frappe.utils"] = utils
    model = types.ModuleType("frappe.model")
    document = types.ModuleType("frappe.model.document")
    class Document:
        pass
    document.Document = Document
    model.document = document
    sys.modules["frappe.model"] = model
    sys.modules["frappe.model.document"] = document
    erpnext = types.ModuleType("erpnext")
    stock = types.ModuleType("erpnext.stock")
    doctype = types.ModuleType("erpnext.stock.doctype")
    stock_entry = types.ModuleType("erpnext.stock.doctype.stock_entry")
    stock_entry_module = types.ModuleType("erpnext.stock.doctype.stock_entry.stock_entry")
    stock_entry_module.get_uom_details = lambda *args, **kwargs: None
    sys.modules["erpnext"] = erpnext
    sys.modules["erpnext.stock"] = stock
    sys.modules["erpnext.stock.doctype"] = doctype
    sys.modules["erpnext.stock.doctype.stock_entry"] = stock_entry
    sys.modules["erpnext.stock.doctype.stock_entry.stock_entry"] = stock_entry_module

    return frappe


def import_doctype(module_name):
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def test_get_work_order_parts_uses_part_detail():
    setup_frappe_stub()
    module = import_doctype(
        "car_workshop.car_workshop.doctype.workshop_material_issue.workshop_material_issue"
    )
    parts = module.get_work_order_parts("WO-001")
    assert parts[0]["required_qty"] == 3
    assert parts[0]["consumed_qty"] == 1
    assert parts[0]["qty"] == 2
