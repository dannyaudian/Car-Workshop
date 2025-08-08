import importlib
import os
import sys
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def setup_frappe_stub():
    """Create a minimal frappe stub with tracking for db.get_value calls."""
    frappe = types.ModuleType("frappe")
    frappe._ = lambda m: m

    def throw(msg):
        raise Exception(msg)

    frappe.throw = throw

    class DB:
        def __init__(self):
            self.calls = []

        def get_value(self, doctype, name, fieldname, *args, **kwargs):
            self.calls.append((doctype, name, fieldname))
            if doctype == "Part":
                return "ITEM-001"
            if doctype == "Bin":
                return types.SimpleNamespace(actual_qty=0, valuation_rate=0)
            return None

    frappe.db = DB()

    utils = types.ModuleType("frappe.utils")
    utils.__path__ = []  # allow submodule imports
    utils.flt = lambda v: float(v)
    utils.cint = lambda v: int(v)
    utils.getdate = lambda v: v
    utils.now_datetime = lambda: types.SimpleNamespace(strftime=lambda fmt: "00:00:00")
    utils.nowdate = lambda: "2024-01-01"
    utils.nowtime = lambda: "00:00:00"
    frappe.utils = utils

    background_jobs = types.ModuleType("frappe.utils.background_jobs")
    background_jobs.enqueue = lambda *args, **kwargs: None
    sys.modules["frappe.utils.background_jobs"] = background_jobs

    model = types.ModuleType("frappe.model")
    document = types.ModuleType("frappe.model.document")

    class Document:
        def __init__(self, *args, **kwargs):
            pass

        def append(self, *args, **kwargs):
            pass

    document.Document = Document
    model.document = document
    frappe.model = model

    def get_doc(doctype, name):
        if doctype == "Work Order":
            part = types.SimpleNamespace(
                consumed_qty=1, item_code="ITEM-001", part="PART-001", name="WO_ITEM"
            )
            return types.SimpleNamespace(part_detail=[part])
        if doctype == "Return Material":
            item = types.SimpleNamespace(item_code="ITEM-001", qty=1)
            return types.SimpleNamespace(items=[item])
        return types.SimpleNamespace()

    frappe.get_doc = get_doc
    def get_all(doctype, filters=None, fields=None, *args, **kwargs):
        frappe.get_all_calls.append((doctype, filters, fields))
        if doctype == "Part":
            return [types.SimpleNamespace(name="PART-001", item_code="ITEM-001")]
        if doctype == "Bin":
            return [types.SimpleNamespace(item_code="ITEM-001", actual_qty=0, valuation_rate=0)]
        return []

    frappe.get_all_calls = []
    frappe.get_all = get_all
    frappe.new_doc = lambda doctype: Document()
    frappe.msgprint = lambda msg: None
    frappe.whitelist = lambda *args, **kwargs: (lambda f: f)

    sys.modules["frappe"] = frappe
    sys.modules["frappe.utils"] = utils
    sys.modules["frappe.model"] = model
    sys.modules["frappe.model.document"] = document
    return frappe


def import_doctype(module_name):
    sys.modules.pop(module_name, None)
    return importlib.import_module(module_name)


def test_part_stock_opname_item_code():
    frappe = setup_frappe_stub()
    module = import_doctype(
        "car_workshop.car_workshop.doctype.part_stock_opname.part_stock_opname"
    )
    opname = module.PartStockOpname()
    opname.opname_items = [types.SimpleNamespace(part="PART-001", qty_counted=1, uom="Nos")]
    opname.warehouse = "WH"
    module.frappe = frappe
    opname.store_system_quantities()
    assert "item_code" in frappe.get_all_calls[0][2]


def test_return_material_item_code():
    frappe = setup_frappe_stub()
    module = import_doctype(
        "car_workshop.car_workshop.doctype.return_material.return_material"
    )
    rm = module.ReturnMaterial()
    rm.work_order = "WO-001"
    rm.items = [
        types.SimpleNamespace(
            part="PART-001",
            item_code=None,
            qty=1,
            work_order_item=None,
            amount=None,
            uom="Nos",
            valuation_rate=1,
        )
    ]
    rm.name = "RM-001"
    rm.is_new = lambda: True
    module.frappe = frappe
    rm.validate_qty_against_work_order()
    assert frappe.db.calls[0][2] == "item_code"


def test_part_stock_adjustment_item_code():
    frappe = setup_frappe_stub()
    module = import_doctype(
        "car_workshop.car_workshop.doctype.part_stock_adjustment.part_stock_adjustment"
    )
    psa = module.PartStockAdjustment()
    psa.adjustment_items = [types.SimpleNamespace(part="PART-001", item_code=None, difference=0)]
    module.frappe = frappe
    psa.make_stock_entries()
    assert frappe.db.calls[0][2] == "item_code"

