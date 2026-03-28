"""UI exports with lazy imports to avoid hard Streamlit dependency at import time."""

from __future__ import annotations

__all__ = [
    "render_app_shell",
    "render_comparative_ui",
    "cached_survival_curves",
    "build_survival_comparison_figure",
    "build_complications_figure",
    "build_shap_like_figure",
    "build_calibration_curve",
    "build_kaplan_meier_comparison",
    "build_risk_category_comparison",
    "build_shap_explainability",
    "build_confidence_gauge",
    "build_qol_comparison",
]


def __getattr__(name: str):  # type: ignore[no-untyped-def]
    if name == "render_app_shell":
        from predi_care.ui.app_shell import render_app_shell

        return render_app_shell
    if name == "render_comparative_ui":
        from predi_care.ui.comparative_ui import render_comparative_ui

        return render_comparative_ui
    if name in {
        "cached_survival_curves",
        "build_survival_comparison_figure",
        "build_complications_figure",
        "build_shap_like_figure",
        "build_calibration_curve",
    }:
        from predi_care.ui import visuals

        return getattr(visuals, name)
    if name in {
        "build_kaplan_meier_comparison",
        "build_risk_category_comparison",
        "build_shap_explainability",
        "build_confidence_gauge",
        "build_qol_comparison",
    }:
        from predi_care.ui import visuals_v2

        return getattr(visuals_v2, name)
    raise AttributeError(f"module 'predi_care.ui' has no attribute '{name}'")

