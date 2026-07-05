"""
Generates docs of 4 types the pipeline handles: vendor
contracts, maintenance SOPs, incident reports, service emails. Domain is
an industrial equipment operator, close to Avathon's own space.
"""

import json
import random
import uuid
from pathlib import Path

random.seed(42)

OUT_DIR = Path(__file__).parent / "documents"
OUT_DIR.mkdir(parents=True, exist_ok=True)

VENDORS = ["Meridian Turbine Services", "Northbend Industrial Supply", "Aravalle Field Ops",
           "Coastal Compressor Co.", "Vantage Rotating Equipment"]
PLANTS = ["Plant 4 - Odessa", "Plant 2 - Gary", "Plant 7 - Baton Rouge", "Plant 1 - Tulsa"]
ASSETS = ["Gas Turbine GT-114", "Centrifugal Compressor C-22", "Feed Pump FP-08",
          "Generator GEN-3", "Cooling Tower Fan CTF-6"]
PPE = ["hard hat, hearing protection, arc-flash suit", "safety glasses, gloves, steel-toe boots",
       "respirator, chemical gloves, face shield"]


def gen_contract(idx):
    vendor = random.choice(VENDORS)
    liability_cap = random.choice([None, 250000, 500000, 1000000])
    auto_renewal = random.choice([True, False])
    notice_days = random.choice([30, 60, 90, None])
    effective = f"2025-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
    term_years = random.choice([1, 2, 3])

    body = f"""SERVICE AND MAINTENANCE AGREEMENT

This Agreement is entered into as of {effective} between Meridian Industrial Operations
("Client") and {vendor} ("Vendor").

1. SCOPE OF SERVICES
Vendor shall provide preventive and corrective maintenance services for rotating equipment
at Client's designated facilities, including quarterly inspections and 24-hour emergency
call-out support.

2. TERM
This Agreement shall remain in effect for {term_years} year(s) from the Effective Date.
{"This Agreement shall automatically renew for successive one-year terms unless either party provides written notice of non-renewal." if auto_renewal else "This Agreement shall terminate at the end of the Term unless renewed by mutual written agreement of both parties."}
{"Either party may terminate this Agreement with " + str(notice_days) + " days' written notice." if notice_days else "This Agreement contains no explicit early termination clause."}

3. LIMITATION OF LIABILITY
{"Vendor's aggregate liability under this Agreement shall not exceed $" + format(liability_cap, ",") + " in any twelve-month period." if liability_cap else "This Agreement does not specify a cap on Vendor's aggregate liability."}

4. PRICING
Client shall pay Vendor a fixed quarterly fee plus time-and-materials for emergency
call-outs, invoiced net-30.

5. GOVERNING LAW
This Agreement is governed by the laws of the state in which the Client facility is located.
"""
    return {
        "doc_id": f"CONTRACT-{idx:03d}",
        "doc_type_true": "vendor_contract",
        "text": body.strip(),
        "ground_truth": {
            "counterparty": vendor,
            "effective_date": effective,
            "liability_cap_usd": liability_cap,
            "auto_renewal": auto_renewal,
            "termination_notice_days": notice_days,
            "term_years": term_years,
        },
    }


def gen_sop(idx):
    asset = random.choice(ASSETS)
    ppe = random.choice(PPE)
    hazard = random.choice(["high", "medium", "low"])
    steps = random.randint(6, 11)
    body = f"""STANDARD OPERATING PROCEDURE
Equipment: {asset}
Document No: SOP-{idx:03d}
Hazard Level: {hazard.upper()}

1. PURPOSE
This procedure describes the lockout/tagout and inspection steps required before
performing maintenance on the {asset}.

2. REQUIRED PPE
Technicians must wear the following before beginning work: {ppe}.

3. PROCEDURE
""" + "\n".join([f"   Step {i+1}: {random.choice(['Isolate energy source and verify zero energy state.', 'Inspect bearing housing for abnormal vibration or heat discoloration.', 'Check lubrication levels and top off per spec sheet.', 'Record readings in the CMMS work order.', 'Verify guard and enclosure are reinstalled before re-energizing.', 'Notify shift supervisor before returning equipment to service.', 'Torque check all fasteners to manufacturer spec.', 'Test emergency stop function.'])}" for i in range(steps)]) + f"""

4. NOTES
Deviations from this procedure must be logged and approved by the maintenance supervisor.
"""
    return {
        "doc_id": f"SOP-{idx:03d}",
        "doc_type_true": "maintenance_sop",
        "text": body.strip(),
        "ground_truth": {
            "equipment": asset,
            "hazard_level": hazard,
            "required_ppe": ppe,
            "step_count": steps,
        },
    }


