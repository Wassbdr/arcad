"""High-Fidelity Visualizations - Premium Design System.

Modern, clean charts with no emoji clutter.
"""

from __future__ import annotations

from typing import Dict, Any

import plotly.graph_objects as go


# Color System
COLORS = {
    "primary": "#0066FF",
    "primary_dark": "#0052CC",
    "secondary": "#00C896",
    "secondary_dark": "#00A67E",
    "text": "#1A1D21",
    "text_muted": "#5E6C84",
    "surface": "#F4F6F8",
    "border": "#E4E7EB",
    "white": "#FFFFFF",
}

CHART_TEMPLATE = {
    "layout": {
        "font": {"family": "Inter, -apple-system, BlinkMacSystemFont, sans-serif", "color": COLORS["text"]},
        "paper_bgcolor": COLORS["white"],
        "plot_bgcolor": COLORS["white"],
        "margin": {"l": 60, "r": 30, "t": 60, "b": 50},
    }
}


def build_kaplan_meier_comparison(survival_data: Dict[str, Any]) -> go.Figure:
    """Build comparative Kaplan-Meier survival curves."""

    months = survival_data["months"]
    surgery_dfs = survival_data["surgery_dfs"]
    ww_dfs = survival_data["ww_dfs"]
    surgery_label = survival_data.get("surgery_label", "Chirurgie")
    ww_label = survival_data.get("ww_label", "Watch & Wait")

    fig = go.Figure()

    # Surgery curve
    fig.add_trace(
        go.Scatter(
            x=months,
            y=surgery_dfs,
            mode="lines+markers",
            name=surgery_label,
            line={"width": 3, "color": COLORS["primary"], "shape": "hv"},
            marker={"size": 8, "symbol": "circle"},
            hovertemplate="<b>Chirurgie</b><br>%{x} mois: %{y:.1f}%<extra></extra>",
        )
    )

    # W&W curve
    fig.add_trace(
        go.Scatter(
            x=months,
            y=ww_dfs,
            mode="lines+markers",
            name=ww_label,
            line={"width": 3, "color": COLORS["secondary"], "shape": "hv"},
            marker={"size": 8, "symbol": "square"},
            hovertemplate="<b>Watch & Wait</b><br>%{x} mois: %{y:.1f}%<extra></extra>",
        )
    )

    # Reference line
    fig.add_hline(
        y=50,
        line_dash="dot",
        line_color=COLORS["text_muted"],
        opacity=0.4,
    )

    fig.update_layout(
        title={
            "text": "Survie sans recidive",
            "x": 0,
            "xanchor": "left",
            "font": {"size": 16, "weight": 600},
        },
        xaxis_title="Temps (mois)",
        yaxis_title="Survie Sans Recidive (%)",
        template="plotly_white",
        hovermode="x unified",
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "bgcolor": "rgba(255,255,255,0)",
        },
        margin={"l": 60, "r": 30, "t": 80, "b": 60},
        height=420,
        font={"family": "Inter, sans-serif"},
    )

    fig.update_xaxes(
        tickmode="array",
        tickvals=[0, 12, 24, 36, 48, 60],
        ticktext=["0", "12m", "24m", "36m", "48m", "60m"],
        showgrid=True,
        gridcolor=COLORS["surface"],
        zeroline=False,
    )

    fig.update_yaxes(
        range=[0, 105],
        showgrid=True,
        gridcolor=COLORS["surface"],
        zeroline=False,
    )

    return fig


