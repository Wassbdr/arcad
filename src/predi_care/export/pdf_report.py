"""PDF Export Module for PREDI-Care Reports."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import TYPE_CHECKING

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
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