def gen_incident(idx):
    asset = random.choice(ASSETS)
    plant = random.choice(PLANTS)
    severity = random.choice(["low", "medium", "high", "critical"])
    downtime = round(random.uniform(0.5, 48), 1)
    root_cause_known = random.random() > 0.3
    body = f"""INCIDENT REPORT #{idx:03d}
Facility: {plant}
Asset: {asset}
Severity: {severity.upper()}

DESCRIPTION
On the shift of record, operators observed {random.choice(['a sharp rise in vibration amplitude', 'an unexpected trip on high bearing temperature', 'oil leakage at the shaft seal', 'a loss of output pressure'])}
on the {asset}. The unit was taken offline for inspection. Estimated downtime: {downtime} hours.

ROOT CAUSE
{"Root cause was determined to be " + random.choice(['bearing wear beyond tolerance', 'a failed lubrication pump', 'seal degradation from age', 'a control system sensor fault']) + "." if root_cause_known else "Root cause investigation is still open pending vendor teardown report."}

CORRECTIVE ACTION
{"Replacement parts ordered and repair scheduled." if root_cause_known else "Interim monitoring increased; formal RCA to follow within 10 business days."}
"""
    return {
        "doc_id": f"INCIDENT-{idx:03d}",
        "doc_type_true": "incident_report",
        "text": body.strip(),
        "ground_truth": {
            "asset": asset,
            "facility": plant,
            "severity": severity,
            "downtime_hours": downtime,
            "root_cause_identified": root_cause_known,
        },
    }


def gen_email(idx):
    plant = random.choice(PLANTS)
    urgency = random.choice(["low", "normal", "high", "urgent"])
    action = random.choice(["schedule an inspection", "expedite a spare part shipment",
                             "send a field technician", "clarify contract renewal terms",
                             "escalate an unresolved vibration alarm"])
    body = f"""From: ops.manager@{plant.split('-')[1].strip().lower().replace(' ','')}.client.com
Subject: {"URGENT: " if urgency == "urgent" else ""}Need help - {action}

Hi team,

We need someone to {action} at {plant} as soon as possible. This has been flagged
{"multiple times this week and is starting to affect production" if urgency in ("high","urgent") else "by the floor supervisor"}.
Please advise on timing and next steps.

Thanks,
Plant Ops
"""
    return {
        "doc_id": f"EMAIL-{idx:03d}",
        "doc_type_true": "service_email",
        "text": body.strip(),
        "ground_truth": {
            "facility": plant,
            "urgency": urgency,
            "requested_action": action,
        },
    }


def main():
    docs = []
    for i in range(1, 14):
        docs.append(gen_contract(i))
    for i in range(1, 14):
        docs.append(gen_sop(i))
    for i in range(1, 13):
        docs.append(gen_incident(i))
    for i in range(1, 12):
        docs.append(gen_email(i))

    random.shuffle(docs)
    for d in docs:
        with open(OUT_DIR / f"{d['doc_id']}.json", "w") as f:
            json.dump(d, f, indent=2)

    manifest = [{"doc_id": d["doc_id"], "doc_type_true": d["doc_type_true"]} for d in docs]
    with open(OUT_DIR.parent / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Generated {len(docs)} synthetic documents in {OUT_DIR}")


if __name__ == "__main__":
    main()
