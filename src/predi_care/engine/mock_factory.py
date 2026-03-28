from __future__ import annotations

from pathlib import Path
from random import Random
from typing import Any, List

from predi_care.engine.patient_types import PatientInput

try:
    import pandas as pd
except Exception:  # pragma: no cover - optional at runtime for minimal environments
    pd = None  # type: ignore[assignment]


DEMO_PROFILES: dict[str, dict[str, Any]] = {
    "bon_repondeur": {
        "label": "Patient A - excellent responder",
        "description": "TRG 2, residual lesion 0.5 cm, normalized ACE trend.",
        "data": {
            "ct_stage": "cT2",
            "cn_stage": "cN0",
            "cm_stage": "cM0",
            "ace_baseline": 6.0,
            "ace_current": 1.0,
            "residual_tumor_ratio": 8.0,
            "residual_size_cm": 0.5,
            "imaging_quality": "Elevee",
            "age": 54,
            "performance_status": 0,
            "distance_marge_anale": 4.0,
            "delay_weeks_post_rct": 10,
            "protocol_neoadjuvant": "RCT standard",
            "emvi": False,
            "mrtrg": 2,
            "asa_score": 1,
            "smoking": False,
            "diabetes": False,
            "albumin": 43.0,
            "hemoglobin": 14.3,
            "msi_status": "MSS/MSI-L",
            "crm_distance_mm": 8.0,
        },
    },
    "mauvais_repondeur": {
        "label": "Patient B - poor responder",
        "description": "TRG 5, residual lesion 3.5 cm, threatened CRM and high ACE.",
        "data": {
            "ct_stage": "cT4",
            "cn_stage": "cN2",
            "cm_stage": "cM0",
            "ace_baseline": 14.0,
            "ace_current": 11.5,
            "residual_tumor_ratio": 75.0,
            "residual_size_cm": 3.5,
            "imaging_quality": "Moyenne",
            "age": 69,
            "performance_status": 2,
            "distance_marge_anale": 9.0,
            "delay_weeks_post_rct": 8,
            "protocol_neoadjuvant": "TNT",
            "emvi": True,
            "mrtrg": 5,
            "asa_score": 3,
            "smoking": True,
            "diabetes": True,
            "albumin": 33.0,
            "hemoglobin": 11.0,
            "msi_status": "MSS/MSI-L",
            "crm_distance_mm": 0.5,
        },
    },
    "intermediaire": {
        "label": "Patient C - multidisciplinary profile",
        "description": "TRG 3 with intermediate lesion burden and mixed signals.",
        "data": {
            "ct_stage": "cT3",
            "cn_stage": "cN1",
            "cm_stage": "cM0",
            "ace_baseline": 9.0,
            "ace_current": 6.5,
            "residual_tumor_ratio": 30.0,
            "residual_size_cm": 1.5,
            "imaging_quality": "Moyenne",
            "age": 61,
            "performance_status": 1,
            "distance_marge_anale": 6.0,
            "delay_weeks_post_rct": 9,
            "protocol_neoadjuvant": "RCT standard",
            "emvi": False,
            "mrtrg": 3,
            "asa_score": 2,
            "smoking": False,
            "diabetes": False,
            "albumin": 38.5,
            "hemoglobin": 12.8,
            "msi_status": "Non teste",
            "crm_distance_mm": 2.0,
        },
    },
}


