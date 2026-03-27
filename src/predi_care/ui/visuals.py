from __future__ import annotations

from typing import Dict, List

import plotly.graph_objects as go


def build_survival_curve(title: str, recurrence_risk: float) -> go.Figure:
    months = list(range(0, 61, 3))
    hazard = 0.03 + 0.11 * recurrence_risk
    survival = [max(0.0, 100.0 * (2.718281828 ** (-hazard * m / 12.0))) for m in months]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=months,
            y=survival,
            mode="lines+markers",
            line={"width": 3, "color": "#005EB8"},
            marker={"size": 6},
            name="Survie sans recidive",
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="Mois",
        yaxis_title="Survie sans recidive (%)",
        template="plotly_white",
        margin={"l": 20, "r": 20, "t": 48, "b": 24},
        height=320,
    )
    fig.update_yaxes(range=[0, 100])
    return fig


def build_risk_comparison(surgery_risk: float, wnw_risk: float) -> go.Figure:
    fig = go.Figure(
        data=[
            go.Bar(
                x=["Chirurgie Radicale", "Watch and Wait"],
                y=[surgery_risk * 100, wnw_risk * 100],
                marker={"color": ["#005EB8", "#2D3748"]},
                text=[f"{surgery_risk * 100:.1f}%", f"{wnw_risk * 100:.1f}%"],
                textposition="outside",
            )
        ]
    )
    fig.update_layout(
        title="Comparaison du risque de recidive",
        yaxis_title="Risque (%)",
        template="plotly_white",
        margin={"l": 20, "r": 20, "t": 52, "b": 24},
        height=320,
    )
    fig.update_yaxes(range=[0, 100])
    return fig


def build_shap_force_like(shap_like: Dict[str, float]) -> go.Figure:
    feature_names = list(shap_like.keys())
    values = [shap_like[k] for k in feature_names]

    fig = go.Figure(
        go.Waterfall(
            orientation="h",
            measure=["relative"] * len(feature_names),
            y=feature_names,
            x=values,
            increasing={"marker": {"color": "#B7791F"}},
            decreasing={"marker": {"color": "#2F855A"}},
            connector={"line": {"color": "#CBD5E0"}},
        )
    )
    fig.update_traces(text=[f"{v:+.3f}" for v in values], textposition="outside")
    fig.update_layout(
        title="SHAP Force-Style Plot (contributions)",
        xaxis_title="Contribution au risque",
        yaxis_title="Variables",
        template="plotly_white",
        margin={"l": 20, "r": 20, "t": 52, "b": 24},
        height=340,
    )
    return fig


def build_shap_summary_like(sample_shap: List[Dict[str, float]]) -> go.Figure:
    if not sample_shap:
        return go.Figure()

    features = list(sample_shap[0].keys())
    mean_abs = []
    for feature in features:
        abs_values = [abs(row[feature]) for row in sample_shap]
        mean_abs.append(sum(abs_values) / len(abs_values))

    paired = sorted(zip(features, mean_abs), key=lambda x: x[1], reverse=True)
    sorted_features = [p[0] for p in paired]
    sorted_values = [p[1] for p in paired]

    fig = go.Figure(
        go.Bar(
            x=sorted_values,
            y=sorted_features,
            orientation="h",
            marker={"color": "#005EB8"},
            text=[f"{v:.3f}" for v in sorted_values],
            textposition="outside",
        )
    )
    fig.update_layout(
        title="SHAP Summary Plot (mean |contribution|)",
        xaxis_title="Impact moyen",
        yaxis_title="Variables",
        template="plotly_white",
        margin={"l": 20, "r": 20, "t": 52, "b": 24},
        height=340,
    )
    return fig
