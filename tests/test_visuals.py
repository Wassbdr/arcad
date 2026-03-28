from predi_care.ui.visuals_v2 import (
    build_confidence_gauge,
    build_kaplan_meier_comparison,
    build_qol_comparison,
    build_risk_category_comparison,
    build_shap_explainability,
)


def test_kaplan_meier_comparison_returns_two_curves() -> None:
    fig = build_kaplan_meier_comparison(
        {
            "months": [1, 3, 6, 12, 24, 36, 60],
            "surgery_dfs": [98.0, 96.0, 94.0, 91.0, 86.0, 84.0, 82.0],
            "ww_dfs": [95.0, 90.0, 82.0, 76.0, 72.0, 70.0, 68.0],
            "surgery_label": "Chirurgie",
            "ww_label": "Watch & Wait",
        }
    )
    assert fig is not None
    assert len(list(fig.data)) == 2


def test_risk_category_comparison_returns_grouped_bars() -> None:
    fig = build_risk_category_comparison(
        {
            "surgery": {
                "local_recurrence": 8.0,
                "distant_metastasis": 14.0,
                "major_complication": 19.0,
            },
            "watch_and_wait": {
                "local_recurrence": 12.0,
                "distant_metastasis": 11.0,
                "regrowth": 26.0,
            },
        }
    )
    assert len(list(fig.data)) == 2


def test_shap_explainability_accepts_feature_contributions() -> None:
    fig = build_shap_explainability(
        {
            "feature_contributions": {
                "TRG Score": 22.5,
                "ycT Stage": -14.0,
                "ACE Normalization": 6.0,
            }
        }
    )
    assert fig is not None
    assert len(list(fig.data)) == 1


def test_qol_comparison_renders_two_categories() -> None:
    fig = build_qol_comparison(68.0, 84.0)
    assert fig is not None
    assert len(list(fig.data)) == 1
    assert len(list(fig.data[0]["x"])) == 2


def test_confidence_gauge_returns_indicator() -> None:
    fig = build_confidence_gauge(76.0, "high")
    assert fig is not None
    assert len(list(fig.data)) == 1
