"""
IntakeClassifierAgent - first stop for a raw document. Classifies it into
one of the four known types, downstream agents key off this.
"""

import json
from src.schemas import AgentMessage, MessageType
from src.llm_client import call_llm

SYSTEM_PROMPT = """You classify enterprise documents into exactly one of:
vendor_contract, maintenance_sop, incident_report, service_email.
Respond ONLY with JSON: {"doc_type": "...", "confidence": 0.0-1.0}"""


def run(trace_id: str, doc_id: str, text: str) -> AgentMessage:
    raw = call_llm(SYSTEM_PROMPT, text, expect_json=True)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"doc_type": "unknown", "confidence": 0.0}

    return AgentMessage(
        trace_id=trace_id,
        sender="IntakeClassifierAgent",
        receiver="ExtractionAgent",
        msg_type=MessageType.RESULT,
        payload={"doc_id": doc_id, "doc_type": parsed["doc_type"]},
        confidence=parsed.get("confidence"),
    )
