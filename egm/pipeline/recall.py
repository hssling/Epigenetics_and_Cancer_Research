"""Recall validation for AI screening.

Produces the sensitivity estimate and confidence interval the registration
commits to publishing, including when the result is unflattering. There is
deliberately no parameter that excludes a block of the sample from the
calculation.
"""
import pathlib
from collections import defaultdict
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from pipeline.screen_schema import (
    ScreeningDecision,
    read_decisions,
    single_ai_provenance,
)

# Confidence below this is the "low" stratum, and so on. Boundaries are
# recorded here so the stratification is reproducible from the code.
# Confidence strata for the recall validation sample, as UPPER bounds (strict).
#
# Reset 2026-09-17 from (0.5, 0.8, 1.01) after inspecting the real exclusion
# confidence distribution, which is what the design spec directs: "strata
# boundaries set after inspecting the confidence distribution, recorded before
# drawing". The original values were written before any screening existed and
# assumed a lower-confidence screener than the one that ran.
#
# Under the old boundaries only 16 of 3,767 AI exclusions fell in `low`, against
# the 500 the registered allocation draws from it. `stratified_sample` refused
# to draw rather than silently returning 16 — which is the behaviour that
# surfaced this at all.
#
# These values are chosen so the SAMPLING FRACTION falls monotonically as
# confidence rises, which is the whole point of the stratification: the
# error-prone tail is over-sampled. With the registered 500/300/200 allocation
# they give N = 790 / 1,369 / 1,608 and fractions 63% / 22% / 12%. Every other
# candidate inspected inverted that ordering, sampling high-confidence
# exclusions more heavily than mid — which would have defeated the design.
#
# Chosen BEFORE the sample was drawn, before any human screening, and before
# any recall figure existed, so they cannot have been tuned toward a
# favourable answer. See protocol/amendments.md, Amendment 5.
STRATUM_BOUNDARIES: tuple[tuple[str, float], ...] = (
    ("low", 0.66),
    ("mid", 0.81),
    ("high", 1.01),
)


class RecallReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    n_validated: int
    false_negatives: int
    sensitivity: float
    sensitivity_ci_low: float
    sensitivity_ci_high: float
    fn_rate: float
    fn_rate_ci_low: float
    fn_rate_ci_high: float
    implied_missed_low: float
    implied_missed_high: float
    total_excluded: int
    by_stratum: dict[str, dict[str, Any]]
    weighted_fn_rate: float
    weighted_fn_rate_ci_low: float
    weighted_fn_rate_ci_high: float
    rate_basis: str
    model_id: Optional[str]
    prompt_sha256: Optional[str]


def _beta_ppf(p: float, a: float, b: float) -> float:
    """Inverse beta CDF by bisection.

    Used for exact Clopper-Pearson bounds without a SciPy dependency.
    """
    if a <= 0:
        return 0.0
    if b <= 0:
        return 1.0

    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if _beta_cdf(mid, a, b) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _beta_cdf(x: float, a: float, b: float) -> float:
    """Regularised incomplete beta function via its continued fraction.

    WARNING: The naive continued fraction without the fixes below has max
    error ≈1.0 and is wrong for most inputs (e.g., 0/1000 returns ≈1.0
    instead of ≈0.00368, breaking the published statistic). The symmetry
    transformation x > (a+1)/(a+b+2) is critical. The closed forms for
    a=1 and b=1 are exact textbook identities. Do NOT restore the literal
    task-brief code without understanding it is non-functional. This
    corrected version agrees with scipy to ~1e-13 across a wide grid.
    """
    import math

    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0

    # Special case for a=1: I_x(1, b) = 1 - (1-x)^b (exact)
    if a == 1.0:
        return 1.0 - (1.0 - x) ** b

    # Special case for b=1: I_x(a, 1) = x^a (exact)
    if b == 1.0:
        return x ** a

    # Use symmetry: if x > (a+1)/(a+b+2), compute 1 - I_{1-x}(b, a)
    # to improve numerical convergence
    if x > (a + 1.0) / (a + b + 2.0):
        return 1.0 - _beta_cdf(1.0 - x, b, a)

    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a

    f, c, d = 1.0, 1.0, 0.0
    for i in range(300):
        m = i // 2
        if i == 0:
            numerator = 1.0
        elif i % 2 == 0:
            numerator = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            numerator = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))

        d = 1.0 + numerator * d
        d = 1e-30 if abs(d) < 1e-30 else d
        d = 1.0 / d

        c = 1.0 + numerator / c
        c = 1e-30 if abs(c) < 1e-30 else c

        f *= c * d
        if abs(1.0 - c * d) < 1e-12:
            break

    result = front * (f - 1.0)
    return min(max(result, 0.0), 1.0)


def clopper_pearson(
    successes: int, n: int, confidence: float = 0.95
) -> tuple[float, float]:
    """Exact binomial confidence interval (Clopper-Pearson)."""
    if n <= 0:
        raise ValueError("n must be positive")
    if successes > n:
        raise ValueError(f"successes ({successes}) cannot exceed n ({n})")
    if successes < 0:
        raise ValueError("successes cannot be negative")

    alpha = 1.0 - confidence
    low = 0.0 if successes == 0 else _beta_ppf(alpha / 2, successes, n - successes + 1)
    high = 1.0 if successes == n else _beta_ppf(
        1 - alpha / 2, successes + 1, n - successes
    )
    return low, high


def stratum_of(confidence: float) -> str:
    for name, upper in STRATUM_BOUNDARIES:
        if confidence < upper:
            return name
    return STRATUM_BOUNDARIES[-1][0]


