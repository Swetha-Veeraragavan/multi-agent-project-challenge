"""
Message schema agents use to talk to each other.
"""

from __future__ import annotations
import uuid
import time
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    TASK = "task"
    RESULT = "result"
    ESCALATION = "escalation"
    APPROVAL = "approval"
    REJECTION = "rejection"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    INFO = "info"


class AgentMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    trace_id: str
    sender: str
    receiver: str
    msg_type: MessageType
    payload: dict[str, Any]
    confidence: Optional[float] = None
    timestamp: float = Field(default_factory=time.time)

    def summary(self) -> str:
        return f"[{self.sender} -> {self.receiver}] {self.msg_type.value} (conf={self.confidence})"


# example payloads
EXAMPLE_TASK_PAYLOAD = {
    "doc_id": "CONTRACT-004",
    "instruction": "extract_structured_fields",
    "doc_type": "vendor_contract",
}

EXAMPLE_ESCALATION_PAYLOAD = {
    "doc_id": "CONTRACT-004",
    "reason": "no_liability_cap_and_short_notice_window",
    "risk_score": 0.82,
    "fields_at_issue": ["liability_cap_usd", "termination_notice_days"],
    "recommended_action": "manual_legal_review",
}
