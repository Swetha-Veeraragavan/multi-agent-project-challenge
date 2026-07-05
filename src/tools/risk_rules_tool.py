"""
policy_rules_db tool - called by RiskComplianceAgent.

Stands in for a real policy/compliance table (would be a DB row in prod).
Kept separate from the extraction tool since thresholds change on a
business cadence, not a code-deploy cadence.
"""

POLICY_THRESHOLDS = {
    "min_extraction_confidence": 0.6,
    "contract_liability_cap_required_above_usd": 0,
    "contract_min_notice_days": 30,
    "incident_downtime_hours_escalation": 24.0,
    "incident_severity_escalation": {"high", "critical"},
    "sop_hazard_requires_review": {"high"},
}


def get_thresholds() -> dict:
    return POLICY_THRESHOLDS


def evaluate_risk(doc_type: str, fields: dict, confidence: float) -> dict:
    """Returns {risk_score, flags, escalate}."""
    thresholds = get_thresholds()
    flags = []

    if confidence < thresholds["min_extraction_confidence"]:
        flags.append(f"low_extraction_confidence({confidence})")

    if doc_type == "vendor_contract":
        if not fields.get("liability_cap_usd"):
            flags.append("no_liability_cap")
        notice = fields.get("termination_notice_days")
        if notice is None or notice < thresholds["contract_min_notice_days"]:
            flags.append("short_or_missing_notice_window")
        if fields.get("auto_renewal") and (notice is None):
            flags.append("auto_renewal_with_no_exit_clause")

    elif doc_type == "incident_report":
        if fields.get("downtime_hours") and fields["downtime_hours"] >= thresholds["incident_downtime_hours_escalation"]:
            flags.append("extended_downtime")
        if fields.get("severity") in thresholds["incident_severity_escalation"]:
            flags.append("high_severity")
        if fields.get("root_cause_identified") is False:
            flags.append("root_cause_unresolved")

    elif doc_type == "maintenance_sop":
        if fields.get("hazard_level") in thresholds["sop_hazard_requires_review"]:
            flags.append("high_hazard_procedure")

    elif doc_type == "service_email":
        if fields.get("urgency") == "urgent":
            flags.append("urgent_customer_request")

    risk_score = min(1.0, 0.2 * len(flags) + (0.3 if confidence < thresholds["min_extraction_confidence"] else 0))
    escalate = len(flags) > 0
    return {"risk_score": round(risk_score, 2), "flags": flags, "escalate": escalate}
