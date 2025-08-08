import sys
import types
from pathlib import Path

import pytest

# Stub Document and frappe modules
class Document:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

frappe_utils_stub = types.SimpleNamespace(
    flt=lambda x: float(x or 0),
    cint=lambda x: int(x or 0),
    getdate=lambda x: x,
    nowdate=lambda: "2024-01-01",
    add_days=lambda date, days: date,
    get_datetime=lambda: "2024-01-01 00:00:00",
)

frappe_stub = types.SimpleNamespace(
    _=lambda msg: msg,
    throw=lambda *a, **k: (_ for _ in ()).throw(Exception(a[0] if a else "")),
    utils=frappe_utils_stub,
    session=types.SimpleNamespace(user="test_user"),
    whitelist=lambda *a, **k: (lambda f: f),
)

frappe_stub.model = types.SimpleNamespace(document=types.SimpleNamespace(Document=Document))

# Register stubs
sys.modules['frappe'] = frappe_stub
sys.modules['frappe.model'] = frappe_stub.model
sys.modules['frappe.model.document'] = frappe_stub.model.document
sys.modules['frappe.utils'] = frappe_utils_stub
sys.modules['erpnext.accounts.general_ledger'] = types.SimpleNamespace(make_gl_entries=lambda *a, **k: None)
sys.modules['erpnext.accounts.utils'] = types.SimpleNamespace(get_account_currency=lambda *a, **k: None)
sys.modules['erpnext.accounts.party'] = types.SimpleNamespace(get_party_account=lambda *a, **k: None)
sys.modules['erpnext.controllers.accounts_controller'] = types.SimpleNamespace(AccountsController=Document)

# Ensure package root on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_workshop.car_workshop.doctype.work_order_billing.work_order_billing import WorkOrderBilling
from car_workshop.car_workshop.doctype.work_order_billing_return.work_order_billing_return import WorkOrderBillingReturn
from car_workshop.car_workshop.doctype.work_order_billing_cancellation.work_order_billing_cancellation import (
    WorkOrderBillingCancellation,
)


def test_process_returns_and_cancellations_sets_flags():
    return_item = WorkOrderBillingReturn(part_item="ITEM-1", quantity=1, rate=10)
    cancellation_item = WorkOrderBillingCancellation(job_type_item="JOB-1", amount=5)
    wob = WorkOrderBilling(return_items=[return_item], cancellation_items=[cancellation_item])
    wob.process_returns_and_cancellations()
    assert return_item.stock_adjusted
    assert return_item.credit_note_issued
    assert return_item.refund_processed
    assert return_item.additional_salary_reversed
    assert cancellation_item.debit_note_issued
    assert cancellation_item.refund_processed
    assert cancellation_item.additional_salary_reversed


def test_update_approval_fields_sets_audit_info():
    wob = WorkOrderBilling(approval_status="Approved")
    wob.update_approval_fields()
    assert wob.approved_by == "test_user"
    assert wob.approved_on == "2024-01-01 00:00:00"
