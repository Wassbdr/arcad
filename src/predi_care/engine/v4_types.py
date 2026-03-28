"""Core v4 data contracts for Digital Twin and multi-agent orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


FeatureSource = Literal["dataset", "simulated", "simulation", "derived", "llm"]
FeatureQuality = Literal["observed", "imputed", "unknown"]
RuntimeMode = Literal["openai", "alt_llm", "heuristic"]


@dataclass
class FeatureTrace:
    """Traceability metadata for one feature used by the engine."""

    value: Any
    source: FeatureSource
    quality: FeatureQuality


@dataclass
class DataTwinProfile:
    """Unified patient profile used by v4 inference."""

    patient_id: str
    core_clinical: dict[str, Any]
    imaging_stub: dict[str, Any] = field(default_factory=dict)
    omics_stub: dict[str, Any] = field(default_factory=dict)
    pros_stub: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, FeatureTrace] = field(default_factory=dict)
    missing_inputs: list[str] = field(default_factory=list)

    def get(self, key: str, default: Any = None) -> Any:
        return self.core_clinical.get(key, default)


@dataclass
class ComplicationRisk:
    """One typed complication estimate with provenance."""

    name: str
    value: float
    source: FeatureSource
    confidence: float
    supporting_factors: list[str] = field(default_factory=list)


@dataclass
class AgentOutput:
    """Normalized output contract for every expert agent."""

    agent_name: str
    scores: dict[str, float] = field(default_factory=dict)
    rationale: list[str] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)
    counterfactuals: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    feature_sources: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0


@dataclass
class ConsensusReport:
    """Coordinator synthesis over all agent outputs."""

    recommendation: str
    recommendation_strength: str
    disagreement_level: Literal["low", "medium", "high"]
    confidence: float
    rationale: str
    alerts: list[str] = field(default_factory=list)
    counterfactuals: list[str] = field(default_factory=list)
    supporting_agents: list[str] = field(default_factory=list)
    mode_runtime: RuntimeMode = "heuristic"
    model_used: str = "heuristic"


@dataclass
class SafetyInvariantResult:
    """Single safety rule result."""

    name: str
    passed: bool
    severity: Literal["warning", "critical"]
    message: str


@dataclass
class SafetyCheckReport:
    """Formalized safety envelope report for one inference."""

    passed: bool
    invariants: list[SafetyInvariantResult] = field(default_factory=list)
    blocking_violations: list[str] = field(default_factory=list)


@dataclass
class ScenarioResultV4:
    """Scenario-level outcomes and typed complications."""

    label: str
    eligible: bool
    eligibility_score: float
    survival_2y: float
    survival_5y: float
    local_recurrence_2y: float
    local_recurrence_5y: float
    distant_metastasis_5y: float
    major_complication: float
    qol_score: float
    r0_probability: float
    survival_curve: dict[int, float]
    complications: list[ComplicationRisk] = field(default_factory=list)
    source: FeatureSource = "simulated"


@dataclass
class EngineResultV4:
    """Top-level v4 engine output consumed by UI and exports."""

    patient_profile: DataTwinProfile
    surgery: ScenarioResultV4
    watch_wait: ScenarioResultV4
    consensus: ConsensusReport
    safety: SafetyCheckReport
    feature_contributions: dict[str, float]
    primary_factors: list[tuple[str, float, str]]
    indicator_sources: dict[str, FeatureSource] = field(default_factory=dict)
    medical_disclaimer: str = (
        "Outil d'aide a la decision clinique. Cette analyse ne remplace pas une "
        "discussion pluridisciplinaire ni le jugement medical."
    )

    @property
    def mode_runtime(self) -> RuntimeMode:
        return self.consensus.mode_runtime
