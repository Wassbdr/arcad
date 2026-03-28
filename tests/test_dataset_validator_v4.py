from __future__ import annotations

import pandas as pd

from predi_care.engine.dataset_validator import validate_engine_on_dataset


def test_validate_engine_on_dataset_returns_metrics(monkeypatch) -> None:
    monkeypatch.setenv("LLM_FORCE_HEURISTIC", "1")

    df = pd.DataFrame(
        [
            {
                "patient_id": "P1",
                "baseline_cT": "cT2",
                "baseline_cN": "cN0",
                "cM": "cM0",
                "age_years": 57,
                "ecog_score": 0,
                "asa_class": "II",
                "cea_baseline_ng_ml": 7.0,
                "cea_current_ng_ml": 2.5,
                "residual_tumor_ratio_native": 0.10,
                "restaging_residual_lesion_cm": 0.6,
                "restaging_mrTRG": 2,
                "restaging_endoscopy_response": "CCR",
                "imaging_quality": "good",
                "tumor_distance_from_anal_verge_cm": 4.0,
                "initial_restaging_weeks_post_crt": 9,
                "concomitant_chemotherapy": "RCT standard",
                "baseline_emvi": False,
                "smoking_status": "never",
                "diabetes": False,
                "albumin_g_l": 42.0,
                "hemoglobin_g_dl": 13.8,
                "msi_status": "MSS_pMMR",
                "baseline_mri_crm_mm": 6.0,
                "final_management": "watch_and_wait",
                "local_regrowth_2y": 0,
                "local_recurrence_5y_after_resection": 0,
                "disease_free_5y": 1,
            },
            {
                "patient_id": "P2",
                "baseline_cT": "cT4",
                "baseline_cN": "cN2",
                "cM": "cM0",
                "age_years": 70,
                "ecog_score": 2,
                "asa_class": "III",
                "cea_baseline_ng_ml": 12.0,
                "cea_current_ng_ml": 10.0,
                "residual_tumor_ratio_native": 0.70,
                "restaging_residual_lesion_cm": 3.0,
                "restaging_mrTRG": 5,
                "restaging_endoscopy_response": "NCR",
                "imaging_quality": "acceptable",
                "tumor_distance_from_anal_verge_cm": 9.0,
                "initial_restaging_weeks_post_crt": 8,
                "concomitant_chemotherapy": "TNT",
                "baseline_emvi": True,
                "smoking_status": "current",
                "diabetes": True,
                "albumin_g_l": 33.0,
                "hemoglobin_g_dl": 11.2,
                "msi_status": "MSS_pMMR",
                "baseline_mri_crm_mm": 0.8,
                "final_management": "tme_direct",
                "local_regrowth_2y": 0,
                "local_recurrence_5y_after_resection": 1,
                "disease_free_5y": 0,
            },
        ]
    )

    report = validate_engine_on_dataset(df)
    assert report["sample_size"] == 2
    assert "mae" in report
    assert "brier" in report
    assert "calibration_curve" in report
    assert "top_errors" in report

