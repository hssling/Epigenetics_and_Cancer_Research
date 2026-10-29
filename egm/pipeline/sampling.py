"""Validation-sample selection.

The ONLY module permitted to import `random` (spec section 8.3 rule 3).
Sampling is a methodological procedure, not a data-production step: it
selects which records a human re-screens. It never produces a value that
appears in results.
"""
import random
from typing import Sequence, TypeVar

T = TypeVar("T")


def stratified_sample(
    items: Sequence[T], strata: Sequence[str], per_stratum: dict[str, int], seed: int
) -> list[T]:
    """Draw a reproducible stratified sample.

    `seed` is mandatory: the validation sample must be reproducible from the
    published protocol.
    """
    if len(items) != len(strata):
        raise ValueError(f"items ({len(items)}) and strata ({len(strata)}) must align")

    rng = random.Random(seed)
    buckets: dict[str, list[T]] = {}
    for item, stratum in zip(items, strata):
        buckets.setdefault(stratum, []).append(item)

    selected: list[T] = []
    for stratum, wanted in sorted(per_stratum.items()):
        available = buckets.get(stratum, [])
        if wanted > len(available):
            raise ValueError(
                f"stratum {stratum!r}: requested {wanted}, only {len(available)} available"
            )
        selected.extend(rng.sample(available, wanted))
    return selected
