"""The coded dataset: one row per included study (protocol Section 6).

This module is the structural correction the project exists to make. The
superseded pipeline in this repository committed to producing a network
meta-analysis, then substituted constants wherever the source data could not
fill that shape: `effect = 0.3` occupied 69% of one column, `population = 200`
occupied 76% of another, and `random.random()` supplied reported outcomes.

The corrective is not vigilance. It is that the shapes those values would have
to occupy do not exist here:

* A quantitative value cannot be constructed without the page, table or figure
  it was read from (`QuantitativeValue`, enforced by the type).
* Every optional field is `Optional[X]` with NO default, which Pydantic treats
  as required-but-nullable. A coder must say "absent"; they cannot omit.
* The epigenetic-quality tier is derived from the six flags on every access,
  so it cannot be set to something the flags do not support.
* The risk-of-bias tool is checked against the coded modality and design, so a
  study cannot carry an assessment from the wrong instrument.
* `detect_placeholder_columns` looks for the prior failure's exact signature
  across a finished dataset, because a per-row rule cannot see a column.

Dimensions are stored independently of any display format. Protocol Section
6.3: every map variant -- approach x care stage, approach x condition domain,
the chain-completeness cross-tabulation -- is a grouping over this one table.
No output shape is baked in, which is the specific thing that went wrong before.
"""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pipeline.schema import QuantitativeValue

# --- the map's dimensions, from the registered design ------------------------
#
# Enumerated rather than free text. A free-text `approach` column cannot be
# pivoted into a map without a cleaning step, and a cleaning step is where
# categories quietly get invented. The row set is provisional by protocol
# (Section 9 contingencies); changing it means editing this tuple and
# recording an amendment, which is the point.

Approach = Literal[
    # Interventions acting through the epigenome
    "nutrition_dietary",
    "physical_activity",
    "tobacco_alcohol",
    "environmental_exposure",
    "psychosocial_stress_sleep",
    "perinatal_early_life",
    "pharmacological_epigenetic",
    # Epigenetic measurement used to inform a decision
    "methylation_screening_test",
    "epigenetic_clock",
    "molecular_classifier",
]

CareStage = Literal[
    "health_promotion",
    "primary_prevention",
    "screening_early_detection",
    "risk_stratification",
    "treatment_disease_modification",
    "prognosis_monitoring",
    "recovery_survivorship",
]

ConditionDomain = Literal[
    "cardiometabolic",
    "oncological",
    "neurological_mental_health",
    "respiratory",
    "perinatal",
    "immune_infectious",
    "ageing_mortality",
    "other",
]

Modality = Literal["intervention_effect", "diagnostic_accuracy", "prognostic"]

# Protocol Section 3.2. Coded as a mapped variable, never as an exclusion:
# eligibility requires link B alone. Making completeness a filter would delete
# the mechanistic and prognostic literature that makes the translational gap
# visible, and reporting that gap is what a gap map is for.
ChainLink = Literal["A_B", "B_C", "A_B_C"]

MarkerClass = Literal[
    "methylation_global",
    "methylation_candidate",
    "methylation_ewas",
    "histone",
    "chromatin",
    "clock",
]

Design = Literal[
    "rct",
    "non_randomised_trial",
    "cohort",
    "case_control",
    "cross_sectional",
]

RobTool = Literal["rob2", "robins_i", "quadas2", "probast"]

RobJudgement = Literal["low", "some_concerns", "high", "unclear"]

# Three states, not a boolean. "The paper does not say whether cell composition
# was adjusted for" is a different fact from "it was not adjusted for", and
# collapsing them would either flatter studies that stayed silent or condemn
# them for something they may have done. The field's classic confounder is an
# apparent methylation difference that is really a shift in leukocyte
# proportions, so this distinction is the one the checklist exists to make.
QualityFlag = Literal["yes", "no", "unclear"]

QualityTier = Literal["high", "moderate", "low"]

# The six epigenetic-methods items, protocol Section 7, in registered order.
QUALITY_ITEMS: tuple[str, ...] = (
    "cell_composition_adjusted",
    "batch_effects_corrected",
    "multiple_testing_corrected",
    "independent_replication",
    "tissue_relevance_justified",
    "platform_normalisation_reported",
)

