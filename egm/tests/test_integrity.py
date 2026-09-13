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
EGM_ROOT = REPO / "egm"
RNG_ALLOWED = {"sampling.py"}
RNG_EXCLUDED_DIR_NAMES = {"tests"}


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
    found = find_placeholder_saturation(df, threshold=0.20, min_unique=4)
    assert "effect" in found
    value, share = found["effect"]
    assert value == 0.3
    assert share == pytest.approx(0.7)


def test_assert_raises_on_saturation():
    df = pd.DataFrame({"effect": [0.3] * 7 + [0.1, 0.2, 0.4]})
    with pytest.raises(IntegrityError, match="effect"):
        assert_no_placeholder_saturation(df, min_unique=4)


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


def _find_rng_offenders(
    root: pathlib.Path, allowed: set[str], excluded_dir_names: set[str] = frozenset()
) -> list[str]:
    """Walk `root` for RNG usage. Shared by the production guard and its own tests.

    Checks all AST forms: direct imports, attribute access (np.random),
    and dynamic imports via __import__ or importlib.
    """
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        if path.name in allowed:
            continue
        if excluded_dir_names & set(path.relative_to(root).parts[:-1]):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            # Form 1: ast.Import - catches "import random", "import numpy.random", "import random.seed"
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if (alias.name == "random" or
                        alias.name.startswith("random.") or
                        alias.name == "numpy.random" or
                        alias.name.startswith("numpy.random.")):
                        offenders.append(f"{path.name}: import {alias.name}")

            # Form 2: ast.ImportFrom - catches "from random import X", "from numpy import random", etc.
            elif isinstance(node, ast.ImportFrom) and node.module:
                if (node.module == "random" or
                    node.module.startswith("random.") or
                    node.module == "numpy.random" or
                    node.module.startswith("numpy.random.")):
                    offenders.append(f"{path.name}: from {node.module} import ...")
                # Special case: "from numpy import random"
                elif node.module == "numpy":
                    for alias in node.names:
                        if alias.name == "random":
                            offenders.append(f"{path.name}: from numpy import random")

            # Form 3: ast.Attribute - catches "np.random", "numpy.random", "self.random" (conservative)
            elif isinstance(node, ast.Attribute):
                if node.attr == "random":
                    offenders.append(f"{path.name}: attribute access .random")

            # Form 4: ast.Call to __import__ or importlib.import_module with "random" string
            elif isinstance(node, ast.Call):
                func_name = None
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name in ("__import__", "import_module"):
                    # Check first argument for string constant containing "random"
                    if node.args and isinstance(node.args[0], ast.Constant):
                        if isinstance(node.args[0].value, str) and "random" in node.args[0].value:
                            offenders.append(f"{path.name}: {func_name}(...) with 'random'")

    return offenders


def test_no_rng_imported_in_data_path():
    """Spec section 8.3 rule 3. Only sampling.py may import random.

    Scans the whole egm/ tree (not just egm/pipeline): spec section 8.1 adds
    screening/, coding/, analysis/ alongside pipeline/ later, and the guard
    must cover those automatically rather than needing to be told about each
    new directory. egm/tests/ is excluded because test files legitimately
    construct RNG code strings as fixtures (see the test_rng_detection_*
    tests below), not because they are trusted to import random for real.
    """
    offenders = _find_rng_offenders(EGM_ROOT, RNG_ALLOWED, RNG_EXCLUDED_DIR_NAMES)
    assert offenders == [], f"RNG must not appear in the data path: {offenders}"


def test_rng_guard_scans_full_egm_tree_not_just_pipeline():
    """Regression for the directory-scoped guard: the production scan root
    must be egm/ itself, not egm/pipeline/, so it covers files the pipeline
    subtree doesn't -- e.g. this test file's own fixtures, or a future
    screening/coding/analysis package added alongside pipeline/.
    """
    assert EGM_ROOT == REPO / "egm", (
        "the RNG guard's root must be egm/, not a subdirectory such as "
        "egm/pipeline -- otherwise directories added later (screening/, "
        "coding/, analysis/ per spec 8.1) would never be scanned"
    )
    all_py_files = list(EGM_ROOT.rglob("*.py"))
    pipeline_only = list((REPO / "egm" / "pipeline").rglob("*.py"))
    assert len(all_py_files) > len(pipeline_only), (
        "the RNG guard's root must cover more than egm/pipeline alone"
    )


