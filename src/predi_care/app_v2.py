"""PREDI-Care V2 - High-Fidelity Clinical Decision Support.

Premium UI - Clean, modern design.
"""

from __future__ import annotations

import csv
import logging
from io import StringIO
import plotly.graph_objects as go
import streamlit as st
import tempfile
from pathlib import Path
from typing import Any, TypedDict

from predi_care.engine.patient_types import PatientInput
from predi_care.engine.brain_engine_v2 import DecisionResult
from predi_care.engine.legacy_ui_adapter import LegacyUIEngine
from predi_care.engine.mock_factory import get_preset_scenario, list_preset_scenarios
from predi_care.data.loader import LoadResult, ValidationIssue, load_patients_from_csv_result
from predi_care.ui.comparative_ui import render_comparative_ui
from predi_care.export.pdf_report import generate_cohort_pdf_report, generate_pdf_report

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SidebarSubmission(TypedDict):
    """Payload returned by sidebar actions."""

    patient_input: PatientInput | None
    cohort_load_result: LoadResult | None


class CohortSimulationEntry(TypedDict):
    """Flattened cohort simulation output for tables and exports."""

    patient_id: str
    recommendation: str
    strength: str
    dfs_2y_surgery: float
    dfs_2y_watch_wait: float
    dfs_5y_surgery: float
    dfs_5y_watch_wait: float
    qol_surgery: float
    qol_watch_wait: float
    local_recurrence_surgery: float
    local_recurrence_watch_wait: float
    distant_metastasis_surgery: float
    distant_metastasis_watch_wait: float
    major_complication_surgery: float
    regrowth_watch_wait: float
    risk_score: float
    risk_level: str


@st.cache_resource
def get_engine() -> LegacyUIEngine:
    """Get cached engine instance (legacy UI adapter over v4 backend)."""
    return LegacyUIEngine()


def inject_local_css() -> None:
    """Inject custom CSS theme."""
    css_path = Path(__file__).resolve().parent / "theme" / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def _load_cohort_from_uploaded_file(uploaded_file: Any) -> LoadResult:
    """Persist uploaded file to temp storage and run CSV validation pipeline."""
    if uploaded_file is None:
        return LoadResult(
            errors=[
                ValidationIssue(
                    row_number=0,
                    field="__file__",
                    value="",
                    message="Aucun fichier CSV fourni.",
                )
            ]
        )

    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as handle:
            handle.write(uploaded_file.getvalue())
            tmp_path = handle.name

        return load_patients_from_csv_result(Path(tmp_path))
    except OSError:
        return LoadResult(
            errors=[
                ValidationIssue(
                    row_number=0,
                    field="__file__",
                    value=str(getattr(uploaded_file, "name", "uploaded.csv")),
                    message="Impossible de lire le fichier CSV charge.",
                )
            ]
        )
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass


