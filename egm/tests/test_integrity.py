"""Integrity rules (spec sections 8.3, 8.4)."""
import ast
import pathlib

import pandas as pd
import pytest

from pipeline.integrity import (
    IntegrityError,
    assert_no_placeholder_saturation,
    find_placeholder_saturation,
    modal_share,
)

REPO = pathlib.Path(__file__).resolve().parents[2]
PIPELINE = REPO / "egm" / "pipeline"
RNG_ALLOWED = {"sampling.py"}


def test_modal_share_of_uniform_column_is_one():
    assert modal_share([0.3] * 10) == pytest.approx(1.0)


def test_modal_share_ignores_none():
    assert modal_share([1.0, 2.0, None, None]) == pytest.approx(0.5)


def test_modal_share_of_empty_is_zero():
    assert modal_share([]) == 0.0
    assert modal_share([None, None]) == 0.0


def test_clean_column_passes():
    df = pd.DataFrame({"effect": [0.1, 0.2, 0.3, 0.4, 0.5]})
    assert find_placeholder_saturation(df) == {}


def test_saturated_column_is_flagged_with_value_and_share():
    df = pd.DataFrame({"effect": [0.3] * 7 + [0.1, 0.2, 0.4]})
    found = find_placeholder_saturation(df, threshold=0.20)
    assert "effect" in found
    value, share = found["effect"]
    assert value == 0.3
    assert share == pytest.approx(0.7)


def test_assert_raises_on_saturation():
    df = pd.DataFrame({"effect": [0.3] * 7 + [0.1, 0.2, 0.4]})
    with pytest.raises(IntegrityError, match="effect"):
        assert_no_placeholder_saturation(df)


def test_detector_catches_the_actual_fabricated_dataset():
    """Regression fixture: the real failure this repository already had.

    data/epigenetic_master_dataset.csv has epigenetic_effect_size == 0.3 in
    69% of rows and population_size == 200 in 76%. If the detector cannot
    catch this, it is useless.
    """
    fabricated = REPO / "data" / "epigenetic_master_dataset.csv"
    if not fabricated.exists():
        pytest.skip("superseded dataset not present")

    df = pd.read_csv(fabricated)[["epigenetic_effect_size", "population_size"]]
    found = find_placeholder_saturation(df, threshold=0.20)

    assert "epigenetic_effect_size" in found
    assert found["epigenetic_effect_size"][0] == pytest.approx(0.3)
    assert found["epigenetic_effect_size"][1] > 0.65

    assert "population_size" in found
    assert found["population_size"][0] == 200
    assert found["population_size"][1] > 0.70


def test_no_rng_imported_in_data_path():
    """Spec section 8.3 rule 3. Only sampling.py may import random."""
    offenders: list[str] = []
    for path in PIPELINE.rglob("*.py"):
        if path.name in RNG_ALLOWED:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root == "random" or alias.name.startswith("numpy.random"):
                        offenders.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] == "random" or "numpy.random" in node.module:
                    offenders.append(f"{path.name}: from {node.module} import ...")
    assert offenders == [], f"RNG must not appear in the data path: {offenders}"
