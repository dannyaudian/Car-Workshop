import sys
import types
from pathlib import Path
import pytest

# Stub Frappe modules and Document class
class Document:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

frappe_utils_stub = types.SimpleNamespace(flt=lambda x: float(x or 0))

frappe_stub = types.SimpleNamespace(
    _=lambda msg: msg,
    throw=lambda *args, **kwargs: (_ for _ in ()).throw(Exception(args[0] if args else "")),
    utils=frappe_utils_stub,
)

frappe_stub.model = types.SimpleNamespace(
    document=types.SimpleNamespace(Document=Document)
)

# Register stubs in sys.modules
sys.modules['frappe'] = frappe_stub
sys.modules['frappe.model'] = frappe_stub.model
sys.modules['frappe.model.document'] = frappe_stub.model.document
sys.modules['frappe.utils'] = frappe_utils_stub

# Ensure the package root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_workshop.car_workshop.doctype.work_order_part.work_order_part import WorkOrderPart


def test_calculate_amount_succeeds_with_positive_values():
    part = WorkOrderPart(quantity=2, rate=5)
    part.calculate_amount()
    assert part.amount == 10


def test_calculate_amount_raises_for_non_positive_quantity():
    part = WorkOrderPart(quantity=0, rate=5)
    with pytest.raises(Exception):
        part.calculate_amount()


def test_calculate_amount_raises_for_non_positive_rate():
    part = WorkOrderPart(quantity=1, rate=0)
    with pytest.raises(Exception):
        part.calculate_amount()

