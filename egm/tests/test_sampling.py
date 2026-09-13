"""Stratified sampling for the validation sets.

This module draws the two samples the published recall statistics rest on: the
300-record calibration set and the 1,000-record set of AI-excluded records that
is hand-screened to estimate recall. The registered protocol states both are
"seeded and reproducible", so reproducibility is a methodological commitment
here, not a convenience — a reader must be able to redraw the same sample from
the published seed and check the reported numbers.
"""
import pytest

from pipeline.sampling import stratified_sample


def _population(n_per_stratum: dict[str, int]):
    """Build aligned items/strata lists with globally unique item labels."""
    items, strata = [], []
    for stratum, count in sorted(n_per_stratum.items()):
        for i in range(count):
            items.append(f"{stratum}-{i}")
            strata.append(stratum)
    return items, strata


# --- reproducibility --------------------------------------------------------


def test_same_seed_yields_the_identical_sample():
    """The protocol's reproducibility claim depends on exactly this."""
    items, strata = _population({"high": 50, "low": 50})
    want = {"high": 10, "low": 10}

    first = stratified_sample(items, strata, want, seed=20260913)
    second = stratified_sample(items, strata, want, seed=20260913)

    assert first == second


def test_different_seeds_yield_different_samples():
    """Guards against a seed that is accepted but not actually used."""
    items, strata = _population({"high": 200, "low": 200})
    want = {"high": 40, "low": 40}

    a = stratified_sample(items, strata, want, seed=1)
    b = stratified_sample(items, strata, want, seed=2)

    assert a != b


def test_result_does_not_depend_on_per_stratum_dict_ordering():
    """Strata are iterated in sorted order, so insertion order cannot leak in."""
    items, strata = _population({"high": 30, "low": 30, "mid": 30})

    a = stratified_sample(items, strata, {"high": 5, "low": 5, "mid": 5}, seed=7)
    b = stratified_sample(items, strata, {"mid": 5, "high": 5, "low": 5}, seed=7)

    assert a == b


# --- correctness of the draw ------------------------------------------------


def test_draws_the_requested_count_from_each_stratum():
    items, strata = _population({"high": 100, "mid": 100, "low": 100})
    sample = stratified_sample(
        items, strata, {"high": 30, "mid": 20, "low": 10}, seed=42
    )

    assert len(sample) == 60
    counts = {s: sum(1 for x in sample if x.startswith(f"{s}-")) for s in ("high", "mid", "low")}
    assert counts == {"high": 30, "mid": 20, "low": 10}


def test_every_drawn_item_comes_from_the_population():
    items, strata = _population({"high": 40, "low": 40})
    sample = stratified_sample(items, strata, {"high": 15, "low": 15}, seed=3)
    assert set(sample) <= set(items)


def test_sampling_is_without_replacement():
    """A duplicated record would be hand-screened twice and double-counted."""
    items, strata = _population({"only": 100})
    sample = stratified_sample(items, strata, {"only": 100}, seed=5)
    assert len(sample) == len(set(sample)) == 100


def test_a_stratum_omitted_from_per_stratum_is_not_sampled():
    """Over-sampling low-confidence exclusions means deliberately skipping others."""
    items, strata = _population({"high": 50, "low": 50})
    sample = stratified_sample(items, strata, {"low": 10}, seed=11)

    assert len(sample) == 10
    assert all(x.startswith("low-") for x in sample)


def test_requesting_the_whole_stratum_returns_all_of_it():
    items, strata = _population({"tiny": 3, "big": 50})
    sample = stratified_sample(items, strata, {"tiny": 3}, seed=9)
    assert sorted(sample) == ["tiny-0", "tiny-1", "tiny-2"]


def test_empty_request_returns_empty_sample():
    items, strata = _population({"high": 10})
    assert stratified_sample(items, strata, {}, seed=1) == []


# --- failure modes ----------------------------------------------------------


def test_misaligned_items_and_strata_raise():
    with pytest.raises(ValueError, match="align"):
        stratified_sample(["a", "b", "c"], ["x", "y"], {"x": 1}, seed=1)


def test_requesting_more_than_a_stratum_holds_raises():
    """Silently returning fewer would understate the validation sample size."""
    items, strata = _population({"scarce": 5})
    with pytest.raises(ValueError, match="requested 10, only 5 available"):
        stratified_sample(items, strata, {"scarce": 10}, seed=1)


def test_requesting_from_an_absent_stratum_raises():
    items, strata = _population({"present": 10})
    with pytest.raises(ValueError, match="only 0 available"):
        stratified_sample(items, strata, {"absent": 1}, seed=1)


def test_seed_is_mandatory():
    """An unseeded draw could not be reproduced from the published protocol."""
    items, strata = _population({"high": 10})
    with pytest.raises(TypeError):
        stratified_sample(items, strata, {"high": 2})


# --- the real shapes this will be used for ----------------------------------


def test_draws_the_protocol_calibration_sample():
    """300 records drawn at random from a 9,088-record corpus."""
    items = [f"egm-{n:06d}" for n in range(9088)]
    strata = ["corpus"] * 9088

    sample = stratified_sample(items, strata, {"corpus": 300}, seed=20260913)

    assert len(sample) == len(set(sample)) == 300
    assert sample == stratified_sample(items, strata, {"corpus": 300}, seed=20260913)


def test_draws_the_protocol_recall_sample_oversampling_low_confidence():
    """1,000 AI-excluded records, stratified so low-confidence is over-sampled.

    The protocol over-samples low-confidence exclusions because those are where
    a false negative is most likely to be hiding.
    """
    items, strata = _population({"low_conf": 1500, "mid_conf": 3500, "high_conf": 6000})

    sample = stratified_sample(
        items, strata, {"low_conf": 500, "mid_conf": 300, "high_conf": 200}, seed=20260913
    )

    assert len(sample) == len(set(sample)) == 1000
    drawn = {s: sum(1 for x in sample if x.startswith(f"{s}-")) for s in
             ("low_conf", "mid_conf", "high_conf")}
    assert drawn == {"low_conf": 500, "mid_conf": 300, "high_conf": 200}

    # Low-confidence records are 15% of the population but 50% of the sample.
    assert drawn["low_conf"] / len(sample) > 1500 / 11000
