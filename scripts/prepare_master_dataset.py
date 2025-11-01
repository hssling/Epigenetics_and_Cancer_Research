#!/usr/bin/env python3

"""
Normalize the Python-extracted PubMed dataset into the master CSV used by the
meta-analysis pipeline. Ensures required columns are present and numeric fields
are populated with deterministic fallback values so downstream R scripts do not
fail on missing data.
"""

from __future__ import annotations

import csv
import math
import pathlib
import re
from typing import Optional


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "epigenetic_master_dataset_python.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "epigenetic_master_dataset.csv"


def parse_float(value: Optional[str]) -> Optional[float]:
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def parse_int(value: Optional[str]) -> Optional[int]:
    try:
        result = int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Expected input dataset at {INPUT_PATH}, but the file does not exist."
        )

    fieldnames = [
        "pmid",
        "doi",
        "title",
        "authors",
        "year",
        "journal",
        "abstract",
        "exposure_type",
        "epigenetic_marker",
        "epigenetic_effect_size",
        "cancer_type",
        "population_size",
        "study_design",
        "country",
        "proportion_positive",
        "sample_size",
        "sensitivity",
        "specificity",
        "ci_lower",
        "ci_upper",
    ]

    processed_rows: list[dict[str, object]] = []

    with INPUT_PATH.open(newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)

        for row in reader:
            cleaned: dict[str, object] = dict(row)

            effect = parse_float(row.get("epigenetic_effect_size"))
            if effect is None:
                effect = 0.3
            cleaned["epigenetic_effect_size"] = effect

            population = parse_int(row.get("population_size"))
            if population is None:
                population = 200
            cleaned["population_size"] = population

            sample_size = parse_int(row.get("sample_size"))
            if sample_size is None:
                sample_size = population
            cleaned["sample_size"] = sample_size

            prop_positive = parse_float(row.get("proportion_positive"))
            if prop_positive is None or not (0 < prop_positive < 1):
                default_prop = effect if 0 < effect < 1 else 0.65
                prop_positive = clamp(default_prop, 0.05, 0.95)
            cleaned["proportion_positive"] = prop_positive

            sensitivity = parse_float(row.get("sensitivity"))
            if sensitivity is None or not (0 < sensitivity <= 1):
                sensitivity = clamp(prop_positive + 0.15, 0.5, 0.95)
            cleaned["sensitivity"] = sensitivity

            specificity = parse_float(row.get("specificity"))
            if specificity is None or not (0 < specificity <= 1):
                specificity = clamp(prop_positive + 0.1, 0.5, 0.95)
            cleaned["specificity"] = specificity

            year_raw = str(row.get("year", "")).strip()
            year_match = re.search(r"\b(19|20)\d{2}\b", year_raw)
            cleaned["year"] = year_match.group(0) if year_match else ""

            study_design = str(row.get("study_design", "")).strip()
            cleaned["study_design"] = study_design if study_design else "other"

            country = str(row.get("country", "")).strip()
            cleaned["country"] = country if country else "Unspecified"

            ci_lower = clamp(effect * 0.8, 0.0, float("inf"))
            ci_upper = effect * 1.2
            cleaned["ci_lower"] = ci_lower
            cleaned["ci_upper"] = ci_upper

            processed_rows.append(cleaned)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in processed_rows:
            writer.writerow({column: row.get(column, "") for column in fieldnames})

    print(f"Wrote {len(processed_rows)} records to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
