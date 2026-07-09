"""
change_detector.py
==================
Formulary change detection engine.

Compares two weekly snapshots for the same payer and detects
every change — tier moves, PA additions/removals, step therapy
additions, and quantity limit changes.

Each change is classified by type, direction, and severity
using the CHANGE_IMPACT lookup table from formulary.py.

WHY A LOOKUP TABLE NOT IF-ELSE CHAINS
---------------------------------------
A lookup table makes the classification logic explicit,
testable, and easy to update. Adding a new tier combination
is one line in the dict. An if-else chain would require
reading through nested conditions to find and update the rule.

Author: Siva Annapareddy
Domain: Market Access and Pricing Analytics
"""

from dataclasses import dataclass
from typing import List
from src.formulary import FormularyRecord, CHANGE_IMPACT


@dataclass
class FormularyChange:
    """
    A single detected formulary change at a specific payer and week.
    """
    payer_id:       str
    payer_name:     str
    channel:        str
    covered_lives_m: float
    week:           int
    change_type:    str    # tier_change | pa_added | pa_removed | step_added | ql_added
    direction:      str    # DETERIORATION | IMPROVEMENT | NEUTRAL
    severity:       str    # CRITICAL | HIGH | MEDIUM | LOW
    prior_value:    str
    new_value:      str
    description:    str
    action_required: str


class FormularyChangeDetector:
    """
    Detects all formulary changes between two weekly snapshots
    for the same payer.
    """

    def detect(
        self,
        prior: FormularyRecord,
        current: FormularyRecord
    ) -> List[FormularyChange]:
        """
        Compare prior week to current week and return all changes.
        Returns empty list if no changes detected.
        """
        changes = []

        # ── Tier change ───────────────────────────────────────────
        if prior.formulary_tier != current.formulary_tier:
            key = (prior.formulary_tier, current.formulary_tier)
            direction, severity = CHANGE_IMPACT.get(key, ("NEUTRAL", "LOW"))
            action = self._tier_action(direction, severity, current)
            changes.append(FormularyChange(
                payer_id=current.payer_id,
                payer_name=current.payer_name,
                channel=current.channel,
                covered_lives_m=current.covered_lives_m,
                week=current.week,
                change_type="tier_change",
                direction=direction,
                severity=severity,
                prior_value=prior.formulary_tier,
                new_value=current.formulary_tier,
                description=f"Tier changed: {prior.formulary_tier} to {current.formulary_tier}",
                action_required=action,
            ))

        # ── PA added ──────────────────────────────────────────────
        if not prior.pa_required and current.pa_required:
            changes.append(FormularyChange(
                payer_id=current.payer_id,
                payer_name=current.payer_name,
                channel=current.channel,
                covered_lives_m=current.covered_lives_m,
                week=current.week,
                change_type="pa_added",
                direction="DETERIORATION",
                severity="HIGH",
                prior_value="No PA",
                new_value=current.pa_criteria_text[:60],
                description="Prior authorization requirement added",
                action_required=(
                    "Review PA criteria alignment with label. "
                    "Escalate to medical affairs if off-label criteria detected. "
                    "Brief field force on PA documentation requirements."
                ),
            ))

        # ── PA removed ────────────────────────────────────────────
        if prior.pa_required and not current.pa_required:
            changes.append(FormularyChange(
                payer_id=current.payer_id,
                payer_name=current.payer_name,
                channel=current.channel,
                covered_lives_m=current.covered_lives_m,
                week=current.week,
                change_type="pa_removed",
                direction="IMPROVEMENT",
                severity="HIGH",
                prior_value="PA required",
                new_value="No PA",
                description="Prior authorization requirement removed",
                action_required=(
                    "Update field force briefing. "
                    "Communicate unrestricted access to KAMs and MSLs. "
                    "Update patient support hub protocols."
                ),
            ))

        # ── Step therapy added ────────────────────────────────────
        new_steps = set(current.step_agents) - set(prior.step_agents)
        if new_steps:
            severity = "CRITICAL" if len(new_steps) > 1 else "HIGH"
            changes.append(FormularyChange(
                payer_id=current.payer_id,
                payer_name=current.payer_name,
                channel=current.channel,
                covered_lives_m=current.covered_lives_m,
                week=current.week,
                change_type="step_added",
                direction="DETERIORATION",
                severity=severity,
                prior_value=", ".join(prior.step_agents) or "None",
                new_value=", ".join(current.step_agents),
                description=f"Step therapy added: {', '.join(new_steps)}",
                action_required=(
                    "Immediate payer engagement required. "
                    "Assess label compatibility with step criteria. "
                    "Legal review if step-through is off-label. "
                    "Brief field force on patient navigation."
                ),
            ))

        # ── Quantity limits added ─────────────────────────────────
        if not prior.quantity_limits and current.quantity_limits:
            changes.append(FormularyChange(
                payer_id=current.payer_id,
                payer_name=current.payer_name,
                channel=current.channel,
                covered_lives_m=current.covered_lives_m,
                week=current.week,
                change_type="ql_added",
                direction="DETERIORATION",
                severity="MEDIUM",
                prior_value="No QL",
                new_value="QL imposed",
                description="Quantity limits imposed",
                action_required=(
                    "Assess impact on dosing flexibility. "
                    "Communicate to field force and hub. "
                    "Monitor for patient abandonment signals."
                ),
            ))

        return changes

    def _tier_action(
        self,
        direction: str,
        severity: str,
        current: FormularyRecord
    ) -> str:
        """Generate action required text based on direction and severity."""
        if direction == "DETERIORATION" and severity == "CRITICAL":
            return (
                f"URGENT: Escalate to VP Market Access immediately. "
                f"Schedule payer meeting within 5 days. "
                f"Review contract terms for {current.payer_name}. "
                f"Brief field force to redirect where possible."
            )
        elif direction == "DETERIORATION" and severity == "HIGH":
            return (
                f"Schedule payer meeting within 2 weeks. "
                f"Assess rebate contract levers for {current.payer_name}. "
                f"Update field force briefing."
            )
        elif direction == "IMPROVEMENT":
            return (
                f"Update field force briefing — access improved at {current.payer_name}. "
                f"Communicate win to brand team and KAMs."
            )
        else:
            return "Monitor. No immediate action required."


if __name__ == "__main__":
    from src.formulary import build_baseline_payers
    import copy

    # Test: simulate CVS moving from Tier 2 to Tier 3 at week 4
    baseline = build_baseline_payers(week=1)
    week4 = copy.deepcopy(baseline)
    for p in week4:
        p.week = 4
        if p.payer_id == "P001":
            p.formulary_tier = "tier3"
            p.pa_required = True
            p.pa_criteria_text = "Step through generic first"

    detector = FormularyChangeDetector()
    prior_map = {p.payer_id: p for p in baseline}
    current_map = {p.payer_id: p for p in week4}

    all_changes = []
    for pid in current_map:
        if pid in prior_map:
            changes = detector.detect(prior_map[pid], current_map[pid])
            all_changes.extend(changes)

    print(f"Changes detected at week 4: {len(all_changes)}")
    print()
    for c in all_changes:
        print(f"[{c.severity}] {c.payer_name} — {c.change_type}")
        print(f"  {c.description}")
        print(f"  Action: {c.action_required[:80]}")
        print()