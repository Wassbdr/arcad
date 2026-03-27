from predi_care.app_shell import build_pdf_bytes


def test_pdf_export_has_valid_signature() -> None:
    pdf_data = build_pdf_bytes([
        "PREDI-Care - Resume de decision clinique",
        "Recommendation finale: Chirurgie Radicale",
        "Niveau d'incertitude: Moyenne",
    ])
    assert isinstance(pdf_data, bytes)
    assert pdf_data.startswith(b"%PDF")
    assert len(pdf_data) > 500
