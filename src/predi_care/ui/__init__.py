"""UI exports for the consolidated v2 frontend."""

from .comparative_ui import render_comparative_ui
from .visuals_v2 import (
    build_confidence_gauge,
    build_kaplan_meier_comparison,
    build_qol_comparison,
    build_risk_category_comparison,
    build_shap_explainability,
)

__all__ = [
    "render_comparative_ui",
    "build_kaplan_meier_comparison",
    "build_risk_category_comparison",
    "build_shap_explainability",
    "build_confidence_gauge",
    "build_qol_comparison",
]
