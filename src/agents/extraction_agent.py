"""
ExtractionAgent - calls the structured_extractor tool to pull type-specific
fields out of a classified doc. The tool_call message gets logged too so
the tool use is visible in the trace, not just its result.
"""

from src.schemas import AgentMessage, MessageType
from src.tools import extraction_tool


def run(trace_id: str, doc_id: str, doc_type: str, text: str) -> tuple[AgentMessage, AgentMessage]:
    tool_call_msg = AgentMessage(
        trace_id=trace_id,
        sender="ExtractionAgent",
        receiver="tool:structured_extractor",
        msg_type=MessageType.TOOL_CALL,
        payload={"doc_id": doc_id, "doc_type": doc_type},
    )

    fields, confidence = extraction_tool.extract(doc_type, text)

    result_msg = AgentMessage(
        trace_id=trace_id,
        sender="ExtractionAgent",
        receiver="RiskComplianceAgent",
        msg_type=MessageType.RESULT,
        payload={"doc_id": doc_id, "doc_type": doc_type, "fields": fields},
        confidence=confidence,
    )
    return tool_call_msg, result_msg
