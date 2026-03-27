from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from textwrap import wrap
from typing import Dict, List, TypedDict, cast

import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from predi_care.chat import ExpertChatService
from predi_care.engine import (
    DecisionPack,
    PatientInput,
    PRESET_SCENARIOS,
    generate_mock_cohort,
    generate_mock_patient,
    list_preset_scenarios,
    render_decision_lines,
    run_multimodal_pipeline,
)
from predi_care.ui import (
    build_risk_comparison,
    build_shap_force_like,
    build_shap_summary_like,
    build_survival_curve,
)


class SidebarPayload(TypedDict):
    run_eval: bool
    patient_data: PatientInput


def inject_local_css(css_file: str = "") -> None:
    css_path = Path(css_file) if css_file else Path(__file__).resolve().parent / "theme" / "style.css"
    if not css_path.exists():
        st.warning("Le fichier de theme CSS est introuvable. Le style par defaut est applique.")
        return
    st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def render_header() -> None:
    st.markdown(
        """
        <section class="medical-header">
            <span class="header-kicker">Hackathon A.R.CA.D 2026</span>
            <h1 class="header-title">PREDI-Care | Decision Support Rectal Cancer</h1>
            <p class="header-subtitle">
                Plateforme d'aide a la decision clinique pour orienter le choix therapeutique
                entre Chirurgie Radicale et strategie Watch and Wait, avec approche IA multimodale.
            </p>
            <div class="header-badges">
                <span class="badge">Agent Radiologue</span>
                <span class="badge">Agent Biologiste</span>
                <span class="badge">Agent Coordinateur</span>
                <span class="badge">Mode Expert IA</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> SidebarPayload:
    st.sidebar.markdown("## Donnees Patient")
    st.sidebar.caption("Saisie clinique structuree pour le moteur de fusion multimodale")

    # Scenario predefini selection
    scenario_options = ["-- Saisie manuelle --"] + list_preset_scenarios()
    selected_scenario = st.sidebar.selectbox(
        "Charger un scenario",
        scenario_options,
        index=0,
        help="Selectionnez un scenario clinique predefini pour la demonstration",
    )

    if selected_scenario != "-- Saisie manuelle --":
        st.session_state["patient_data"] = PRESET_SCENARIOS[selected_scenario].copy()
        st.sidebar.success(f"Scenario: {selected_scenario}")

    if st.sidebar.button("Patient aleatoire", width="stretch"):
        st.session_state["patient_seed"] = st.session_state.get("patient_seed", 7) + 1
        st.session_state["patient_data"] = generate_mock_patient(seed=st.session_state["patient_seed"])

    patient_data = cast(PatientInput, st.session_state.get("patient_data", generate_mock_patient(seed=7)))
    st.session_state["patient_data"] = patient_data

    ct_stage = st.sidebar.selectbox("Stade cT", ["cT1", "cT2", "cT3", "cT4"], index=["cT1", "cT2", "cT3", "cT4"].index(patient_data["ct_stage"]))
    cn_stage = st.sidebar.selectbox("Stade cN", ["cN0", "cN1", "cN2"], index=["cN0", "cN1", "cN2"].index(patient_data["cn_stage"]))
    cm_stage = st.sidebar.selectbox("Stade cM", ["cM0", "cM1"], index=["cM0", "cM1"].index(patient_data["cm_stage"]))

    ace_baseline = st.sidebar.slider("ACE pre-traitement (ng/mL)", 0.0, 50.0, float(patient_data["ace_baseline"]), 0.1)
    ace_current = st.sidebar.slider("ACE actuel (ng/mL)", 0.0, 50.0, float(patient_data["ace_current"]), 0.1)
    residual_tumor_ratio = st.sidebar.slider("Residus tumoraux IRM (%)", 0.0, 100.0, float(patient_data["residual_tumor_ratio"]), 0.5)
    imaging_quality = st.sidebar.selectbox("Qualite imagerie", ["Elevee", "Moyenne"], index=["Elevee", "Moyenne"].index(patient_data["imaging_quality"]))
    age = st.sidebar.slider("Age", 18, 100, int(patient_data["age"]), 1)
    performance_status = st.sidebar.selectbox("Performance Status (ECOG)", [0, 1, 2, 3, 4], index=min(int(patient_data["performance_status"]), 4))

    st.sidebar.divider()
    run_eval = st.sidebar.button("Lancer Evaluation IA", width="stretch")

    payload: PatientInput = {
        "ct_stage": ct_stage,
        "cn_stage": cn_stage,
        "cm_stage": cm_stage,
        "ace_baseline": ace_baseline,
        "ace_current": ace_current,
        "residual_tumor_ratio": residual_tumor_ratio,
        "imaging_quality": imaging_quality,
        "age": age,
        "performance_status": performance_status,
    }
    st.session_state["patient_data"] = payload
    return SidebarPayload(run_eval=bool(run_eval), patient_data=payload)


def render_decision_stage(decision_pack: DecisionPack) -> None:
    st.markdown("### Comparaison des scenarios therapeutiques")
    coordinator = decision_pack["coordinator"]
    base_shap = coordinator["shap_like"]
    surgery_shap = {k: round(v * 0.9, 3) for k, v in base_shap.items()}
    wnw_shap = {k: round(v * 1.05, 3) for k, v in base_shap.items()}

    col_left, col_right = st.columns(2, gap="large")

    with col_left:
        st.markdown(
            """
            <article class="decision-card">
                <span class="decision-accent">Scenario A</span>
                <h3>Chirurgie Radicale</h3>
                <p class="placeholder-copy">
                    Controle local agressif avec reduction du risque de recidive,
                    au prix d'un impact fonctionnel post-operatoire plus important.
                </p>
                <div class="metric-strip">
                    <div class="metric-pill">Risque de recidive (simulation): {surgery_risk:.1f}%</div>
                    <div class="metric-pill">Confiance du modele: {surgery_conf:.1f}%</div>
                    <div class="metric-pill">Impact qualite de vie: {surgery_qol:.1f}%</div>
                </div>
            </article>
            """.format(
                surgery_risk=coordinator["scenario_surgery"]["risk"] * 100,
                surgery_conf=coordinator["scenario_surgery"]["confidence"] * 100,
                surgery_qol=coordinator["scenario_surgery"]["qol_impact"] * 100,
            ),
            unsafe_allow_html=True,
        )
        st.plotly_chart(build_survival_curve("Survie sans recidive - Chirurgie", float(coordinator["scenario_surgery"]["risk"])), width="stretch")
        st.plotly_chart(build_shap_force_like(surgery_shap), width="stretch")

    with col_right:
        st.markdown(
            """
            <article class="decision-card">
                <span class="decision-accent">Scenario B</span>
                <h3>Surveillance Watch and Wait</h3>
                <p class="placeholder-copy">
                    Strategie de preservation d'organe avec surveillance intensive
                    et reevaluation radioclinique continue.
                </p>
                <div class="metric-strip">
                    <div class="metric-pill">Risque de recidive (simulation): {wnw_risk:.1f}%</div>
                    <div class="metric-pill">Confiance du modele: {wnw_conf:.1f}%</div>
                    <div class="metric-pill">Impact qualite de vie: {wnw_qol:.1f}%</div>
                </div>
            </article>
            """.format(
                wnw_risk=coordinator["scenario_watch_wait"]["risk"] * 100,
                wnw_conf=coordinator["scenario_watch_wait"]["confidence"] * 100,
                wnw_qol=coordinator["scenario_watch_wait"]["qol_impact"] * 100,
            ),
            unsafe_allow_html=True,
        )
        st.plotly_chart(build_survival_curve("Survie sans recidive - Watch and Wait", float(coordinator["scenario_watch_wait"]["risk"])), width="stretch")
        st.plotly_chart(build_shap_force_like(wnw_shap), width="stretch")


def build_pdf_bytes(lines: List[str]) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margin_x = 50
    y = height - 56

    pdf.setTitle("PREDI-Care - Resume clinique")
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(margin_x, y, "PREDI-Care | Resume de decision clinique")
    y -= 22

    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin_x, y, f"Genere le: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    y -= 24

    pdf.setFont("Helvetica", 11)
    for raw_line in lines:
        normalized = raw_line.replace("\t", " ").strip()
        wrapped = wrap(normalized, width=95) or [""]
        for chunk in wrapped:
            if y <= 62:
                pdf.showPage()
                y = height - 56
                pdf.setFont("Helvetica", 11)
            pdf.drawString(margin_x, y, chunk)
            y -= 16
        y -= 2

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def render_xai_and_chat(decision_pack: DecisionPack) -> None:
    st.markdown("### Explicabilite IA (XAI)")
    xai_left, xai_right = st.columns(2, gap="large")

    with xai_left:
        st.plotly_chart(build_shap_force_like(decision_pack["coordinator"]["shap_like"]), width="stretch")

    with xai_right:
        cohort = generate_mock_cohort(size=14, base_seed=17)
        cohort_shap = [run_multimodal_pipeline(p)["coordinator"]["shap_like"] for p in cohort]
        st.plotly_chart(build_shap_summary_like(cohort_shap), width="stretch")

    st.markdown("### Mode Discussion | Expert IA")
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []

    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["text"])

    question = st.chat_input("Posez une question sur la recommandation (ex: Pourquoi privilegier la surveillance ici ?)")
    if question:
        st.session_state["chat_messages"].append({"role": "user", "text": question})
        service = ExpertChatService(mode="simulated")
        answer = service.answer(question, decision_pack)
        st.session_state["chat_messages"].append({"role": "assistant", "text": answer})
        st.rerun()


def render_summary_and_export(decision_pack: DecisionPack) -> None:
    coordinator = decision_pack["coordinator"]
    st.markdown("### Synthese finale")
    st.success(f"Recommendation IA: {coordinator['recommendation']}")
    st.caption(coordinator["rationale"])

    # Metriques avec delta pour comparaison claire
    surgery_risk = coordinator["scenario_surgery"]["risk"]
    wnw_risk = coordinator["scenario_watch_wait"]["risk"]
    risk_diff = (wnw_risk - surgery_risk) * 100

    metric_cols = st.columns(4)
    with metric_cols[0]:
        st.metric(
            "Risque Chirurgie",
            f"{surgery_risk*100:.1f}%",
            help="Risque de recidive avec chirurgie radicale",
        )
    with metric_cols[1]:
        st.metric(
            "Risque Watch & Wait",
            f"{wnw_risk*100:.1f}%",
            delta=f"{risk_diff:+.1f}% vs chirurgie",
            delta_color="inverse",
            help="Risque de recidive avec surveillance active",
        )
    with metric_cols[2]:
        st.metric(
            "Probabilite globale",
            f"{coordinator['recurrence_probability']*100:.1f}%",
            help="Probabilite de recidive estimee par le modele",
        )
    with metric_cols[3]:
        uncertainty_color = {"Faible": "🟢", "Moyenne": "🟠", "Elevee": "🔴"}.get(coordinator["uncertainty_level"], "⚪")
        st.metric(
            "Incertitude",
            f"{uncertainty_color} {coordinator['uncertainty_level']}",
            help="Niveau d'incertitude global de la prediction",
        )

    st.markdown(
        f"**Conflit inter-agents:** {'Oui' if coordinator['conflict_detected'] else 'Non'}"
    )
    if coordinator["clinical_alerts"]:
        st.warning("Alertes cliniques: " + "; ".join(coordinator["clinical_alerts"]))
    if coordinator["conflict_reasons"]:
        st.info("Motifs de conflit: " + "; ".join(coordinator["conflict_reasons"]))

    st.plotly_chart(
        build_risk_comparison(
            surgery_risk=float(coordinator["scenario_surgery"]["risk"]),
            wnw_risk=float(coordinator["scenario_watch_wait"]["risk"]),
        ),
        width="stretch",
    )

    decision_lines = render_decision_lines(decision_pack)
    decision_lines.append(f"Date de generation: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    st.download_button(
        label="Exporter le resume PDF",
        data=build_pdf_bytes(decision_lines),
        file_name="predi_care_resume.pdf",
        mime="application/pdf",
        width="stretch",
    )


def run_app() -> None:
    st.set_page_config(
        page_title="PREDI-Care | ARC.A.D 2026",
        page_icon="🩺",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_local_css()
    render_header()
    sidebar_payload: SidebarPayload = render_sidebar()

    if sidebar_payload["run_eval"] or "decision_pack" not in st.session_state:
        with st.spinner("Analyse en cours par les agents specialises..."):
            st.session_state["decision_pack"] = run_multimodal_pipeline(sidebar_payload["patient_data"])

    decision_pack = cast(DecisionPack, st.session_state["decision_pack"])

    # Expander avec details des agents
    with st.expander("Details par agent", expanded=False):
        col_rad, col_bio, col_coord = st.columns(3)
        with col_rad:
            st.markdown("**Agent Radiologue**")
            radiology = decision_pack["radiology"]
            st.metric("Risque local", f"{radiology['local_recurrence_risk']*100:.1f}%")
            st.metric("Confiance", f"{radiology['radiology_confidence']*100:.1f}%")
            st.caption(radiology["summary"])
        with col_bio:
            st.markdown("**Agent Biologiste**")
            biology = decision_pack["biology"]
            st.metric("Risque bio", f"{biology['bio_risk']*100:.1f}%")
            st.metric("Baisse ACE", f"{biology['ace_drop_pct']:.1f}%")
            st.caption(biology["summary"])
        with col_coord:
            st.markdown("**Agent Coordinateur**")
            coordinator = decision_pack["coordinator"]
            st.metric("Probabilite recidive", f"{coordinator['recurrence_probability']*100:.1f}%")
            st.metric("Incertitude", coordinator["uncertainty_level"])
            st.caption(f"Conflits: {'Oui' if coordinator['conflict_detected'] else 'Non'}")

    render_decision_stage(decision_pack)
    render_summary_and_export(decision_pack)
    render_xai_and_chat(decision_pack)
