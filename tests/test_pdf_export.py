from predi_care.export.pdf_report import generate_cohort_pdf_report


def test_cohort_pdf_export_has_valid_signature() -> None:
    entries = [
        {
            "patient_id": "P001",
            "recommendation": "surgery",
            "strength": "strong",
            "dfs_5y_surgery": 86.2,
            "dfs_5y_watch_wait": 72.4,
            "qol_surgery": 68.0,
            "qol_watch_wait": 85.0,
        },
        {
            "patient_id": "P002",
            "recommendation": "watch_and_wait",
            "strength": "moderate",
            "dfs_5y_surgery": 83.1,
            "dfs_5y_watch_wait": 78.0,
            "qol_surgery": 70.0,
            "qol_watch_wait": 88.0,
        },
    ]

    pdf_data = generate_cohort_pdf_report(entries)

    assert isinstance(pdf_data, bytes)
    assert pdf_data.startswith(b"%PDF")
    assert len(pdf_data) > 800


def test_cohort_pdf_export_accepts_validation_messages() -> None:
    entries = [
        {
            "patient_id": "P010",
            "recommendation": "uncertain",
            "strength": "weak",
            "dfs_5y_surgery": 79.5,
            "dfs_5y_watch_wait": 74.1,
            "qol_surgery": 66.0,
            "qol_watch_wait": 82.0,
        }
    ]

    pdf_data = generate_cohort_pdf_report(
        entries,
        warning_messages=["Ligne 3 | age: valeur corrigee"],
        error_messages=["Ligne 2 | ct_stage: valeur invalide"],
    )

    assert pdf_data.startswith(b"%PDF")
    assert len(pdf_data) > 800


def test_cohort_pdf_export_handles_pagination_by_subgroup() -> None:
    entries = []
    for index in range(75):
        recommendation = "surgery" if index < 30 else "watch_and_wait" if index < 55 else "uncertain"
        entries.append(
            {
                "patient_id": f"P{index:03d}",
                "recommendation": recommendation,
                "strength": "moderate",
                "dfs_5y_surgery": 80.0 + (index % 7),
                "dfs_5y_watch_wait": 70.0 + (index % 9),
                "qol_surgery": 62.0 + (index % 5),
                "qol_watch_wait": 78.0 + (index % 6),
                "risk_score": 15.0 + (index % 40),
            }
        )

    pdf_data = generate_cohort_pdf_report(entries)

    assert pdf_data.startswith(b"%PDF")
    assert len(pdf_data) > 2500
