from predi_care.app_v2 import _build_enriched_cohort_csv, _build_subgroup_stats, _risk_level_from_score


def _entry(patient_id: str, recommendation: str, risk_score: float) -> dict[str, object]:
    return {
        "patient_id": patient_id,
        "recommendation": recommendation,
        "strength": "moderate",
        "dfs_2y_surgery": 88.0,
        "dfs_2y_watch_wait": 75.0,
        "dfs_5y_surgery": 82.0,
        "dfs_5y_watch_wait": 72.0,
        "qol_surgery": 66.0,
        "qol_watch_wait": 84.0,
        "local_recurrence_surgery": 8.0,
        "local_recurrence_watch_wait": 15.0,
        "distant_metastasis_surgery": 10.0,
        "distant_metastasis_watch_wait": 18.0,
        "major_complication_surgery": 16.0,
        "regrowth_watch_wait": 28.0,
        "risk_score": risk_score,
        "risk_level": _risk_level_from_score(risk_score),
    }


def test_risk_level_thresholds() -> None:
    assert _risk_level_from_score(10.0) == "Faible"
    assert _risk_level_from_score(20.0) == "Modere"
    assert _risk_level_from_score(35.0) == "Eleve"
    assert _risk_level_from_score(50.0) == "Critique"


def test_subgroup_stats_and_enriched_csv_include_summary_rows() -> None:
    entries = [
        _entry("P001", "surgery", 18.0),
        _entry("P002", "surgery", 32.0),
        _entry("P003", "watch_and_wait", 42.0),
    ]

    subgroup_stats = _build_subgroup_stats(entries)  # type: ignore[arg-type]

    assert len(subgroup_stats) == 2
    labels = {item["label"] for item in subgroup_stats}
    assert "Chirurgie recommandee" in labels
    assert "Watch & Wait recommande" in labels

    csv_payload = _build_enriched_cohort_csv(entries, subgroup_stats)  # type: ignore[arg-type]

    assert "row_type,subgroup,patient_id,recommendation" in csv_payload
    assert "patient,Chirurgie,P001,surgery" in csv_payload
    assert "summary,Chirurgie recommandee" in csv_payload
    assert "summary,Watch & Wait recommande" in csv_payload
