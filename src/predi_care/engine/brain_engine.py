"""PREDI-Care v4 Digital Twin engine with multi-agent orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from predi_care.engine.datatwin import build_profile_from_patient_input, build_profile_from_v3_row
from predi_care.engine.llm_client import MedicalLLMResponse, call_medical_llm_with_runtime
from predi_care.engine.multi_agent import OrchestrationResult, RCPOrchestrator
from predi_care.engine.patient_types import PatientInput
from predi_care.engine.safety import SafetyEnvelopeChecker, apply_curve_safety, clamp_probability
from predi_care.engine.v4_types import (
    ComplicationRisk,
    EngineResultV4,
    SafetyCheckReport,
    ScenarioResultV4,
)


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _default_calibration() -> dict[str, float]:
    return {
        "surgery_major_complication": 12.6,
        "surgery_local_recurrence_5y": 8.0,
        "surgery_distant_metastasis_5y": 25.0,
        "surgery_dfs_5y": 71.0,
        "surgery_os_5y": 89.0,
        "ww_regrowth_2y": 22.0,
        "ww_distant_metastasis_5y": 7.0,
        "ww_dfs_5y": 72.0,
        "ww_os_5y": 87.0,
    }


def _load_v3_calibration() -> dict[str, float]:
    calibration = _default_calibration()
    dataset_path = Path(__file__).resolve().parents[3] / "data" / "greccar_synthetic_decision_support_cohort_v3.csv"
    if not dataset_path.exists():
        return calibration
    try:
        import pandas as pd

        df = pd.read_csv(dataset_path)
    except Exception:
        return calibration

    if "final_management" not in df.columns:
        return calibration

    surgery_mask = df["final_management"].isin(
        ["tme_direct", "local_excision", "local_excision_then_completion_tme"]
    )
    ww_mask = df["final_management"] == "watch_and_wait"

    surgery = df[surgery_mask]
    watch_wait = df[ww_mask]

    def _mean(frame: Any, column: str, fallback: float) -> float:
        if column not in frame.columns:
            return fallback
        series = frame[column].dropna()
        if len(series) == 0:
            return fallback
        return float(series.mean() * 100.0)

    calibration["surgery_major_complication"] = _mean(
        surgery, "postop_major_complication", calibration["surgery_major_complication"] / 100.0
    )
    calibration["surgery_local_recurrence_5y"] = _mean(
        surgery, "local_recurrence_5y_after_resection", calibration["surgery_local_recurrence_5y"] / 100.0
    )
    calibration["surgery_distant_metastasis_5y"] = _mean(
        surgery, "distant_metastasis_5y", calibration["surgery_distant_metastasis_5y"] / 100.0
    )
    calibration["surgery_dfs_5y"] = _mean(
        surgery, "disease_free_5y", calibration["surgery_dfs_5y"] / 100.0
    )
    calibration["surgery_os_5y"] = _mean(
        surgery, "alive_5y", calibration["surgery_os_5y"] / 100.0
    )
    calibration["ww_regrowth_2y"] = _mean(
        watch_wait, "local_regrowth_2y", calibration["ww_regrowth_2y"] / 100.0
    )
    calibration["ww_distant_metastasis_5y"] = _mean(
        watch_wait, "distant_metastasis_5y", calibration["ww_distant_metastasis_5y"] / 100.0
    )
    calibration["ww_dfs_5y"] = _mean(
        watch_wait, "disease_free_5y", calibration["ww_dfs_5y"] / 100.0
    )
    calibration["ww_os_5y"] = _mean(
        watch_wait, "alive_5y", calibration["ww_os_5y"] / 100.0
    )
    return calibration


def _build_survival_curve(survival_2y: float, survival_5y: float) -> dict[int, float]:
    months = [1, 3, 6, 12, 24, 36, 60]
    anchors = {
        1: min(100.0, survival_2y + 10.0),
        3: min(100.0, survival_2y + 7.0),
        6: min(100.0, survival_2y + 5.0),
        12: min(100.0, survival_2y + 3.0),
        24: survival_2y,
        36: (survival_2y + survival_5y) / 2.0,
        60: survival_5y,
    }
    return {month: clamp_probability(anchors[month]) for month in months}


def _estimate_lars_risk(residual_cm: float, low_rectum: bool) -> float:
    base = 25.0 + residual_cm * 6.0
    if low_rectum:
        base += 18.0
    return clamp_probability(base)


@dataclass
class EngineRuntimeMeta:
    mode_runtime: str
    model_used: str
    llm_response: MedicalLLMResponse | None
    errors: list[str]


class BrainEngineV4:
    """Main v4 engine: Digital Twin + multi-agent + safety envelope."""

    def __init__(self) -> None:
        self.calibration = _load_v3_calibration()
        self.orchestrator = RCPOrchestrator()
        self.safety_checker = SafetyEnvelopeChecker()

    def run_decision(self, patient_input: PatientInput) -> EngineResultV4:
        profile = build_profile_from_patient_input(patient_input)
        return self.run_profile(profile)

    def run_dataset_row(self, row: Mapping[str, Any]) -> EngineResultV4:
        profile = build_profile_from_v3_row(row)
        return self.run_profile(profile)

    def run_profile(self, profile: Any) -> EngineResultV4:
        runtime = self._resolve_runtime(profile)
        orchestration = self.orchestrator.run(profile, runtime.mode_runtime, runtime.model_used)
        if runtime.mode_runtime == "heuristic":
            orchestration.consensus.alerts.append(
                f"Fallback heuristique actif: {self._runtime_error_summary(runtime.errors)}"
            )
        surgery = self._build_surgery_result(profile, orchestration, runtime)
        watch_wait = self._build_watch_wait_result(profile, orchestration, runtime)

        surgery = apply_curve_safety(surgery)
        watch_wait = apply_curve_safety(watch_wait)

        provisional = EngineResultV4(
            patient_profile=profile,
            surgery=surgery,
            watch_wait=watch_wait,
            consensus=orchestration.consensus,
            safety=SafetyCheckReport(passed=True, invariants=[], blocking_violations=[]),
            feature_contributions=orchestration.feature_contributions,
            primary_factors=orchestration.primary_factors,
            indicator_sources=self._indicator_sources(runtime.mode_runtime),
        )
        safety_report = self.safety_checker.check(provisional)

        result = EngineResultV4(
            patient_profile=profile,
            surgery=surgery,
            watch_wait=watch_wait,
            consensus=orchestration.consensus,
            safety=safety_report,
            feature_contributions=orchestration.feature_contributions,
            primary_factors=orchestration.primary_factors,
            indicator_sources=self._indicator_sources(runtime.mode_runtime),
        )

        if not result.safety.passed:
            result.consensus.recommendation = "multidisciplinary"
            result.consensus.recommendation_strength = "strong"
            result.consensus.alerts.extend(
                [f"Safety invariant failed: {name}" for name in result.safety.blocking_violations]
            )

        return result

    def _resolve_runtime(self, profile: Any) -> EngineRuntimeMeta:
        patient_context = self._build_llm_context(profile)
        runtime = call_medical_llm_with_runtime(patient_context)
        return EngineRuntimeMeta(
            mode_runtime=runtime.mode_runtime,
            model_used=runtime.model_used,
            llm_response=runtime.response,
            errors=list(runtime.errors),
        )

    def _runtime_error_summary(self, errors: list[str]) -> str:
        if not errors:
            return "aucun detail technique disponible."
        first = errors[0]
        if "openai:unavailable" in first:
            return "cle OpenAI absente ou non lue."
        if "alt_llm:unavailable" in first:
            return "provider alternatif non configure."
        return first.replace(":", " | ")

    def _build_llm_context(self, profile: Any) -> dict[str, Any]:
        return {
            "clinical": {
                "cT": profile.get("ct_stage"),
                "cN": profile.get("cn_stage"),
                "cM": profile.get("cm_stage"),
                "age": profile.get("age"),
                "ecog": profile.get("ecog"),
                "asa_score": profile.get("asa_score"),
            },
            "response": {
                "trg": profile.get("trg"),
                "residual_size_cm": profile.get("residual_size_cm"),
                "clinical_response": profile.get("clinical_response"),
            },
            "imaging": {
                "crm_status": profile.get("crm_status"),
                "crm_distance_mm": profile.get("crm_distance_mm"),
                "emvi": profile.get("emvi"),
                "imaging_quality": profile.get("imaging_quality"),
            },
            "biology": {
                "ace_baseline": profile.get("ace_baseline"),
                "ace_current": profile.get("ace_current"),
                "albumin": profile.get("albumin"),
                "hemoglobin": profile.get("hemoglobin"),
                "msi_status": profile.get("msi_status"),
            },
            "comorbidities": {
                "smoking": profile.get("smoking"),
                "diabetes": profile.get("diabetes"),
            },
        }

    def _build_surgery_result(
        self,
        profile: Any,
        orchestration: OrchestrationResult,
        runtime: EngineRuntimeMeta,
    ) -> ScenarioResultV4:
        scores = orchestration.agent_outputs
        residual_cm = float(profile.get("residual_size_cm", 0.0))
        low_rectum = float(profile.get("distance_marge_anale", 8.0)) < 5.0

        dfs_5y = (
            self.calibration["surgery_dfs_5y"]
            + (scores["radiology"].scores["surgery_control"] - 50.0) * 0.12
            - (scores["comorbidity"].scores["frailty"] - 30.0) * 0.08
        )
        dfs_2y = min(100.0, dfs_5y + 9.0)
        local_5y = (
            self.calibration["surgery_local_recurrence_5y"]
            + max(0.0, residual_cm - 1.0) * 3.5
            + (5.0 if profile.get("crm_status") == "positive" else 0.0)
        )
        local_2y = local_5y * 0.65
        distant_5y = (
            self.calibration["surgery_distant_metastasis_5y"]
            + (6.0 if profile.get("emvi") else 0.0)
            + (3.0 if profile.get("cm_stage") == "cM1" else 0.0)
        )
        major_comp = (
            scores["surgery_risk"].scores["major_complication"] * 0.65
            + scores["biology"].scores["surgery_comp_risk"] * 0.35
        )
        r0_probability = scores["surgery_risk"].scores["r0_probability"]
        lars_risk = _estimate_lars_risk(residual_cm, low_rectum)
        leak_risk = clamp_probability(4.0 + (6.0 if profile.get("smoking") else 0.0) + max(0, int(profile.get("asa_score", 2)) - 2) * 1.5)
        infectious = clamp_probability(9.0 + major_comp * 0.35)
        urinary = clamp_probability(5.0 + (4.0 if low_rectum else 0.0))
        stoma = clamp_probability(12.0 + (18.0 if low_rectum else 0.0))
        medical = clamp_probability(7.0 + max(0.0, float(profile.get("age", 62)) - 70.0) * 0.3)
        qol = clamp_probability(88.0 - lars_risk * 0.35 - major_comp * 0.25 - stoma * 0.10)

        if runtime.llm_response is not None:
            # Blend deterministic simulation with LLM response while keeping bounded output.
            dfs_2y = (dfs_2y * 0.7) + (runtime.llm_response.surgery.survival_dfs_2y * 0.3)
            dfs_5y = (dfs_5y * 0.7) + (runtime.llm_response.surgery.survival_dfs_5y * 0.3)
            local_5y = (local_5y * 0.65) + (runtime.llm_response.surgery.recurrence_local_5y * 0.35)
            distant_5y = (distant_5y * 0.65) + (runtime.llm_response.surgery.recurrence_systemic_2y * 0.35)
            major_comp = (major_comp * 0.65) + (runtime.llm_response.surgery.complication_rate * 0.35)
            r0_probability = (r0_probability * 0.6) + (runtime.llm_response.surgery.r0_probability * 0.4)
            lars_risk = (lars_risk * 0.65) + (runtime.llm_response.surgery.lars_risk * 0.35)

        complications = [
            ComplicationRisk("LARS syndrome", lars_risk, "simulated", 78.0, ["Tumor height", "Residual burden"]),
            ComplicationRisk("Anastomotic leak", leak_risk, "dataset", 75.0, ["Smoking", "ASA"]),
            ComplicationRisk("Infectious complication", infectious, "dataset", 72.0, ["Comorbidity", "Major complications"]),
            ComplicationRisk("Urinary dysfunction", urinary, "simulated", 65.0, ["Low rectum surgery"]),
            ComplicationRisk("Stoma-related complication", stoma, "dataset", 68.0, ["Tumor distance from anal verge"]),
            ComplicationRisk("Medical systemic complication", medical, "dataset", 70.0, ["Age", "Frailty"]),
        ]

        return ScenarioResultV4(
            label="surgery",
            eligible=True,
            eligibility_score=100.0,
            survival_2y=clamp_probability(dfs_2y),
            survival_5y=clamp_probability(dfs_5y),
            local_recurrence_2y=clamp_probability(local_2y),
            local_recurrence_5y=clamp_probability(local_5y),
            distant_metastasis_5y=clamp_probability(distant_5y),
            major_complication=clamp_probability(major_comp),
            qol_score=qol,
            r0_probability=clamp_probability(r0_probability),
            survival_curve=_build_survival_curve(clamp_probability(dfs_2y), clamp_probability(dfs_5y)),
            complications=complications,
            source="dataset",
        )

    def _build_watch_wait_result(
        self,
        profile: Any,
        orchestration: OrchestrationResult,
        runtime: EngineRuntimeMeta,
    ) -> ScenarioResultV4:
        scores = orchestration.agent_outputs
        residual_cm = float(profile.get("residual_size_cm", 0.0))
        trg = int(profile.get("trg", 3))
        ww_candidate = scores["watch_wait"].scores["ww_candidate"] * 0.7 + scores["biology"].scores["ww_candidate"] * 0.3
        ww_candidate = clamp_probability(ww_candidate)
        eligible = ww_candidate >= 60.0 and residual_cm <= 2.0 and trg <= 2

        regrowth_2y = (
            self.calibration["ww_regrowth_2y"]
            + max(0.0, residual_cm - 1.0) * 6.5
            + max(0, trg - 2) * 7.0
        )
        local_5y = regrowth_2y * 1.25
        distant_5y = self.calibration["ww_distant_metastasis_5y"] + regrowth_2y * 0.12
        dfs_5y = self.calibration["ww_dfs_5y"] - max(0.0, regrowth_2y - 20.0) * 0.35
        dfs_2y = min(100.0, dfs_5y + 7.0)
        burden = clamp_probability(35.0 + regrowth_2y * 0.6)
        anxiety = clamp_probability(25.0 + burden * 0.4)
        systemic_conditional = clamp_probability(regrowth_2y * 0.35)
        qol = clamp_probability(94.0 - burden * 0.25 - anxiety * 0.10)

        if runtime.llm_response is not None:
            dfs_2y = (dfs_2y * 0.7) + (runtime.llm_response.watch_wait.survival_dfs_2y * 0.3)
            dfs_5y = (dfs_5y * 0.7) + (runtime.llm_response.watch_wait.survival_dfs_5y * 0.3)
            regrowth_2y = (regrowth_2y * 0.7) + (runtime.llm_response.watch_wait.regrowth_2y * 0.3)
            local_5y = (local_5y * 0.7) + (runtime.llm_response.watch_wait.regrowth_5y * 0.3)
            systemic_conditional = (
                systemic_conditional * 0.6
                + runtime.llm_response.watch_wait.systemic_relapse_if_regrowth * 0.4
            )

        complications = [
            ComplicationRisk("Local regrowth risk", clamp_probability(regrowth_2y), "dataset", 80.0, ["TRG", "Residual lesion"]),
            ComplicationRisk(
                "Conditional systemic relapse if regrowth",
                clamp_probability(systemic_conditional),
                "simulated",
                72.0,
                ["Regrowth risk"],
            ),
            ComplicationRisk("Surveillance burden", burden, "simulated", 64.0, ["Follow-up intensity"]),
            ComplicationRisk("Follow-up anxiety burden", anxiety, "simulated", 60.0, ["PRO synthetic stub"]),
        ]

        return ScenarioResultV4(
            label="watch_wait",
            eligible=eligible,
            eligibility_score=ww_candidate,
            survival_2y=clamp_probability(dfs_2y),
            survival_5y=clamp_probability(dfs_5y),
            local_recurrence_2y=clamp_probability(regrowth_2y),
            local_recurrence_5y=clamp_probability(local_5y),
            distant_metastasis_5y=clamp_probability(distant_5y),
            major_complication=2.0,
            qol_score=qol,
            r0_probability=0.0,
            survival_curve=_build_survival_curve(clamp_probability(dfs_2y), clamp_probability(dfs_5y)),
            complications=complications,
            source="dataset",
        )

    def _indicator_sources(self, mode_runtime: str) -> dict[str, str]:
        base = {
            "surgery.major_complication": "dataset",
            "surgery.local_recurrence_5y": "dataset",
            "watch_wait.local_regrowth_2y": "dataset",
            "watch_wait.distant_metastasis_5y": "dataset",
            "watch_wait.surveillance_burden": "simulated",
            "watch_wait.anxiety_burden": "simulated",
            "explainability.feature_contributions": "simulated",
        }
        if mode_runtime in {"openai", "alt_llm"}:
            base["llm.runtime"] = "llm"
        else:
            base["llm.runtime"] = "simulated"
        return base


def create_brain_engine(version: str = "v4") -> BrainEngineV4:
    normalized = version.strip().lower()
    if normalized in {"v4", "v3", "latest"}:
        return BrainEngineV4()
    raise ValueError(f"Unknown brain engine version: {version}")
