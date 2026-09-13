"""The frozen prompt and its hash."""
import hashlib

import pytest

from pipeline.prompt_loader import load_prompt
from pipeline.screen_schema import CRITERIA


def test_loads_text_and_hash():
    text, digest = load_prompt("v1")
    assert text.strip()
    assert len(digest) == 64
    assert digest == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_hash_is_stable_across_loads():
    assert load_prompt("v1")[1] == load_prompt("v1")[1]


def test_prompt_names_every_registered_criterion():
    """A criterion the screener is never told about cannot be applied."""
    text, _ = load_prompt("v1")
    for criterion in CRITERIA:
        assert criterion in text, f"prompt does not mention {criterion}"


def test_prompt_states_the_uncertainty_rule():
    """The registration commits to resolving uncertainty toward inclusion."""
    text, _ = load_prompt("v1")
    assert "unclear" in text.lower()


def test_unknown_version_raises():
    with pytest.raises(FileNotFoundError, match="v99"):
        load_prompt("v99")
