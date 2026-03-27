"""CSV data loader for patient cohorts."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Dict, Any

from predi_care.engine.brain_engine import PatientInput


def load_patients_from_csv(filepath: Path) -> List[Dict[str, Any]]:
    """Load patient data from a CSV file.

    Expected CSV columns:
    - patient_id: unique identifier
    - ct_stage: "cT1", "cT2", "cT3", "cT4"
    - cn_stage: "cN0", "cN1", "cN2"
    - cm_stage: "cM0", "cM1"
    - ace_baseline: float (ng/mL)
    - ace_current: float (ng/mL)
    - residual_tumor_ratio: float (%)
    - imaging_quality: "Elevee", "Moyenne", "Basse"
    - age: int
    - performance_status: int (ECOG 0-4)

    Returns:
        List of dicts with patient_id and PatientInput fields.
    """
    patients: List[Dict[str, Any]] = []

    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            patient_data: Dict[str, Any] = {
                "patient_id": row.get("patient_id", f"P{len(patients)+1:03d}"),
                "input": PatientInput(
                    ct_stage=row["ct_stage"],
                    cn_stage=row["cn_stage"],
                    cm_stage=row["cm_stage"],
                    ace_baseline=float(row["ace_baseline"]),
                    ace_current=float(row["ace_current"]),
                    residual_tumor_ratio=float(row["residual_tumor_ratio"]),
                    imaging_quality=row["imaging_quality"],
                    age=int(row["age"]),
                    performance_status=int(row["performance_status"]),
                ),
            }
            patients.append(patient_data)

    return patients


def get_available_cohorts(data_dir: Path | None = None) -> List[Path]:
    """List available CSV cohort files in the data directory.

    Args:
        data_dir: Directory to search. Defaults to data/cohorts/.

    Returns:
        List of Path objects for available CSV files.
    """
    if data_dir is None:
        data_dir = Path(__file__).parent.parent.parent.parent / "data" / "cohorts"

    if not data_dir.exists():
        return []

    return sorted(data_dir.glob("*.csv"))
