"""
RiskComplianceAgent - the decision point. 
"""

from src.schemas import AgentMessage, MessageType
from src.tools import risk_rules_tool


def run(trace_id: str, doc_id: str, doc_type: str, fields: dict, confidence: float) -> tuple[AgentMessage, AgentMessage]:
    tool_call_msg = AgentMessage(
        trace_id=trace_id,
        sender="RiskComplianceAgent",
        receiver="tool:policy_rules_db",
        msg_type=MessageType.TOOL_CALL,
        payload={"doc_id": doc_id, "doc_type": doc_type},
    )

    risk = risk_rules_tool.evaluate_risk(doc_type, fields, confidence)

    if risk["escalate"]:
        result_msg = AgentMessage(
            trace_id=trace_id,
            sender="RiskComplianceAgent",
            receiver="HumanReviewCheckpoint",
            msg_type=MessageType.ESCALATION,
            payload={
                "doc_id": doc_id,
                "doc_type": doc_type,
                "fields": fields,
                "flags": risk["flags"],
                "risk_score": risk["risk_score"],
                "recommended_action": _recommend(risk["flags"]),
            },
            confidence=confidence,
        )
    else:
        result_msg = AgentMessage(
            trace_id=trace_id,
            sender="RiskComplianceAgent",
            receiver="SummarizerQAAgent",
            msg_type=MessageType.APPROVAL,
            payload={"doc_id": doc_id, "doc_type": doc_type, "fields": fields, "risk_score": risk["risk_score"]},
            confidence=confidence,
        )
    return tool_call_msg, result_msg


def _recommend(flags: list[str]) -> str:
    if any("liability" in f or "notice" in f for f in flags):
        return "route_to_legal_review"
    if "root_cause_unresolved" in flags or "extended_downtime" in flags:
        return "route_to_reliability_engineer"
    if "high_hazard_procedure" in flags:
        return "route_to_ehs_reviewer"
    if "urgent_customer_request" in flags:
        return "route_to_account_manager"
    return "route_to_general_reviewer"
