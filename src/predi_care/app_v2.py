"""PREDI-Care V2 - High-Fidelity Clinical Decision Support.

Premium UI - Clean, modern design.
"""

from __future__ import annotations

import streamlit as st
from pathlib import Path
from typing import Dict

from predi_care.engine.brain_engine import PatientInput
from predi_care.engine.brain_engine_v2 import BrainEngineV2, DecisionResult
from predi_care.ui.comparative_ui import render_comparative_ui
from predi_care.export.pdf_report import generate_pdf_report


# Demo scenarios for presentation
DEMO_SCENARIOS: Dict[str, PatientInput] = {
    "Candidat W&W ideal": PatientInput(
        ct_stage="cT1",
        cn_stage="cN0",
        cm_stage="cM0",
        ace_baseline=12.0,
        ace_current=1.8,
        residual_tumor_ratio=0.0,
        imaging_quality="Elevee",
        age=58,
        performance_status=0,
    ),
    "Candidat Chirurgie": PatientInput(
        ct_stage="cT3",
        cn_stage="cN1",
        cm_stage="cM0",
        ace_baseline=15.0,
        ace_current=9.5,
        residual_tumor_ratio=65.0,
        imaging_quality="Moyenne",
        age=67,
        performance_status=1,
    ),
    "Cas Limite - Decision partagee": PatientInput(
        ct_stage="cT2",
        cn_stage="cN0",
        cm_stage="cM0",
        ace_baseline=8.0,
        ace_current=2.8,
        residual_tumor_ratio=8.0,  # TRG 2 - near complete
        imaging_quality="Elevee",
        age=62,
        performance_status=0,
    ),
}


@st.cache_resource
def get_engine() -> BrainEngineV2:
    """Get cached engine instance."""
    return BrainEngineV2()


