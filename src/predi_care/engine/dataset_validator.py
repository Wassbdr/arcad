"""Dataset validation utilities for BrainEngineV4.

Run from CLI:
    python -m predi_care.engine.dataset_validator --dataset data/greccar_synthetic_decision_support_cohort_v3.csv
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any

from predi_care.engine.brain_engine import BrainEngineV4


def _to_binary(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return 1.0 if float(value) >= 0.5 else 0.0
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "oui"}:
        return 1.0
    if text in {"0", "false", "no", "n", "non"}:
        return 0.0
    try:
        return 1.0 if float(text) >= 0.5 else 0.0
    except ValueError:
        return 0.0


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _auc_score(scores: list[float], labels: list[float]) -> float | None:
    if not scores or len(scores) != len(labels):
        return None
    positives = [(score, label) for score, label in zip(scores, labels) if label == 1.0]
    negatives = [(score, label) for score, label in zip(scores, labels) if label == 0.0]
    if not positives or not negatives:
        return None

    wins = 0.0
    for pos_score, _ in positives:
        for neg_score, _ in negatives:
            if pos_score > neg_score:
                wins += 1.0
            elif pos_score == neg_score:
                wins += 0.5
    total_pairs = float(len(positives) * len(negatives))
    return wins / total_pairs if total_pairs > 0 else None


def _build_calibration_rows(predictions: list[float], observations: list[float], bins: int = 10) -> list[dict[str, float]]:
    if not predictions:
        return []
    ordered = sorted(zip(predictions, observations), key=lambda item: item[0])
    size = len(ordered)
    rows: list[dict[str, float]] = []
    for bucket in range(bins):
        start = int((bucket * size) / bins)
        end = int(((bucket + 1) * size) / bins)
        slice_items = ordered[start:end]
        if not slice_items:
            continue
        pred = _mean([item[0] for item in slice_items])
        obs = _mean([item[1] for item in slice_items])
        rows.append(
            {
                "bin": float(bucket + 1),
                "predicted": pred,
                "observed": obs,
                "count": float(len(slice_items)),
            }
        )
    return rows


@dataclass
class ValidationReport:
    mae: float
    brier: float
    auc: float | None
    sample_size: int
    calibration_curve: list[dict[str, float]]
    top_errors: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mae": self.mae,
            "brier": self.brier,
            "auc": self.auc,
            "sample_size": self.sample_size,
            "calibration_curve": self.calibration_curve,
            "top_errors": self.top_errors,
        }


def generate_calibration_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    local_errors = [abs(float(row["pred_local_prob"]) - float(row["obs_local"])) for row in results]
    mae = _mean(local_errors) * 100.0
    brier_values = [(float(row["pred_dfs_prob"]) - float(row["obs_dfs"])) ** 2 for row in results]
    brier = _mean(brier_values)
    auc = _auc_score(
        [float(row["pred_ww_score"]) for row in results],
        [float(row["obs_ww"]) for row in results],
    )
    calibration_curve = _build_calibration_rows(
        [float(row["pred_local_prob"]) for row in results],
        [float(row["obs_local"]) for row in results],
        bins=10,
    )

    top_errors = sorted(
        results,
        key=lambda row: abs(float(row["pred_local_prob"]) - float(row["obs_local"])),
        reverse=True,
    )[:10]

    return {
        "mae": mae,
        "brier": brier,
        "auc": auc,
        "calibration_curve": calibration_curve,
        "top_errors": top_errors,
        "sample_size": len(results),
    }


def validate_engine_on_dataset(df: Any) -> dict[str, Any]:
    """Run v4 engine row-by-row against dataset outcomes."""
    engine = BrainEngineV4()
    rows: list[dict[str, Any]] = []

    # Force deterministic and fast validation, without remote LLM calls.
    import os

    previous_force = os.environ.get("LLM_FORCE_HEURISTIC")
    os.environ["LLM_FORCE_HEURISTIC"] = "1"
    try:
        records = df.to_dict(orient="records")
        for idx, row in enumerate(records):
            result = engine.run_dataset_row(row)
            final_management = str(row.get("final_management", ""))
            is_watch_wait = final_management == "watch_and_wait"

            if is_watch_wait:
                pred_local_prob = float(result.watch_wait.local_recurrence_2y) / 100.0
                pred_dfs_prob = float(result.watch_wait.survival_5y) / 100.0
                obs_local = _to_binary(row.get("local_regrowth_2y"))
            else:
                pred_local_prob = float(result.surgery.local_recurrence_2y) / 100.0
                pred_dfs_prob = float(result.surgery.survival_5y) / 100.0
                # Surgery cohorts often store 5y local recurrence; used here as proxy for local failure.
                obs_local = _to_binary(row.get("local_recurrence_5y_after_resection"))

            rows.append(
                {
                    "row_index": idx,
                    "patient_id": row.get("patient_id", f"IDX-{idx}"),
                    "pred_local_prob": pred_local_prob,
                    "obs_local": obs_local,
                    "pred_dfs_prob": pred_dfs_prob,
                    "obs_dfs": _to_binary(row.get("disease_free_5y")),
                    "pred_ww_score": float(result.watch_wait.eligibility_score) / 100.0,
                    "obs_ww": 1.0 if is_watch_wait else 0.0,
                    "recommendation": result.consensus.recommendation,
                    "recommendation_strength": result.consensus.recommendation_strength,
                }
            )
    finally:
        if previous_force is None:
            os.environ.pop("LLM_FORCE_HEURISTIC", None)
        else:
            os.environ["LLM_FORCE_HEURISTIC"] = previous_force

    return generate_calibration_report(rows)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate BrainEngineV4 on dataset rows.")
    parser.add_argument("--dataset", required=True, help="Path to CSV dataset file.")
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()
    import pandas as pd

    df = pd.read_csv(args.dataset)
    report = validate_engine_on_dataset(df)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
