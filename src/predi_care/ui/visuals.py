"""V4 visualization helpers for the multi-agent UI."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st

from predi_care.engine.v4_types import ComplicationRisk, EngineResultV4


def _ordered_points(curve: dict[int, float]) -> tuple[tuple[int, float], ...]:
    return tuple(sorted((int(k), float(v)) for k, v in curve.items()))


@st.cache_data(ttl=300, show_spinner=False)
def cached_survival_curves(
    surgery_points: tuple[tuple[int, float], ...],
    watch_wait_points: tuple[tuple[int, float], ...],
) -> go.Figure:
    surgery_months = [m for m, _ in surgery_points]
    surgery_values = [v for _, v in surgery_points]
    ww_months = [m for m, _ in watch_wait_points]
    ww_values = [v for _, v in watch_wait_points]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=surgery_months,
            y=surgery_values,
            mode="lines+markers",
            name="Surgery DFS",
            line={"color": "#0A58CA", "width": 3, "shape": "hv"},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ww_months,
            y=ww_values,
            mode="lines+markers",
            name="Watch and Wait DFS",
            line={"color": "#198754", "width": 3, "shape": "hv"},
        )
    )
    fig.update_layout(
        title="Monotone survival curves",
        xaxis_title="Months",
        yaxis_title="Disease-free survival (%)",
        yaxis={"range": [0, 100]},
        template="plotly_white",
        height=360,
        margin={"l": 40, "r": 30, "t": 50, "b": 40},
    )
    return fig


def build_survival_comparison_figure(result: EngineResultV4) -> go.Figure:
    return cached_survival_curves(
        _ordered_points(result.surgery.survival_curve),
        _ordered_points(result.watch_wait.survival_curve),
    )


def build_complications_figure(complications: list[ComplicationRisk], title: str) -> go.Figure:
    names = [item.name for item in complications]
    values = [float(item.value) for item in complications]
    colors = ["#BB2D3B" if value >= 30 else "#FD7E14" if value >= 15 else "#0D6EFD" for value in values]
    fig = go.Figure(
        data=[
            go.Bar(
                x=values,
                y=names,
                orientation="h",
                marker={"color": colors},
                text=[f"{value:.1f}%" for value in values],
                textposition="outside",
            )
        ]
    )
    fig.update_layout(
        title=title,
        xaxis_title="Risk (%)",
        yaxis_title="Complication",
        xaxis={"range": [0, 100]},
        template="plotly_white",
        height=max(260, 70 + 45 * len(complications)),
        margin={"l": 30, "r": 30, "t": 50, "b": 40},
    )
    return fig


def build_shap_like_figure(feature_contributions: dict[str, float]) -> go.Figure:
    ordered = sorted(feature_contributions.items(), key=lambda item: abs(float(item[1])), reverse=True)
    names = [name for name, _ in ordered]
    values = [float(value) for _, value in ordered]
    colors = ["#198754" if value >= 0 else "#BB2D3B" for value in values]
    fig = go.Figure(
        data=[
            go.Bar(
                x=values,
                y=names,
                orientation="h",
                marker={"color": colors},
                text=[f"{value:+.1f}" for value in values],
                textposition="outside",
            )
        ]
    )
    fig.add_vline(x=0.0, line_dash="dot", line_color="#6C757D")
    fig.update_layout(
        title="Feature contribution map",
        xaxis_title="Contribution",
        yaxis_title="Feature",
        template="plotly_white",
        height=max(260, 70 + 45 * len(feature_contributions)),
        margin={"l": 30, "r": 30, "t": 50, "b": 40},
    )
    return fig


def build_calibration_curve(report: dict[str, Any]) -> go.Figure:
    rows = list(report.get("calibration_curve", []))
    predicted = [float(row["predicted"]) * 100.0 for row in rows]
    observed = [float(row["observed"]) * 100.0 for row in rows]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=predicted,
            y=observed,
            mode="lines+markers",
            name="Calibration",
            line={"color": "#0A58CA", "width": 2},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[0.0, 100.0],
            y=[0.0, 100.0],
            mode="lines",
            name="Perfect calibration",
            line={"dash": "dash", "color": "#6C757D"},
        )
    )
    fig.update_layout(
        title="Calibration curve",
        xaxis_title="Predicted local event rate (%)",
        yaxis_title="Observed local event rate (%)",
        template="plotly_white",
        height=320,
        margin={"l": 40, "r": 30, "t": 50, "b": 40},
    )
    return fig

