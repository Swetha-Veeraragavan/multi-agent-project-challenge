"""
Runs the two showcase scenarios end to end and writes trace files.

Usage:
    python run_demo.py                 # writes traces/trace_success.json
                                        # and traces/trace_edge_case.json
    python run_demo.py --interactive   # same, but the edge case pauses
                                        # for a real human on stdin
"""

import json
import sys
from pathlib import Path

from src.orchestrator import run_pipeline
from src.agents.human_checkpoint import interactive_reviewer_fn

DOCS_DIR = Path(__file__).parent / "data" / "documents"
TRACES_DIR = Path(__file__).parent / "traces"
TRACES_DIR.mkdir(exist_ok=True)


def load(doc_id: str) -> dict:
    return json.loads((DOCS_DIR / f"{doc_id}.json").read_text())


def run_success_scenario():
    """Clean contract, cap + notice window both present -> auto-approves, no human needed."""
    doc = load("CONTRACT-007")
    state = run_pipeline(doc["doc_id"], doc["text"], question="What is our liability exposure under this contract?")
    _write_trace("trace_success.json", doc, state)
    print(f"[success scenario] {doc['doc_id']} -> review_status="
          f"{state['final_result']['review_status']}")


def run_edge_case_scenario(interactive: bool = False):
    """Contract with no cap, no notice window -> should escalate and stop at the human checkpoint."""
    doc = load("CONTRACT-004")
    reviewer_fn = interactive_reviewer_fn if interactive else None
    state = run_pipeline(doc["doc_id"], doc["text"],
                          question="What is our liability exposure under this contract?",
                          reviewer_fn=reviewer_fn)
    _write_trace("trace_edge_case.json", doc, state)
    print(f"[edge case scenario] {doc['doc_id']} -> review_status="
          f"{state['final_result']['review_status']} "
          f"(escalated: {state.get('escalation') is not None})")


def _write_trace(filename: str, doc: dict, state: dict):
    trace = {
        "trace_id": state["trace_id"],
        "doc_id": doc["doc_id"],
        "doc_type_true": doc["doc_type_true"],
        "messages": state["messages"],
        "final_result": state["final_result"],
    }
    (TRACES_DIR / filename).write_text(json.dumps(trace, indent=2))


if __name__ == "__main__":
    interactive = "--interactive" in sys.argv
    run_success_scenario()
    run_edge_case_scenario(interactive=interactive)
    print(f"\nTraces written to {TRACES_DIR}/")
