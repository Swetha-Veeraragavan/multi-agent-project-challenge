"""
SummarizerQAAgent - last node. Only ever sees a doc that's been approved
(auto or human), produces a stakeholder summary and optionally answers a
question about it.
"""

from src.schemas import AgentMessage, MessageType
from src.llm_client import call_llm

SYSTEM_PROMPT = "Summarize this enterprise document for a busy stakeholder in 2-3 sentences."


def run(trace_id: str, upstream_msg: AgentMessage, original_text: str, question: str | None = None) -> AgentMessage:
    summary = call_llm(SYSTEM_PROMPT, original_text)

    payload = {
        "doc_id": upstream_msg.payload["doc_id"],
        "doc_type": upstream_msg.payload["doc_type"],
        "fields": upstream_msg.payload.get("fields", {}),
        "summary": summary,
        "review_status": upstream_msg.payload.get("human_decision", "AUTO_APPROVED"),
    }
    if upstream_msg.payload.get("human_note"):
        payload["review_note"] = upstream_msg.payload["human_note"]

    if question:
        payload["question"] = question
        payload["answer"] = _answer(question, payload["fields"], payload)

    return AgentMessage(
        trace_id=trace_id,
        sender="SummarizerQAAgent",
        receiver="OUTPUT",
        msg_type=MessageType.RESULT,
        payload=payload,
    )


def _answer(question: str, fields: dict, payload: dict) -> str:
    q = question.lower()
    if "liability" in q or "exposure" in q:
        cap = fields.get("liability_cap_usd")
        return (f"No cap is specified in the extracted terms -- exposure is uncapped, "
                f"which is why this was flagged: {payload.get('review_note', '')}") if not cap else \
               f"Liability is capped at ${cap:,} per twelve-month period per the extracted terms."
    if "downtime" in q:
        return f"Recorded downtime for this incident was {fields.get('downtime_hours', 'unknown')} hours."
    if "hazard" in q or "ppe" in q:
        return f"Hazard level: {fields.get('hazard_level', 'unknown')}. Required PPE: {fields.get('required_ppe', 'unknown')}."
    return "This question isn't covered by the fields this pipeline currently extracts."
