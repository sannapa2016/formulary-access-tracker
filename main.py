"""
main.py
=======
Single entry point for the Formulary Access Tracker.

Runs three analyses:
    1. Formulary change alert log across 12 weeks
    2. Critical and high severity action queue
    3. Access trajectory summary per payer

Author: Siva Annapareddy
Domain: Market Access and Pricing Analytics
"""

import os
import pandas as pd
from src.formulary import build_baseline_payers
from src.change_detector import FormularyChangeDetector, FormularyChange
from src.trajectory import simulate_snapshots, compute_trajectory

os.makedirs("outputs", exist_ok=True)


def build_change_log(snapshots) -> pd.DataFrame:
    """
    Walk through weekly snapshots and detect all changes.
    Returns a DataFrame of every change detected across all weeks.
    """
    detector = FormularyChangeDetector()

    by_week = {}
    for snap in snapshots:
        by_week.setdefault(snap.week, {})[snap.payer_id] = snap

    all_changes = []
    for week in sorted(by_week.keys()):
        if week == 1:
            continue
        prior_week = by_week[week - 1]
        curr_week = by_week[week]
        for pid in curr_week:
            if pid in prior_week:
                changes = detector.detect(prior_week[pid], curr_week[pid])
                all_changes.extend(changes)

    if not all_changes:
        return pd.DataFrame()

    return pd.DataFrame([{
        "week":            c.week,
        "payer_name":      c.payer_name,
        "channel":         c.channel,
        "covered_lives_m": c.covered_lives_m,
        "change_type":     c.change_type,
        "direction":       c.direction,
        "severity":        c.severity,
        "prior_value":     c.prior_value,
        "new_value":       c.new_value,
        "description":     c.description,
        "action_required": c.action_required,
    } for c in all_changes])


def main():
    print("=" * 65)
    print("FORMULARY ACCESS TRACKER WITH ALERT SYSTEM")
    print("Author: Siva Annapareddy | Amrak Pharma Analytics")
    print("=" * 65)

    # Run 12-week simulation
    snapshots = simulate_snapshots(n_weeks=12)
    change_log = build_change_log(snapshots)
    detail_df, traj_df = compute_trajectory(snapshots)

    # ── Analysis 1: Full change log ───────────────────────────────
    print("\n[1] FORMULARY CHANGE ALERT LOG\n")
    if not change_log.empty:
        print(change_log[[
            "week", "payer_name", "channel",
            "change_type", "direction", "severity", "description"
        ]].to_string(index=False))
    else:
        print("  No changes detected.")

    # ── Analysis 2: Action queue ──────────────────────────────────
    print("\n[2] CRITICAL AND HIGH SEVERITY ACTIONS REQUIRED\n")
    if not change_log.empty:
        priority = change_log[
            change_log["severity"].isin(["CRITICAL", "HIGH"])
        ].sort_values(["severity", "covered_lives_m"], ascending=[True, False])

        for _, row in priority.iterrows():
            print(f"  Week {row['week']:>2} | [{row['severity']:<8}] "
                  f"{row['payer_name']:<20} | {row['covered_lives_m']:.0f}M lives")
            print(f"         {row['description']}")
            print(f"         Action: {row['action_required'][:90]}")
            print()

    # ── Analysis 3: Access trajectory ────────────────────────────
    print("\n[3] ACCESS TRAJECTORY — 12-week view\n")
    print(traj_df.to_string(index=False))

    improving = (traj_df["trajectory"] == "IMPROVING").sum()
    stable = (traj_df["trajectory"] == "STABLE").sum()
    deteriorating = (traj_df["trajectory"] == "DETERIORATING").sum()

    print(f"\n  IMPROVING:     {improving}")
    print(f"  STABLE:        {stable}")
    print(f"  DETERIORATING: {deteriorating}")

    # ── Key insights ──────────────────────────────────────────────
    print("\n[4] KEY INSIGHTS\n")
    if not change_log.empty:
        critical = change_log[change_log["severity"] == "CRITICAL"]
        high = change_log[change_log["severity"] == "HIGH"]
        print(f"  Total changes detected:  {len(change_log)}")
        print(f"  CRITICAL alerts:         {len(critical)}")
        print(f"  HIGH alerts:             {len(high)}")
        print(f"  Deteriorating payers:    {deteriorating}")

        if not critical.empty:
            worst = critical.sort_values(
                "covered_lives_m", ascending=False
            ).iloc[0]
            print(f"  Most critical change:    {worst['payer_name']} "
                  f"Week {worst['week']} — {worst['description']}")

    # ── Export ────────────────────────────────────────────────────
    if not change_log.empty:
        change_log.to_csv("outputs/formulary_change_log.csv", index=False)
    traj_df.to_csv("outputs/access_trajectory.csv", index=False)
    detail_df.to_csv("outputs/access_scores_weekly.csv", index=False)

    print("\n[OK] Results saved to outputs/")
    print("=" * 65)


if __name__ == "__main__":
    main()