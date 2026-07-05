"""
Wraps LLM calls behind one function so agents don't care whether they're
hitting a real model or the mock. Real mode = OpenAI, mock mode = simple
keyword rules. Mock is the default so the whole thing runs without an API
key.
"""

from __future__ import annotations
import os
import re
import json

MODE = "real" if os.environ.get("OPENAI_API_KEY") else "mock"


def call_llm(system_prompt: str, user_prompt: str, expect_json: bool = False) -> str:
    if MODE == "real":
        return _call_real(system_prompt, user_prompt, expect_json)
    return _call_mock(system_prompt, user_prompt, expect_json)


def _call_real(system_prompt: str, user_prompt: str, expect_json: bool) -> str:
    from openai import OpenAI

    client = OpenAI()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=800,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return resp.choices[0].message.content


def _call_mock(system_prompt: str, user_prompt: str, expect_json: bool) -> str:
    # route on what the prompt is asking for, keeps agent code identical either way
    if "classify" in system_prompt.lower():
        return _mock_classify(user_prompt)
    if "summar" in system_prompt.lower():
        return _mock_summarize(user_prompt)
    return "I don't have a mock handler for this prompt type."


def _mock_classify(text: str) -> str:
    text_l = text.lower()
    scores = {
        "vendor_contract": sum(k in text_l for k in ["agreement", "vendor", "liability", "governing law", "term"]),
        "maintenance_sop": sum(k in text_l for k in ["standard operating procedure", "ppe", "hazard", "lockout", "step "]),
        "incident_report": sum(k in text_l for k in ["incident report", "root cause", "downtime", "severity", "corrective action"]),
        "service_email": sum(k in text_l for k in ["subject:", "from:", "hi team", "thanks,", "please advise"]),
    }
    doc_type = max(scores, key=scores.get)
    total = sum(scores.values()) or 1
    confidence = round(scores[doc_type] / total, 2)
    return json.dumps({"doc_type": doc_type, "confidence": max(confidence, 0.55)})


def _mock_summarize(payload_text: str) -> str:
    # crude extractive summary: lead sentence + densest sentence
    sentences = re.split(r"(?<=[.!?])\s+", payload_text.strip())
    sentences = [s for s in sentences if len(s) > 20]
    if not sentences:
        return "No summarizable content."
    lead = sentences[0]
    dense = max(sentences, key=lambda s: len(re.findall(r"\b\w+\b", s)))
    if dense == lead and len(sentences) > 1:
        dense = sentences[1]
    return f"{lead} {dense}".strip()
