"""Streamlit shell for PREDI-Care v4 Digital Twin mode."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from predi_care.engine.brain_engine import BrainEngineV4
from predi_care.engine.dataset_validator import validate_engine_on_dataset
from predi_care.engine.mock_factory import get_preset_scenario, list_preset_scenarios
from predi_care.engine.patient_types import PatientInput
from predi_care.engine.v4_types import ComplicationRisk, EngineResultV4
from predi_care.ui.visuals import (
    build_calibration_curve,
    build_complications_figure,
    build_shap_like_figure,
    build_survival_comparison_figure,
)


@st.cache_resource
def get_engine() -> BrainEngineV4:
    return BrainEngineV4()


def inject_local_css() -> None:
    css_path = Path(__file__).resolve().parents[1] / "theme" / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def _tag(text: str, background: str, border: str) -> None:
    st.markdown(
        f"""
        <div style="
            background: {background};
            border-left: 4px solid {border};
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 10px;
            font-size: 0.92rem;
        ">{text}</div>
        """,
        unsafe_allow_html=True,
    )


def _render_header() -> None:
    st.markdown(
        """
        <div style="
            padding: 1.4rem 1.8rem;
            background: linear-gradient(135deg, #0A58CA 0%, #084298 100%);
            border-radius: 14px;
            color: white;
            margin-bottom: 1rem;
        ">
            <h2 style="margin: 0; font-size: 1.55rem;">PREDI-Care v4</h2>
            <p style="margin: 0.35rem 0 0; opacity: 0.9;">
                Digital Twin tabulaire, orchestration multi-agent, garde-fous cliniques.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _build_sidebar_patient() -> PatientInput | None:
    st.sidebar.markdown("## Patient input")
    scenarios = ["Manual entry"] + list_preset_scenarios()
    selected = st.sidebar.selectbox("Demo profile", scenarios, key="v4_demo_profile")
    preset = get_preset_scenario(selected) if selected != "Manual entry" else None

    def _default(name: str, fallback: Any) -> Any:
        if preset is None:
            return fallback
        return preset.get(name, fallback)

    ct_stage = st.sidebar.selectbox("ycT stage", ["cT1", "cT2", "cT3", "cT4"], index=["cT1", "cT2", "cT3", "cT4"].index(str(_default("ct_stage", "cT3"))))
    cn_stage = st.sidebar.selectbox("ycN stage", ["cN0", "cN1", "cN2"], index=["cN0", "cN1", "cN2"].index(str(_default("cn_stage", "cN0"))))
    cm_stage = st.sidebar.selectbox("cM stage", ["cM0", "cM1"], index=["cM0", "cM1"].index(str(_default("cm_stage", "cM0"))))

    residual_ratio = st.sidebar.slider("Residual tumor ratio (%)", 0.0, 100.0, float(_default("residual_tumor_ratio", 20.0)), 1.0)
    residual_size = st.sidebar.number_input("Residual lesion size (cm)", 0.0, 6.0, float(_default("residual_size_cm", residual_ratio / 20.0)), 0.1)
    mrtrg = st.sidebar.selectbox("TRG", [1, 2, 3, 4, 5], index=max(0, int(_default("mrtrg", 3)) - 1))
    crm_distance_mm = st.sidebar.number_input("CRM distance (mm)", 0.0, 20.0, float(_default("crm_distance_mm", 5.0)), 0.1)
    imaging_quality = st.sidebar.selectbox("Imaging quality", ["Elevee", "Moyenne", "Basse"], index=["Elevee", "Moyenne", "Basse"].index(str(_default("imaging_quality", "Moyenne"))))

    ace_baseline = st.sidebar.number_input("ACE baseline", 0.0, 200.0, float(_default("ace_baseline", 8.0)), 0.1)
    ace_current = st.sidebar.number_input("ACE current", 0.0, 200.0, float(_default("ace_current", 4.0)), 0.1)
    msi_status = st.sidebar.selectbox("MSI status", ["MSS/MSI-L", "dMMR/MSI-H", "Non teste"], index=["MSS/MSI-L", "dMMR/MSI-H", "Non teste"].index(str(_default("msi_status", "Non teste")) if str(_default("msi_status", "Non teste")) in {"MSS/MSI-L", "dMMR/MSI-H", "Non teste"} else "Non teste"))

    age = st.sidebar.number_input("Age", 18, 100, int(_default("age", 62)), 1)
    performance_status = st.sidebar.selectbox("ECOG", [0, 1, 2, 3, 4], index=int(_default("performance_status", 1)))
    asa_score = st.sidebar.selectbox("ASA", [1, 2, 3, 4], index=max(0, int(_default("asa_score", 2)) - 1))
    smoking = st.sidebar.checkbox("Current smoking", value=bool(_default("smoking", False)))
    diabetes = st.sidebar.checkbox("Diabetes", value=bool(_default("diabetes", False)))
    emvi = st.sidebar.checkbox("EMVI positive", value=bool(_default("emvi", False)))
    albumin = st.sidebar.number_input("Albumin (g/L)", 10.0, 60.0, float(_default("albumin", 40.0)), 0.5)
    hemoglobin = st.sidebar.number_input("Hemoglobin (g/dL)", 5.0, 20.0, float(_default("hemoglobin", 13.0)), 0.1)
    distance_marge_anale = st.sidebar.number_input("Tumor distance from anal verge (cm)", 0.0, 15.0, float(_default("distance_marge_anale", 8.0)), 0.1)
    delay_weeks_post_rct = st.sidebar.slider("Delay post RCT (weeks)", 4, 16, int(_default("delay_weeks_post_rct", 8)))
    protocol_neoadjuvant = st.sidebar.selectbox("Neoadjuvant protocol", ["RCT standard", "FOLFIRINOX+CAP50", "TNT"], index=["RCT standard", "FOLFIRINOX+CAP50", "TNT"].index(str(_default("protocol_neoadjuvant", "RCT standard")) if str(_default("protocol_neoadjuvant", "RCT standard")) in {"RCT standard", "FOLFIRINOX+CAP50", "TNT"} else "RCT standard"))

    run = st.sidebar.button("Run simulation", type="primary", use_container_width=True)
    if not run:
        return None

    return PatientInput(
        ct_stage=ct_stage,
        cn_stage=cn_stage,
        cm_stage=cm_stage,
        ace_baseline=float(ace_baseline),
        ace_current=float(ace_current),
        residual_tumor_ratio=float(residual_ratio),
        residual_size_cm=float(residual_size),
        imaging_quality=imaging_quality,
        age=int(age),
        performance_status=int(performance_status),
        distance_marge_anale=float(distance_marge_anale),
        delay_weeks_post_rct=int(delay_weeks_post_rct),
        protocol_neoadjuvant=protocol_neoadjuvant,
        emvi=bool(emvi),
        mrtrg=int(mrtrg),
        asa_score=int(asa_score),
        smoking=bool(smoking),
        diabetes=bool(diabetes),
        albumin=float(albumin),
        hemoglobin=float(hemoglobin),
        msi_status=str(msi_status),
        crm_distance_mm=float(crm_distance_mm),
    )


def _render_consensus(result: EngineResultV4) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Recommendation", result.consensus.recommendation)
    c2.metric("Strength", result.consensus.recommendation_strength)
    c3.metric("Confidence", f"{result.consensus.confidence:.1f}%")
    c4.metric("Disagreement", result.consensus.disagreement_level)
    _tag(
        f"Rationale: {result.consensus.rationale}",
        background="#E9F2FF",
        border="#0A58CA",
    )

    for alert in result.consensus.alerts:
        if any(token in alert.lower() for token in ["safety", "contra", "metast", "ecog"]):
            _tag(alert, background="#FFE9E9", border="#BB2D3B")
        else:
            _tag(alert, background="#FFF4E0", border="#CC7A00")


def _render_indicator_provenance(result: EngineResultV4, keys: list[str], zone: str) -> None:
    rows = []
    for key in keys:
        rows.append(
            {
                "indicator": key,
                "source": result.indicator_sources.get(key, "unknown"),
                "runtime_mode": result.mode_runtime,
                "zone": zone,
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_complication_table(complications: list[ComplicationRisk]) -> None:
    rows = [
        {
            "name": item.name,
            "risk": f"{item.value:.1f}%",
            "source": item.source,
            "confidence": f"{item.confidence:.1f}%",
            "supporting_factors": ", ".join(item.supporting_factors),
        }
        for item in complications
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_surgery_zone(result: EngineResultV4) -> None:
    surgery = result.surgery
    st.markdown("### Zone 1 - Surgery")
    st.metric("R0 success probability", f"{surgery.r0_probability:.1f}%")
    st.metric("DFS 2 years", f"{surgery.survival_2y:.1f}%")
    st.metric("DFS 5 years", f"{surgery.survival_5y:.1f}%")
    st.metric("Major complication risk", f"{surgery.major_complication:.1f}%")
    st.plotly_chart(
        build_complications_figure(surgery.complications, "Detailed surgery complications"),
        use_container_width=True,
        key="v4_surgery_complications",
    )
    _render_complication_table(surgery.complications)
    _render_indicator_provenance(
        result,
        ["surgery.major_complication", "surgery.local_recurrence_5y"],
        "surgery",
    )


def _render_watch_wait_zone(result: EngineResultV4) -> None:
    ww = result.watch_wait
    st.markdown("### Zone 2 - Watch and Wait")
    st.metric("Eligibility score", f"{ww.eligibility_score:.1f}/100")
    st.metric("Eligible", "yes" if ww.eligible else "no")
    st.metric("Local regrowth 2 years", f"{ww.local_recurrence_2y:.1f}%")
    st.metric("DFS 5 years", f"{ww.survival_5y:.1f}%")
    st.plotly_chart(
        build_complications_figure(ww.complications, "Watch and Wait burden and risks"),
        use_container_width=True,
        key="v4_ww_complications",
    )
    _render_complication_table(ww.complications)
    _render_indicator_provenance(
        result,
        ["watch_wait.local_regrowth_2y", "watch_wait.surveillance_burden"],
        "watch_wait",
    )


def _render_explainability_zone(result: EngineResultV4) -> None:
    st.markdown("### Zone 3 - Explainability")
    st.plotly_chart(
        build_shap_like_figure(result.feature_contributions),
        use_container_width=True,
        key="v4_shap_like",
    )
    st.markdown("#### Primary factors")
    for factor, weight, description in result.primary_factors:
        st.markdown(f"- **{factor}** ({weight:.2f}) - {description}")

    st.markdown("#### Counterfactuals")
    for line in result.consensus.counterfactuals:
        st.markdown(f"- {line}")
    _render_indicator_provenance(result, ["explainability.feature_contributions", "llm.runtime"], "explainability")


def _render_validation_tab() -> None:
    st.markdown("### Validation")
    dataset_path_default = "data/greccar_synthetic_decision_support_cohort_v3.csv"
    dataset_path = st.text_input("Dataset path", value=dataset_path_default)

    if st.button("Run engine validation on dataset", key="v4_run_validation"):
        with st.spinner("Validation running..."):
            try:
                df = pd.read_csv(dataset_path)
                report = validate_engine_on_dataset(df)
                st.session_state["v4_validation_report"] = report
            except Exception as exc:
                st.session_state["v4_validation_error"] = str(exc)

    if "v4_validation_error" in st.session_state:
        _tag(
            f"Validation error: {st.session_state['v4_validation_error']}",
            background="#FFE9E9",
            border="#BB2D3B",
        )
        st.session_state.pop("v4_validation_error", None)

    report = st.session_state.get("v4_validation_report")
    if not isinstance(report, dict):
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("MAE local recurrence", f"{float(report.get('mae', 0.0)):.2f}%")
    c2.metric("Brier DFS", f"{float(report.get('brier', 0.0)):.4f}")
    auc_value = report.get("auc")
    c3.metric("AUC recommendation", "n/a" if auc_value is None else f"{float(auc_value):.3f}")

    st.plotly_chart(
        build_calibration_curve(report),
        use_container_width=True,
        key="v4_calibration_curve",
    )

    top_errors = report.get("top_errors", [])
    if top_errors:
        st.markdown("#### Top local prediction errors")
        st.dataframe(top_errors, use_container_width=True, hide_index=True)


def render_app_shell() -> None:
    st.set_page_config(
        page_title="PREDI-Care v4",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_local_css()
    _render_header()

    tabs = st.tabs(["Decision", "Validation"])
    patient_input = _build_sidebar_patient()

    with tabs[0]:
        if patient_input is not None:
            with st.spinner("LLM analysis in progress..."):
                result = get_engine().run_decision(patient_input)
            st.session_state["v4_result"] = result

        result = st.session_state.get("v4_result")
        if not isinstance(result, EngineResultV4):
            st.info("Provide patient inputs and run simulation.")
            return

        # Mandatory disclaimer shown before any result card.
        _tag(result.medical_disclaimer, background="#FFF4E0", border="#CC7A00")

        if result.mode_runtime == "openai":
            _tag(f"Runtime mode: OPENAI ({result.consensus.model_used})", "#E9F7EF", "#1E7E34")
        elif result.mode_runtime == "alt_llm":
            _tag(f"Runtime mode: ALTERNATE LLM ({result.consensus.model_used})", "#E9F2FF", "#0A58CA")
        else:
            _tag("Runtime mode: HEURISTIC", "#FFF4E0", "#CC7A00")

        _render_consensus(result)

        col1, col2, col3 = st.columns(3)
        with col1:
            _render_surgery_zone(result)
        with col2:
            _render_watch_wait_zone(result)
        with col3:
            _render_explainability_zone(result)

        st.markdown("### Survival trajectories")
        st.plotly_chart(
            build_survival_comparison_figure(result),
            use_container_width=True,
            key="v4_survival_curves",
        )

    with tabs[1]:
        _render_validation_tab()

