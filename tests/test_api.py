import sys
import types
from pathlib import Path

# Create a stub frappe module
def identity_decorator(*args, **kwargs):
    def wrapper(fn):
        return fn
    return wrapper


frappe_stub = types.SimpleNamespace(
    db=types.SimpleNamespace(exists=lambda doctype, name: True),
    get_all=lambda *args, **kwargs: [],
    whitelist=identity_decorator,
    _=lambda msg: msg,
    throw=lambda msg: (_ for _ in ()).throw(Exception(msg)),
)

sys.modules['frappe'] = frappe_stub

# Ensure the package root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_workshop.car_workshop import api


def test_get_latest_vehicle_log_returns_first_log():
    frappe_stub.get_all = lambda *args, **kwargs: [{"fieldname": "mileage"}]
    assert api.get_latest_vehicle_log("CV-001") == {"fieldname": "mileage"}


def test_get_latest_vehicle_log_returns_none_when_no_logs():
    frappe_stub.get_all = lambda *args, **kwargs: []
    assert api.get_latest_vehicle_log("CV-001") is None

