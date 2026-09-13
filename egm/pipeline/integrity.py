"""Integrity checks against the failure modes of the superseded pipeline.

See DEPRECATED.md. The detector here is validated in tests against that
dataset directly.
"""
from collections import Counter
from typing import Iterable

import pandas as pd


class IntegrityError(Exception):
    """Raised when data violates an integrity rule. Never caught internally."""


def modal_share(values: Iterable) -> float:
    """Fraction of non-null values occupied by the single most common value."""
    present = [v for v in values if v is not None and not pd.isna(v)]
    if not present:
        return 0.0
    _, count = Counter(present).most_common(1)[0]
    return count / len(present)


def find_placeholder_saturation(
    df: pd.DataFrame, threshold: float = 0.20, min_unique: int = 10
) -> dict[str, tuple[object, float]]:
    """Return numeric columns whose modal value exceeds `threshold` share.

    A legitimately measured quantity rarely repeats one exact value in more
    than a fifth of rows; a substituted constant always does.

    Columns with fewer than `min_unique` distinct non-null values are skipped
    (they are categorical flags or codes, not measurements; modal share is
    meaningless for them).
    """
    flagged: dict[str, tuple[object, float]] = {}
    for column in df.select_dtypes(include="number").columns:
        series = df[column].dropna()
        if series.empty:
            continue
        # Skip low-cardinality columns (categorical/flag data)
        if series.nunique() < min_unique:
            continue
        share = modal_share(series.tolist())
        if share > threshold:
            flagged[column] = (series.mode().iloc[0], share)
    return flagged


def assert_no_placeholder_saturation(
    df: pd.DataFrame, threshold: float = 0.20, min_unique: int = 10
) -> None:
    """Raise IntegrityError if any numeric column looks constant-filled."""
    flagged = find_placeholder_saturation(df, threshold, min_unique)
    if flagged:
        detail = "; ".join(
            f"{col}={value!r} in {share:.0%} of rows" for col, (value, share) in flagged.items()
        )
        raise IntegrityError(f"Placeholder saturation detected: {detail}")
