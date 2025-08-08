"""Utility functions for incentive calculations and processing.

This module provides helpers to compute incentives based on several
methods such as percentage, fixed amount, tiered thresholds and
team-based distribution. It also exposes a hook that can be attached to
``Work Order Billing`` submission to automatically create ``Additional
Salary`` records and log incentive history.
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence, Union

try:  # pragma: no cover - frappe not required for pure calculations
    import frappe  # type: ignore
except Exception:  # pragma: no cover - fallback for tests
    frappe = None  # type: ignore


def calculate_incentive(
    amount: float,
    config: Dict[str, Union[str, float, Sequence[Dict[str, float]]]],
    team_members: Optional[Sequence[str]] = None,
) -> Union[float, Dict[str, float]]:
    """Return incentive amount based on configuration.

    Args:
        amount: Base amount to calculate incentive from.
        config: Mapping containing ``incentive_type`` and any supporting
            configuration such as ``rate`` or ``tiers``.
        team_members: Optional sequence of employee ids used for
            team-based incentives.

    Returns:
        A single float for most incentive types.  For team-based
        incentives a mapping of employee to incentive amount is returned
        so the caller can create a record for each member.
    """

    incentive_type = (config.get("incentive_type") or "").lower()
    rate = float(config.get("rate") or 0)

    if incentive_type == "percentage":
        return amount * rate / 100.0

    if incentive_type == "fixed":
        return rate

    if incentive_type == "tiered":
        tiers: Sequence[Dict[str, float]] = config.get("tiers", [])  # type: ignore[assignment]
        applicable_rate = 0.0
        for tier in sorted(tiers, key=lambda x: x.get("threshold", 0)):
            if amount >= float(tier.get("threshold", 0)):
                applicable_rate = float(tier.get("rate", 0))
            else:
                break
        return amount * applicable_rate / 100.0

    if incentive_type == "team-based":
        base = amount * rate / 100.0
        members = list(team_members or [])
        if not members:
            return base
        share = base / len(members)
        return {m: share for m in members}

    return 0.0


def create_additional_salary(
    employee: str,
    amount: float,
    salary_component: str,
    reference_doctype: str,
    reference_name: str,
) -> str:
    """Create an ``Additional Salary`` document for a given employee.

    The document is left in draft state so that it can go through the
    standard approval workflow.
    """

    doc = frappe.new_doc("Additional Salary")
    doc.employee = employee
    doc.salary_component = salary_component
    doc.amount = amount
    doc.reference_doctype = reference_doctype
    doc.reference_name = reference_name
    doc.flags.ignore_permissions = True
    doc.insert()
    return doc.name


def log_incentive(
    employee: str,
    amount: float,
    salary_component: str,
    work_order: str,
    work_order_billing: str,
    additional_salary: str,
) -> None:
    """Insert a record into ``Incentive History`` for audit trail."""

    history = frappe.new_doc("Incentive History")
    history.employee = employee
    history.work_order = work_order
    history.work_order_billing = work_order_billing
    history.salary_component = salary_component
    history.amount = amount
    history.additional_salary = additional_salary
    history.flags.ignore_permissions = True
    history.insert()


def process_work_order_billing(doc, method=None):  # pragma: no cover - Frappe hook
    """Hook to generate incentives when a ``Work Order Billing`` is submitted."""

    for item in getattr(doc, "job_type_items", []):
        configs = frappe.get_all(
            "Incentive Configuration",
            filters={"job_type": item.job_type},
            limit=1,
        )
        if not configs:
            continue
        config_doc = frappe.get_doc("Incentive Configuration", configs[0].name)
        incentive = calculate_incentive(
            amount=float(getattr(item, "amount", 0)),
            config={
                "incentive_type": config_doc.incentive_type,
                "rate": config_doc.rate,
                "tiers": [
                    {"threshold": t.threshold, "rate": t.rate}
                    for t in getattr(config_doc, "tiers", [])
                ],
            },
        )
        salary_component = config_doc.salary_component

        if isinstance(incentive, dict):
            distribution = incentive
        else:
            # Default to service advisor on the linked work order
            work_order = frappe.get_value("Work Order", doc.work_order, "service_advisor")
            if not work_order:
                continue
            distribution = {work_order: incentive}

        for employee, amount in distribution.items():
            add_sal = create_additional_salary(
                employee=employee,
                amount=amount,
                salary_component=salary_component,
                reference_doctype=doc.doctype,
                reference_name=doc.name,
            )
            log_incentive(
                employee=employee,
                amount=amount,
                salary_component=salary_component,
                work_order=doc.work_order,
                work_order_billing=doc.name,
                additional_salary=add_sal,
            )

