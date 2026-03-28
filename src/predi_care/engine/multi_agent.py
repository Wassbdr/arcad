"""Multi-agent orchestration layer for v4 Digital Twin inference."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from predi_care.engine.v4_types import AgentOutput, ConsensusReport, DataTwinProfile


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _ace_drop_ratio(profile: DataTwinProfile) -> float:
    baseline = float(profile.get("ace_baseline", 0.0))
    current = float(profile.get("ace_current", 0.0))
    if baseline <= 0:
        return 0.0
    return _clamp((baseline - current) / baseline, 0.0, 1.0)


def _source_for(profile: DataTwinProfile, key: str) -> str:
    trace = profile.provenance.get(key)
    if trace is None:
        return "unknown"
    return str(trace.source)


class AgentRadiology:
    def evaluate(self, profile: DataTwinProfile) -> AgentOutput:
        residual_cm = float(profile.get("residual_size_cm", 0.0))
        trg = int(profile.get("trg", 3))
        emvi = bool(profile.get("emvi", False))
        crm_status = str(profile.get("crm_status", "threatened"))
        imaging_quality = str(profile.get("imaging_quality", "Moyenne"))

        crm_penalty = {"negative": 0.0, "threatened": 8.0, "positive": 18.0}.get(crm_status, 8.0)
        quality_bonus = {"Elevee": 10.0, "Moyenne": 3.0, "Basse": -8.0}.get(imaging_quality, 0.0)

        ww_candidate = 88.0 - residual_cm * 22.0 - max(0, trg - 1) * 14.0 - crm_penalty - (8.0 if emvi else 0.0)
        surgery_control = 62.0 + max(0, trg - 1) * 8.0 + crm_penalty * 0.8 + (7.0 if emvi else 0.0)
        confidence = _clamp(70.0 + quality_bonus, 30.0, 95.0)

        rationale = [
            f"Residual lesion estimate: {residual_cm:.1f} cm",
            f"TRG class: {trg}",
            f"CRM status: {crm_status}",
        ]
        if emvi:
            rationale.append("EMVI is positive and increases systemic and local risk.")

        return AgentOutput(
            agent_name="radiology",
            scores={
                "ww_candidate": _clamp(ww_candidate),
                "surgery_control": _clamp(surgery_control),
            },
            rationale=rationale,
            evidence=[
                "GRECCAR-style residual and TRG criteria",
                "CRM and EMVI risk gradients",
            ],
            feature_sources={
                "residual_size_cm": _source_for(profile, "residual_size_cm"),
                "trg": _source_for(profile, "trg"),
                "crm_status": _source_for(profile, "crm_status"),
                "emvi": _source_for(profile, "emvi"),
            },
            confidence=confidence,
        )


class AgentBiology:
    def evaluate(self, profile: DataTwinProfile) -> AgentOutput:
        ace_drop = _ace_drop_ratio(profile)
        current = float(profile.get("ace_current", 0.0))
        albumin = float(profile.get("albumin", 40.0))
        hemoglobin = float(profile.get("hemoglobin", 13.0))
        msi = str(profile.get("msi_status", "Non teste"))

        ww_candidate = 45.0 + ace_drop * 40.0
        surgery_comp_risk = 20.0
        alerts: list[str] = []

        if current > 5.0:
            ww_candidate -= 12.0
            alerts.append("CEA/ACE remains above normal and suggests persistent disease.")
        if albumin < 35.0:
            surgery_comp_risk += 7.0
            alerts.append("Hypoalbuminemia increases perioperative complication risk.")
        if hemoglobin < 12.0:
            ww_candidate -= 5.0
            alerts.append("Low hemoglobin can reduce treatment efficacy.")
        if msi == "dMMR/MSI-H":
            ww_candidate += 10.0

        return AgentOutput(
            agent_name="biology",
            scores={
                "ww_candidate": _clamp(ww_candidate),
                "surgery_comp_risk": _clamp(surgery_comp_risk),
            },
            rationale=[
                f"CEA/ACE drop ratio: {ace_drop:.2f}",
                f"Albumin: {albumin:.1f} g/L",
                f"Hemoglobin: {hemoglobin:.1f} g/dL",
                f"MSI status: {msi}",
            ],
            alerts=alerts,
            evidence=["CEA trend, nutrition, and MSI-driven response priors"],
            feature_sources={
                "ace_baseline": _source_for(profile, "ace_baseline"),
                "ace_current": _source_for(profile, "ace_current"),
                "albumin": _source_for(profile, "albumin"),
                "hemoglobin": _source_for(profile, "hemoglobin"),
                "msi_status": _source_for(profile, "msi_status"),
            },
            confidence=72.0,
        )


class AgentSurgeryRisk:
    def evaluate(self, profile: DataTwinProfile) -> AgentOutput:
        asa = int(profile.get("asa_score", 2))
        ecog = int(profile.get("ecog", 1))
        age = int(profile.get("age", 62))
        smoking = bool(profile.get("smoking", False))
        diabetes = bool(profile.get("diabetes", False))
        crm_status = str(profile.get("crm_status", "threatened"))

        base_comp = 12.0 + max(0, asa - 2) * 6.0 + max(0, ecog - 1) * 4.0
        if age >= 80:
            base_comp += 6.0
        if smoking:
            base_comp += 5.0
        if diabetes:
            base_comp += 3.0

        r0_probability = 96.0
        if crm_status == "threatened":
            r0_probability -= 9.0
        elif crm_status == "positive":
            r0_probability -= 20.0

        return AgentOutput(
            agent_name="surgery_risk",
            scores={
                "major_complication": _clamp(base_comp),
                "r0_probability": _clamp(r0_probability),
            },
            rationale=[
                f"ASA: {asa}, ECOG: {ecog}, age: {age}",
                f"CRM status impacts R0 probability: {crm_status}",
            ],
            evidence=["ASA/ECOG and CRM-based surgery risk priors"],
            feature_sources={
                "asa_score": _source_for(profile, "asa_score"),
                "ecog": _source_for(profile, "ecog"),
                "age": _source_for(profile, "age"),
                "crm_status": _source_for(profile, "crm_status"),
            },
            confidence=78.0,
        )


class AgentWatchWait:
    def evaluate(self, profile: DataTwinProfile) -> AgentOutput:
        residual_cm = float(profile.get("residual_size_cm", 0.0))
        trg = int(profile.get("trg", 3))
        ace_drop = _ace_drop_ratio(profile)
        cM = str(profile.get("cm_stage", "cM0"))

        regrowth_2y = 18.0 + residual_cm * 10.0 + max(0, trg - 2) * 8.0 - ace_drop * 6.0
        organ_preservation_3y = 82.0 - max(0, trg - 1) * 5.0 - residual_cm * 6.0
        ww_candidate = 82.0 - regrowth_2y * 0.8

        alerts: list[str] = []
        if cM == "cM1":
            alerts.append("Metastatic stage is not compatible with standard watch-and-wait.")

        return AgentOutput(
            agent_name="watch_wait",
            scores={
                "regrowth_2y": _clamp(regrowth_2y),
                "organ_preservation_3y": _clamp(organ_preservation_3y),
                "ww_candidate": _clamp(ww_candidate),
            },
            rationale=[
                f"Predicted regrowth risk at 2 years: {_clamp(regrowth_2y):.1f}%",
                f"Predicted organ preservation at 3 years: {_clamp(organ_preservation_3y):.1f}%",
            ],
            alerts=alerts,
            evidence=["TRG and residual burden drive regrowth dynamics"],
            feature_sources={
                "residual_size_cm": _source_for(profile, "residual_size_cm"),
                "trg": _source_for(profile, "trg"),
                "cm_stage": _source_for(profile, "cm_stage"),
            },
            confidence=74.0,
        )


class AgentComorbidity:
    def evaluate(self, profile: DataTwinProfile) -> AgentOutput:
        ecog = int(profile.get("ecog", 1))
        asa = int(profile.get("asa_score", 2))
        age = int(profile.get("age", 62))

        frailty = 8.0 + ecog * 12.0 + max(0, asa - 2) * 10.0 + max(0, age - 70) * 0.6
        return AgentOutput(
            agent_name="comorbidity",
            scores={"frailty": _clamp(frailty)},
            rationale=[f"Frailty index from ECOG/ASA/age: {_clamp(frailty):.1f}"],
            evidence=["Comorbidity-weighted tolerance estimate"],
            feature_sources={
                "ecog": _source_for(profile, "ecog"),
                "asa_score": _source_for(profile, "asa_score"),
                "age": _source_for(profile, "age"),
            },
            confidence=70.0,
        )


class AgentEthicsRules:
    def evaluate(self, profile: DataTwinProfile) -> AgentOutput:
        residual_cm = float(profile.get("residual_size_cm", 0.0))
        trg = int(profile.get("trg", 3))
        cm_stage = str(profile.get("cm_stage", "cM0"))
        ecog = int(profile.get("ecog", 1))

        alerts: list[str] = []
        forced = 0.0

        if residual_cm > 2.0:
            alerts.append("Residual lesion above 2 cm blocks watch-and-wait recommendation.")
            forced = 1.0
        if trg > 2:
            alerts.append("TRG above 2 blocks watch-and-wait recommendation.")
            forced = 1.0
        if cm_stage == "cM1":
            alerts.append("cM1 requires multidisciplinary escalation.")
            forced = 1.0
        if ecog >= 4:
            alerts.append("ECOG 4 contraindicates surgery and requires multidisciplinary escalation.")
            forced = 1.0

        return AgentOutput(
            agent_name="ethics_rules",
            scores={"forced_multidisciplinary": forced},
            alerts=alerts,
            rationale=["Hard safety rules enforce non-negotiable protocol constraints."],
            evidence=["Symbolic safety envelope"],
            feature_sources={
                "residual_size_cm": _source_for(profile, "residual_size_cm"),
                "trg": _source_for(profile, "trg"),
                "cm_stage": _source_for(profile, "cm_stage"),
                "ecog": _source_for(profile, "ecog"),
            },
            confidence=95.0,
        )


@dataclass
class OrchestrationResult:
    agent_outputs: dict[str, AgentOutput]
    consensus: ConsensusReport
    feature_contributions: dict[str, float]
    primary_factors: list[tuple[str, float, str]]


class RCPOrchestrator:
    """Coordinate specialized agents and return one consensus recommendation."""

    def __init__(self) -> None:
        self.radiology = AgentRadiology()
        self.biology = AgentBiology()
        self.surgery_risk = AgentSurgeryRisk()
        self.watch_wait = AgentWatchWait()
        self.comorbidity = AgentComorbidity()
        self.ethics = AgentEthicsRules()

    def run(self, profile: DataTwinProfile, mode_runtime: str, model_used: str) -> OrchestrationResult:
        outputs = {
            "radiology": self.radiology.evaluate(profile),
            "biology": self.biology.evaluate(profile),
            "surgery_risk": self.surgery_risk.evaluate(profile),
            "watch_wait": self.watch_wait.evaluate(profile),
            "comorbidity": self.comorbidity.evaluate(profile),
            "ethics_rules": self.ethics.evaluate(profile),
        }

        if outputs["ethics_rules"].scores.get("forced_multidisciplinary", 0.0) >= 1.0:
            consensus = ConsensusReport(
                recommendation="multidisciplinary",
                recommendation_strength="strong",
                disagreement_level="high",
                confidence=92.0,
                rationale="Hard protocol constraints are triggered and require multidisciplinary review.",
                alerts=outputs["ethics_rules"].alerts,
                counterfactuals=self._counterfactuals(profile),
                supporting_agents=list(outputs.keys()),
                mode_runtime=mode_runtime,
                model_used=model_used,
            )
            return OrchestrationResult(
                agent_outputs=outputs,
                consensus=consensus,
                feature_contributions=self._feature_contributions(outputs),
                primary_factors=self._primary_factors(outputs),
            )

        ww_score = (
            outputs["radiology"].scores["ww_candidate"] * 0.38
            + outputs["biology"].scores["ww_candidate"] * 0.27
            + outputs["watch_wait"].scores["ww_candidate"] * 0.25
            + (100.0 - outputs["comorbidity"].scores["frailty"]) * 0.10
        )
        surgery_score = (
            outputs["radiology"].scores["surgery_control"] * 0.40
            + (100.0 - outputs["surgery_risk"].scores["major_complication"]) * 0.28
            + outputs["surgery_risk"].scores["r0_probability"] * 0.22
            + (100.0 - outputs["comorbidity"].scores["frailty"]) * 0.10
        )

        delta = abs(surgery_score - ww_score)
        if delta < 7:
            recommendation = "multidisciplinary"
            disagreement = "high"
            strength = "weak"
            rationale = "Agent disagreement is high; multidisciplinary arbitration is recommended."
        elif surgery_score >= ww_score:
            recommendation = "surgery"
            disagreement = "low" if delta > 18 else "medium"
            strength = "strong" if delta > 18 else "moderate"
            rationale = "Surgery has the strongest consensus signal across oncologic control and safety."
        else:
            recommendation = "watch_wait"
            disagreement = "low" if delta > 18 else "medium"
            strength = "strong" if delta > 18 else "moderate"
            rationale = "Watch-and-wait has the strongest consensus signal across response and quality of life."

        alerts: list[str] = []
        for output in outputs.values():
            alerts.extend(output.alerts)
        alerts = sorted(set(alerts))

        confidence = _clamp(
            sum(output.confidence for output in outputs.values()) / max(1, len(outputs))
            - (8.0 if disagreement == "high" else 0.0),
            35.0,
            95.0,
        )

        consensus = ConsensusReport(
            recommendation=recommendation,
            recommendation_strength=strength,
            disagreement_level=disagreement,
            confidence=confidence,
            rationale=rationale,
            alerts=alerts,
            counterfactuals=self._counterfactuals(profile),
            supporting_agents=list(outputs.keys()),
            mode_runtime=mode_runtime,  # type: ignore[arg-type]
            model_used=model_used,
        )

        return OrchestrationResult(
            agent_outputs=outputs,
            consensus=consensus,
            feature_contributions=self._feature_contributions(outputs),
            primary_factors=self._primary_factors(outputs),
        )

    def _feature_contributions(self, outputs: dict[str, AgentOutput]) -> dict[str, float]:
        return {
            "Radiology_WW": outputs["radiology"].scores.get("ww_candidate", 0.0) - 50.0,
            "Radiology_Surgery": outputs["radiology"].scores.get("surgery_control", 0.0) - 50.0,
            "Biology_WW": outputs["biology"].scores.get("ww_candidate", 0.0) - 50.0,
            "Comorbidity_Frailty": 50.0 - outputs["comorbidity"].scores.get("frailty", 0.0),
            "Surgery_Complications": 50.0 - outputs["surgery_risk"].scores.get("major_complication", 0.0),
            "W&W_Regrowth": 50.0 - outputs["watch_wait"].scores.get("regrowth_2y", 0.0),
        }

    def _primary_factors(self, outputs: dict[str, AgentOutput]) -> list[tuple[str, float, str]]:
        items = [
            ("Radiology signal", outputs["radiology"].scores.get("ww_candidate", 0.0) / 100.0, "Residual burden and TRG"),
            ("Biology signal", outputs["biology"].scores.get("ww_candidate", 0.0) / 100.0, "CEA trend and blood profile"),
            ("Surgery R0", outputs["surgery_risk"].scores.get("r0_probability", 0.0) / 100.0, "Resection margin quality"),
            ("Frailty", outputs["comorbidity"].scores.get("frailty", 0.0) / 100.0, "ECOG/ASA/age tolerance"),
        ]
        return items

    def _counterfactuals(self, profile: DataTwinProfile) -> list[str]:
        residual_cm = float(profile.get("residual_size_cm", 0.0))
        ace_baseline = float(profile.get("ace_baseline", 0.0))
        ace_current = float(profile.get("ace_current", 0.0))
        trg = int(profile.get("trg", 3))

        messages: list[str] = []
        if residual_cm > 2.0:
            messages.append(
                f"If residual lesion decreased by at least {residual_cm - 2.0:.1f} cm, watch-and-wait would become eligible."
            )
        if trg > 2:
            messages.append("If TRG improved to 2 or less, watch-and-wait eligibility would increase.")
        if ace_baseline > 0 and ace_current > 0:
            target = max(0.0, ace_current * 0.90)
            messages.append(
                f"If CEA/ACE current value dropped by 10% to {target:.2f}, watch-and-wait score would improve."
            )
        if not messages:
            messages.append("If CRM margin improved by 1 mm, surgery confidence would increase.")
        return messages