def inject_local_css() -> None:
    """Inject custom CSS theme."""
    css_path = Path(__file__).resolve().parent / "theme" / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def render_header() -> None:
    """Render premium application header."""
    st.markdown(
        """
        <div style="
            position: relative;
            padding: 2rem 2.5rem;
            background: linear-gradient(135deg, #0066FF 0%, #0052CC 100%);
            border-radius: 20px;
            color: white;
            overflow: hidden;
            margin-bottom: 2rem;
        ">
            <div style="
                position: absolute;
                top: -50%;
                right: -20%;
                width: 60%;
                height: 200%;
                background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, transparent 50%);
                transform: rotate(-12deg);
            "></div>
            <span style="
                display: inline-block;
                font-size: 0.7rem;
                font-weight: 700;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                color: rgba(255,255,255,0.85);
                background: rgba(255,255,255,0.15);
                padding: 0.35rem 0.85rem;
                border-radius: 100px;
                margin-bottom: 1rem;
            ">Hackathon A.R.CA.D 2026</span>
            <h1 style="
                font-size: clamp(1.75rem, 3vw, 2.5rem);
                font-weight: 800;
                margin: 0;
                letter-spacing: -0.02em;
                line-height: 1.2;
            ">PREDI-Care</h1>
            <p style="
                font-size: 1rem;
                color: rgba(255,255,255,0.8);
                margin-top: 0.5rem;
                margin-bottom: 0;
                font-weight: 400;
            ">Simulateur Decisionnel Cancer du Rectum</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> PatientInput | None:
    """Render sidebar with patient input form."""

    st.sidebar.markdown(
        """
        <p style="
            font-size: 0.85rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #8993A4;
            margin-bottom: 1rem;
        ">Donnees Patient</p>
        """,
        unsafe_allow_html=True,
    )

    # Demo scenario selector
    scenario_names = ["-- Saisie manuelle --"] + list(DEMO_SCENARIOS.keys())
    selected = st.sidebar.selectbox("Scenario Demo", scenario_names, index=0)

    if selected != "-- Saisie manuelle --":
        preset = DEMO_SCENARIOS[selected]
        st.session_state["demo_preset"] = preset

    # Get default values from preset or session
    preset = st.session_state.get("demo_preset", None)

    # TNM Staging section
    st.sidebar.markdown(
        '<p style="font-size: 0.75rem; font-weight: 600; color: #0066FF; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.06em;">Staging TNM</p>',
        unsafe_allow_html=True,
    )

    default_ct = ["cT1", "cT2", "cT3", "cT4"].index(preset["ct_stage"]) if preset else 2
    ct_stage = st.sidebar.selectbox(
        "Stade T (ycT)",
        ["cT1", "cT2", "cT3", "cT4"],
        index=default_ct,
        help="Stade tumoral post-neoadjuvant",
    )

    default_cn = ["cN0", "cN1", "cN2"].index(preset["cn_stage"]) if preset else 0
    cn_stage = st.sidebar.selectbox(
        "Stade N (ycN)",
        ["cN0", "cN1", "cN2"],
        index=default_cn,
        help="Statut ganglionnaire",
    )

    default_cm = ["cM0", "cM1"].index(preset["cm_stage"]) if preset else 0
    cm_stage = st.sidebar.selectbox(
        "Stade M (cM)",
        ["cM0", "cM1"],
        index=default_cm,
        help="Metastases a distance",
    )

    st.sidebar.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # Tumor Response section
    st.sidebar.markdown(
        '<p style="font-size: 0.75rem; font-weight: 600; color: #0066FF; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.06em;">Reponse Tumorale</p>',
        unsafe_allow_html=True,
    )

    default_residual = preset["residual_tumor_ratio"] if preset else 15.0
    residual_tumor_ratio = st.sidebar.slider(
        "Residu tumoral (%)",
        0.0,
        100.0,
        float(default_residual),
        5.0,
        help="0% = reponse complete",
    )

    default_quality = ["Elevee", "Moyenne", "Basse"].index(preset["imaging_quality"]) if preset else 0
    imaging_quality = st.sidebar.selectbox(
        "Qualite IRM",
        ["Elevee", "Moyenne", "Basse"],
        index=default_quality,
    )

    st.sidebar.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # Biomarkers section
    st.sidebar.markdown(
        '<p style="font-size: 0.75rem; font-weight: 600; color: #0066FF; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.06em;">Marqueurs Biologiques</p>',
        unsafe_allow_html=True,
    )

    default_ace_base = preset["ace_baseline"] if preset else 8.5
    ace_baseline = st.sidebar.number_input(
        "ACE baseline (ng/mL)",
        min_value=0.0,
        max_value=100.0,
        value=float(default_ace_base),
        step=0.5,
    )

    default_ace_cur = preset["ace_current"] if preset else 2.1
    ace_current = st.sidebar.number_input(
        "ACE actuel (ng/mL)",
        min_value=0.0,
        max_value=100.0,
        value=float(default_ace_cur),
        step=0.5,
    )

    st.sidebar.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # Patient data section
    st.sidebar.markdown(
        '<p style="font-size: 0.75rem; font-weight: 600; color: #0066FF; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.06em;">Patient</p>',
        unsafe_allow_html=True,
    )

    default_age = preset["age"] if preset else 62
    age = st.sidebar.number_input(
        "Age (annees)",
        min_value=18,
        max_value=100,
        value=int(default_age),
        step=1,
    )

    default_ps = preset["performance_status"] if preset else 0
    performance_status = st.sidebar.selectbox(
        "Performance Status (ECOG)",
        [0, 1, 2, 3, 4],
        index=int(default_ps),
        help="0 = asymptomatique",
    )

    st.sidebar.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    # Buttons
    col1, col2 = st.sidebar.columns(2)
    with col1:
        run_eval = st.button("Simuler", type="primary", use_container_width=True)
    with col2:
        if st.button("Reset", use_container_width=True):
            st.session_state.pop("demo_preset", None)
            st.session_state.pop("result", None)
            st.rerun()

    if run_eval:
        return PatientInput(
            ct_stage=ct_stage,
            cn_stage=cn_stage,
            cm_stage=cm_stage,
            ace_baseline=ace_baseline,
            ace_current=ace_current,
            residual_tumor_ratio=residual_tumor_ratio,
            imaging_quality=imaging_quality,
            age=age,
            performance_status=performance_status,
        )

    return None


def render_welcome_screen() -> None:
    """Render welcome/landing screen."""

    col1, col2, col3 = st.columns(3)

    feature_cards = [
        {
            "title": "Simulation CRF",
            "desc": "Mapping automatique depuis les protocoles GRECCAR avec variables validees",
            "color": "#0066FF",
        },
        {
            "title": "Modele Probabiliste",
            "desc": "Prediction Bayesian-style basee sur les donnees de survie GRECCAR 12",
            "color": "#00C896",
        },
        {
            "title": "Explicabilite",
            "desc": "Contributions SHAP-style pour comprendre chaque decision",
            "color": "#FF8B00",
        },
    ]

    for col, feature in zip([col1, col2, col3], feature_cards):
        with col:
            st.markdown(
                f"""
                <div style="
                    background: white;
                    border: 1px solid #E4E7EB;
                    border-top: 3px solid {feature['color']};
                    border-radius: 12px;
                    padding: 1.5rem;
                    height: 160px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.06);
                ">
                    <h4 style="font-size: 1rem; font-weight: 600; color: #1A1D21; margin: 0 0 0.5rem;">{feature['title']}</h4>
                    <p style="font-size: 0.85rem; color: #5E6C84; margin: 0; line-height: 1.5;">{feature['desc']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="
            background: #F4F6F8;
            border-radius: 12px;
            padding: 1.5rem 2rem;
            text-align: center;
        ">
            <p style="color: #5E6C84; margin: 0; font-size: 0.95rem;">
                Selectionnez un scenario demo ou completez les donnees patient pour demarrer
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_export_section(result: DecisionResult) -> None:
    """Render export section with PDF download."""

    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])

    with col1:
        # Generate PDF
        pdf_bytes = generate_pdf_report(result)
        st.download_button(
            label="Telecharger Rapport PDF",
            data=pdf_bytes,
            file_name="predi_care_rapport.pdf",
            mime="application/pdf",
            type="secondary",
        )

    with col2:
        if st.button("Nouvelle Simulation"):
            st.session_state.pop("demo_preset", None)
            st.session_state.pop("result", None)
            st.rerun()


def main() -> None:
    """Main application entry point."""

    st.set_page_config(
        page_title="PREDI-Care | Decision Support",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    inject_local_css()
    render_header()

    patient_input = render_sidebar()

    if patient_input is None:
        render_welcome_screen()
        return

    # Run simulation with cached engine
    with st.spinner("Simulation en cours..."):
        engine = get_engine()
        result = engine.run_decision(patient_input)
        st.session_state["result"] = result

    render_comparative_ui(result)
    render_export_section(result)


if __name__ == "__main__":
    main()
