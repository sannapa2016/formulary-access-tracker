# Formulary Access Tracker with Alert System

**Weekly Formulary Monitoring Pipeline — Change Detection + Access Trajectory**

---

## The Problem

A payer moved our drug from Tier 2 to Tier 3 on a Tuesday.
The brand team found out the following Monday.

In those 6 days every physician who tried to prescribe hit
a higher copay barrier. Some patients abandoned at the pharmacy.
Those dispensed units are permanently lost.

Without weekly monitoring you are always 4 to 8 weeks behind.

---

## What This Tool Does

- Ingests weekly formulary snapshots across 8 payers
- Detects every change — tier moves, PA additions, step therapy,
  quantity limits
- Classifies each change by type, direction, and severity
- Generates an actionable alert queue with specific actions required
- Tracks access trajectory using linear regression on access scores
- Exports change log, trajectory summary, and weekly scores to CSV

---

## Model Assumptions

| Parameter | Value | Notes |
|---|---|---|
| Payers tracked | 8 | Commercial, Part D, Managed Medicaid |
| Simulation horizon | 12 weeks | Post-launch monitoring window |
| Trajectory window | 8 weeks | Rolling regression window |
| IMPROVING threshold | slope above 0.05 | Sustained upward trend |
| DETERIORATING threshold | slope below -0.05 | Sustained downward trend |

---

## Key Output

Total changes detected:  4
CRITICAL alerts:         0
HIGH alerts:             3
Deteriorating payers:    1
Most critical: Molina Week 8 — Tier 3 to Non-formulary

---

## Change Severity Framework

| Change | Direction | Severity |
|---|---|---|
| Tier 2 to Non-formulary | DETERIORATION | CRITICAL |
| Tier 1 to Tier 3 | DETERIORATION | CRITICAL |
| Tier 2 to Tier 3 | DETERIORATION | HIGH |
| PA added | DETERIORATION | HIGH |
| Step therapy 2+ agents | DETERIORATION | CRITICAL |
| Tier 3 to Tier 2 | IMPROVEMENT | MEDIUM |
| PA removed | IMPROVEMENT | HIGH |

---

## Quick Start

```bash
git clone https://github.com/sannapa2016/formulary-access-tracker.git
cd formulary-access-tracker
pip install -r requirements.txt
pip install -e .
python main.py
```

---

## Project Structure

formulary-access-tracker/
├── src/
│   ├── init.py          Makes src a Python package
│   ├── formulary.py         FormularyRecord dataclass and baseline payers
│   ├── change_detector.py   Change detection engine and severity classification
│   └── trajectory.py        12-week simulation and access trajectory analysis
├── outputs/                 CSV results generated on run
├── main.py                  Single entry point
└── requirements.txt         numpy, pandas

---

## Author

**Siva Annapareddy**
Founder and AVP, Amrak Pharma Analytics
18 years in pharma commercial analytics

*Project 5 of 36 — open-source pharma analytics portfolio*

