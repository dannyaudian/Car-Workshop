from test_item_code_resolution import setup_frappe_stub, import_doctype


def test_get_work_order_parts_uses_part_detail():
    frappe = setup_frappe_stub()
    module = import_doctype(
        "car_workshop.car_workshop.doctype.workshop_material_issue.workshop_material_issue"
    )
    module.frappe = frappe
    parts = module.get_work_order_parts("WO-001")
    assert parts[0]["part"] == "PART-001"
    assert parts[0]["required_qty"] == 2
    assert parts[0]["consumed_qty"] == 1
    assert parts[0]["qty"] == 1

