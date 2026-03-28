"""PDF Export Module for PREDI-Care Reports."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

if TYPE_CHECKING:
    from predi_care.engine.brain_engine_v2 import DecisionResult


def generate_pdf_report(result: "DecisionResult") -> bytes:
    """Generate PDF report from DecisionResult.

    Args:
        result: DecisionResult from BrainEngineV2

    Returns:
        PDF bytes ready for download
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
        textColor=colors.HexColor("#0066FF"),
    )

    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=16,
        spaceAfter=8,
        textColor=colors.HexColor("#1A1D21"),
    )

    normal_style = ParagraphStyle(
        "Normal",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=6,
    )

    # Build content
    content = []

    # Header
    content.append(Paragraph("PREDI-Care - Rapport Decisionnel", title_style))
    content.append(Paragraph(
        f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        normal_style
    ))
    content.append(Spacer(1, 10 * mm))

    # Recommendation Banner
    rec_scenario = result.recommended_scenario.replace("_", " ").upper()
    rec_strength = result.recommendation_strength.upper()
    content.append(Paragraph(f"RECOMMANDATION: {rec_scenario}", heading_style))
    content.append(Paragraph(f"Force: {rec_strength}", normal_style))
    content.append(Paragraph(result.rationale.recommendation_text, normal_style))
    content.append(Spacer(1, 8 * mm))

    # Comparison Table
    content.append(Paragraph("Comparaison des Scenarios", heading_style))

    surgery = result.surgery_outcome
    ww = result.ww_outcome

    table_data = [
        ["Metrique", "Chirurgie", "Watch & Wait"],
        ["Eligibilite", "Oui", "Oui" if ww.eligible else "Non"],
        ["Score", f"{surgery.eligibility_score:.0f}/100", f"{ww.eligibility_score:.0f}/100"],
        ["DFS 2 ans", f"{surgery.dfs_2_years:.1f}%", f"{ww.dfs_2_years:.1f}%"],
        ["DFS 5 ans", f"{surgery.dfs_5_years:.1f}%", f"{ww.dfs_5_years:.1f}%"],
        ["Qualite de Vie", f"{surgery.qol_score:.0f}/100", f"{ww.qol_score:.0f}/100"],
        ["Confiance", f"{surgery.confidence_score:.0f}%", f"{ww.confidence_score:.0f}%"],
    ]

    table = Table(table_data, colWidths=[60 * mm, 45 * mm, 45 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F4F6F8")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#5E6C84")),
        ("TEXTCOLOR", (1, 1), (1, -1), colors.HexColor("#0066FF")),
        ("TEXTCOLOR", (2, 1), (2, -1), colors.HexColor("#00C896")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E7EB")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    content.append(table)
    content.append(Spacer(1, 8 * mm))

    # Key Factors
    content.append(Paragraph("Facteurs Principaux", heading_style))
    for var, weight, desc in result.rationale.primary_factors:
        content.append(Paragraph(
            f"<b>{var}</b> (poids: {weight:.0%}): {desc}",
            normal_style
        ))
    content.append(Spacer(1, 6 * mm))

    # Clinical Alerts
    if result.rationale.clinical_alerts:
        content.append(Paragraph("Alertes Cliniques", heading_style))
        for alert in result.rationale.clinical_alerts:
            clean_alert = alert.replace("⚠️", "").replace("🚨", "").strip()
            content.append(Paragraph(f"- {clean_alert}", normal_style))
        content.append(Spacer(1, 6 * mm))

    # Risks Summary
    content.append(Paragraph("Resume des Risques", heading_style))

    risk_data = [
        ["Risque", "Chirurgie", "Watch & Wait"],
        ["Recidive locale", f"{surgery.local_recurrence_risk:.1f}%", f"{ww.local_recurrence_risk:.1f}%"],
        ["Metastase distante", f"{surgery.distant_metastasis_risk:.1f}%", f"{ww.distant_metastasis_risk:.1f}%"],
        ["Complication majeure", f"{surgery.major_complication_risk:.1f}%", "-"],
        ["Repousse tumorale", "-", f"{ww.regrowth_risk:.1f}%"],
    ]

    risk_table = Table(risk_data, colWidths=[60 * mm, 45 * mm, 45 * mm])
    risk_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F4F6F8")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E7EB")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    content.append(risk_table)
    content.append(Spacer(1, 10 * mm))

    # Footer
    content.append(Paragraph(
        "Ce rapport est genere par PREDI-Care, un outil d'aide a la decision. "
        "Il ne remplace pas le jugement clinique.",
        ParagraphStyle("Footer", parent=normal_style, fontSize=8, textColor=colors.gray)
    ))

    # Build PDF
    doc.build(content)
    return buffer.getvalue()