def _run_cohort_simulation(
    engine: Any,
    load_result: LoadResult,
) -> tuple[list[CohortSimulationEntry], list[ValidationIssue]]:
    """Run model inference for each valid cohort patient."""
    entries: list[CohortSimulationEntry] = []
    run_warnings: list[ValidationIssue] = []

    for row_index, patient_record in enumerate(load_result.patients, start=1):
        patient_id = str(patient_record.get("patient_id", f"P{row_index:03d}"))
        patient_input = patient_record.get("input")
        if not isinstance(patient_input, dict):
            run_warnings.append(
                ValidationIssue(
                    row_number=row_index,
                    field="__simulation__",
                    value=patient_id,
                    message="Patient invalide ignore pendant la simulation.",
                )
            )
            continue

        try:
            result = engine.run_decision(patient_input)
        except Exception:
            run_warnings.append(
                ValidationIssue(
                    row_number=row_index,
                    field="__simulation__",
                    value=patient_id,
                    message="Echec de simulation pour ce patient.",
                )
            )
            continue

        surgery_peak_risk = max(
            float(result.surgery_outcome.local_recurrence_risk),
            float(result.surgery_outcome.distant_metastasis_risk),
            float(result.surgery_outcome.major_complication_risk),
        )
        watch_wait_peak_risk = max(
            float(result.ww_outcome.local_recurrence_risk),
            float(result.ww_outcome.distant_metastasis_risk),
            float(result.ww_outcome.regrowth_risk),
        )
        if result.recommended_scenario == "surgery":
            risk_score = surgery_peak_risk
        elif result.recommended_scenario == "watch_and_wait":
            risk_score = watch_wait_peak_risk
        else:
            risk_score = max(surgery_peak_risk, watch_wait_peak_risk)

        entries.append(
            {
                "patient_id": patient_id,
                "recommendation": result.recommended_scenario,
                "strength": result.recommendation_strength,
                "dfs_2y_surgery": float(result.surgery_outcome.dfs_2_years),
                "dfs_2y_watch_wait": float(result.ww_outcome.dfs_2_years),
                "dfs_5y_surgery": float(result.surgery_outcome.dfs_5_years),
                "dfs_5y_watch_wait": float(result.ww_outcome.dfs_5_years),
                "qol_surgery": float(result.surgery_outcome.qol_score),
                "qol_watch_wait": float(result.ww_outcome.qol_score),
                "local_recurrence_surgery": float(result.surgery_outcome.local_recurrence_risk),
                "local_recurrence_watch_wait": float(result.ww_outcome.local_recurrence_risk),
                "distant_metastasis_surgery": float(result.surgery_outcome.distant_metastasis_risk),
                "distant_metastasis_watch_wait": float(result.ww_outcome.distant_metastasis_risk),
                "major_complication_surgery": float(result.surgery_outcome.major_complication_risk),
                "regrowth_watch_wait": float(result.ww_outcome.regrowth_risk),
                "risk_score": float(risk_score),
                "risk_level": _risk_level_from_score(float(risk_score)),
            }
        )

    return entries, run_warnings


def _risk_level_from_score(risk_score: float) -> str:
    """Map continuous risk score to an operational risk bucket."""
    if risk_score < 20.0:
        return "Faible"
    if risk_score < 35.0:
        return "Modere"
    if risk_score < 50.0:
        return "Eleve"
    return "Critique"


def _recommendation_label(recommendation: str) -> str:
    """Human-readable French label for recommendation values."""
    labels = {
        "surgery": "Chirurgie",
        "watch_and_wait": "Watch & Wait",
        "uncertain": "Incertaine",
    }
    return labels.get(recommendation, recommendation)


def _build_subgroup_stats(entries: list[CohortSimulationEntry]) -> list[dict[str, Any]]:
    """Aggregate cohort metrics by recommendation subgroups."""
    subgroup_specs = [
        ("Chirurgie recommandee", "surgery"),
        ("Watch & Wait recommande", "watch_and_wait"),
        ("Recommendation incertaine", "uncertain"),
    ]

    subgroup_stats: list[dict[str, Any]] = []
    for group_label, recommendation_key in subgroup_specs:
        subgroup_entries = [
            entry
            for entry in entries
            if entry["recommendation"] == recommendation_key
        ]
        if not subgroup_entries:
            continue

        subgroup_stats.append(
            {
                "label": group_label,
                "recommendation": recommendation_key,
                "patients": len(subgroup_entries),
                "mean_dfs_5y_surgery": sum(item["dfs_5y_surgery"] for item in subgroup_entries) / len(subgroup_entries),
                "mean_dfs_5y_watch_wait": sum(item["dfs_5y_watch_wait"] for item in subgroup_entries) / len(subgroup_entries),
                "mean_qol_surgery": sum(item["qol_surgery"] for item in subgroup_entries) / len(subgroup_entries),
                "mean_qol_watch_wait": sum(item["qol_watch_wait"] for item in subgroup_entries) / len(subgroup_entries),
                "mean_risk_score": sum(item["risk_score"] for item in subgroup_entries) / len(subgroup_entries),
            }
        )

    return subgroup_stats