def build_risk_category_comparison(risk_data: Dict[str, Any]) -> go.Figure:
    """Build grouped bar chart comparing risks."""

    surgery_risks = risk_data["surgery"]
    ww_risks = risk_data["watch_and_wait"]

    categories = []
    surgery_values = []
    ww_values = []

    risk_labels = {
        "local_recurrence": "Recidive locale",
        "distant_metastasis": "Metastase distante",
        "major_complication": "Complication majeure",
        "regrowth": "Repousse tumorale",
    }

    for key, label in risk_labels.items():
        if key in surgery_risks or key in ww_risks:
            categories.append(label)
            surgery_values.append(surgery_risks.get(key, 0))
            ww_values.append(ww_risks.get(key, 0))

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            name="Chirurgie",
            x=categories,
            y=surgery_values,
            marker_color=COLORS["primary"],
            text=[f"{v:.1f}%" for v in surgery_values],
            textposition="outside",
            textfont={"size": 11, "weight": 600},
            hovertemplate="<b>Chirurgie</b><br>%{x}: %{y:.1f}%<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            name="Watch & Wait",
            x=categories,
            y=ww_values,
            marker_color=COLORS["secondary"],
            text=[f"{v:.1f}%" for v in ww_values],
            textposition="outside",
            textfont={"size": 11, "weight": 600},
            hovertemplate="<b>Watch & Wait</b><br>%{x}: %{y:.1f}%<extra></extra>",
        )
    )

    fig.update_layout(
        title={
            "text": "Comparaison des Risques",
            "x": 0,
            "xanchor": "left",
            "font": {"size": 16, "weight": 600},
        },
        yaxis_title="Risque (%)",
        barmode="group",
        template="plotly_white",
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "bgcolor": "rgba(255,255,255,0)",
        },
        margin={"l": 60, "r": 30, "t": 80, "b": 100},
        height=380,
        font={"family": "Inter, sans-serif"},
        bargap=0.3,
        bargroupgap=0.1,
    )

    max_val = max(max(surgery_values or [0]), max(ww_values or [0]))
    fig.update_yaxes(
        range=[0, max_val * 1.25],
        showgrid=True,
        gridcolor=COLORS["surface"],
        zeroline=False,
    )

    fig.update_xaxes(
        tickangle=-20,
        showgrid=False,
    )

    return fig


def build_shap_explainability(explainability_data: Dict[str, Any]) -> go.Figure:
    """Build SHAP-style feature contribution plot."""

    contributions = explainability_data["feature_contributions"]

    # Sort by absolute contribution
    sorted_items = sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)
    features = [item[0] for item in sorted_items]
    values = [item[1] for item in sorted_items]

    # Color based on direction
    colors = [COLORS["secondary"] if v > 0 else COLORS["primary"] for v in values]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=values,
            y=features,
            orientation="h",
            marker_color=colors,
            text=[f"{v:+.1f}" for v in values],
            textposition="outside",
            textfont={"size": 11, "weight": 600},
            hovertemplate="<b>%{y}</b><br>Contribution: %{x:+.1f}<extra></extra>",
        )
    )

    fig.add_vline(x=0, line_color=COLORS["text_muted"], line_width=1)

    fig.update_layout(
        title={
            "text": "Impact des Variables",
            "x": 0,
            "xanchor": "left",
            "font": {"size": 16, "weight": 600},
        },
        xaxis_title="Contribution",
        template="plotly_white",
        margin={"l": 140, "r": 60, "t": 60, "b": 80},
        height=320,
        font={"family": "Inter, sans-serif"},
        annotations=[
            {
                "text": "Favorise Chirurgie",
                "xref": "paper",
                "yref": "paper",
                "x": 0.02,
                "y": -0.2,
                "showarrow": False,
                "font": {"size": 11, "color": COLORS["primary"]},
            },
            {
                "text": "Favorise W&W",
                "xref": "paper",
                "yref": "paper",
                "x": 0.98,
                "y": -0.2,
                "showarrow": False,
                "font": {"size": 11, "color": COLORS["secondary"]},
                "xanchor": "right",
            },
        ],
    )

    fig.update_yaxes(showgrid=False)
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["surface"], zeroline=False)

    return fig


def build_confidence_gauge(confidence_score: float, confidence_level: str) -> go.Figure:
    """Build gauge chart showing model confidence."""

    color_map = {
        "low": "#DE350B",
        "medium": "#FF8B00",
        "high": "#00875A",
    }
    gauge_color = color_map.get(confidence_level, "#6B778C")

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=confidence_score,
            number={"suffix": "%", "font": {"size": 28, "weight": 600}},
            domain={"x": [0, 1], "y": [0, 1]},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": COLORS["border"]},
                "bar": {"color": gauge_color, "thickness": 0.7},
                "bgcolor": COLORS["surface"],
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 60], "color": "#FFEBE6"},
                    {"range": [60, 75], "color": "#FFFAE6"},
                    {"range": [75, 100], "color": "#E3FCEF"},
                ],
            },
        )
    )

    fig.update_layout(
        margin={"l": 20, "r": 20, "t": 40, "b": 20},
        height=200,
        font={"family": "Inter, sans-serif"},
    )

    return fig