# Which instrument each modality and design calls for (protocol Section 7).
# Keyed by (modality, is_randomised) because the intervention-effect row is the
# only one where design picks the tool.
ROB_TOOL_FOR: dict[tuple[str, bool], str] = {
    ("intervention_effect", True): "rob2",
    ("intervention_effect", False): "robins_i",
    ("diagnostic_accuracy", True): "quadas2",
    ("diagnostic_accuracy", False): "quadas2",
    ("prognostic", True): "probast",
    ("prognostic", False): "probast",
}


def derive_quality_tier(flags: dict[str, str]) -> QualityTier:
    """Composite tier from the six flags. Derived, never stored.

    A stored tier is a number that stops agreeing with its inputs the moment
    either changes, and this one drives cell colour in the published map -- the
    single most-read output. So it is recomputed on every access instead.

    `unclear` does not count toward the tier. A study that does not report
    whether it adjusted for cell composition has not shown that it did, and the
    map's question is whether the evidence is demonstrably sound, not whether it
    might be. This is deliberately the conservative reading and it is a
    judgement a reader may disagree with: the six flags are retained
    individually (protocol Section 7, "flags support transparency and reader
    re-weighting") precisely so the tier can be recomputed under a different
    rule without re-coding a single study.
    """
    met = sum(1 for item in QUALITY_ITEMS if flags[item] == "yes")
    if met >= 5:
        return "high"
    if met >= 3:
        return "moderate"
    return "low"


class CodedStudy(BaseModel):
    """One included study, coded across every mapped dimension.

    Every `Optional` field below is deliberately without a default. In Pydantic
    v2 that makes it required-but-nullable: the coder must write `None`. The
    difference matters because the prior pipeline's placeholders arrived
    through fields that could be quietly skipped.
    """

    model_config = ConfigDict(extra="forbid")

    # --- identity ---
    study_id: str = Field(min_length=1)
    record_id: str = Field(min_length=1)
    pmid: Optional[str]
    doi: Optional[str]

    # --- map dimensions ---
    approach: Approach
    care_stage: CareStage
    condition_domain: ConditionDomain
    modality: Modality
    chain_link: ChainLink
    marker_class: MarkerClass
    design: Design

    # --- study characteristics ---
    # `n` carries a source location like any other extracted number: a sample
    # size read off an abstract and one counted from a flow diagram are not
    # equally reliable, and the prior pipeline's `population = 200` entered
    # exactly here.
    n: Optional[QuantitativeValue]
    population: Optional[str]
    country: Optional[str]
    follow_up: Optional[str]

    # --- effect ---
    # Nullable, no defaults. This is the field that held 0.3 in 69% of rows.
    effect_metric: Optional[str]
    effect_value: Optional[QuantitativeValue]
    effect_variance: Optional[QuantitativeValue]

    # --- risk of bias ---
    rob_tool: RobTool
    rob_domains: dict[str, RobJudgement]
    rob_overall: RobJudgement

    # --- epigenetic methods quality ---
    quality_flags: dict[str, QualityFlag]

    # --- provenance ---
    coded_by: Literal["ai", "human"]
    coded_at: str
    verified_by_human: bool

    @model_validator(mode="after")
    def _quality_flags_are_complete(self) -> "CodedStudy":
        """All six items, no more and no fewer.

        A partial checklist would silently change what the tier means: five
        items scored out of six reads as a lower tier than the same study
        scored fully, with nothing on the row to say so.
        """
        missing = [item for item in QUALITY_ITEMS if item not in self.quality_flags]
        unknown = [item for item in self.quality_flags if item not in QUALITY_ITEMS]
        if missing or unknown:
            raise ValueError(
                f"quality_flags must hold exactly the six registered items; "
                f"missing {missing}, unexpected {unknown}"
            )
        return self

    @model_validator(mode="after")
    def _rob_tool_matches_the_design(self) -> "CodedStudy":
        """Protocol Section 7 selects the instrument from modality and design.

        Assessing an RCT with ROBINS-I, or a diagnostic-accuracy study with
        RoB 2, produces domain judgements that are not comparable with the rest
        of the column -- and risk of bias is a mapped dimension here, so an
        incomparable judgement lands in the map as if it belonged.
        """
        expected = ROB_TOOL_FOR[(self.modality, self.design == "rct")]
        if self.rob_tool != expected:
            raise ValueError(
                f"modality {self.modality!r} with design {self.design!r} calls "
                f"for {expected!r}, not {self.rob_tool!r} (protocol Section 7)"
            )
        return self

    @model_validator(mode="after")
    def _variance_needs_a_value(self) -> "CodedStudy":
        """A variance without its effect is not a usable estimate.

        The poolability gate requires "an extractable common effect metric with
        variance". A row carrying variance alone would satisfy a naive check for
        the variance being present while contributing nothing poolable.
        """
        if self.effect_variance is not None and self.effect_value is None:
            raise ValueError(
                f"{self.study_id}: effect_variance recorded with no effect_value"
            )
        if self.effect_value is not None and self.effect_metric is None:
            raise ValueError(
                f"{self.study_id}: effect_value recorded with no effect_metric; "
                "a number whose metric is unknown cannot be pooled or reported"
            )
        return self

    @property
    def quality_tier(self) -> QualityTier:
        """Derived on access. See `derive_quality_tier`."""
        return derive_quality_tier(self.quality_flags)

    @property
    def quality_items_met(self) -> int:
        return sum(1 for i in QUALITY_ITEMS if self.quality_flags[i] == "yes")

    @property
    def quality_items_unclear(self) -> int:
        """How much of the tier rests on silence rather than on a stated failure.

        Reported alongside the tier so a reader can tell a study that did the
        work badly from one that did not say.
        """
        return sum(1 for i in QUALITY_ITEMS if self.quality_flags[i] == "unclear")

    @property
    def is_poolable_candidate(self) -> bool:
        """Whether this row could contribute to a pooled estimate at all.

        Per-study half of the protocol Section 8 gate. The cell-level half --
        at least ten studies, shared modality, comparable comparator, not
        uniformly high risk of bias -- cannot be decided from one row.
        """
        return (
            self.effect_metric is not None
            and self.effect_value is not None
            and self.effect_variance is not None
        )


