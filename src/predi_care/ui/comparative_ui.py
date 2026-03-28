"""Module UI comparatif historique, connecte au moteur v4 via adaptateur."""

from __future__ import annotations

import html
import streamlit as st
from typing import Any

from predi_care.engine.brain_engine_v2 import DecisionResult
from predi_care.ui import visuals_v2


def _repair_display_text(value: Any) -> str:
    """Repair common mojibake artifacts and return safe display text."""
    text = str(value)
    if "Ã" in text or "Â" in text:
        try:
            return text.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return text
    return text


def _normalize_french_text(value: Any) -> str:
    """Normalize common unaccented French phrases seen in model outputs."""
    text = _repair_display_text(value)
    replacements = {
        "Des contraintes protocolaires strictes sont activees et imposent une revue pluridisciplinaire.": (
            "Des contraintes protocolaires strictes sont activées et imposent une revue pluridisciplinaire."
        ),
        "Contrefactuel cle": "Contrefactuel clé",
        "Si le TRG s'ameliorait a 2 ou moins, l'eligibilite a la surveillance active augmenterait.": (
            "Si le TRG s'améliorait à 2 ou moins, l'éligibilité à la surveillance active augmenterait."
        ),
        "Un TRG superieur a 2 contre-indique la surveillance active.": (
            "Un TRG supérieur à 2 contre-indique la surveillance active."
        ),
        "reponse": "réponse",
        "s'ameliorait": "s'améliorait",
        "eligibilite": "éligibilité",
        "superieur": "supérieur",
        "activees": "activées",
    }
    normalized = text
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized


def _normalize_factor_label(value: Any) -> str:
    text = _normalize_french_text(value).strip()
    mapping = {
        "Radiology signal": "Signal radiologique",
        "Biology signal": "Signal biologique",
        "Surgery R0": "Probabilité de résection R0",
        "Frailty": "Fragilité globale",
        "Reponse radiologique (TRG + residu)": "Réponse radiologique (TRG + résidu)",
        "Réponse radiologique (TRG + résidu)": "Réponse radiologique (TRG + résidu)",
        "Cinetique ACE": "Cinétique ACE",
        "Cinétique ACE": "Cinétique ACE",
        "Fragilite medico-chirurgicale": "Fragilité médico-chirurgicale",
        "Fragilité médico-chirurgicale": "Fragilité médico-chirurgicale",
        "Controle local attendu avec chirurgie": "Contrôle local attendu avec chirurgie",
        "Contrôle local attendu avec chirurgie": "Contrôle local attendu avec chirurgie",
    }
    return mapping.get(text, text)


def _normalize_factor_description(value: Any) -> str:
    text = _normalize_french_text(value).strip()
    mapping = {
        "Residual burden and TRG": "Charge tumorale résiduelle et TRG",
        "CEA trend and blood profile": "Cinétique ACE et profil biologique",
        "Resection margin quality": "Qualité de la marge de résection",
        "ECOG/ASA/age tolerance": "Tolérance médico-chirurgicale (ECOG/ASA/âge)",
    }
    return mapping.get(text, text)


def _ensure_sentence(value: str) -> str:
    text = value.strip()
    while text.endswith(".."):
        text = text[:-1]
    if not text:
        return ""
    if text.endswith((".", "!", "?")):
        return text
    return text + "."


