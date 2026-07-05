"""
HumanReviewCheckpoint - the required human-in-the-loop stop.
"""

from src.schemas import AgentMessage, MessageType


def default_reviewer_fn(escalation_payload: dict) -> dict:
    flags = escalation_payload["flags"]
    if "no_liability_cap" in flags and "short_or_missing_notice_window" in flags:
        return {"decision": "REJECT", "note": "Contract needs a liability cap and a defined notice period before it can be filed. Sent back to vendor for redline."}
    if "root_cause_unresolved" in flags:
        return {"decision": "APPROVE_WITH_CONDITION", "note": "Approved for filing, but flagged for RCA follow-up in 10 business days per policy."}
    return {"decision": "APPROVE", "note": "Reviewed, no objection."}


def interactive_reviewer_fn(escalation_payload: dict) -> dict:
    print("\n=== HUMAN REVIEW REQUIRED ===")
    print(f"Document: {escalation_payload['doc_id']} ({escalation_payload['doc_type']})")
    print(f"Flags: {escalation_payload['flags']}")
    print(f"Risk score: {escalation_payload['risk_score']}")
    print(f"System recommendation: {escalation_payload['recommended_action']}")
    decision = input("Decision [APPROVE / APPROVE_WITH_CONDITION / REJECT]: ").strip().upper() or "APPROVE"
    note = input("Reviewer note: ").strip()
    return {"decision": decision, "note": note}


def run(trace_id: str, escalation_msg: AgentMessage, reviewer_fn=default_reviewer_fn) -> AgentMessage:
    decision = reviewer_fn(escalation_msg.payload)
    msg_type = MessageType.REJECTION if decision["decision"] == "REJECT" else MessageType.APPROVAL

    return AgentMessage(
        trace_id=trace_id,
        sender="HumanReviewCheckpoint",
        receiver="SummarizerQAAgent",
        msg_type=msg_type,
        payload={
            **escalation_msg.payload,
            "human_decision": decision["decision"],
            "human_note": decision["note"],
        },
    )
