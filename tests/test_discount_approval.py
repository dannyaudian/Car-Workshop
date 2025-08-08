import sys
import types
from pathlib import Path

import pytest

class Document:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

# Stubs
frappe_utils_stub = types.SimpleNamespace(
    flt=lambda x: float(x or 0),
    cint=lambda x: int(x or 0),
    getdate=lambda x: x,
    nowdate=lambda: "2024-01-01",
    add_days=lambda date, days: date,
    get_datetime=lambda: "2024-01-01 00:00:00",
)

def _throw(msg):
    raise Exception(msg)

settings = {
    "discount_approval_threshold": 50,
    "discount_approver_roles": "Accountant",
}

frappe_stub = types.SimpleNamespace(
    _=lambda msg: msg,
    throw=_throw,
    utils=frappe_utils_stub,
    session=types.SimpleNamespace(user="test_user"),
    db=types.SimpleNamespace(get_single_value=lambda doctype, field: settings.get(field)),
    get_roles=lambda user=None: ["Workshop Manager"],
    whitelist=lambda *a, **k: (lambda f: f),
)

frappe_stub.model = types.SimpleNamespace(document=types.SimpleNamespace(Document=Document))

# Register modules
sys.modules['frappe'] = frappe_stub
sys.modules['frappe.model'] = frappe_stub.model
sys.modules['frappe.model.document'] = frappe_stub.model.document
sys.modules['frappe.utils'] = frappe_utils_stub
sys.modules['erpnext.accounts.general_ledger'] = types.SimpleNamespace(make_gl_entries=lambda *a, **k: None)
sys.modules['erpnext.accounts.utils'] = types.SimpleNamespace(get_account_currency=lambda *a, **k: None)
sys.modules['erpnext.accounts.party'] = types.SimpleNamespace(get_party_account=lambda *a, **k: None)
sys.modules['erpnext.controllers.accounts_controller'] = types.SimpleNamespace(AccountsController=Document)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_workshop.car_workshop.doctype.work_order_billing.work_order_billing import WorkOrderBilling

def test_discount_requires_approval_role_and_status():
    wob = WorkOrderBilling(discount_amount=100, approval_status="Pending Approval")
    with pytest.raises(Exception):
        wob.validate_discount_approval()

    frappe_stub.get_roles = lambda user=None: ["Accountant"]
    with pytest.raises(Exception):
        wob.validate_discount_approval()

    wob.approval_status = "Approved"
    wob.validate_discount_approval()


def test_record_status_history_logs_user_and_timestamp():
    messages = []
    wob = WorkOrderBilling(status="Pending Payment")
    wob.add_comment = lambda typ, msg: messages.append(msg)
    wob.record_status_history()
    assert "Pending Payment" in messages[0]
    assert "test_user" in messages[0]
    assert "2024-01-01 00:00:00" in messages[0]
