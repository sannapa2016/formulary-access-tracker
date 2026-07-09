"""
formulary.py
============
FormularyRecord dataclass and baseline payer definitions.

A formulary snapshot captures the access status of a drug
at a specific payer at a specific point in time. Weekly
snapshots allow change detection by comparing week N to week N-1.

WHY WEEKLY NOT MONTHLY
-----------------------
A payer can change formulary status without notice at any time.
Monthly monitoring means 4 weeks of revenue lost before detection.
Weekly monitoring means maximum 7 days of detection lag.

Author: Siva Annapareddy
Domain: Market Access and Pricing Analytics
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class FormularyRecord:
    """
    A single payer formulary snapshot for one week.

    Attributes
    ----------
    payer_id : str
        Unique payer identifier
    payer_name : str
        Full payer name for display
    channel : str
        commercial | part_d | managed_medicaid
    covered_lives_m : float
        Covered lives in millions — weights alert severity
    formulary_tier : str
        tier1 | tier2 | tier3 | non-formulary | not_covered
    pa_required : bool
        Prior authorization required
    pa_criteria_text : str
        Description of PA criteria
    step_therapy_required : bool
        Step therapy required before coverage
    step_agents : List[str]
        Specific agents required in step therapy
    quantity_limits : bool
        Quantity limits imposed
    week : int
        Snapshot week number (1 = launch week)
    """
    payer_id:             str
    payer_name:           str
    channel:              str
    covered_lives_m:      float
    formulary_tier:       str
    pa_required:          bool
    pa_criteria_text:     str
    step_therapy_required: bool
    step_agents:          List[str]
    quantity_limits:      bool
    week:                 int


# Tier rank for access score calculation
# Lower number = better access
TIER_ORDER = {
    "tier1":         1,
    "tier2":         2,
    "tier3":         3,
    "non-formulary": 4,
    "not_covered":   5,
}

# Change impact lookup table
# Maps (prior_tier, new_tier) to (direction, severity)
CHANGE_IMPACT = {
    ("tier1", "tier2"):         ("DETERIORATION", "HIGH"),
    ("tier1", "tier3"):         ("DETERIORATION", "CRITICAL"),
    ("tier1", "non-formulary"): ("DETERIORATION", "CRITICAL"),
    ("tier2", "tier3"):         ("DETERIORATION", "HIGH"),
    ("tier2", "non-formulary"): ("DETERIORATION", "CRITICAL"),
    ("tier3", "non-formulary"): ("DETERIORATION", "HIGH"),
    ("tier2", "tier1"):         ("IMPROVEMENT",   "HIGH"),
    ("tier3", "tier2"):         ("IMPROVEMENT",   "MEDIUM"),
    ("tier3", "tier1"):         ("IMPROVEMENT",   "HIGH"),
    ("non-formulary", "tier3"): ("IMPROVEMENT",   "HIGH"),
    ("non-formulary", "tier2"): ("IMPROVEMENT",   "CRITICAL"),
    ("non-formulary", "tier1"): ("IMPROVEMENT",   "CRITICAL"),
}


def build_baseline_payers(week: int = 1) -> List[FormularyRecord]:
    """
    Baseline formulary snapshot at launch week.
    8 payers across three channels representing a realistic
    specialty drug launch access landscape.
    """
    return [
        FormularyRecord("P001", "CVS Caremark",    "commercial",      95.0,
            "tier2", True,  "FDA-approved indication only",
            False, [], False, week),
        FormularyRecord("P002", "Express Scripts",  "commercial",      80.0,
            "tier3", True,  "Step through formulary agent first",
            True,  ["Agent-A"], False, week),
        FormularyRecord("P003", "OptumRx",          "commercial",      75.0,
            "tier2", False, "",
            False, [], False, week),
        FormularyRecord("P004", "SilverScript",     "part_d",          30.0,
            "tier2", True,  "On-label use only",
            False, [], False, week),
        FormularyRecord("P005", "Humana Part D",    "part_d",          28.0,
            "tier3", True,  "ECOG PS 2 or below required",
            False, [], True,  week),
        FormularyRecord("P006", "BCBS Part D",      "part_d",          22.0,
            "tier2", False, "",
            False, [], False, week),
        FormularyRecord("P007", "Medi-Cal",         "managed_medicaid",15.0,
            "tier2", True,  "Specialist attestation required",
            True,  ["Agent-B"], False, week),
        FormularyRecord("P008", "Molina",           "managed_medicaid", 9.0,
            "tier3", True,  "Step through SOC",
            True,  ["Agent-A", "Agent-B"], False, week),
    ]


if __name__ == "__main__":
    payers = build_baseline_payers(week=1)
    print(f"Baseline payers loaded: {len(payers)}")
    print()
    print(f"{'ID':<6} {'Payer':<20} {'Channel':<20} {'Tier':<15} {'PA':<6} {'Steps'}")
    print("-" * 75)
    for p in payers:
        steps = len(p.step_agents)
        print(f"{p.payer_id:<6} {p.payer_name:<20} {p.channel:<20} "
              f"{p.formulary_tier:<15} {str(p.pa_required):<6} {steps}")