def generate_mock_patient(seed: int = 7) -> PatientInput:
    rng = Random(seed)

    ct_stage = rng.choice(["cT1", "cT2", "cT3", "cT4"])
    cn_stage = rng.choice(["cN0", "cN1", "cN2"])
    cm_stage = rng.choice(["cM0", "cM0", "cM0", "cM1"])

    age = rng.randint(38, 84)
    performance_status = rng.choice([0, 1, 1, 2, 2, 3])

    ace_baseline = round(rng.uniform(2.5, 28.0), 1)
    ace_current = round(max(0.2, ace_baseline * rng.uniform(0.25, 1.05)), 1)

    residual_tumor_ratio = round(rng.uniform(2.0, 68.0), 1)
    imaging_quality = rng.choice(["Elevee", "Moyenne"])

    # New clinical fields
    distance_marge_anale = round(rng.uniform(2.0, 12.0), 1)
    delay_weeks_post_rct = rng.randint(4, 16)
    protocol_neoadjuvant = rng.choice(["RCT standard", "FOLFIRINOX+CAP50", "TNT"])
    emvi = rng.choice([True, False, False, False])
    mrtrg = rng.choice([1, 2, 3, 4, 5])
    asa_score = rng.choice([1, 1, 2, 2, 3])
    smoking = rng.choice([True, False, False])
    diabetes = rng.choice([True, False, False])
    albumin = round(rng.uniform(30.0, 45.0), 1)
    hemoglobin = round(rng.uniform(9.0, 15.0), 1)
    msi_status = rng.choice(["MSS/MSI-L", "MSS/MSI-L", "dMMR/MSI-H", "Non teste"])

    return {
        "ct_stage": ct_stage,
        "cn_stage": cn_stage,
        "cm_stage": cm_stage,
        "ace_baseline": ace_baseline,
        "ace_current": ace_current,
        "residual_tumor_ratio": residual_tumor_ratio,
        "imaging_quality": imaging_quality,
        "age": age,
        "performance_status": performance_status,
        "distance_marge_anale": distance_marge_anale,
        "delay_weeks_post_rct": delay_weeks_post_rct,
        "protocol_neoadjuvant": protocol_neoadjuvant,
        "emvi": emvi,
        "mrtrg": mrtrg,
        "asa_score": asa_score,
        "smoking": smoking,
        "diabetes": diabetes,
        "albumin": albumin,
        "hemoglobin": hemoglobin,
        "msi_status": msi_status,
    }


def generate_mock_cohort(size: int = 16, base_seed: int = 10) -> List[PatientInput]:
    return [generate_mock_patient(seed=base_seed + idx) for idx in range(size)]


# Scenarios cliniques predefinis pour demo et tests
PRESET_SCENARIOS: dict[str, PatientInput] = {
    "Candidat ideal Watch & Wait": {
        "ct_stage": "cT2",
        "cn_stage": "cN0",
        "cm_stage": "cM0",
        "ace_baseline": 6.5,
        "ace_current": 2.0,
        "residual_tumor_ratio": 8.0,
        "imaging_quality": "Elevee",
        "age": 52,
        "performance_status": 0,
        "distance_marge_anale": 3.5,
        "delay_weeks_post_rct": 10,
        "protocol_neoadjuvant": "RCT standard",
        "emvi": False,
        "mrtrg": 2,
        "asa_score": 1,
        "smoking": False,
        "diabetes": False,
        "albumin": 42.0,
        "hemoglobin": 14.5,
        "msi_status": "MSS/MSI-L",
    },
    "Indication chirurgicale claire": {
        "ct_stage": "cT4",
        "cn_stage": "cN2",
        "cm_stage": "cM0",
        "ace_baseline": 18.0,
        "ace_current": 14.5,
        "residual_tumor_ratio": 42.0,
        "imaging_quality": "Elevee",
        "age": 68,
        "performance_status": 1,
        "distance_marge_anale": 8.0,
        "delay_weeks_post_rct": 8,
        "protocol_neoadjuvant": "FOLFIRINOX+CAP50",
        "emvi": True,
        "mrtrg": 4,
        "asa_score": 3,
        "smoking": True,
        "diabetes": True,
        "albumin": 34.0,
        "hemoglobin": 11.2,
        "msi_status": "MSS/MSI-L",
    },
    "Cas de conflit decisionnel": {
        "ct_stage": "cT2",
        "cn_stage": "cN0",
        "cm_stage": "cM0",
        "ace_baseline": 8.0,
        "ace_current": 7.2,
        "residual_tumor_ratio": 12.0,
        "imaging_quality": "Moyenne",
        "age": 61,
        "performance_status": 0,
        "distance_marge_anale": 6.0,
        "delay_weeks_post_rct": 9,
        "protocol_neoadjuvant": "TNT",
        "emvi": False,
        "mrtrg": 3,
        "asa_score": 2,
        "smoking": False,
        "diabetes": False,
        "albumin": 39.0,
        "hemoglobin": 13.0,
        "msi_status": "Non teste",
    },
    "Metastatique (cM1)": {
        "ct_stage": "cT3",
        "cn_stage": "cN1",
        "cm_stage": "cM1",
        "ace_baseline": 22.0,
        "ace_current": 18.0,
        "residual_tumor_ratio": 35.0,
        "imaging_quality": "Elevee",
        "age": 72,
        "performance_status": 2,
        "distance_marge_anale": 10.0,
        "delay_weeks_post_rct": 7,
        "protocol_neoadjuvant": "RCT standard",
        "emvi": True,
        "mrtrg": 4,
        "asa_score": 3,
        "smoking": True,
        "diabetes": True,
        "albumin": 32.0,
        "hemoglobin": 10.5,
        "msi_status": "MSS/MSI-L",
    },
    "Reponse biologique excellente": {
        "ct_stage": "cT3",
        "cn_stage": "cN1",
        "cm_stage": "cM0",
        "ace_baseline": 15.0,
        "ace_current": 3.5,
        "residual_tumor_ratio": 18.0,
        "imaging_quality": "Elevee",
        "age": 58,
        "performance_status": 0,
        "distance_marge_anale": 5.0,
        "delay_weeks_post_rct": 12,
        "protocol_neoadjuvant": "TNT",
        "emvi": False,
        "mrtrg": 2,
        "asa_score": 1,
        "smoking": False,
        "diabetes": False,
        "albumin": 44.0,
        "hemoglobin": 15.0,
        "msi_status": "dMMR/MSI-H",
    },
}

