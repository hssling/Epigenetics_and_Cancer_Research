import pytest

from pipeline.integrity import IntegrityError
from pipeline.prisma import PrismaFlow, PrismaStage


def test_included_is_identified_minus_excluded():
    flow = PrismaFlow(stages=[
        PrismaStage(name="identification", identified=14000, excluded=2000,
                    reason="duplicates removed"),
    ])
    assert flow.included_after("identification") == 12000


def test_validate_accepts_a_real_flow():
    flow = PrismaFlow(stages=[
        PrismaStage(name="identification", identified=14000, excluded=2000, reason="duplicates"),
        PrismaStage(name="screening", identified=12000, excluded=10500, reason="ineligible"),
        PrismaStage(name="full_text", identified=1500, excluded=400, reason="no measured marker"),
    ])
    flow.validate()


def test_zero_exclusions_across_the_whole_flow_is_rejected():
    """The exact shape of the superseded pipeline's PRISMA file."""
    flow = PrismaFlow(stages=[
        PrismaStage(name="identification", identified=616, excluded=0, reason="none"),
        PrismaStage(name="screening", identified=616, excluded=0, reason="none"),
        PrismaStage(name="full_text", identified=616, excluded=0, reason="none"),
    ])
    with pytest.raises(IntegrityError, match="zero exclusions"):
        flow.validate()


def test_stage_carry_forward_mismatch_is_rejected():
    flow = PrismaFlow(stages=[
        PrismaStage(name="identification", identified=14000, excluded=2000, reason="duplicates"),
        PrismaStage(name="screening", identified=9999, excluded=500, reason="ineligible"),
    ])
    with pytest.raises(IntegrityError, match="carry-forward"):
        flow.validate()


def test_excluding_more_than_identified_is_rejected():
    with pytest.raises(ValueError):
        PrismaStage(name="screening", identified=10, excluded=11, reason="impossible")


def test_exclusion_requires_a_reason():
    with pytest.raises(ValueError, match="reason"):
        PrismaStage(name="screening", identified=10, excluded=5, reason="")


def test_to_csv_round_trips(tmp_path):
    flow = PrismaFlow(stages=[
        PrismaStage(name="identification", identified=100, excluded=10, reason="duplicates"),
        PrismaStage(name="screening", identified=90, excluded=40, reason="ineligible"),
    ])
    out = tmp_path / "prisma.csv"
    flow.to_csv(out)
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0] == "stage,identified,excluded,included,reason"
    assert lines[1].startswith("identification,100,10,90,")
