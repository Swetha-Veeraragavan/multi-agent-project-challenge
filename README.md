# Document Flow - Multi-Agent Enterprise Document Intelligence

**AI/ML Hiring Challenge — Track A (Agentic/Multi-Agent AI) × Scenario S2 (Gen AI for Enterprise Documents)**

## Problem

A mid-size industrial equipment operator (rotating machinery, field service, vendor
contracts — deliberately close to Avathon's own domain) has four kinds of documents piling
up faster than anyone can read them: **vendor/maintenance contracts**, **maintenance SOPs**,
**incident reports**, and **plant-manager emails**. Someone needs to classify them, pull out
the fields that actually matter (liability caps, hazard levels, downtime hours, urgency),
flag the risky ones for a human, and produce a stakeholder-ready summary — without a human
reading every single document end to end, but *also* without an LLM unilaterally deciding
that a contract with no liability cap is fine to file.

## Why this is an agentic problem, not a single prompt

A single "read this document and tell me what's important" prompt can't:
- Apply different, non-negotiable business rules per document type (a missing liability cap
  is illegal to auto-approve; a missing PPE line in an SOP is a safety issue, not a legal one)
- Stop and wait for a human decision partway through, then resume with that decision baked
  into the final output
- Give you an audit trail of *why* something was escalated, in a format compliance can
  actually read

That's a decomposition problem (intake → extract → apply policy → maybe pause for a human →
summarize), which is what multi-agent orchestration is for.

## Architecture

```
 raw document
      │
      ▼
┌─────────────────────┐
│ IntakeClassifierAgent│  classifies: contract / SOP / incident / email
└─────────┬────────────┘
          ▼
┌─────────────────────┐   tool: structured_extractor
│  ExtractionAgent     │──────────────────────────────►  type-specific fields + confidence
└─────────┬────────────┘
          ▼
┌─────────────────────┐   tool: policy_rules_db
│ RiskComplianceAgent  │──────────────────────────────►  risk_score, flags, escalate?
└─────────┬────────────┘
          │
   escalate?  ──── no ───────────────────────┐
          │ yes                              │
          ▼                                  │
┌─────────────────────┐                      │
│ HumanReviewCheckpoint│  ← graph PAUSES here│
│  (interrupt_before)  │  (real human, or    │
└─────────┬────────────┘   stand-in reviewer)│
          │                                  │
          ▼                                  ▼
┌──────────────────────────────────────────────┐
│           SummarizerQAAgent                   │  final summary + Q&A
└────────────────────────────────────────────────┘
```

Four agents with distinct, single-purpose roles + one hard human-in-the-loop checkpoint,
orchestrated with **LangGraph** (`src/orchestrator.py`), which gives native
`interrupt_before` support for the checkpoint and a typed, inspectable state object at every
node — see the orchestrator's module docstring for the full comparison against
CrewAI/AutoGen.

## Message schema

Every hop between nodes is a serialized `AgentMessage` (`src/schemas.py`):

```python
class AgentMessage(BaseModel):
    message_id: str
    trace_id: str
    sender: str
    receiver: str
    msg_type: MessageType 
    payload: dict
    confidence: float | None
    timestamp: float
```

Example escalation payload (`RiskComplianceAgent` → `HumanReviewCheckpoint`):
```json
{
  "doc_id": "CONTRACT-004",
  "doc_type": "vendor_contract",
  "flags": ["no_liability_cap", "short_or_missing_notice_window", "auto_renewal_with_no_exit_clause"],
  "risk_score": 0.6,
  "recommended_action": "route_to_legal_review"
}
```

## Repo layout

```
data/
  generate_synthetic_data.py   # synthetic doc generator (49 docs, 4 types)
  documents/*.json             # generated docs + ground truth
  manifest.json
src/
  schemas.py                   # AgentMessage + MessageType
  llm_client.py                # real (OpenAI) / mock LLM backend switch
  orchestrator.py              # LangGraph StateGraph, routing, HITL interrupt
  evaluate.py                  # classification + extraction + escalation eval
  agents/
    classifier_agent.py
    extraction_agent.py
    risk_agent.py
    human_checkpoint.py
    summarizer_agent.py
  tools/
    extraction_tool.py         # structured_extractor tool
    risk_rules_tool.py         # policy_rules_db tool
traces/
  trace_success.json           # end-to-end happy path
  trace_edge_case.json         # end-to-end escalation + human rejection
results/
  eval_results.json            # full evaluation output
write-up/
  writeup.doc
run_demo.py                    # produces the two trace files above
```

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
# generate the input docs
python data/generate_synthetic_data.py     
```

## Reproducing all results

```bash
python run_demo.py

```
The near-perfect scores are a direct consequence of evaluating rule-based extraction against
templated synthetic data generated by the same author, this is flagged, not hidden, and
discussed at length in the write-up along with a genuine failure mode we found in the
`urgency` field. See `write-up/writeup.doc`, Section 3, and `results/eval_results.json` for
the row-level data.

