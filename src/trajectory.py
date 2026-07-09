"""
trajectory.py
=============
12-week formulary snapshot simulation and access trajectory analysis.

Simulates realistic formulary evolution across 8 payers over 12 weeks
with pre-defined changes at specific weeks to demonstrate the tracker.

ACCESS SCORE FORMULA
---------------------
access_score = (5 - tier_rank)
             - 0.5  if PA required
             - 0.3  per step therapy agent
             - 0.2  if quantity limits

Higher score = better access.
Tier 1, no PA, no step therapy = maximum score of 4.5

TRAJECTORY CLASSIFICATION
--------------------------
Linear regression slope on 8-week rolling window:
  slope > +0.05  = IMPROVING
  slope < -0.05  = DETERIORATING
  otherwise      = STABLE

WHY LINEAR REGRESSION NOT SIMPLE DELTA
----------------------------------------
A single week change can be noise — operational issue, data error.
Linear regression on 8 weeks smooths noise and detects sustained trend.
Gives 4 to 6 weeks of early warning before a formal tier change occurs.

Author: Siva Annapareddy
Domain: Market Access and Pricing Analytics
"""

import copy
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from src.formulary import FormularyRecord, TIER_ORDER, build_baseline_payers


def simulate_snapshots(n_weeks: int = 12) -> List[FormularyRecord]:
    """
    Simulate 12 weeks of formulary evolution with realistic changes.

    Pre-defined changes:
      Week 4: Express Scripts improves from Tier 3 to Tier 2
              after successful rebate negotiation
      Week 6: Humana Part D removes PA requirement
      Week 8: Molina deteriorates to Non-formulary
              with additional step therapy added
    """
    baseline = build_baseline_payers(week=1)
    current_state = {p.payer_id: copy.deepcopy(p) for p in baseline}
    snapshots = []

    for week in range(1, n_weeks + 1):

        # Week 4 — Express Scripts negotiation win
        if week == 4:
            current_state["P002"].formulary_tier = "tier2"
            current_state["P002"].pa_required = True
            current_state["P002"].pa_criteria_text = "FDA-approved indication"
            current_state["P002"].step_therapy_required = False
            current_state["P002"].step_agents = []

        # Week 6 — Humana removes PA
        if week == 6:
            current_state["P005"].pa_required = False
            current_state["P005"].pa_criteria_text = ""

        # Week 8 — Molina adverse change
        if week == 8:
            current_state["P008"].formulary_tier = "non-formulary"
            current_state["P008"].step_agents = ["Agent-A", "Agent-B", "Agent-C"]

        # Take snapshot of all payers this week
        for pid, state in current_state.items():
            snap = copy.deepcopy(state)
            snap.week = week
            snapshots.append(snap)

    return snapshots


def compute_access_score(record: FormularyRecord) -> float:
    """
    Compute access score for a single payer snapshot.
    Higher = better patient access.
    """
    tier_rank = TIER_ORDER.get(record.formulary_tier, 5)
    score = 5 - tier_rank
    if record.pa_required:
        score -= 0.5
    score -= 0.3 * len(record.step_agents)
    if record.quantity_limits:
        score -= 0.2
    return round(score, 2)


def compute_trajectory(
    snapshots: List[FormularyRecord],
    window_weeks: int = 8
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compute access scores over time and classify trajectory per payer.

    Returns
    -------
    detail_df  : week-by-week access scores per payer
    summary_df : trajectory classification per payer
    """
    rows = []
    for snap in snapshots:
        rows.append({
            "payer_id":    snap.payer_id,
            "payer_name":  snap.payer_name,
            "week":        snap.week,
            "tier":        snap.formulary_tier,
            "access_score": compute_access_score(snap),
        })

    detail_df = pd.DataFrame(rows)

    # Classify trajectory per payer
    traj_rows = []
    for pid in detail_df["payer_id"].unique():
        sub = detail_df[detail_df["payer_id"] == pid].sort_values("week")
        recent = sub.tail(min(window_weeks, len(sub)))

        if len(recent) >= 2:
            slope = np.polyfit(recent["week"], recent["access_score"], 1)[0]
        else:
            slope = 0.0

        latest = sub.iloc[-1]

        if slope > 0.05:
            trajectory = "IMPROVING"
        elif slope < -0.05:
            trajectory = "DETERIORATING"
        else:
            trajectory = "STABLE"

        traj_rows.append({
            "payer_id":      pid,
            "payer_name":    latest["payer_name"],
            "latest_tier":   latest["tier"],
            "latest_score":  latest["access_score"],
            "trend_slope":   round(slope, 4),
            "trajectory":    trajectory,
        })

    summary_df = pd.DataFrame(traj_rows).sort_values(
        "latest_score", ascending=False
    ).reset_index(drop=True)

    return detail_df, summary_df


if __name__ == "__main__":
    snapshots = simulate_snapshots(n_weeks=12)
    detail_df, summary_df = compute_trajectory(snapshots)

    print("ACCESS TRAJECTORY SUMMARY — 12 weeks\n")
    print(summary_df.to_string(index=False))

    print(f"\nIMPROVING:     {(summary_df['trajectory']=='IMPROVING').sum()}")
    print(f"STABLE:        {(summary_df['trajectory']=='STABLE').sum()}")
    print(f"DETERIORATING: {(summary_df['trajectory']=='DETERIORATING').sum()}")