def generate_cohort_pdf_report(
    entries: Sequence[Mapping[str, Any]],
    warning_messages: Sequence[str] | None = None,
    error_messages: Sequence[str] | None = None,
) -> bytes:
    """Generate grouped cohort PDF report.

    Args:
        entries: Cohort simulation rows as dict-like records.
        warning_messages: Optional validation/simulation warnings.
        error_messages: Optional blocking errors retained for traceability.

    Returns:
        PDF bytes ready for download.
    """
    entries_list = list(entries)
    warning_messages_list = list(warning_messages or [])
    error_messages_list = list(error_messages or [])

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CohortTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
        textColor=colors.HexColor("#0066FF"),
    )
    heading_style = ParagraphStyle(
        "CohortHeading",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#1A1D21"),
    )
    normal_style = ParagraphStyle(
        "CohortNormal",
        parent=styles["Normal"],
        fontSize=9,
        spaceAfter=4,
        leading=12,
    )

    def _safe_float(entry: Mapping[str, Any], key: str) -> float:
        try:
            return float(entry.get(key, 0.0))
        except (TypeError, ValueError):
            return 0.0

    def _average(key: str) -> float:
        if not entries_list:
            return 0.0
        values = [_safe_float(entry, key) for entry in entries_list]
        return sum(values) / len(values)

    def _risk_score(entry: Mapping[str, Any]) -> float:
        explicit_score = entry.get("risk_score")
        try:
            if explicit_score is not None:
                return float(explicit_score)
        except (TypeError, ValueError):
            pass

        surgery_peak = max(
            _safe_float(entry, "local_recurrence_surgery"),
            _safe_float(entry, "distant_metastasis_surgery"),
            _safe_float(entry, "major_complication_surgery"),
        )
        watch_wait_peak = max(
            _safe_float(entry, "local_recurrence_watch_wait"),
            _safe_float(entry, "distant_metastasis_watch_wait"),
            _safe_float(entry, "regrowth_watch_wait"),
        )

        recommendation = str(entry.get("recommendation", ""))
        if recommendation == "surgery":
            return surgery_peak
        if recommendation == "watch_and_wait":
            return watch_wait_peak
        return max(surgery_peak, watch_wait_peak)

    def _risk_level(score: float) -> str:
        if score < 20.0:
            return "Faible"
        if score < 35.0:
            return "Modere"
        if score < 50.0:
            return "Eleve"
        return "Critique"

    surgery_count = sum(str(entry.get("recommendation", "")) == "surgery" for entry in entries_list)
    watch_wait_count = sum(
        str(entry.get("recommendation", "")) == "watch_and_wait"
        for entry in entries_list
    )
    uncertain_count = sum(str(entry.get("recommendation", "")) == "uncertain" for entry in entries_list)

    content = [
        Paragraph("PREDI-Care - Rapport Cohorte", title_style),
        Paragraph(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}", normal_style),
        Spacer(1, 8 * mm),
        Paragraph("Synthese globale", heading_style),
    ]

    summary_table_data = [
        ["Metrique", "Valeur"],
        ["Patients simules", str(len(entries_list))],
        ["Recommandation chirurgie", str(surgery_count)],
        ["Recommandation watch & wait", str(watch_wait_count)],
        ["Recommendation incertaine", str(uncertain_count)],
        ["DFS 5 ans moyen chirurgie", f"{_average('dfs_5y_surgery'):.1f}%"],
        ["DFS 5 ans moyen watch & wait", f"{_average('dfs_5y_watch_wait'):.1f}%"],
        ["QoL moyenne chirurgie", f"{_average('qol_surgery'):.1f}"],
        ["QoL moyenne watch & wait", f"{_average('qol_watch_wait'):.1f}"],
    ]

    summary_table = Table(summary_table_data, colWidths=[85 * mm, 65 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F4F6F8")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#5E6C84")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E7EB")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    content.append(summary_table)

    content.append(Paragraph("Qualite des donnees", heading_style))
    content.append(
        Paragraph(
            (
                f"Erreurs detectees: {len(error_messages_list)} | "
                f"Avertissements detectes: {len(warning_messages_list)}"
            ),
            normal_style,
        )
    )
    for message in error_messages_list[:10]:
        content.append(Paragraph(f"Erreur - {message}", normal_style))
    for message in warning_messages_list[:10]:
        content.append(Paragraph(f"Avertissement - {message}", normal_style))

    subgroup_specs = [
        ("Chirurgie recommandee", "surgery"),
        ("Watch & Wait recommande", "watch_and_wait"),
        ("Recommendation incertaine", "uncertain"),
    ]
    for subgroup_label, subgroup_key in subgroup_specs:
        subgroup_entries = [
            entry
            for entry in entries_list
            if str(entry.get("recommendation", "")) == subgroup_key
        ]
        if not subgroup_entries:
            continue

        content.append(PageBreak())
        content.append(Paragraph(f"Sous-cohorte: {subgroup_label}", heading_style))
        mean_risk = sum(_risk_score(entry) for entry in subgroup_entries) / len(subgroup_entries)
        content.append(
            Paragraph(
                (
                    f"Patients: {len(subgroup_entries)} | "
                    f"Risque moyen: {mean_risk:.1f}% | "
                    f"DFS 5 ans moyen Chirurgie: "
                    f"{sum(_safe_float(entry, 'dfs_5y_surgery') for entry in subgroup_entries) / len(subgroup_entries):.1f}% | "
                    f"DFS 5 ans moyen W&W: "
                    f"{sum(_safe_float(entry, 'dfs_5y_watch_wait') for entry in subgroup_entries) / len(subgroup_entries):.1f}%"
                ),
                normal_style,
            )
        )

        page_chunk_size = 24
        for chunk_start in range(0, len(subgroup_entries), page_chunk_size):
            chunk = subgroup_entries[chunk_start: chunk_start + page_chunk_size]
            if chunk_start > 0:
                content.append(PageBreak())
                content.append(Paragraph(f"Sous-cohorte: {subgroup_label} (suite)", heading_style))

            detail_table_data = [[
                "Patient",
                "Force",
                "Risque",
                "Niveau",
                "DFS5 Chir",
                "DFS5 W&W",
                "QoL Chir",
                "QoL W&W",
            ]]
            for entry in chunk:
                score = _risk_score(entry)
                detail_table_data.append(
                    [
                        str(entry.get("patient_id", "")),
                        str(entry.get("strength", "")),
                        f"{score:.1f}%",
                        _risk_level(score),
                        f"{_safe_float(entry, 'dfs_5y_surgery'):.1f}%",
                        f"{_safe_float(entry, 'dfs_5y_watch_wait'):.1f}%",
                        f"{_safe_float(entry, 'qol_surgery'):.1f}",
                        f"{_safe_float(entry, 'qol_watch_wait'):.1f}",
                    ]
                )

            detail_table = Table(
                detail_table_data,
                colWidths=[20 * mm, 18 * mm, 18 * mm, 18 * mm, 24 * mm, 24 * mm, 20 * mm, 20 * mm],
                repeatRows=1,
            )
            detail_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F4F6F8")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#5E6C84")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E7EB")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            content.append(detail_table)

    doc.build(content)
    return buffer.getvalue()
