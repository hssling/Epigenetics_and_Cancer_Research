"""The coded dataset must make the prior pipeline's failure unrepresentable.

That pipeline filled `effect = 0.3` in 69% of one column, `population = 200` in
76% of another, and drew reported outcomes from `random.random()`. Every test
here asks the same question of a different field: could that value get in?
"""
import pytest
from pydantic import ValidationError

from pipeline.coding_schema import (
    QUALITY_ITEMS,
    CodedStudy,
    assert_no_placeholder_columns,
    derive_quality_tier,
    detect_placeholder_columns,
)
from pipeline.schema import QuantitativeValue


def _flags(**overrides):
    flags = {item: "yes" for item in QUALITY_ITEMS}
    flags.update(overrides)
    return flags


def _study(study_id="s1", **overrides):
    base = dict(
        study_id=study_id,
        record_id="egm-000001",
        pmid="12345678",
        doi=None,
        approach="nutrition_dietary",
        care_stage="primary_prevention",
        condition_domain="cardiometabolic",
        modality="intervention_effect",
        chain_link="A_B",
        marker_class="methylation_ewas",
        design="rct",
        n=QuantitativeValue(value=120, source_location="Table 1"),
        population="adults with prediabetes",
        country="India",
        follow_up="12 months",
        effect_metric="SMD",
        effect_value=QuantitativeValue(value=0.42, source_location="Table 3"),
        effect_variance=QuantitativeValue(value=0.031, source_location="Table 3"),
        rob_tool="rob2",
        rob_domains={"randomisation": "low", "outcome_measurement": "low"},
        rob_overall="low",
        quality_flags=_flags(),
        coded_by="ai",
        coded_at="2026-09-18T00:00:00Z",
        verified_by_human=False,
    )
    base.update(overrides)
    return CodedStudy(**base)


def _varied(i, **overrides):
    """A study whose numeric fields differ from its neighbours'.

    The dataset-level detector looks for one value dominating a column, so a
    control group has to vary every numeric column -- not just the one under
    test. An earlier version of these fixtures held `n` and `effect_variance`
    at the helper's constant and was flagged, which was the detector working.
    """
    base = dict(
        n=QuantitativeValue(value=40 + (i * 7) % 300, source_location="Table 1"),
        effect_value=QuantitativeValue(value=round(0.05 + i * 0.013, 4),
                                       source_location="Table 3"),
        effect_variance=QuantitativeValue(value=round(0.004 + i * 0.0007, 5),
                                          source_location="Table 3"),
    )
    base.update(overrides)
    return _study(f"s{i}", **base)


# --- the no-default contract -------------------------------------------------


def test_a_nullable_field_must_still_be_stated():
    """Pydantic v2: Optional without a default is required-but-nullable.

    The prior pipeline's placeholders arrived through fields a coder could
    quietly skip. Omitting `country` must be an error, not an implicit null.
    """
    fields = {k: v for k, v in _study().model_dump().items() if k != "country"}
    fields["n"] = QuantitativeValue(value=120, source_location="Table 1")
    fields["effect_value"] = QuantitativeValue(value=0.4, source_location="T3")
    fields["effect_variance"] = QuantitativeValue(value=0.03, source_location="T3")

    with pytest.raises(ValidationError, match="country"):
        CodedStudy(**fields)


def test_an_explicit_none_is_accepted():
    """Stating absence is always allowed; only silence is refused."""
    study = _study(country=None, follow_up=None, population=None)

    assert study.country is None and study.follow_up is None


def test_an_effect_value_cannot_exist_without_a_source_location():
    """The column that held 0.3 in 69% of rows.

    A bare float has nowhere to record where it came from, so the type refuses
    to construct one.
    """
    with pytest.raises(ValidationError):
        QuantitativeValue(value=0.3, source_location="")

    with pytest.raises(ValidationError):
        _study(effect_value=0.3)


def test_a_sample_size_cannot_exist_without_a_source_location():
    """The column that held 200 in 76% of rows."""
    with pytest.raises(ValidationError):
        _study(n=200)


def test_a_whitespace_source_location_is_not_a_source_location():
    with pytest.raises(ValidationError):
        QuantitativeValue(value=0.3, source_location="   ")


def test_unknown_fields_are_refused():
    """extra='forbid'. A typo'd field name would otherwise vanish silently."""
    with pytest.raises(ValidationError):
        _study(effect_sizes=0.3)


# --- fields that only mean something together --------------------------------


def test_a_variance_without_an_effect_is_refused():
    """A row carrying variance alone satisfies a naive poolability check while
    contributing nothing poolable."""
    with pytest.raises(ValidationError, match="no effect_value"):
        _study(effect_value=None, effect_metric=None)