def _build_enriched_cohort_csv(
    entries: list[CohortSimulationEntry],
    subgroup_stats: list[dict[str, Any]],
) -> str:
    """Build a single enriched CSV with patient rows and subgroup summary rows."""
    csv_buffer = StringIO()
    fieldnames = [
        "row_type",
        "subgroup",
        "patient_id",
        "recommendation",
        "strength",
        "risk_level",
        "risk_score",
        "dfs_2y_surgery",
        "dfs_2y_watch_wait",
        "dfs_5y_surgery",
        "dfs_5y_watch_wait",
        "qol_surgery",
        "qol_watch_wait",
        "local_recurrence_surgery",
        "local_recurrence_watch_wait",
        "distant_metastasis_surgery",
        "distant_metastasis_watch_wait",
        "major_complication_surgery",
        "regrowth_watch_wait",
        "patients_count",
    ]
    writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
    writer.writeheader()

    for entry in entries:
        writer.writerow(
            {
                "row_type": "patient",
                "subgroup": _recommendation_label(entry["recommendation"]),
                "patient_id": entry["patient_id"],
                "recommendation": entry["recommendation"],
                "strength": entry["strength"],
                "risk_level": entry["risk_level"],
                "risk_score": f"{entry['risk_score']:.1f}",
                "dfs_2y_surgery": f"{entry['dfs_2y_surgery']:.1f}",
                "dfs_2y_watch_wait": f"{entry['dfs_2y_watch_wait']:.1f}",
                "dfs_5y_surgery": f"{entry['dfs_5y_surgery']:.1f}",
                "dfs_5y_watch_wait": f"{entry['dfs_5y_watch_wait']:.1f}",
                "qol_surgery": f"{entry['qol_surgery']:.1f}",
                "qol_watch_wait": f"{entry['qol_watch_wait']:.1f}",
                "local_recurrence_surgery": f"{entry['local_recurrence_surgery']:.1f}",
                "local_recurrence_watch_wait": f"{entry['local_recurrence_watch_wait']:.1f}",
                "distant_metastasis_surgery": f"{entry['distant_metastasis_surgery']:.1f}",
                "distant_metastasis_watch_wait": f"{entry['distant_metastasis_watch_wait']:.1f}",
                "major_complication_surgery": f"{entry['major_complication_surgery']:.1f}",
                "regrowth_watch_wait": f"{entry['regrowth_watch_wait']:.1f}",
                "patients_count": "",
            }
        )

    for subgroup in subgroup_stats:
        writer.writerow(
            {
                "row_type": "summary",
                "subgroup": subgroup["label"],
                "patient_id": "",
                "recommendation": subgroup["recommendation"],
                "strength": "",
                "risk_level": _risk_level_from_score(float(subgroup["mean_risk_score"])),
                "risk_score": f"{float(subgroup['mean_risk_score']):.1f}",
                "dfs_2y_surgery": "",
                "dfs_2y_watch_wait": "",
                "dfs_5y_surgery": f"{float(subgroup['mean_dfs_5y_surgery']):.1f}",
                "dfs_5y_watch_wait": f"{float(subgroup['mean_dfs_5y_watch_wait']):.1f}",
                "qol_surgery": f"{float(subgroup['mean_qol_surgery']):.1f}",
                "qol_watch_wait": f"{float(subgroup['mean_qol_watch_wait']):.1f}",
                "local_recurrence_surgery": "",
                "local_recurrence_watch_wait": "",
                "distant_metastasis_surgery": "",
                "distant_metastasis_watch_wait": "",
                "major_complication_surgery": "",
                "regrowth_watch_wait": "",
                "patients_count": str(subgroup["patients"]),
            }
        )

    return csv_buffer.getvalue()