def build_qol_comparison(surgery_qol: float, ww_qol: float) -> go.Figure:
    """Build quality of life comparison chart."""

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=["Chirurgie", "Watch & Wait"],
            y=[surgery_qol, ww_qol],
            marker_color=[COLORS["primary"], COLORS["secondary"]],
            text=[f"{surgery_qol:.0f}", f"{ww_qol:.0f}"],
            textposition="outside",
            textfont={"size": 14, "weight": 700},
            hovertemplate="<b>%{x}</b><br>Score: %{y:.0f}/100<extra></extra>",
        )
    )

    fig.add_hline(
        y=75,
        line_dash="dot",
        line_color=COLORS["text_muted"],
        opacity=0.5,
        annotation_text="Seuil optimal",
        annotation_position="right",
        annotation_font_size=10,
    )

    fig.update_layout(
        title={
            "text": "Qualite de Vie",
            "x": 0,
            "xanchor": "left",
            "font": {"size": 16, "weight": 600},
        },
        yaxis_title="Score (0-100)",
        template="plotly_white",
        margin={"l": 60, "r": 30, "t": 60, "b": 50},
        height=380,
        font={"family": "Inter, sans-serif"},
        showlegend=False,
    )

    fig.update_yaxes(
        range=[0, 110],
        showgrid=True,
        gridcolor=COLORS["surface"],
        zeroline=False,
    )

    fig.update_xaxes(showgrid=False)

    return fig


def build_scenario_comparison_table(surgery_outcome: Any, ww_outcome: Any) -> str:
    """Build clean comparison table."""

    rows = [
        ("Eligibilite", "Oui", "Oui" if ww_outcome.eligible else "Non"),
        ("Score eligibilite", f"{surgery_outcome.eligibility_score:.0f}/100", f"{ww_outcome.eligibility_score:.0f}/100"),
        ("DFS 2 ans", f"{surgery_outcome.dfs_2_years:.1f}%", f"{ww_outcome.dfs_2_years:.1f}%"),
        ("DFS 5 ans", f"{surgery_outcome.dfs_5_years:.1f}%", f"{ww_outcome.dfs_5_years:.1f}%"),
        ("Qualite de Vie", f"{surgery_outcome.qol_score:.0f}/100", f"{ww_outcome.qol_score:.0f}/100"),
        ("Confiance Modele", f"{surgery_outcome.confidence_score:.0f}%", f"{ww_outcome.confidence_score:.0f}%"),
    ]

    rows_html = ""
    for metric, surgery_val, ww_val in rows:
        rows_html += f"""
            <tr>
                <td style="padding: 1rem; border-top: 1px solid #E4E7EB; color: #5E6C84;">{metric}</td>
                <td style="padding: 1rem; border-top: 1px solid #E4E7EB; color: #0066FF; font-weight: 600;">{surgery_val}</td>
                <td style="padding: 1rem; border-top: 1px solid #E4E7EB; color: #00C896; font-weight: 600;">{ww_val}</td>
            </tr>
        """

    html = f"""
    <table style="
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #E4E7EB;
        font-family: Inter, sans-serif;
    ">
        <thead>
            <tr>
                <th style="
                    background: #F4F6F8;
                    padding: 1rem;
                    font-size: 0.75rem;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 0.06em;
                    color: #5E6C84;
                    text-align: left;
                ">Metrique</th>
                <th style="
                    background: #F4F6F8;
                    padding: 1rem;
                    font-size: 0.75rem;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 0.06em;
                    color: #0066FF;
                    text-align: left;
                ">Chirurgie</th>
                <th style="
                    background: #F4F6F8;
                    padding: 1rem;
                    font-size: 0.75rem;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 0.06em;
                    color: #00C896;
                    text-align: left;
                ">Watch & Wait</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """

    return html