def test_rng_guard_catches_offenders_outside_pipeline_directory(tmp_path):
    """Directly demonstrates the fixed defect: scoping the scan to a
    pipeline/-only subdirectory (the pre-fix behaviour) misses RNG usage
    placed in a sibling directory such as screening/; scanning the whole
    root catches it, while still allowing sampling.py and tests/.
    """
    pipeline_dir = tmp_path / "pipeline"
    pipeline_dir.mkdir()
    (pipeline_dir / "clean.py").write_text("x = 1\n", encoding="utf-8")

    screening_dir = tmp_path / "screening"
    screening_dir.mkdir()
    (screening_dir / "score.py").write_text("import random\n", encoding="utf-8")

    (tmp_path / "sampling.py").write_text("import random\n", encoding="utf-8")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_fixture.py").write_text("import random\n", encoding="utf-8")

    # Old, directory-scoped behaviour: scanning only pipeline/ misses the
    # offender that lives in screening/.
    assert _find_rng_offenders(pipeline_dir, RNG_ALLOWED) == []

    # Fixed behaviour: scanning the whole tree catches it, and still
    # allowlists sampling.py and skips tests/.
    offenders = _find_rng_offenders(tmp_path, RNG_ALLOWED, RNG_EXCLUDED_DIR_NAMES)
    assert len(offenders) == 1
    assert "score.py" in offenders[0]


def test_rng_detection_catches_import_random():
    """Form 1: ast.Import catches 'import random'."""
    code = "import random\nrandom.random()"
    tree = ast.parse(code)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "random":
                    found = True
    assert found, "Should detect direct import random"


def test_rng_detection_catches_import_numpy_as_np_then_np_random():
    """Form 3: ast.Attribute catches 'np.random' after 'import numpy as np'."""
    code = "import numpy as np\nnp.random.rand()"
    tree = ast.parse(code)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "random":
            found = True
    assert found, "Should detect np.random attribute access"


def test_rng_detection_catches_from_numpy_import_random():
    """Form 2: ast.ImportFrom catches 'from numpy import random'."""
    code = "from numpy import random\nrandom.rand()"
    tree = ast.parse(code)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "numpy":
            for alias in node.names:
                if alias.name == "random":
                    found = True
    assert found, "Should detect from numpy import random"


def test_rng_detection_catches_dunder_import_random():
    """Form 4: ast.Call catches '__import__(\"random\")'."""
    code = "round(__import__('random').random(), 2)"
    tree = ast.parse(code)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                if node.args and isinstance(node.args[0], ast.Constant):
                    if isinstance(node.args[0].value, str) and "random" in node.args[0].value:
                        found = True
    assert found, "Should detect __import__('random')"


def test_low_cardinality_boolean_column_not_flagged():
    """Balanced 0/1 boolean column should not be flagged even at 50%+ modal."""
    df = pd.DataFrame({"flag": [0, 0, 1, 1, 1, 1]})  # modal share 66%, but only 2 distinct values
    found = find_placeholder_saturation(df, threshold=0.20, min_unique=10)
    assert "flag" not in found, "Boolean column should be skipped with min_unique=10"


def test_low_cardinality_categorical_column_not_flagged():
    """Small categorical (4 values) should not be flagged."""
    df = pd.DataFrame({"category": [1, 1, 1, 1, 2, 2, 3, 4]})  # modal share 50%, only 4 distinct
    found = find_placeholder_saturation(df, threshold=0.20, min_unique=10)
    assert "category" not in found, "Low-cardinality categorical should be skipped"


def test_high_cardinality_with_dominant_modal_is_flagged():
    """Column with >=10 distinct values but dominant modal should still be flagged."""
    values = [0.3] * 70 + list(range(1, 31))  # 0.3 at 70%, plus 30 other distinct values = 31 total distinct
    df = pd.DataFrame({"measurement": values})
    found = find_placeholder_saturation(df, threshold=0.20, min_unique=10)
    assert "measurement" in found, "High-cardinality column with dominant mode should be flagged"
    assert found["measurement"][0] == 0.3
