"""Comparative UI Module - Premium Dual-Panel Clinical Decision Interface.

Modern, visually impactful design without emoji overload.
"""

from __future__ import annotations

import streamlit as st
from typing import Any

from predi_care.engine.brain_engine_v2 import DecisionResult
from predi_care.ui import visuals_v2


def render_comparative_ui(result: DecisionResult) -> None:
    """Render complete comparative UI with dual panels and explainability."""

    # 1. Recommendation Banner
    _render_recommendation_banner(result)

    # 1b. LLM / Fallback badge
    _render_source_badge(result)

    # 1c. Patient-friendly summary (LLM)
    _render_patient_summary(result)

    # 2. Dual Panel Comparison
    _render_scenario_panels(result)

    # 3. Survival Curves (full width)
    st.markdown('<div style="margin-top: 2rem;"></div>', unsafe_allow_html=True)
    _render_section_header("Courbes de Survie", "Comparaison Disease-Free Survival")
    st.plotly_chart(
        _get_km_comparison_chart(result),
        width="stretch",
        key="km_comparison",
    )

    # 4. Risk & QoL Comparison
    col_risk, col_qol = st.columns(2)
    with col_risk:
        st.plotly_chart(
            _get_risk_comparison_chart(result),
            width="stretch",
            key="risk_comparison",
        )
    with col_qol:
        st.plotly_chart(
            _get_qol_comparison_chart(result),
            width="stretch",
            key="qol_comparison",
        )

    # 5. Explainability Section
    st.markdown('<div style="margin-top: 2rem;"></div>', unsafe_allow_html=True)
    _render_explainability_section(result)

    # 6. Detailed Comparison Table
    st.markdown('<div style="margin-top: 2rem;"></div>', unsafe_allow_html=True)
    _render_section_header("Tableau Comparatif", "Synthese des metriques")
    _render_comparison_table(result)

    # 7. What-If mode (delay slider)
    _render_whatif_section(result)