def test_an_effect_without_a_metric_is_refused():
    """0.42 of what? An unlabelled number cannot be pooled or reported."""
    with pytest.raises(ValidationError, match="no effect_metric"):
        _study(effect_metric=None)


def test_a_study_with_no_effect_at_all_is_perfectly_valid():
    """Most of this literature reports no extractable effect. That is a mapped
    fact, not a defect -- and it is exactly what the prior pipeline refused to
    accept, substituting a constant rather than carrying the absence."""
    study = _study(effect_metric=None, effect_value=None, effect_variance=None)

    assert study.is_poolable_candidate is False


# --- the risk-of-bias instrument ---------------------------------------------


def test_an_rct_must_be_assessed_with_rob2():
    with pytest.raises(ValidationError, match="calls for 'rob2'"):
        _study(rob_tool="robins_i")


def test_a_non_randomised_intervention_study_must_use_robins_i():
    with pytest.raises(ValidationError, match="calls for 'robins_i'"):
        _study(design="cohort", rob_tool="rob2")


def test_a_diagnostic_accuracy_study_must_use_quadas2():
    with pytest.raises(ValidationError, match="calls for 'quadas2'"):
        _study(modality="diagnostic_accuracy", design="cross_sectional",
               rob_tool="robins_i")


def test_a_prognostic_study_must_use_probast():
    with pytest.raises(ValidationError, match="calls for 'probast'"):
        _study(modality="prognostic", design="cohort", rob_tool="robins_i")


def test_the_right_tool_passes():
    assert _study(modality="prognostic", design="cohort",
                  rob_tool="probast").rob_tool == "probast"


# --- the epigenetic-methods checklist ----------------------------------------


def test_all_six_quality_items_are_required():
    """Five items scored out of six reads as a lower tier than the same study
    scored fully, with nothing on the row to say so."""
    partial = _flags()
    partial.pop("batch_effects_corrected")

    with pytest.raises(ValidationError, match="missing"):
        _study(quality_flags=partial)


def test_an_invented_quality_item_is_refused():
    with pytest.raises(ValidationError, match="unexpected"):
        _study(quality_flags=_flags(made_up_item="yes"))


def test_a_quality_flag_has_three_states_not_two():
    """"Not reported" is not "no".

    Collapsing them would either flatter studies that stayed silent or condemn
    them for something they may well have done.
    """
    study = _study(quality_flags=_flags(cell_composition_adjusted="unclear"))

    assert study.quality_flags["cell_composition_adjusted"] == "unclear"
    with pytest.raises(ValidationError):
        _study(quality_flags=_flags(cell_composition_adjusted="maybe"))


def test_the_tier_is_derived_and_cannot_be_set():
    """A stored tier stops agreeing with its inputs the moment either changes,
    and this one drives cell colour in the published map."""
    with pytest.raises(ValidationError):
        _study(quality_tier="high")

    study = _study()
    assert study.quality_tier == "high"


def test_the_tier_tracks_the_flags():
    assert derive_quality_tier(_flags()) == "high"
    assert derive_quality_tier(_flags(independent_replication="no")) == "high"
    assert derive_quality_tier(
        _flags(independent_replication="no", batch_effects_corrected="no")
    ) == "moderate"
    assert derive_quality_tier(
        _flags(**{i: "no" for i in QUALITY_ITEMS[:4]})
    ) == "low"


def test_unclear_does_not_count_toward_the_tier():
    """Conservative by design: a study that did not report adjusting for cell
    composition has not shown that it did."""
    silent = _flags(**{i: "unclear" for i in QUALITY_ITEMS[:4]})
    stated_failure = _flags(**{i: "no" for i in QUALITY_ITEMS[:4]})

    assert derive_quality_tier(silent) == derive_quality_tier(stated_failure) == "low"


def test_silence_is_reported_separately_from_stated_failure():
    """The tier treats them alike; the row must not, or a reader cannot tell a
    badly done study from an under-reported one."""
    silent = _study(quality_flags=_flags(**{i: "unclear" for i in QUALITY_ITEMS[:4]}))
    stated = _study(quality_flags=_flags(**{i: "no" for i in QUALITY_ITEMS[:4]}))

    assert silent.quality_tier == stated.quality_tier
    assert silent.quality_items_unclear == 4
    assert stated.quality_items_unclear == 0


# --- chain completeness is mapped, never filtered ----------------------------