def _latest(decisions: list[ScreeningDecision]) -> dict[str, ScreeningDecision]:
    latest: dict[str, ScreeningDecision] = {}
    for decision in decisions:
        latest[decision.record_id] = decision
    return latest


def validate_recall(
    human_path: pathlib.Path,
    ai_path: pathlib.Path,
    expected_record_ids: set[str],
    stratum_sizes: dict[str, int],
    confidence: float = 0.95,
) -> RecallReport:
    """Estimate screening recall from hand-screened AI exclusions.

    `expected_record_ids` is the full drawn validation sample. The registered
    denominator is that whole sample, not however much of it happens to have
    a human decision recorded so far — an abandoned or partial screening
    session must fail loudly rather than quietly publish a smaller n.

    `stratum_sizes` gives the population size of each confidence stratum
    across ALL AI exclusions, which is what makes the weighted estimate
    meaningful: the sample deliberately over-samples low-confidence records,
    so its raw rate is not the population rate.
    """
    human = _latest(read_decisions(human_path))
    ai = _latest(read_decisions(ai_path))

    missing = expected_record_ids - set(human)
    if missing:
        raise ValueError(
            f"{len(missing)} of {len(expected_record_ids)} drawn records have no human "
            f"decision (e.g. {sorted(missing)[:5]}); recall cannot be estimated from a "
            "partial sample — the registered denominator is the full drawn sample"
        )

    missing_ai = expected_record_ids - set(ai)
    if missing_ai:
        raise ValueError(
            f"{len(missing_ai)} of {len(expected_record_ids)} drawn records have no AI "
            f"decision (e.g. {sorted(missing_ai)[:5]}); recall cannot be estimated "
            "against a truncated screening log"
        )

    shared = sorted(set(human) & set(ai))
    if not shared:
        raise ValueError("no records appear in both decision logs")

    not_excluded = [r for r in shared if ai[r].decision != "exclude"]
    if not_excluded:
        raise ValueError(
            "validation sample contains records not excluded by AI "
            f"({not_excluded[:5]}); recall is estimated from exclusions only"
        )

    per_stratum: dict[str, dict[str, int]] = defaultdict(
        lambda: {"n": 0, "false_negatives": 0}
    )
    false_negatives = 0

    for record_id in shared:
        stratum = stratum_of(ai[record_id].confidence)
        per_stratum[stratum]["n"] += 1
        # The AI excluded it. If a human would not have, it is a miss —
        # 'unclear' counts, because that record should have reached a human.
        if human[record_id].decision in ("include", "unclear"):
            per_stratum[stratum]["false_negatives"] += 1
            false_negatives += 1

    unknown = set(per_stratum) - set(stratum_sizes)
    if unknown:
        raise ValueError(
            f"sample contains strata absent from stratum_sizes: {sorted(unknown)}; "
            "they would be dropped from the weighted estimate"
        )

    n = len(shared)
    sensitivity = (n - false_negatives) / n
    sens_low, sens_high = clopper_pearson(n - false_negatives, n, confidence)
    fn_low, fn_high = clopper_pearson(false_negatives, n, confidence)

    total_excluded = sum(stratum_sizes.values())

    weighted = 0.0
    by_stratum: dict[str, dict[str, Any]] = {}
    for stratum, size in stratum_sizes.items():
        counts = per_stratum.get(stratum, {"n": 0, "false_negatives": 0})
        rate = counts["false_negatives"] / counts["n"] if counts["n"] else 0.0
        weighted += rate * (size / total_excluded) if total_excluded else 0.0
        by_stratum[stratum] = {
            "population": size,
            "sampled": counts["n"],
            "false_negatives": counts["false_negatives"],
            "fn_rate": rate,
        }

    # The raw fn_rate above comes from a sample that deliberately over-samples
    # low-confidence exclusions, so it is not the rate to project onto the
    # full excluded population. implied_missed must instead be built from the
    # stratum-weighted rate — including its uncertainty, via the per-stratum
    # Clopper-Pearson bounds under the same population weights. A stratum with
    # population but no sampled records is fully uncertain (0.0 to 1.0), never
    # assumed to be 0.
    weighted_low = 0.0
    weighted_high = 0.0
    for stratum, size in stratum_sizes.items():
        counts = per_stratum.get(stratum, {"n": 0, "false_negatives": 0})
        share = size / total_excluded if total_excluded else 0.0
        if counts["n"]:
            s_low, s_high = clopper_pearson(
                counts["false_negatives"], counts["n"], confidence
            )
        else:
            s_low, s_high = 0.0, 1.0
        weighted_low += s_low * share
        weighted_high += s_high * share

    model_id, prompt_sha256 = single_ai_provenance([ai[r] for r in shared])

    return RecallReport(
        n_validated=n,
        false_negatives=false_negatives,
        sensitivity=sensitivity,
        sensitivity_ci_low=sens_low,
        sensitivity_ci_high=sens_high,
        fn_rate=false_negatives / n,
        fn_rate_ci_low=fn_low,
        fn_rate_ci_high=fn_high,
        implied_missed_low=weighted_low * total_excluded,
        implied_missed_high=weighted_high * total_excluded,
        total_excluded=total_excluded,
        by_stratum=by_stratum,
        weighted_fn_rate=weighted,
        weighted_fn_rate_ci_low=weighted_low,
        weighted_fn_rate_ci_high=weighted_high,
        rate_basis=(
            "implied_missed is derived from the stratum-weighted rate; fn_rate "
            "is the unweighted sample rate"
        ),
        model_id=model_id,
        prompt_sha256=prompt_sha256,
    )