def _render_section_header(title: str, subtitle: str = "") -> None:
    """Render a clean section header."""
    st.markdown(
        f"""
        <div style="margin-bottom: 1rem;">
            <h3 style="font-size: 1.1rem; font-weight: 600; color: #1A1D21; margin: 0;">
                {title}
            </h3>
            {f'<p style="font-size: 0.85rem; color: #5E6C84; margin: 0.25rem 0 0;">{subtitle}</p>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_recommendation_banner(result: DecisionResult) -> None:
    """Render top banner with main recommendation."""

    scenario_styles = {
        "surgery": {
            "bg": "linear-gradient(135deg, #0066FF 0%, #0052CC 100%)",
            "label": "CHIRURGIE RECOMMANDEE",
            "icon": "S",
        },
        "watch_and_wait": {
            "bg": "linear-gradient(135deg, #00C896 0%, #00A67E 100%)",
            "label": "WATCH & WAIT RECOMMANDE",
            "icon": "W",
        },
        "uncertain": {
            "bg": "linear-gradient(135deg, #6B778C 0%, #505F79 100%)",
            "label": "DECISION EQUILIBREE",
            "icon": "?",
        },
    }

    strength_labels = {
        "strong": "Recommandation Forte",
        "moderate": "Recommandation Moderee",
        "weak": "Recommandation Faible",
    }

    style = scenario_styles.get(result.recommended_scenario, scenario_styles["uncertain"])
    strength = strength_labels.get(result.recommendation_strength, "")

    st.markdown(
        f"""
        <div style="
            background: {style['bg']};
            padding: 1.5rem 2rem;
            border-radius: 16px;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        ">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div style="
                    width: 48px;
                    height: 48px;
                    background: rgba(255,255,255,0.2);
                    border-radius: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 1.5rem;
                    font-weight: 700;
                    color: white;
                ">{style['icon']}</div>
                <div>
                    <h2 style="color: white; font-size: 1.4rem; font-weight: 700; margin: 0; letter-spacing: -0.01em;">
                        {style['label']}
                    </h2>
                    <p style="color: rgba(255,255,255,0.85); font-size: 0.9rem; margin: 0.25rem 0 0;">
                        {strength}
                    </p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Rationale in clean card
    st.markdown(
        f"""
        <div style="
            background: #F4F6F8;
            border-left: 3px solid #0066FF;
            padding: 1rem 1.25rem;
            border-radius: 0 8px 8px 0;
            margin-bottom: 1.5rem;
        ">
            <p style="margin: 0; color: #1A1D21; font-size: 0.95rem; line-height: 1.5;">
                {result.rationale.recommendation_text}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_source_badge(result: DecisionResult) -> None:
    """Render a badge indicating whether the recommendation came from LLM or heuristic fallback."""
    if result.llm_source:
        badge_html = """
        <div style="display: inline-block; background: #EEEBFF; color: #402E8A; font-size: 0.8rem; font-weight: 600; padding: 0.25rem 0.75rem; border-radius: 100px; margin-bottom: 2rem;">
            🤖 Analyse IA (NVIDIA NIM)
        </div>
        """
    else:
        badge_html = """
        <div style="display: inline-block; background: #FFF4E5; color: #B25A00; font-size: 0.8rem; font-weight: 600; padding: 0.25rem 0.75rem; border-radius: 100px; margin-bottom: 2rem;">
            ⚙️ Mode Heuristique (Fallback)
        </div>
        """
    st.markdown(badge_html, unsafe_allow_html=True)


def _render_patient_summary(result: DecisionResult) -> None:
    """Render the patient friendly summary from the LLM if available."""
    if result.llm_response and result.llm_response.patient_friendly_summary:
        st.markdown("### Resume pour le patient")
        st.info(result.llm_response.patient_friendly_summary, icon="ℹ️")
        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)



def _render_scenario_panels(result: DecisionResult) -> None:
    """Render dual scenario panels."""

    col_surgery, col_ww = st.columns(2)

    with col_surgery:
        _render_surgery_panel(result)

    with col_ww:
        _render_ww_panel(result)


def _render_surgery_panel(result: DecisionResult) -> None:
    """Render Surgery scenario panel."""

    outcome = result.surgery_outcome

    st.markdown(
        """
        <div style="
            background: white;
            border: 1px solid #E4E7EB;
            border-top: 3px solid #0066FF;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        ">
            <p style="
                font-size: 0.7rem;
                font-weight: 700;
                letter-spacing: 0.1em;
                text-transform: uppercase;
                color: #0066FF;
                margin: 0 0 1rem;
                padding-bottom: 0.75rem;
                border-bottom: 1px solid #E4E7EB;
            ">CHIRURGIE RADICALE</p>
        """,
        unsafe_allow_html=True,
    )

    # Metrics grid
    col1, col2 = st.columns(2)
    with col1:
        st.metric("DFS 2 ans", f"{outcome.dfs_2_years:.1f}%")
    with col2:
        st.metric("DFS 5 ans", f"{outcome.dfs_5_years:.1f}%")

    col3, col4 = st.columns(2)
    with col3:
        st.metric("Qualite de Vie", f"{outcome.qol_score:.0f}/100")
    with col4:
        st.metric("Confiance", f"{outcome.confidence_score:.0f}%")

    # Extended metrics from LLM
    col5, col6 = st.columns(2)
    with col5:
        st.metric("Risque LARS majeur", f"{outcome.lars_risk:.1f}%")
    with col6:
        st.metric("Risque stomie", f"{outcome.stoma_risk:.1f}%")

    # R0 probability (if LLM data available)
    if result.llm_response is not None:
        st.metric("Probabilite R0", f"{result.llm_response.surgery.r0_probability:.1f}%")

    # Risks
    with st.expander("Details des Risques"):
        st.markdown(f"**Recidive locale:** {outcome.local_recurrence_risk:.1f}%")
        st.markdown(f"**Metastase:** {outcome.distant_metastasis_risk:.1f}%")
        st.markdown(f"**Complication majeure:** {outcome.major_complication_risk:.1f}%")
        st.markdown(f"**Stomie permanente:** {outcome.stoma_risk:.1f}%")
        st.markdown(f"**LARS majeur:** {outcome.lars_risk:.1f}%")

    st.markdown("</div>", unsafe_allow_html=True)


def _render_ww_panel(result: DecisionResult) -> None:
    """Render Watch & Wait panel."""

    outcome = result.ww_outcome

    # Eligibility badge
    eligibility_style = (
        "background: #E3FCEF; color: #00875A;"
        if outcome.eligible
        else "background: #FFEBE6; color: #DE350B;"
    )
    eligibility_text = "Eligible" if outcome.eligible else "Non eligible"

    st.markdown(
        f"""
        <div style="
            background: white;
            border: 1px solid #E4E7EB;
            border-top: 3px solid #00C896;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; padding-bottom: 0.75rem; border-bottom: 1px solid #E4E7EB;">
                <p style="
                    font-size: 0.7rem;
                    font-weight: 700;
                    letter-spacing: 0.1em;
                    text-transform: uppercase;
                    color: #00C896;
                    margin: 0;
                ">WATCH & WAIT</p>
                <span style="
                    {eligibility_style}
                    font-size: 0.75rem;
                    font-weight: 600;
                    padding: 0.35rem 0.75rem;
                    border-radius: 100px;
                ">{eligibility_text} ({outcome.eligibility_score:.0f}/100)</span>
            </div>
        """,
        unsafe_allow_html=True,
    )

    # Metrics
    col1, col2 = st.columns(2)
    with col1:
        st.metric("DFS 2 ans", f"{outcome.dfs_2_years:.1f}%")
    with col2:
        st.metric("DFS 5 ans", f"{outcome.dfs_5_years:.1f}%")

    col3, col4 = st.columns(2)
    with col3:
        st.metric("Qualite de Vie", f"{outcome.qol_score:.0f}/100")
    with col4:
        st.metric("Confiance", f"{outcome.confidence_score:.0f}%")

    # Extended W&W metrics
    if result.llm_response is not None:
        col5, col6 = st.columns(2)
        with col5:
            st.metric("Preservation organe 2a", f"{result.llm_response.watch_wait.organ_preservation_2y:.1f}%")
        with col6:
            burden_labels = {"low": "Faible", "moderate": "Modere", "high": "Eleve"}
            burden = burden_labels.get(result.llm_response.watch_wait.surveillance_burden, "Modere")
            st.metric("Charge surveillance", burden)

    # Risks
    with st.expander("Details des Risques"):
        st.markdown(f"**Repousse tumorale:** {outcome.regrowth_risk:.1f}%")
        st.markdown(f"**Chirurgie de sauvetage:** {outcome.salvage_surgery_risk:.1f}%")
        st.markdown(f"**Recidive locale:** {outcome.local_recurrence_risk:.1f}%")
        st.markdown(f"**Metastase:** {outcome.distant_metastasis_risk:.1f}%")

    st.markdown("</div>", unsafe_allow_html=True)


def _render_explainability_section(result: DecisionResult) -> None:
    """Render explainability section."""

    _render_section_header("Raisonnement Clinique", "Facteurs influencant la decision")

    # Primary factors as clean cards
    for var, weight, desc in result.rationale.primary_factors:
        st.markdown(
            f"""
            <div style="
                background: #F4F6F8;
                border-left: 3px solid #0066FF;
                border-radius: 0 8px 8px 0;
                padding: 1rem 1.25rem;
                margin-bottom: 0.75rem;
            ">
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
                    <span style="font-weight: 600; color: #1A1D21;">{var}</span>
                    <span style="
                        background: #E6F0FF;
                        color: #0066FF;
                        font-size: 0.7rem;
                        font-weight: 700;
                        padding: 0.2rem 0.5rem;
                        border-radius: 100px;
                    ">{weight:.0%}</span>
                </div>
                <p style="margin: 0; color: #5E6C84; font-size: 0.85rem;">{desc}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # SHAP contributions chart
    explainability_data = {
        "feature_contributions": result.rationale.feature_contributions,
        "primary_factors": [
            {"name": var, "weight": weight, "description": desc}
            for var, weight, desc in result.rationale.primary_factors
        ],
    }
    st.plotly_chart(
        visuals_v2.build_shap_explainability(explainability_data),
        width="stretch",
        key="shap_contributions",
    )

    # Clinical Alerts
    if result.rationale.clinical_alerts:
        st.markdown(
            """
            <div style="margin-top: 1rem;">
                <p style="font-size: 0.85rem; font-weight: 600; color: #1A1D21; margin-bottom: 0.5rem;">
                    Alertes Cliniques
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for alert in result.rationale.clinical_alerts:
            st.markdown(
                f"""
                <div style="
                    background: #FFFAE6;
                    border-left: 3px solid #FF8B00;
                    padding: 0.75rem 1rem;
                    border-radius: 0 6px 6px 0;
                    margin-bottom: 0.5rem;
                    color: #974F0C;
                    font-size: 0.9rem;
                ">{alert}</div>
                """,
                unsafe_allow_html=True,
            )


def _get_km_comparison_chart(result: DecisionResult) -> Any:
    """Get Kaplan-Meier comparison chart."""
    from predi_care.engine.brain_engine_v2 import BrainEngineV2

    survival_data = BrainEngineV2.get_survival_comparison_data(result)
    return visuals_v2.build_kaplan_meier_comparison(survival_data)


def _get_risk_comparison_chart(result: DecisionResult) -> Any:
    """Get risk comparison chart."""
    from predi_care.engine.brain_engine_v2 import BrainEngineV2

    risk_data = BrainEngineV2.get_risk_comparison_data(result)
    return visuals_v2.build_risk_category_comparison(risk_data)


def _get_qol_comparison_chart(result: DecisionResult) -> Any:
    """Get quality of life comparison chart."""
    surgery_qol = result.surgery_outcome.qol_score
    ww_qol = result.ww_outcome.qol_score
    return visuals_v2.build_qol_comparison(surgery_qol, ww_qol)


def _render_comparison_table(result: DecisionResult) -> None:
    """Render detailed comparison table."""
    surgery = result.surgery_outcome
    ww = result.ww_outcome

    # Use native Streamlit dataframe for reliability
    import pandas as pd

    data = {
        "Metrique": [
            "Eligibilite",
            "Score eligibilite",
            "DFS 2 ans",
            "DFS 5 ans",
            "Qualite de Vie",
            "Confiance Modele",
        ],
        "Chirurgie": [
            "Oui",
            f"{surgery.eligibility_score:.0f}/100",
            f"{surgery.dfs_2_years:.1f}%",
            f"{surgery.dfs_5_years:.1f}%",
            f"{surgery.qol_score:.0f}/100",
            f"{surgery.confidence_score:.0f}%",
        ],
        "Watch & Wait": [
            "Oui" if ww.eligible else "Non",
            f"{ww.eligibility_score:.0f}/100",
            f"{ww.dfs_2_years:.1f}%",
            f"{ww.dfs_5_years:.1f}%",
            f"{ww.qol_score:.0f}/100",
            f"{ww.confidence_score:.0f}%",
        ],
    }

    df = pd.DataFrame(data)

    st.dataframe(df, hide_index=True, use_container_width=True)


def _render_whatif_section(result: DecisionResult) -> None:
    """Render What-If mode for exploring different parameters (e.g., surgical delay)."""
    st.markdown('<div style="margin-top: 3rem; padding-top: 2rem; border-top: 1px solid #E4E7EB;"></div>', unsafe_allow_html=True)
    _render_section_header("Mode What-If", "Exploration des alternatives cliniques")

    st.markdown("Testez l'impact d'un allongement du delai post-RCT (donnees GRECCAR 6) :")

    # The slider state lives isolated here, but to re-run we need to update PatientInput and re-run engine.
    # To keep it simple in Streamlit, we update session state and trigger a rerun.
    
    col1, col2 = st.columns([2, 1])
    with col1:
        current_delay = getattr(result.patient_input, "delay_weeks_post_rct", result.patient_input.get("delay_weeks_post_rct", 8))
        new_delay = st.slider(
            "Nouveau delai post-RCT (semaines)",
            4, 16, int(current_delay), 1,
            key="whatif_delay_slider"
        )
    with col2:
        st.write("")
        st.write("")
        if st.button("Re-simuler avec ce delai", use_container_width=True, type="secondary"):
            if "patient_input" in st.session_state and st.session_state["patient_input"]:
                st.session_state["patient_input"]["delay_weeks_post_rct"] = new_delay
            # Since patient_input might just be in the main app closure, we use a global signal or just 
            # let the user change it in the sidebar. For now, we update sidebar state:
            st.session_state["demo_preset"] = dict(result.patient_input)
            st.session_state["demo_preset"]["delay_weeks_post_rct"] = new_delay
            # clear result
            st.session_state.pop("result", None)
            st.rerun()