def test_every_chain_link_is_representable():
    """Protocol Section 3.2: eligibility requires link B alone.

    If the model could not hold A->B, the mechanistic literature would vanish
    from the map -- and the translational gap, which is the map's central
    finding, is only visible against it.
    """
    for link in ("A_B", "B_C", "A_B_C"):
        assert _study(chain_link=link).chain_link == link


# --- the dataset-level check a row cannot make -------------------------------


def test_a_constant_filled_effect_column_is_detected():
    """The prior dataset, reconstructed: 0.3 in 69% of rows.

    Every individual row is well-formed. No per-row rule can see this.
    """
    studies = [
        _varied(i, effect_value=QuantitativeValue(
            value=0.3 if i < 69 else round(i / 100, 2), source_location="Table 3"))
        for i in range(100)
    ]

    flagged = detect_placeholder_columns(studies)

    value, share = flagged["effect_value"]
    assert value == 0.3 and share == pytest.approx(0.69)
    # Only that column. Flagging the whole table would make the report useless
    # for finding which column to explain.
    assert set(flagged) == {"effect_value"}


def test_a_constant_filled_sample_size_column_is_detected():
    """200 in 76% of rows."""
    studies = [
        _varied(i, n=QuantitativeValue(
            value=200 if i < 76 else 50 + i, source_location="Table 1"))
        for i in range(100)
    ]

    flagged = detect_placeholder_columns(studies)

    assert flagged["n"] == (200, pytest.approx(0.76))
    assert set(flagged) == {"n"}


def test_genuine_data_with_ordinary_repetition_is_not_flagged():
    """Real sample sizes repeat; they do not fill a fifth of a corpus.

    `n` here takes five recurring values, so the modal share is 20% -- right at
    the threshold and deliberately so. A check that fires on honest data is a
    check that gets turned off.
    """
    studies = [
        _varied(i, n=QuantitativeValue(value=[50, 60, 100, 120, 240][i % 5],
                                       source_location="Table 1"))
        for i in range(100)
    ]

    assert detect_placeholder_columns(studies) == {}


def test_a_column_of_explicit_nulls_is_not_a_placeholder_column():
    """Absence is the correct answer for most of this literature. Treating a
    column of honest nulls as suspicious would push a coder toward filling it."""
    studies = [
        _varied(i, effect_metric=None, effect_value=None, effect_variance=None)
        for i in range(100)
    ]

    assert detect_placeholder_columns(studies) == {}


def test_the_assertion_names_the_column_and_the_value():
    studies = [
        _varied(i, effect_value=QuantitativeValue(
            value=0.3, source_location="Table 3"))
        for i in range(50)
    ]

    with pytest.raises(ValueError, match=r"effect_value=0.3 in 100% of rows"):
        assert_no_placeholder_columns(studies)


def test_a_clean_dataset_passes_the_assertion():
    studies = [_varied(i) for i in range(60)]

    assert_no_placeholder_columns(studies)


def test_an_empty_dataset_is_not_reported_as_clean_by_accident():
    """No rows means nothing was checked. That must not read as a pass with
    findings -- but it also must not raise, or an empty coding stage could not
    be run at all."""
    assert detect_placeholder_columns([]) == {}


# --- no display format is baked into the row ---------------------------------


def test_the_same_row_supports_every_registered_map_view():
    """Protocol Section 6.3: dimensions, not displays.

    The prior pipeline fixed its output shape first and bent data to fit. Each
    map variant here is a grouping over independent fields.
    """
    studies = [
        _study("a", approach="nutrition_dietary", care_stage="primary_prevention",
               condition_domain="cardiometabolic", chain_link="A_B"),
        _study("b", approach="nutrition_dietary", care_stage="primary_prevention",
               condition_domain="oncological", chain_link="A_B_C"),
        _study("c", approach="epigenetic_clock", care_stage="risk_stratification",
               condition_domain="ageing_mortality", chain_link="B_C",
               modality="prognostic", design="cohort", rob_tool="probast"),
    ]

    def pivot(*fields):
        counts: dict[tuple, int] = {}
        for s in studies:
            key = tuple(getattr(s, f) for f in fields)
            counts[key] = counts.get(key, 0) + 1
        return counts

    # Three published views, three groupings, one table, no re-coding.
    assert pivot("approach", "care_stage") == {
        ("nutrition_dietary", "primary_prevention"): 2,
        ("epigenetic_clock", "risk_stratification"): 1,
    }
    assert pivot("approach", "condition_domain") == {
        ("nutrition_dietary", "cardiometabolic"): 1,
        ("nutrition_dietary", "oncological"): 1,
        ("epigenetic_clock", "ageing_mortality"): 1,
    }
    assert pivot("chain_link") == {("A_B",): 1, ("A_B_C",): 1, ("B_C",): 1}
