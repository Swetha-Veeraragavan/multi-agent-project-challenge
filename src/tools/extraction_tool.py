"""
structured_extractor tool - called by ExtractionAgent.

Regex-based instead of an LLM call on purpose: these docs are templated
enough that regex is more reliable and way more auditable than asking a
model to pull out a dollar figure and hoping it doesn't hallucinate one.

Returns (fields, confidence). confidence = fraction of expected fields
that matched a known pattern, used later by the risk agent.
"""

import re
from typing import Any


def extract(doc_type: str, text: str) -> tuple[dict[str, Any], float]:
    if doc_type == "vendor_contract":
        return _extract_contract(text)
    if doc_type == "maintenance_sop":
        return _extract_sop(text)
    if doc_type == "incident_report":
        return _extract_incident(text)
    if doc_type == "service_email":
        return _extract_email(text)
    return {}, 0.0


def _extract_contract(text: str) -> tuple[dict, float]:
    fields, hits = {}, []

    m = re.search(r"between Meridian Industrial Operations.*?and ([A-Za-z0-9 .&\-]+?)\s*\(\"Vendor\"\)", text, re.S)
    fields["counterparty"] = m.group(1).strip() if m else None
    hits.append(1.0 if m else 0.0)

    m = re.search(r"as of (\d{4}-\d{2}-\d{2})", text)
    fields["effective_date"] = m.group(1) if m else None
    hits.append(1.0 if m else 0.0)

    m = re.search(r"aggregate liability.*?not exceed \$([\d,]+)", text)
    fields["liability_cap_usd"] = int(m.group(1).replace(",", "")) if m else None
    hits.append(1.0 if m else 0.0)

    fields["auto_renewal"] = "automatically renew" in text
    hits.append(1.0)

    m = re.search(r"terminate this Agreement with (\d+) days", text)
    fields["termination_notice_days"] = int(m.group(1)) if m else None
    hits.append(1.0 if m else 0.0)

    confidence = round(sum(hits) / len(hits), 2)
    return fields, confidence


def _extract_sop(text: str) -> tuple[dict, float]:
    fields, hits = {}, []

    m = re.search(r"Equipment: (.+)", text)
    fields["equipment"] = m.group(1).strip() if m else None
    hits.append(1.0 if m else 0.0)

    m = re.search(r"Hazard Level: (\w+)", text)
    fields["hazard_level"] = m.group(1).lower() if m else None
    hits.append(1.0 if m else 0.0)

    m = re.search(r"wear the following before beginning work: (.+?)\.", text)
    fields["required_ppe"] = m.group(1).strip() if m else None
    hits.append(1.0 if m else 0.0)

    steps = re.findall(r"Step \d+:", text)
    fields["step_count"] = len(steps) if steps else None
    hits.append(1.0 if steps else 0.0)

    confidence = round(sum(hits) / len(hits), 2)
    return fields, confidence


def _extract_incident(text: str) -> tuple[dict, float]:
    fields, hits = {}, []

    m = re.search(r"Asset: (.+)", text)
    fields["asset"] = m.group(1).strip() if m else None
    hits.append(1.0 if m else 0.0)

    m = re.search(r"Facility: (.+)", text)
    fields["facility"] = m.group(1).strip() if m else None
    hits.append(1.0 if m else 0.0)

    m = re.search(r"Severity: (\w+)", text)
    fields["severity"] = m.group(1).lower() if m else None
    hits.append(1.0 if m else 0.0)

    m = re.search(r"Estimated downtime: ([\d.]+) hours", text)
    fields["downtime_hours"] = float(m.group(1)) if m else None
    hits.append(1.0 if m else 0.0)

    fields["root_cause_identified"] = "still open" not in text and "Root cause was determined" in text
    hits.append(1.0)

    confidence = round(sum(hits) / len(hits), 2)
    return fields, confidence


def _extract_email(text: str) -> tuple[dict, float]:
    fields, hits = {}, []

    m = re.search(r"at (Plant \d+ - \w+)", text)
    fields["facility"] = m.group(1) if m else None
    hits.append(1.0 if m else 0.0)

    text_l = text.lower()
    if "urgent" in text_l:
        fields["urgency"] = "urgent"
    elif "as soon as possible" in text_l or "affect production" in text_l:
        fields["urgency"] = "high"
    else:
        fields["urgency"] = "normal"
    hits.append(0.5)  # weaker heuristic than the others, so lower confidence weight

    m = re.search(r"Need help - (.+)", text)
    fields["requested_action"] = m.group(1).strip() if m else None
    hits.append(1.0 if m else 0.0)

    confidence = round(sum(hits) / len(hits), 2)
    return fields, confidence
