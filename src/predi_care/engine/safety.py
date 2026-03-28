"""Safety envelope checks and monotone survival utilities."""

from __future__ import annotations

from predi_care.engine.v4_types import (
    EngineResultV4,
    SafetyCheckReport,
    SafetyInvariantResult,
    ScenarioResultV4,
)


def clamp_probability(value: float) -> float:
    return max(0.0, min(100.0, value))


def enforce_monotone_curve(curve: dict[int, float]) -> dict[int, float]:
    """Ensure survival curves never increase with time."""
    ordered_months = sorted(curve.keys())
    if not ordered_months:
        return {}
    monotone: dict[int, float] = {}
    running = clamp_probability(curve[ordered_months[0]])
    monotone[ordered_months[0]] = running
    for month in ordered_months[1:]:
        running = min(running, clamp_probability(curve[month]))
        monotone[month] = running
    return monotone


def apply_curve_safety(scenario: ScenarioResultV4) -> ScenarioResultV4:
    scenario.survival_curve = enforce_monotone_curve(scenario.survival_curve)
    if 24 in scenario.survival_curve:
        scenario.survival_2y = scenario.survival_curve[24]
    if 60 in scenario.survival_curve:
        scenario.survival_5y = scenario.survival_curve[60]
    scenario.survival_2y = clamp_probability(scenario.survival_2y)
    scenario.survival_5y = clamp_probability(scenario.survival_5y)
    scenario.local_recurrence_2y = clamp_probability(scenario.local_recurrence_2y)
    scenario.local_recurrence_5y = clamp_probability(scenario.local_recurrence_5y)
    scenario.distant_metastasis_5y = clamp_probability(scenario.distant_metastasis_5y)
    scenario.major_complication = clamp_probability(scenario.major_complication)
    scenario.qol_score = clamp_probability(scenario.qol_score)
    scenario.r0_probability = clamp_probability(scenario.r0_probability)
    for item in scenario.complications:
        item.value = clamp_probability(item.value)
        item.confidence = clamp_probability(item.confidence)
    return scenario


class SafetyEnvelopeChecker:
    """Deterministic safety checks for v4 outputs."""

    def check(self, result: EngineResultV4) -> SafetyCheckReport:
        invariants: list[SafetyInvariantResult] = []
        blocking: list[str] = []

        profile = result.patient_profile
        residual_cm = float(profile.get("residual_size_cm", 0.0))
        trg = int(profile.get("trg", 3))
        cm_stage = str(profile.get("cm_stage", "cM0"))
        ecog = int(profile.get("ecog", 1))
        recommendation = result.consensus.recommendation

        # Hard protocol constraints.
        ww_blocked = residual_cm > 2.0 or trg > 2
        passed_ww_rule = not (recommendation == "watch_wait" and ww_blocked)
        invariants.append(
            SafetyInvariantResult(
                name="watch_wait_hard_rule",
                passed=passed_ww_rule,
                severity="critical",
                message="watch_wait requires residual <= 2 cm and TRG <= 2.",
            )
        )
        if not passed_ww_rule:
            blocking.append("watch_wait_hard_rule")

        cm1_rule = not (cm_stage == "cM1" and recommendation != "multidisciplinary")
        invariants.append(
            SafetyInvariantResult(
                name="cm1_multidisciplinary_rule",
                passed=cm1_rule,
                severity="critical",
                message="cM1 must force multidisciplinary recommendation.",
            )
        )
        if not cm1_rule:
            blocking.append("cm1_multidisciplinary_rule")

        ecog4_rule = not (ecog >= 4 and recommendation != "multidisciplinary")
        invariants.append(
            SafetyInvariantResult(
                name="ecog4_multidisciplinary_rule",
                passed=ecog4_rule,
                severity="critical",
                message="ECOG 4 must force multidisciplinary recommendation.",
            )
        )
        if not ecog4_rule:
            blocking.append("ecog4_multidisciplinary_rule")

        # Probability bounds.
        bound_checks = [
            ("surgery_survival_2y", result.surgery.survival_2y),
            ("surgery_survival_5y", result.surgery.survival_5y),
            ("watch_wait_survival_2y", result.watch_wait.survival_2y),
            ("watch_wait_survival_5y", result.watch_wait.survival_5y),
            ("surgery_local_recurrence_5y", result.surgery.local_recurrence_5y),
            ("watch_wait_local_recurrence_2y", result.watch_wait.local_recurrence_2y),
            ("surgery_major_complication", result.surgery.major_complication),
        ]
        for name, value in bound_checks:
            passed = 0.0 <= value <= 100.0
            invariants.append(
                SafetyInvariantResult(
                    name=f"bound_{name}",
                    passed=passed,
                    severity="critical",
                    message=f"{name} must be in [0, 100].",
                )
            )
            if not passed:
                blocking.append(f"bound_{name}")

        # Monotone survival curves.
        for label, curve in (
            ("surgery", result.surgery.survival_curve),
            ("watch_wait", result.watch_wait.survival_curve),
        ):
            months = sorted(curve.keys())
            monotone_ok = all(curve[m2] <= curve[m1] for m1, m2 in zip(months[:-1], months[1:]))
            invariants.append(
                SafetyInvariantResult(
                    name=f"monotone_curve_{label}",
                    passed=monotone_ok,
                    severity="critical",
                    message=f"{label} survival curve must be non-increasing.",
                )
            )
            if not monotone_ok:
                blocking.append(f"monotone_curve_{label}")

        # Coherence in unfavorable profile.
        unfavorable = residual_cm > 2.0 or trg > 2
        if unfavorable:
            coherence = result.surgery.local_recurrence_5y <= result.watch_wait.local_recurrence_2y
            invariants.append(
                SafetyInvariantResult(
                    name="unfavorable_recurrence_coherence",
                    passed=coherence,
                    severity="warning",
                    message="In unfavorable profile, surgery recurrence should not exceed watch-and-wait recurrence.",
                )
            )

        return SafetyCheckReport(
            passed=len([item for item in invariants if not item.passed and item.severity == "critical"]) == 0,
            invariants=invariants,
            blocking_violations=sorted(set(blocking)),
        )