for profile_name, profile_payload in DEMO_PROFILES.items():
    PRESET_SCENARIOS[profile_payload["label"]] = PatientInput(**profile_payload["data"])


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class RealisticPatientFactory:
    """Dataset-driven patient generator for v4 demos.

    This class samples from empirical distributions extracted from the v3 dataset.
    If no dataset is available, generation falls back to the legacy random factory.
    """

    def __init__(self, df: Any | None = None, dataset_path: str | Path | None = None) -> None:
        self.rng = Random(42)
        self.df = None
        self.dataset_path = (
            Path(dataset_path)
            if dataset_path is not None
            else Path(__file__).resolve().parents[3] / "data" / "greccar_synthetic_decision_support_cohort_v3.csv"
        )

        if df is not None:
            self.df = df
        elif pd is not None and self.dataset_path.exists():
            try:
                self.df = pd.read_csv(self.dataset_path)
            except Exception:
                self.df = None

        self._fit()

    def _fit(self) -> None:
        self.trg_values = [2, 3, 4]
        self.trg_weights = [0.25, 0.5, 0.25]
        self.age_mean = 62.0
        self.age_std = 10.0
        self.residual_mean = 1.4
        self.residual_std = 0.7
        self.ace_baseline_mean = 8.0
        self.ace_current_mean = 4.0

        if self.df is None:
            return
        try:
            trg_series = self.df["restaging_mrTRG"].dropna().astype(int)
            weight_map = trg_series.value_counts(normalize=True).sort_index()
            if len(weight_map) > 0:
                self.trg_values = [int(item) for item in weight_map.index.tolist()]
                self.trg_weights = [float(item) for item in weight_map.values.tolist()]
            residual_series = self.df["restaging_residual_lesion_cm"].dropna().astype(float)
            if len(residual_series) > 0:
                self.residual_mean = float(residual_series.mean())
                self.residual_std = max(0.3, float(residual_series.std()))
            age_series = self.df["age_years"].dropna().astype(float)
            if len(age_series) > 0:
                self.age_mean = float(age_series.mean())
                self.age_std = max(5.0, float(age_series.std()))
            ace_baseline = self.df["cea_baseline_ng_ml"].dropna().astype(float)
            ace_current = self.df["cea_current_ng_ml"].dropna().astype(float)
            if len(ace_baseline) > 0:
                self.ace_baseline_mean = float(ace_baseline.mean())
            if len(ace_current) > 0:
                self.ace_current_mean = float(ace_current.mean())
        except Exception:
            return

    def _row_to_patient(self, row: Any) -> PatientInput:
        ratio_native = float(row.get("residual_tumor_ratio_native", 0.2))
        residual_ratio = _clamp(ratio_native * 100.0, 0.0, 100.0)
        return PatientInput(
            ct_stage=str(row.get("baseline_cT", "cT3")),
            cn_stage=str(row.get("baseline_cN", "cN0")),
            cm_stage=str(row.get("cM", "cM0")),
            ace_baseline=float(row.get("cea_baseline_ng_ml", self.ace_baseline_mean)),
            ace_current=float(row.get("cea_current_ng_ml", self.ace_current_mean)),
            residual_tumor_ratio=float(residual_ratio),
            residual_size_cm=float(row.get("restaging_residual_lesion_cm", residual_ratio / 20.0)),
            imaging_quality="Elevee" if str(row.get("imaging_quality", "acceptable")).lower() == "good" else "Moyenne",
            age=int(float(row.get("age_years", self.age_mean))),
            performance_status=int(float(row.get("ecog_score", 1))),
            distance_marge_anale=float(row.get("tumor_distance_from_anal_verge_cm", 8.0)),
            delay_weeks_post_rct=int(float(row.get("initial_restaging_weeks_post_crt", 8))),
            protocol_neoadjuvant=str(row.get("concomitant_chemotherapy", "RCT standard")),
            emvi=bool(row.get("baseline_emvi", False)),
            mrtrg=int(float(row.get("restaging_mrTRG", 3))),
            asa_score={"I": 1, "II": 2, "III": 3, "IV": 4}.get(str(row.get("asa_class", "II")).upper(), 2),
            smoking=str(row.get("smoking_status", "never")).strip().lower() == "current",
            diabetes=bool(row.get("diabetes", False)),
            albumin=float(row.get("albumin_g_l", 40.0)),
            hemoglobin=float(row.get("hemoglobin_g_dl", 13.0)),
            msi_status="dMMR/MSI-H" if str(row.get("msi_status", "")).lower() == "msi_h_dmmr" else "MSS/MSI-L",
            crm_distance_mm=float(row.get("baseline_mri_crm_mm", 5.0)),
        )

    def generate(self, profile: str = "random", seed: int | None = None) -> PatientInput:
        if seed is not None:
            self.rng = Random(seed)

        if profile in DEMO_PROFILES:
            return PatientInput(**DEMO_PROFILES[profile]["data"])

        if profile == "profil_dataset" and self.df is not None and len(self.df) > 0:
            sampled = self.df.sample(n=1, random_state=self.rng.randint(0, 10_000_000)).iloc[0]
            return self._row_to_patient(sampled)

        if self.df is None:
            return generate_mock_patient(seed=seed or self.rng.randint(1, 10_000))

        trg = self.rng.choices(self.trg_values, weights=self.trg_weights, k=1)[0]
        residual_cm = _clamp(self.rng.gauss(self.residual_mean, self.residual_std), 0.0, 5.5)
        residual_ratio = _clamp(residual_cm * 20.0, 0.0, 100.0)
        age = int(_clamp(self.rng.gauss(self.age_mean, self.age_std), 18.0, 95.0))
        ace_baseline = _clamp(self.rng.gauss(self.ace_baseline_mean, 3.0), 1.0, 60.0)
        ace_current = _clamp(self.rng.gauss(self.ace_current_mean, 2.5), 0.5, 60.0)

        return PatientInput(
            ct_stage=self.rng.choice(["cT2", "cT3", "cT4"]),
            cn_stage=self.rng.choice(["cN0", "cN1", "cN2"]),
            cm_stage=self.rng.choice(["cM0", "cM0", "cM0", "cM1"]),
            ace_baseline=round(ace_baseline, 1),
            ace_current=round(min(ace_baseline, ace_current), 1),
            residual_tumor_ratio=round(residual_ratio, 1),
            residual_size_cm=round(residual_cm, 1),
            imaging_quality=self.rng.choice(["Elevee", "Moyenne", "Basse"]),
            age=age,
            performance_status=self.rng.choice([0, 1, 1, 2, 2, 3]),
            distance_marge_anale=round(self.rng.uniform(2.0, 12.0), 1),
            delay_weeks_post_rct=self.rng.randint(4, 16),
            protocol_neoadjuvant=self.rng.choice(["RCT standard", "FOLFIRINOX+CAP50", "TNT"]),
            emvi=self.rng.choice([True, False, False]),
            mrtrg=int(trg),
            asa_score=self.rng.choice([1, 2, 2, 3]),
            smoking=self.rng.choice([True, False, False]),
            diabetes=self.rng.choice([True, False, False]),
            albumin=round(self.rng.uniform(30.0, 45.0), 1),
            hemoglobin=round(self.rng.uniform(9.0, 15.0), 1),
            msi_status=self.rng.choice(["MSS/MSI-L", "dMMR/MSI-H", "Non teste"]),
            crm_distance_mm=round(self.rng.uniform(0.3, 10.0), 1),
        )


def get_preset_scenario(name: str) -> PatientInput | None:
    """Retrieve a preset clinical scenario by name."""
    return PRESET_SCENARIOS.get(name)


def list_preset_scenarios() -> list[str]:
    """List all available preset scenario names."""
    return list(PRESET_SCENARIOS.keys())
