"""
Runs classify+extract over every synthetic doc and reports:
  1. Classification accuracy
  2. Extraction field accuracy per doc type
  3. Escalation precision/recall vs. what should actually be escalated

Runs in mock mode by default (no API key needed) so results are
reproducible for a reviewer.
"""

import json
import glob
from collections import defaultdict

from src.agents import classifier_agent
from src.tools import extraction_tool, risk_rules_tool

DOCS = sorted(glob.glob("data/documents/*.json"))


def should_escalate_gt(doc_type: str, gt: dict) -> bool:
    if doc_type == "vendor_contract":
        return (not gt["liability_cap_usd"]) or (gt["termination_notice_days"] is None or gt["termination_notice_days"] < 30)
    if doc_type == "incident_report":
        return gt["downtime_hours"] >= 24.0 or gt["severity"] in ("high", "critical") or not gt["root_cause_identified"]
    if doc_type == "maintenance_sop":
        return gt["hazard_level"] == "high"
    if doc_type == "service_email":
        return gt["urgency"] == "urgent"
    return False


def main():
    class_correct = 0
    field_hits = defaultdict(lambda: [0, 0])  # field -> [correct, total]
    escalation_tp, escalation_fp, escalation_fn, escalation_tn = 0, 0, 0, 0

    rows = []
    for path in DOCS:
        d = json.load(open(path))
        text, true_type, gt = d["text"], d["doc_type_true"], d["ground_truth"]

        clf_msg = classifier_agent.run("eval", d["doc_id"], text)
        pred_type = clf_msg.payload["doc_type"]
        correct_class = pred_type == true_type
        class_correct += int(correct_class)

        fields, confidence = extraction_tool.extract(true_type, text) 
        for k, gt_v in gt.items():
            if k not in fields:
                continue
            field_hits[k][1] += 1
            if fields[k] == gt_v:
                field_hits[k][0] += 1

        risk = risk_rules_tool.evaluate_risk(true_type, fields, confidence)
        gt_escalate = should_escalate_gt(true_type, gt)
        pred_escalate = risk["escalate"]
        if gt_escalate and pred_escalate:
            escalation_tp += 1
        elif not gt_escalate and pred_escalate:
            escalation_fp += 1
        elif gt_escalate and not pred_escalate:
            escalation_fn += 1
        else:
            escalation_tn += 1

        rows.append({
            "doc_id": d["doc_id"], "true_type": true_type, "pred_type": pred_type,
            "classified_correctly": correct_class, "extraction_confidence": confidence,
            "gt_escalate": gt_escalate, "pred_escalate": pred_escalate,
        })

    n = len(DOCS)
    print(f"Documents evaluated: {n}\n")
    print(f"Classification accuracy: {class_correct}/{n} = {class_correct/n:.2%}\n")

    print("Extraction exact-match rate by field:")
    for field, (c, t) in sorted(field_hits.items()):
        print(f"  {field:30s} {c}/{t} = {c/t:.2%}")

    precision = escalation_tp / (escalation_tp + escalation_fp) if (escalation_tp + escalation_fp) else float("nan")
    recall = escalation_tp / (escalation_tp + escalation_fn) if (escalation_tp + escalation_fn) else float("nan")
    print(f"\nEscalation decision quality (RiskComplianceAgent vs. ground-truth rule):")
    print(f"  TP={escalation_tp} FP={escalation_fp} FN={escalation_fn} TN={escalation_tn}")
    print(f"  Precision={precision:.2%}  Recall={recall:.2%}")

    with open("results/eval_results.json", "w") as f:
        json.dump({
            "n_docs": n,
            "classification_accuracy": class_correct / n,
            "field_accuracy": {k: v[0] / v[1] for k, v in field_hits.items()},
            "escalation_precision": precision,
            "escalation_recall": recall,
            "rows": rows,
        }, f, indent=2)
    print("\nFull results written to results/eval_results.json")


if __name__ == "__main__":
    main()
