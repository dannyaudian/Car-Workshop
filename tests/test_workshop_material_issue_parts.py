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
            if doctype == "Work Order" and fieldname == "project":
                return None
            return None

        def get_single_value(self, doctype, fieldname):
            if doctype == "Workshop Settings" and fieldname == "company":
                return "Test Company"
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
    frappe.msgprint = lambda *args, **kwargs: None
    frappe.get_desk_link = lambda doctype, name: name
    frappe.log_error = lambda *args, **kwargs: None
    frappe.defaults = types.SimpleNamespace(get_user_default=lambda key: "Test Company")

    class StockEntryStub:
        def __init__(self):
            self.items = []
            self.flags = types.SimpleNamespace()
            self.name = "SE-TEST"
            self.submitted = False

        def append(self, table, values):
            getattr(self, table).append(values)

        def set_missing_values(self):
            pass

        def save(self):
            pass

        def submit(self):
            self.submitted = True

    created_docs = []

    def new_doc(doctype):
        doc = StockEntryStub()
        created_docs.append(doc)
        return doc

    frappe.new_doc = new_doc
    frappe.created_docs = created_docs

    sys.modules["frappe"] = frappe
    sys.modules["frappe.utils"] = utils
    model = types.ModuleType("frappe.model")
    document = types.ModuleType("frappe.model.document")

    class Document:
        def db_set(self, fieldname, value):
            setattr(self, fieldname, value)

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


def test_stock_entry_submission_without_target_warehouse():
    frappe = setup_frappe_stub()
    module = import_doctype(
        "car_workshop.car_workshop.doctype.workshop_material_issue.workshop_material_issue"
    )
    wmi = module.WorkshopMaterialIssue()
    wmi.name = "WMI-001"
    wmi.posting_date = "2024-01-01"
    wmi.work_order = "WO-001"
    wmi.set_warehouse = "WH"
    item = types.SimpleNamespace(
        item_code="ITEM-001",
        qty=1,
        uom="Nos",
        rate=10,
        amount=10,
        serial_no=None,
        batch_no=None,
        description="Test Item",
    )
    wmi.items = [item]
    wmi.remarks = ""
    wmi.create_stock_entry()
    se = frappe.created_docs[0]
    assert se.to_warehouse is None
    assert all("t_warehouse" not in d for d in se.items)
    assert se.submitted
