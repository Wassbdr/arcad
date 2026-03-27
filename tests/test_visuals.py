from predi_care.ui.visuals import (
    build_risk_comparison,
    build_shap_force_like,
    build_shap_summary_like,
    build_survival_curve,
)


def test_survival_curve_returns_figure() -> None:
    fig = build_survival_curve("test", 0.25)
    assert fig is not None
    assert len(list(fig.data)) > 0


def test_risk_comparison_returns_two_bars() -> None:
    fig = build_risk_comparison(0.2, 0.35)
    assert len(list(fig.data)) == 1
    x_values = list(fig.data[0]["x"])
    assert len(x_values) == 2


def test_shap_force_like_accepts_dict() -> None:
    shap_data = {"cT": 0.11, "ACE": -0.08, "Residu": 0.05}
    fig = build_shap_force_like(shap_data)
    assert fig is not None


def test_shap_summary_like_accepts_list() -> None:
    sample = [
        {"cT": 0.1, "ACE": -0.05, "Residu": 0.04},
        {"cT": 0.08, "ACE": -0.06, "Residu": 0.03},
    ]
    fig = build_shap_summary_like(sample)
    assert fig is not None
