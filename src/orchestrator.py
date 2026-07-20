"""
LangGraph wiring for the 4 agents

Went with LangGraph over CrewAI/AutoGen mainly for the human-in-the-loop
requirement
"""

from __future__ import annotations
import uuid
# from typing import TypedDict, Optional, Any
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.schemas import AgentMessage
from src.agents import classifier_agent, extraction_agent, risk_agent, human_checkpoint, summarizer_agent


class PipelineState(TypedDict, total=False):
    trace_id: str
    doc_id: str
    text: str
    question: Optional[str]
    doc_type: Optional[str]
    fields: Optional[dict]
    confidence: Optional[float]
    escalation: Optional[dict]
    upstream_for_summarizer: Optional[dict]
    final_result: Optional[dict]
    messages: list
    # reviewer_fn: Any


def _log(state: PipelineState, msg: AgentMessage) -> None:
    state.setdefault("messages", []).append(msg.model_dump(mode="json"))


def node_classify(state: PipelineState) -> PipelineState:
    msg = classifier_agent.run(state["trace_id"], state["doc_id"], state["text"])
    _log(state, msg)
    state["doc_type"] = msg.payload["doc_type"]
    return state


def node_extract(state: PipelineState) -> PipelineState:
    tool_msg, result_msg = extraction_agent.run(state["trace_id"], state["doc_id"], state["doc_type"], state["text"])
    _log(state, tool_msg)
    _log(state, result_msg)
    state["fields"] = result_msg.payload["fields"]
    state["confidence"] = result_msg.confidence
    return state


def node_risk(state: PipelineState) -> PipelineState:
    tool_msg, result_msg = risk_agent.run(state["trace_id"], state["doc_id"], state["doc_type"], state["fields"], state["confidence"])
    _log(state, tool_msg)
    _log(state, result_msg)
    if result_msg.msg_type.value == "escalation":
        state["escalation"] = result_msg.model_dump(mode="json")
        state["upstream_for_summarizer"] = None
    else:
        state["escalation"] = None
        state["upstream_for_summarizer"] = result_msg.model_dump(mode="json")
    return state


# def node_human_review(state: PipelineState) -> PipelineState:
#     escalation_msg = AgentMessage.model_validate(state["escalation"])
#     reviewer_fn = state.get("reviewer_fn") or human_checkpoint.default_reviewer_fn
#     result_msg = human_checkpoint.run(state["trace_id"], escalation_msg, reviewer_fn=reviewer_fn)
#     _log(state, result_msg)
#     state["upstream_for_summarizer"] = result_msg.model_dump(mode="json")
#     return state


def node_summarize(state: PipelineState) -> PipelineState:
    upstream_msg = AgentMessage.model_validate(state["upstream_for_summarizer"])
    result_msg = summarizer_agent.run(state["trace_id"], upstream_msg, state["text"], state.get("question"))
    _log(state, result_msg)
    state["final_result"] = result_msg.payload
    return state


def route_after_risk(state: PipelineState) -> str:
    return "human_review" if state.get("escalation") else "summarize"


def build_graph(reviewer_fn=None):
    resolved_reviewer_fn = reviewer_fn or human_checkpoint.default_reviewer_fn
    def node_human_review(state: PipelineState) -> PipelineState:
        escalation_msg = AgentMessage.model_validate(state["escalation"])
        result_msg = human_checkpoint.run(state["trace_id"], escalation_msg, reviewer_fn=resolved_reviewer_fn)
        _log(state, result_msg)
        state["upstream_for_summarizer"] = result_msg.model_dump(mode="json")
        return state
    
    graph = StateGraph(PipelineState)
    graph.add_node("classify", node_classify)
    graph.add_node("extract", node_extract)
    graph.add_node("risk_check", node_risk)
    graph.add_node("human_review", node_human_review)
    graph.add_node("summarize", node_summarize)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "extract")
    graph.add_edge("extract", "risk_check")
    graph.add_conditional_edges("risk_check", route_after_risk, {
        "human_review": "human_review",
        "summarize": "summarize",
    })
    graph.add_edge("human_review", "summarize")
    graph.add_edge("summarize", END)

    return graph.compile(checkpointer=MemorySaver(), interrupt_before=["human_review"])


def run_pipeline(doc_id: str, text: str, question: str | None = None, reviewer_fn=None) -> PipelineState:
    """Runs the pipeline end to end, auto-resolving any interrupt via reviewer_fn."""
    graph = build_graph(reviewer_fn=reviewer_fn)
    trace_id = str(uuid.uuid4())[:8]
    initial_state: PipelineState = {
        "trace_id": trace_id,
        "doc_id": doc_id,
        "text": text,
        "question": question,
        "messages": [],
    }
    config = {"configurable": {"thread_id": trace_id}}

    state = graph.invoke(initial_state, config=config)
    snapshot = graph.get_state(config)
    if snapshot.next:  # paused before a node, resume it
        state = graph.invoke(None, config=config)

    return state
