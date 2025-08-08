import sys
import types
from pathlib import Path

# Create a stub frappe module with required attributes
class Document:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

frappe_stub = types.SimpleNamespace(
    db=types.SimpleNamespace(get_value=lambda *args, **kwargs: 0),
    throw=lambda *args, **kwargs: (_ for _ in ()).throw(Exception(args[0] if args else "")),
)

# Attach the Document class to frappe.model.document
frappe_stub.model = types.SimpleNamespace(
    document=types.SimpleNamespace(Document=Document)
)

# Register the stub in sys.modules
sys.modules['frappe'] = frappe_stub
sys.modules['frappe.model'] = frappe_stub.model
sys.modules['frappe.model.document'] = frappe_stub.model.document

# Ensure the package root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_workshop.car_workshop.doctype.part.part import Part


def test_update_price_from_item_stores_zero():
    part = Part(item_code="ITEM-001", current_price=None, compatibility=[])
    part.update_price_from_item()
    assert part.current_price == 0