# --- dataset-level checks ----------------------------------------------------
#
# A row cannot see its own column. The prior pipeline's failure was invisible
# per row -- every row looked plausible -- and obvious in aggregate, where one
# value held 69% of a column.

PLACEHOLDER_MODAL_SHARE = 0.20


def detect_placeholder_columns(
    studies: list[CodedStudy], threshold: float = PLACEHOLDER_MODAL_SHARE
) -> dict[str, tuple[float, float]]:
    """Find numeric columns dominated by one repeated value.

    Returns {column: (modal_value, share)} for every numeric column whose most
    common value exceeds `threshold` of the non-null entries.

    This is the prior dataset's signature, measured: `0.3` occupied 69% of the
    effect column and `200` occupied 76% of the sample-size column. Neither
    would have tripped any per-row check, because each individual row was
    well-formed. The threshold sits far below those figures and above what
    genuine data plausibly produces -- real effect sizes and sample sizes
    repeat, but not in a fifth of a corpus.

    A hit is not proof of fabrication. It is a column that must be explained
    before anything is published from it.
    """
    columns = {
        "n": [s.n.value for s in studies if s.n is not None],
        "effect_value": [
            s.effect_value.value for s in studies if s.effect_value is not None
        ],
        "effect_variance": [
            s.effect_variance.value for s in studies if s.effect_variance is not None
        ],
    }

    flagged: dict[str, tuple[float, float]] = {}
    for name, values in columns.items():
        if not values:
            continue
        counts: dict[float, int] = {}
        for value in values:
            counts[value] = counts.get(value, 0) + 1
        modal_value, modal_count = max(counts.items(), key=lambda kv: kv[1])
        share = modal_count / len(values)
        if share > threshold:
            flagged[name] = (modal_value, share)
    return flagged


def assert_no_placeholder_columns(studies: list[CodedStudy]) -> None:
    """Raise if any numeric column looks like the prior dataset. Never caught."""
    flagged = detect_placeholder_columns(studies)
    if flagged:
        detail = "; ".join(
            f"{column}={value!r} in {share:.0%} of rows"
            for column, (value, share) in sorted(flagged.items())
        )
        raise ValueError(
            f"numeric column(s) dominated by a single repeated value: {detail}. "
            "This is the signature of the superseded pipeline, where 0.3 filled "
            "69% of the effect column and 200 filled 76% of sample size. Explain "
            "each column against the source papers before anything is published "
            "from this dataset."
        )