def _render_cohort_results(load_result: LoadResult, entries: list[CohortSimulationEntry]) -> None:
    """Render cohort validation logs, aggregate KPIs and per-patient table."""
    st.markdown("### Analyse Cohorte")

    if load_result.errors:
        st.error(f"{len(load_result.errors)} erreur(s) détectée(s) dans le CSV.")
        for issue in load_result.errors:
            st.error(
                f"Ligne {issue.row_number} | {issue.field}: {issue.message}"
            )

    if load_result.warnings:
        st.warning(f"{len(load_result.warnings)} avertissement(s) détecté(s).")
        for issue in load_result.warnings:
            st.warning(
                f"Ligne {issue.row_number} | {issue.field}: {issue.message}"
            )

    if not entries:
        st.info("Aucun patient exploitable pour une simulation de cohorte.")
        return

    surgery_count = sum(entry["recommendation"] == "surgery" for entry in entries)
    watch_wait_count = sum(entry["recommendation"] == "watch_and_wait" for entry in entries)
    uncertain_count = sum(entry["recommendation"] == "uncertain" for entry in entries)

    mean_dfs_5y_surgery = sum(entry["dfs_5y_surgery"] for entry in entries) / len(entries)
    mean_dfs_5y_ww = sum(entry["dfs_5y_watch_wait"] for entry in entries) / len(entries)

    top_row = st.columns(4)
    top_row[0].metric("Patients simulés", str(len(entries)))
    top_row[1].metric("Reco chirurgie", str(surgery_count))
    top_row[2].metric("Reco W&W", str(watch_wait_count))
    top_row[3].metric("Reco incertaine", str(uncertain_count))

    second_row = st.columns(2)
    second_row[0].metric("DFS 5 ans moyen Chirurgie", f"{mean_dfs_5y_surgery:.1f}%")
    second_row[1].metric("DFS 5 ans moyen W&W", f"{mean_dfs_5y_ww:.1f}%")

    recommendation_chart = go.Figure(
        data=[
            go.Bar(
                x=["Chirurgie", "Watch & Wait", "Incertaine"],
                y=[surgery_count, watch_wait_count, uncertain_count],
                marker_color=["#0066FF", "#00C896", "#6B778C"],
                text=[str(surgery_count), str(watch_wait_count), str(uncertain_count)],
                textposition="outside",
            )
        ]
    )
    recommendation_chart.update_layout(
        title="Répartition des recommandations",
        yaxis_title="Nombre de patients",
        xaxis_title="Scénario recommandé",
        showlegend=False,
        margin={"l": 40, "r": 20, "t": 50, "b": 40},
        height=320,
    )
    st.plotly_chart(recommendation_chart, width="stretch", key="cohort_reco_distribution")

    subgroup_stats = _build_subgroup_stats(entries)
    grouped_rows: list[dict[str, Any]] = []
    for subgroup in subgroup_stats:
        grouped_rows.append(
            {
                "Sous-cohorte": subgroup["label"],
                "Patients": subgroup["patients"],
                "Risque moyen": f"{float(subgroup['mean_risk_score']):.1f}%",
                "DFS 5 ans moyen Chirurgie": f"{float(subgroup['mean_dfs_5y_surgery']):.1f}%",
                "DFS 5 ans moyen W&W": f"{float(subgroup['mean_dfs_5y_watch_wait']):.1f}%",
                "QoL moyenne Chirurgie": f"{float(subgroup['mean_qol_surgery']):.1f}",
                "QoL moyenne W&W": f"{float(subgroup['mean_qol_watch_wait']):.1f}",
            }
        )

    if grouped_rows:
        st.markdown("#### Comparaison des sous-cohortes")
        st.dataframe(grouped_rows, width="stretch")

    st.markdown("#### Filtres de lecture")
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    recommendation_filter = filter_col1.selectbox(
        "Filtrer par recommandation",
        ["Toutes", "Chirurgie", "Watch & Wait", "Incertaine"],
        key="cohort_filter_recommendation",
    )
    risk_filter = filter_col2.selectbox(
        "Filtrer par niveau de risque",
        ["Tous", "Faible", "Modere", "Eleve", "Critique"],
        key="cohort_filter_risk",
    )
    sort_label = filter_col3.selectbox(
        "Trier par",
        [
            "Patient (A-Z)",
            "Risque (eleve vers faible)",
            "DFS 5 ans Chirurgie (eleve vers faible)",
            "DFS 5 ans W&W (eleve vers faible)",
            "QoL Chirurgie (eleve vers faible)",
            "QoL W&W (eleve vers faible)",
        ],
        key="cohort_sort_key",
    )

    recommendation_map = {
        "Toutes": None,
        "Chirurgie": "surgery",
        "Watch & Wait": "watch_and_wait",
        "Incertaine": "uncertain",
    }
    selected_recommendation = recommendation_map[recommendation_filter]

    filtered_entries = entries
    if selected_recommendation is not None:
        filtered_entries = [
            entry
            for entry in filtered_entries
            if entry["recommendation"] == selected_recommendation
        ]

    if risk_filter != "Tous":
        filtered_entries = [
            entry
            for entry in filtered_entries
            if entry["risk_level"] == risk_filter
        ]

    sort_specs = {
        "Patient (A-Z)": ("patient_id", False),
        "Risque (eleve vers faible)": ("risk_score", True),
        "DFS 5 ans Chirurgie (eleve vers faible)": ("dfs_5y_surgery", True),
        "DFS 5 ans W&W (eleve vers faible)": ("dfs_5y_watch_wait", True),
        "QoL Chirurgie (eleve vers faible)": ("qol_surgery", True),
        "QoL W&W (eleve vers faible)": ("qol_watch_wait", True),
    }
    sort_key, reverse_sort = sort_specs[sort_label]
    filtered_entries = sorted(filtered_entries, key=lambda item: item[sort_key], reverse=reverse_sort)

    display_rows: list[dict[str, Any]] = []
    for entry in filtered_entries:
        display_rows.append(
            {
                "patient_id": entry["patient_id"],
                "recommendation": _recommendation_label(entry["recommendation"]),
                "strength": entry["strength"],
                "risk_level": entry["risk_level"],
                "risk_score": f"{entry['risk_score']:.1f}%",
                "dfs_2y_surgery": f"{entry['dfs_2y_surgery']:.1f}%",
                "dfs_2y_watch_wait": f"{entry['dfs_2y_watch_wait']:.1f}%",
                "dfs_5y_surgery": f"{entry['dfs_5y_surgery']:.1f}%",
                "dfs_5y_watch_wait": f"{entry['dfs_5y_watch_wait']:.1f}%",
                "qol_surgery": f"{entry['qol_surgery']:.1f}",
                "qol_watch_wait": f"{entry['qol_watch_wait']:.1f}",
            }
        )
    st.caption(f"Patients affichés après filtres: {len(display_rows)} / {len(entries)}")
    st.dataframe(display_rows, width="stretch")

    enriched_csv_data = _build_enriched_cohort_csv(entries, subgroup_stats)

    export_col1, export_col2 = st.columns(2)

    with export_col1:
        st.download_button(
            label="Exporter la synthèse cohorte (CSV)",
            data=enriched_csv_data,
            file_name="predi_care_cohorte_enrichie.csv",
            mime="text/csv",
            type="secondary",
        )

    warning_messages = [
        f"Ligne {issue.row_number} | {issue.field}: {issue.message}"
        for issue in load_result.warnings
    ]
    error_messages = [
        f"Ligne {issue.row_number} | {issue.field}: {issue.message}"
        for issue in load_result.errors
    ]

    with export_col2:
        try:
            cohort_pdf_bytes = generate_cohort_pdf_report(
                entries=entries,
                warning_messages=warning_messages,
                error_messages=error_messages,
            )
        except Exception:
            st.error("L'export PDF cohorte a échoué. Réessayez après une nouvelle analyse.")
        else:
            st.download_button(
                label="Exporter le rapport cohorte (PDF)",
                data=cohort_pdf_bytes,
                file_name="predi_care_cohorte.pdf",
                mime="application/pdf",
                type="secondary",
            )


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
            ">Outil Décisionnel Cancer du Rectum</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> SidebarSubmission:
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
        ">Données Patient</p>
        """,
        unsafe_allow_html=True,
    )

    # Demo scenario selector
    scenario_names = ["-- Saisie manuelle --"] + list_preset_scenarios()
    if st.session_state.get("selected_demo_scenario") not in scenario_names:
        st.session_state["selected_demo_scenario"] = "-- Saisie manuelle --"
    selected = st.sidebar.selectbox("Scénario Démo", scenario_names, key="selected_demo_scenario")

    if selected != "-- Saisie manuelle --":
        preset = get_preset_scenario(selected)
        if preset is not None:
            st.session_state["demo_preset"] = preset.copy()
    else:
        st.session_state.pop("demo_preset", None)

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
        help="Métastases à distance",
    )

    st.sidebar.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # Tumor Response section
    st.sidebar.markdown(
        '<p style="font-size: 0.75rem; font-weight: 600; color: #0066FF; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.06em;">Réponse Tumorale</p>',
        unsafe_allow_html=True,
    )

    default_residual = preset["residual_tumor_ratio"] if preset else 15.0
    residual_tumor_ratio = st.sidebar.slider(
        "Résidu tumoral (%)",
        0.0,
        100.0,
        float(default_residual),
        5.0,
        help="0% = réponse complète",
    )

    default_quality = ["Elevee", "Moyenne", "Basse"].index(preset["imaging_quality"]) if preset else 0
    imaging_quality_labels = {"Elevee": "Élevée", "Moyenne": "Moyenne", "Basse": "Basse"}
    imaging_quality = st.sidebar.selectbox(
        "Qualité IRM",
        ["Elevee", "Moyenne", "Basse"],
        index=default_quality,
        format_func=lambda value: imaging_quality_labels.get(value, value),
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
        "Âge (années)",
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

    st.sidebar.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # --- Advanced Tumor Characterization ---
    st.sidebar.markdown(
        '<p style="font-size: 0.75rem; font-weight: 600; color: #0066FF; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.06em;">Caractérisation Tumorale</p>',
        unsafe_allow_html=True,
    )

    default_dist = preset.get("distance_marge_anale", 8.0) if preset else 8.0
    distance_marge_anale = st.sidebar.slider(
        "Distance marge anale (cm)",
        0.0, 15.0, float(default_dist), 0.5,
        help="Distance tumeur / marge anale en cm",
    )

    default_delay = preset.get("delay_weeks_post_rct", 8) if preset else 8
    delay_weeks_post_rct = st.sidebar.slider(
        "Délai post-RCT (semaines)",
        4, 16, int(default_delay), 1,
        help="GRECCAR 6: 11 sem → +12% pCR vs 7 sem",
    )

    protocols = ["RCT standard", "FOLFIRINOX+CAP50", "TNT"]
    default_proto = protocols.index(preset.get("protocol_neoadjuvant", "RCT standard")) if preset and preset.get("protocol_neoadjuvant") in protocols else 0
    protocol_neoadjuvant = st.sidebar.selectbox(
        "Protocole néoadjuvant", protocols, index=default_proto,
        help="GRECCAR 12: FOLFIRINOX+CAP50 → 71% pCR si tumeur < 4cm",
    )

    mrtrg_options = [1, 2, 3, 4, 5]
    default_mrtrg = int(preset.get("mrtrg", 3)) - 1 if preset else 2
    mrtrg = st.sidebar.selectbox(
        "mrTRG IRM", mrtrg_options, index=default_mrtrg,
        help="1-2 = favorable, 4-5 = défavorable",
    )

    default_emvi = preset.get("emvi", False) if preset else False
    emvi = st.sidebar.checkbox(
        "EMVI (invasion vasculaire)", value=bool(default_emvi),
        help="Invasion vasculaire extramurale: récidive systémique +8%",
    )

    st.sidebar.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # --- Extended Biomarkers ---
    st.sidebar.markdown(
        '<p style="font-size: 0.75rem; font-weight: 600; color: #0066FF; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.06em;">Biomarqueurs Étendus</p>',
        unsafe_allow_html=True,
    )

    default_alb = preset.get("albumin", 40.0) if preset else 40.0
    albumin = st.sidebar.number_input(
        "Albumine (g/L)", 15.0, 55.0, float(default_alb), 1.0,
        help="< 35 g/L: dénutrition → +4% complications",
    )

    default_hb = preset.get("hemoglobin", 13.5) if preset else 13.5
    hemoglobin = st.sidebar.number_input(
        "Hémoglobine (g/dL)", 5.0, 20.0, float(default_hb), 0.5,
        help="< 12 g/dL: réduit efficacité RT",
    )

    msi_options = ["MSS/MSI-L", "dMMR/MSI-H", "Non teste"]
    default_msi = msi_options.index(preset.get("msi_status", "Non teste")) if preset and preset.get("msi_status") in msi_options else 2
    msi_labels = {"MSS/MSI-L": "MSS/MSI-L", "dMMR/MSI-H": "dMMR/MSI-H", "Non teste": "Non testé"}
    msi_status = st.sidebar.selectbox(
        "Statut MSI", msi_options, index=default_msi,
        format_func=lambda value: msi_labels.get(value, value),
        help="dMMR/MSI-H: réponse complète très probable (>60%)",
    )

    st.sidebar.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    # --- Comorbidities ---
    st.sidebar.markdown(
        '<p style="font-size: 0.75rem; font-weight: 600; color: #0066FF; margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.06em;">Comorbidités</p>',
        unsafe_allow_html=True,
    )

    asa_options = [1, 2, 3, 4]
    default_asa = int(preset.get("asa_score", 1)) - 1 if preset else 0
    asa_score = st.sidebar.selectbox(
        "Score ASA", asa_options, index=default_asa,
        help="≥ 3: complications chirurgicales x9",
    )

    default_smoking = preset.get("smoking", False) if preset else False
    smoking = st.sidebar.checkbox(
        "Tabagisme actif", value=bool(default_smoking),
        help="Fistule anastomotique OR=9.69",
    )

    default_diabetes = preset.get("diabetes", False) if preset else False
    diabetes = st.sidebar.checkbox(
        "Diabète", value=bool(default_diabetes),
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
            st.session_state.pop("cohort_load_result", None)
            st.session_state.pop("cohort_entries", None)
            st.session_state["selected_demo_scenario"] = "-- Saisie manuelle --"
            st.rerun()

    if run_eval:
        return {
            "patient_input": PatientInput(
                ct_stage=ct_stage,
                cn_stage=cn_stage,
                cm_stage=cm_stage,
                ace_baseline=ace_baseline,
                ace_current=ace_current,
                residual_tumor_ratio=residual_tumor_ratio,
                imaging_quality=imaging_quality,
                age=age,
                performance_status=performance_status,
                distance_marge_anale=distance_marge_anale,
                delay_weeks_post_rct=delay_weeks_post_rct,
                protocol_neoadjuvant=protocol_neoadjuvant,
                emvi=emvi,
                mrtrg=mrtrg,
                asa_score=asa_score,
                smoking=smoking,
                diabetes=diabetes,
                albumin=albumin,
                hemoglobin=hemoglobin,
                msi_status=msi_status,
            ),
            "cohort_load_result": None,
        }

    st.sidebar.divider()
    st.sidebar.markdown("### Mode Cohorte")
    uploaded_file = st.sidebar.file_uploader(
        "Importer une cohorte CSV",
        type=["csv"],
        key="uploaded_cohort_csv",
    )
    run_cohort = st.sidebar.button("Analyser Cohorte", use_container_width=True)

    if run_cohort:
        return {
            "patient_input": None,
            "cohort_load_result": _load_cohort_from_uploaded_file(uploaded_file),
        }

    return {
        "patient_input": None,
        "cohort_load_result": None,
    }


def render_welcome_screen() -> None:
    """Render welcome/landing screen."""

    col1, col2, col3 = st.columns(3)

    feature_cards = [
        {
            "title": "Simulation CRF",
            "desc": "Mapping automatique depuis les protocoles GRECCAR avec variables validées",
            "color": "#0066FF",
        },
        {
            "title": "Modèle Probabiliste",
            "desc": "Prédiction Bayesian-style basée sur les données de survie GRECCAR 12",
            "color": "#00C896",
        },
        {
            "title": "Explicabilité",
            "desc": "Contributions SHAP-style pour comprendre chaque décision",
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
                Sélectionnez un scénario démo ou complétez les données patient pour démarrer
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
        try:
            pdf_bytes = generate_pdf_report(result)
        except Exception:
            st.error("L'export PDF a échoué. Veuillez relancer la simulation puis réessayer.")
            return
        st.download_button(
            label="Télécharger Rapport PDF",
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

    submission = render_sidebar()
    result: DecisionResult | None = None

    cohort_load_result = submission["cohort_load_result"]
    if cohort_load_result is not None:
        st.session_state["cohort_load_result"] = cohort_load_result
        st.session_state.pop("result", None)

        cohort_entries: list[CohortSimulationEntry] = []
        if cohort_load_result.patients:
            with st.spinner("Analyse cohorte en cours..."):
                try:
                    engine = get_engine()
                    cohort_entries, run_warnings = _run_cohort_simulation(engine, cohort_load_result)
                    if run_warnings:
                        cohort_load_result.warnings.extend(run_warnings)
                except Exception:
                    cohort_load_result.errors.append(
                        ValidationIssue(
                            row_number=0,
                            field="__simulation__",
                            value="cohorte",
                            message="Echec de simulation de cohorte.",
                        )
                    )

        st.session_state["cohort_load_result"] = cohort_load_result
        st.session_state["cohort_entries"] = cohort_entries

    if isinstance(st.session_state.get("cohort_load_result"), LoadResult):
        cohort_entries_state = st.session_state.get("cohort_entries", [])
        cohort_entries = cohort_entries_state if isinstance(cohort_entries_state, list) else []
        _render_cohort_results(st.session_state["cohort_load_result"], cohort_entries)
        return

    patient_input = submission["patient_input"]
    if patient_input is not None:
        st.session_state.pop("cohort_load_result", None)
        st.session_state.pop("cohort_entries", None)
        with st.spinner("Simulation en cours..."):
            try:
                engine = get_engine()
                result = engine.run_decision(patient_input)
                st.session_state["result"] = result
                if result.llm_source:
                    logger.info("Inference mode: llm")
                else:
                    logger.warning("Inference mode: heuristic_fallback")
                    fallback_alert = next(
                        (
                            alert
                            for alert in result.rationale.clinical_alerts
                            if "fallback heuristique" in alert.lower()
                        ),
                        None,
                    )
                    if fallback_alert:
                        logger.warning("Fallback reason: %s", fallback_alert)
            except Exception:
                st.error("La simulation a echoue. Verifiez les donnees et reessayez.")
                return
    elif isinstance(st.session_state.get("result"), DecisionResult):
        result = st.session_state["result"]

    if result is None:
        render_welcome_screen()
        return

    render_comparative_ui(result)
    render_export_section(result)


if __name__ == "__main__":
    main()