def render_comparative_ui(result: DecisionResult) -> None:
    """Render complete comparative UI with dual panels and explainability."""

    # 1. Recommendation Banner
    _render_recommendation_banner(result)

    # 1b. Patient-friendly summary (LLM)
    _render_patient_summary(result)

    # 2. Dual Panel Comparison
    _render_scenario_panels(result)

    # 3. Survival Curves (full width)
    st.markdown('<div style="margin-top: 2rem;"></div>', unsafe_allow_html=True)
    _render_section_header("Courbes de Survie", "Comparaison de la survie sans récidive")
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
    _render_section_header("Tableau Comparatif", "Synthèse des métriques")
    _render_comparison_table(result)

    # 6b. Option cards focused on complication probabilities
    st.markdown('<div style="margin-top: 2rem;"></div>', unsafe_allow_html=True)
    _render_section_header(
        "Options: Probabilités de Complications",
        "Comparaison patient des complications possibles",
    )
    _render_patient_scenario_cards(result)

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
            "label": "CHIRURGIE RECOMMANDÉE",
            "icon": "S",
        },
        "watch_and_wait": {
            "bg": "linear-gradient(135deg, #00C896 0%, #00A67E 100%)",
            "label": "WATCH & WAIT RECOMMANDÉ",
            "icon": "W",
        },
        "uncertain": {
            "bg": "linear-gradient(135deg, #6B778C 0%, #505F79 100%)",
            "label": "DÉCISION ÉQUILIBRÉE",
            "icon": "?",
        },
    }

    strength_labels = {
        "strong": "Recommandation Forte",
        "moderate": "Recommandation Modérée",
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

    clinician_summary = html.escape(_build_clinician_summary(result)).replace("\n", "<br>")
    st.markdown(
        f"""
        <div style="
            background: #F4F6F8;
            border-left: 3px solid #0066FF;
            padding: 1rem 1.25rem;
            border-radius: 0 8px 8px 0;
            margin-bottom: 1.5rem;
        ">
            <p style="
                margin: 0 0 0.45rem;
                color: #5E6C84;
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            ">
                Synthèse pour l'équipe
            </p>
            <p style="margin: 0; color: #1A1D21; font-size: 0.95rem; line-height: 1.5;">
                {clinician_summary}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_patient_summary(result: DecisionResult) -> None:
    """Render a plain-language patient summary without alert styling."""
    summary = _resolve_patient_summary(result)
    if not summary:
        return

    safe_summary = html.escape(summary).replace("\n", "<br>")
    st.markdown("### Résumé pour le patient")
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(180deg, #F8FAFC 0%, #FFFFFF 100%);
            border: 1px solid #D9E2EC;
            border-radius: 14px;
            padding: 1rem 1.25rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        ">
            <p style="margin: 0; color: #1A1D21; font-size: 0.98rem; line-height: 1.65;">
                {safe_summary}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _resolve_patient_summary(result: DecisionResult) -> str:
    """Return the deterministic patient-friendly summary."""
    return _build_patient_summary_fallback(result)


def _is_generic_patient_summary(summary: str) -> bool:
    normalized = " ".join(summary.lower().split())
    generic_markers = (
        "jumeau numerique clinique multi-agent",
        "jumeau numérique clinique multi-agent",
        "decision therapeutique finale doit etre validee en reunion pluridisciplinaire",
        "decision thérapeutique finale doit être validée en réunion pluridisciplinaire",
        "decision finale doit etre validee",
        "decision finale doit etre discutee en rcp",
    )
    return not normalized or any(marker in normalized for marker in generic_markers)


def _is_patient_friendly_llm_summary(summary: str) -> bool:
    normalized = " ".join(summary.lower().split())
    technical_markers = (
        "mrtrg",
        "trg",
        "eligibilite",
        "eligibility",
        "contrefactuel",
        "counterfactual",
        "pluridisciplinaire",
        "multi-agent",
        "protocolaire",
        "dfs",
        "rcp",
    )
    return not any(marker in normalized for marker in technical_markers)


def _build_clinician_summary(result: DecisionResult) -> str:
    segments: list[str] = []

    recommendation_text = _normalize_french_text(result.rationale.recommendation_text or "").strip()
    if recommendation_text:
        segments.append(_ensure_sentence(recommendation_text))

    recommendation_context = {
        "surgery": "Orientation actuelle: chirurgie priorisée.",
        "watch_and_wait": "Orientation actuelle: Watch & Wait priorisé.",
        "uncertain": "Orientation actuelle: équilibre entre les deux options.",
    }
    segments.append(recommendation_context.get(result.recommended_scenario, "Orientation actuelle: analyse en cours."))

    segments.append(
        (
            "Instantané patient: "
            f"DFS 5 ans chirurgie {result.surgery_outcome.dfs_5_years:.1f}% vs "
            f"W&W {result.ww_outcome.dfs_5_years:.1f}%; "
            f"complications majeures chirurgie {result.surgery_outcome.major_complication_risk:.1f}%; "
            f"repousse en surveillance {result.ww_outcome.regrowth_risk:.1f}%."
        )
    )

    primary_descriptions = [
        _normalize_factor_description(description).strip()
        for _, _, description in result.rationale.primary_factors[:2]
        if _normalize_factor_description(description).strip()
    ]
    if primary_descriptions:
        segments.append(_ensure_sentence("Facteurs dominants: " + " ; ".join(primary_descriptions)))
    else:
        top_contribs = sorted(
            result.rationale.feature_contributions.items(),
            key=lambda item: abs(float(item[1])),
            reverse=True,
        )[:2]
        if top_contribs:
            factors = [
                f"{_normalize_factor_label(name)} ({float(value):+.1f})"
                for name, value in top_contribs
            ]
            segments.append(_ensure_sentence("Facteurs dominants: " + " ; ".join(factors)))

    if result.rationale.clinical_alerts:
        alert = _normalize_french_text(result.rationale.clinical_alerts[0])
        segments.append(_ensure_sentence(f"Alerte principale: {alert}"))

    return " ".join(segment.strip() for segment in segments if segment.strip())


def _build_patient_summary_fallback(result: DecisionResult) -> str:
    patient = result.patient_input
    recommendation = result.recommended_scenario
    surgery = result.surgery_outcome
    watch_wait = result.ww_outcome

    residual_ratio = float(patient.get("residual_tumor_ratio", 0.0))
    residual_cm = float(patient.get("residual_size_cm", residual_ratio / 20.0))
    mrtrg = int(patient.get("mrtrg", 3))
    ace_baseline = float(patient.get("ace_baseline", 0.0))
    ace_current = float(patient.get("ace_current", 0.0))

    response_sentence = _build_response_sentence(
        residual_cm=residual_cm,
        residual_ratio=residual_ratio,
        mrtrg=mrtrg,
        ace_baseline=ace_baseline,
        ace_current=ace_current,
    )

    if recommendation == "watch_and_wait":
        return " ".join(
            [
                "Aujourd'hui, l'équipe pense qu'il est possible d'éviter une operation tout de suite.",
                response_sentence,
                (
                    f"Dans ce profil, la surveillance expose à un risque de repousse d'environ "
                    f"{watch_wait.regrowth_risk:.1f}%, et une operation secondaire peut devenir nécessaire "
                    f"dans environ {watch_wait.salvage_surgery_risk:.1f}% des cas."
                ),
                (
                    f"La chirurgie reste une alternative avec environ {surgery.dfs_5_years:.1f}% "
                    f"de contrôle de la maladie à 5 ans."
                ),
            ]
        )

    if recommendation == "surgery":
        return " ".join(
            [
                "Aujourd'hui, l'équipe penche plutôt pour une operation.",
                response_sentence,
                (
                    f"Dans ce profil, la chirurgie offre environ {surgery.dfs_5_years:.1f}% "
                    f"de contrôle de la maladie à 5 ans."
                ),
                (
                    f"En parallèle, une surveillance seule exposerait à un risque de repousse "
                    f"d'environ {watch_wait.regrowth_risk:.1f}%."
                ),
            ]
        )

    return " ".join(
        [
            "Aujourd'hui, deux choix restent possibles: une operation ou une surveillance très rapprochée.",
            response_sentence,
            (
                f"Repères chiffrés: chirurgie {surgery.dfs_5_years:.1f}% de contrôle à 5 ans; "
                f"surveillance {watch_wait.regrowth_risk:.1f}% de risque de repousse et "
                f"{watch_wait.salvage_surgery_risk:.1f}% de risque d'operation secondaire."
            ),
            "La décision dépend surtout de ce que vous préférez entre plus de sécurité tout de suite, ou éviter l'operation mais accepter des contrôles fréquents.",
        ]
    )


def _build_response_sentence(
    *,
    residual_cm: float,
    residual_ratio: float,
    mrtrg: int,
    ace_baseline: float,
    ace_current: float,
) -> str:
    if residual_cm <= 0.5 or residual_ratio <= 10.0 or mrtrg <= 1:
        response = (
            f"Le traitement semble avoir très bien marché et il reste très peu de chose visible, environ {residual_cm:.1f} cm."
        )
    elif residual_cm >= 2.0 or residual_ratio >= 50.0 or mrtrg >= 4:
        response = (
            f"Le traitement a aidé, mais il reste encore une zone d'environ {residual_cm:.1f} cm."
        )
    else:
        response = (
            f"Le traitement a plutôt bien marché, mais il reste encore une petite zone d'environ {residual_cm:.1f} cm."
        )

    if ace_baseline > 0.0:
        if ace_current <= ace_baseline - 1.0:
            response += " La prise de sang va plutôt dans le bon sens."
        elif ace_current >= ace_baseline + 1.0 or ace_current > 5.0:
            response += " La prise de sang pousse à rester prudent."

    return response


def _render_patient_scenario_cards(result: DecisionResult) -> None:
    cards = _build_patient_scenario_cards(result)
    st.markdown(
        """
        <div style="margin: 0.25rem 0 0.9rem;">
            <p style="
                margin: 0;
                color: #5E6C84;
                font-size: 0.82rem;
                font-weight: 600;
                letter-spacing: 0.02em;
            ">
                Deux options à discuter
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    columns = st.columns(2)
    for column, card in zip(columns, cards):
        with column:
            _render_patient_scenario_card(card)

    st.markdown("<div style='height: 1.25rem;'></div>", unsafe_allow_html=True)


def _build_patient_scenario_cards(result: DecisionResult) -> list[dict[str, Any]]:
    surgery_badge = _patient_option_badge(result, "surgery")
    watch_badge = _patient_option_badge(result, "watch_and_wait")

    surgery_points = [
        (
            "Complication importante possible: "
            f"{result.surgery_outcome.major_complication_risk:.1f}%."
        ),
        (
            "Troubles digestifs durables possibles (LARS majeur): "
            f"{result.surgery_outcome.lars_risk:.1f}%."
        ),
        (
            "Stomie permanente possible: "
            f"{result.surgery_outcome.stoma_risk:.1f}%."
        ),
        (
            "Risque de récidive locale: "
            f"{result.surgery_outcome.local_recurrence_risk:.1f}%."
        ),
    ]

    surgery_card = {
        "eyebrow": "Option 1",
        "title": "Operation",
        "display_title": "Opération",
        "accent": "#0066FF",
        "badge": surgery_badge,
        "summary": "On retire la zone restante. Voici les probabilités des complications possibles pour ce patient.",
        "points": surgery_points,
    }

    watch_points = [
        (
            "La maladie peut revenir au même endroit (repousse): "
            f"{result.ww_outcome.regrowth_risk:.1f}%."
        ),
        (
            "Une opération plus tard peut devenir nécessaire: "
            f"{result.ww_outcome.salvage_surgery_risk:.1f}%."
        ),
        (
            "Risque de récidive locale: "
            f"{result.ww_outcome.local_recurrence_risk:.1f}%."
        ),
        (
            "Risque de métastase à distance: "
            f"{result.ww_outcome.distant_metastasis_risk:.1f}%."
        ),
    ]

    watch_card = {
        "eyebrow": "Option 2",
        "title": "Surveillance rapprochee",
        "display_title": "Surveillance rapprochée",
        "accent": "#00A67E",
        "badge": watch_badge,
        "summary": "On n'opère pas tout de suite. Voici les probabilités des complications possibles pour ce patient.",
        "points": watch_points,
    }

    return [surgery_card, watch_card]


def _patient_option_badge(result: DecisionResult, option: str) -> str:
    if result.recommended_scenario == "uncertain":
        return "Option possible"
    if result.recommended_scenario == option:
        return "Option plutôt privilégiée"
    return "Option encore possible"


def _render_patient_scenario_card(card: dict[str, Any]) -> None:
    points = [_normalize_french_text(point) for point in card.get("points", [])]
    points_html = "".join(
        f'<li style="margin: 0 0 0.45rem; color: #7B341E;">{html.escape(point)}</li>'
        for point in points
    )

    display_title = _normalize_french_text(card.get("display_title", card.get("title", "")))
    st.markdown(
        f"""
        <div style="
            background: #FFFFFF;
            border: 1px solid #D9E2EC;
            border-top: 4px solid {card['accent']};
            border-radius: 16px;
            padding: 1rem 1.1rem 1.1rem;
            height: 100%;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.05);
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; margin-bottom: 0.8rem;">
                <div>
                    <p style="
                        margin: 0 0 0.18rem;
                        color: #5E6C84;
                        font-size: 0.72rem;
                        font-weight: 700;
                        letter-spacing: 0.08em;
                        text-transform: uppercase;
                    ">
                        {html.escape(str(card['eyebrow']))}
                    </p>
                    <h4 style="margin: 0; color: #102A43; font-size: 1.02rem; font-weight: 700;">
                        {html.escape(display_title)}
                    </h4>
                </div>
                <span style="
                    display: inline-flex;
                    align-items: center;
                    padding: 0.28rem 0.6rem;
                    border-radius: 999px;
                    background: color-mix(in srgb, {card['accent']} 10%, white);
                    color: {card['accent']};
                    font-size: 0.74rem;
                    font-weight: 700;
                    white-space: normal;
                    max-width: 160px;
                    text-align: center;
                    line-height: 1.25;
                ">
                    {html.escape(str(card['badge']))}
                </span>
            </div>
            <p style="margin: 0 0 0.85rem; color: #243B53; font-size: 0.93rem; line-height: 1.55;">
                {html.escape(str(card['summary']))}
            </p>
            <div>
                <p style="margin: 0 0 0.45rem; color: #486581; font-size: 0.79rem; font-weight: 700; letter-spacing: 0.02em;">
                    Probabilités de complications possibles
                </p>
                <ul style="margin: 0; padding-left: 1.1rem; font-size: 0.9rem; line-height: 1.55; word-break: break-word;">
                    {points_html}
                </ul>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
        st.metric("Qualité de Vie", f"{outcome.qol_score:.0f}/100")
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
        st.metric("Probabilité R0", f"{result.llm_response.surgery.r0_probability:.1f}%")

    # Risks
    with st.expander("Détails des Risques"):
        st.markdown(f"**Récidive locale:** {outcome.local_recurrence_risk:.1f}%")
        st.markdown(f"**Métastase:** {outcome.distant_metastasis_risk:.1f}%")
        st.markdown(f"**Complication majeure:** {outcome.major_complication_risk:.1f}%")
        st.markdown(f"**Stomie permanente:** {outcome.stoma_risk:.1f}%")
        st.markdown(f"**LARS majeur:** {outcome.lars_risk:.1f}%")
        if result.rationale.surgery_risks:
            st.markdown("**Complications prévues (détail):**")
            for line in result.rationale.surgery_risks[:8]:
                st.markdown(f"- {line}")

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
    eligibility_text = "Éligible" if outcome.eligible else "Non éligible"

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
        st.metric("Qualité de Vie", f"{outcome.qol_score:.0f}/100")
    with col4:
        st.metric("Confiance", f"{outcome.confidence_score:.0f}%")

    # Extended W&W metrics
    if result.llm_response is not None:
        col5, col6 = st.columns(2)
        with col5:
            st.metric("Préservation organe 2a", f"{result.llm_response.watch_wait.organ_preservation_2y:.1f}%")
        with col6:
            burden_labels = {"low": "Faible", "moderate": "Modérée", "high": "Élevée"}
            burden = burden_labels.get(result.llm_response.watch_wait.surveillance_burden, "Modérée")
            st.metric("Charge surveillance", burden)

    # Risks
    with st.expander("Détails des Risques"):
        st.markdown(f"**Repousse tumorale:** {outcome.regrowth_risk:.1f}%")
        st.markdown(f"**Chirurgie de sauvetage:** {outcome.salvage_surgery_risk:.1f}%")
        st.markdown(f"**Récidive locale:** {outcome.local_recurrence_risk:.1f}%")
        st.markdown(f"**Métastase:** {outcome.distant_metastasis_risk:.1f}%")
        if result.rationale.ww_risks:
            st.markdown("**Complications prévues (détail):**")
            for line in result.rationale.ww_risks[:8]:
                st.markdown(f"- {line}")

    st.markdown("</div>", unsafe_allow_html=True)


def _render_explainability_section(result: DecisionResult) -> None:
    """Render explainability section."""

    _render_section_header("Raisonnement Clinique", "Facteurs influençant la décision")

    # Primary factors as clean cards
    for var, weight, desc in result.rationale.primary_factors:
        clean_var = _normalize_factor_label(var)
        clean_desc = _normalize_factor_description(desc)
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
                    <span style="font-weight: 600; color: #1A1D21;">{clean_var}</span>
                    <span style="
                        background: #E6F0FF;
                        color: #0066FF;
                        font-size: 0.7rem;
                        font-weight: 700;
                        padding: 0.2rem 0.5rem;
                        border-radius: 100px;
                    ">{weight:.0%}</span>
                </div>
                <p style="margin: 0; color: #5E6C84; font-size: 0.85rem;">{clean_desc}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # SHAP contributions chart
    clean_feature_contributions: dict[str, float] = {}
    for name, value in result.rationale.feature_contributions.items():
        clean_name = _normalize_factor_label(name)
        clean_feature_contributions[clean_name] = clean_feature_contributions.get(clean_name, 0.0) + float(value)

    explainability_data = {
        "feature_contributions": clean_feature_contributions,
        "primary_factors": [
            {
                "name": _normalize_factor_label(var),
                "weight": weight,
                "description": _normalize_factor_description(desc),
            }
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
            clean_alert = _normalize_french_text(alert)
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
                ">{clean_alert}</div>
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
        "Métrique": [
            "Éligibilité",
            "Score éligibilité",
            "DFS 2 ans",
            "DFS 5 ans",
            "Qualité de Vie",
            "Confiance Modèle",
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
    _render_section_header("Mode Scénarios", "Exploration des alternatives cliniques")

    st.markdown("Testez l'impact d'un allongement du délai post-RCT (données GRECCAR 6) :")

    # The slider state lives isolated here, but to re-run we need to update PatientInput and re-run engine.
    # To keep it simple in Streamlit, we update session state and trigger a rerun.
    
    col1, col2 = st.columns([2, 1])
    with col1:
        current_delay = getattr(result.patient_input, "delay_weeks_post_rct", result.patient_input.get("delay_weeks_post_rct", 8))
        new_delay = st.slider(
            "Nouveau délai post-RCT (semaines)",
            4, 16, int(current_delay), 1,
            key="whatif_delay_slider"
        )
    with col2:
        st.write("")
        st.write("")
        if st.button("Re-simuler avec ce délai", use_container_width=True, type="secondary"):
            if "patient_input" in st.session_state and st.session_state["patient_input"]:
                st.session_state["patient_input"]["delay_weeks_post_rct"] = new_delay
            # Since patient_input might just be in the main app closure, we use a global signal or just 
            # let the user change it in the sidebar. For now, we update sidebar state:
            st.session_state["demo_preset"] = dict(result.patient_input)
            st.session_state["demo_preset"]["delay_weeks_post_rct"] = new_delay
            # clear result
            st.session_state.pop("result", None)
            st.rerun()
