"""The no-default contract (spec section 8.3 rules 1 and 2)."""
import pytest
from pydantic import ValidationError

from pipeline.schema import QuantitativeValue, SearchRecord


def _valid_record_kwargs():
    return dict(
        source_db="pubmed", source_id="12345678", doi="10.1000/x", pmid="12345678",
        title="A study", abstract="Text.", year=2020, journal="J Epi",
        authors=["Smith J"], retrieved_at="2026-09-13T10:00:00Z", query_hash="ab12cd34",
    )


def test_quantitative_value_requires_source_location():
    with pytest.raises(ValidationError):
        QuantitativeValue(value=0.42)


def test_quantitative_value_rejects_blank_source_location():
    with pytest.raises(ValidationError):
        QuantitativeValue(value=0.42, source_location="   ")


def test_quantitative_value_is_frozen():
    qv = QuantitativeValue(value=0.42, source_location="Table 2, row 3")
    with pytest.raises(ValidationError):
        qv.value = 0.99


def test_omitting_an_optional_field_raises_rather_than_defaulting():
    """The crux: absence must be stated, never assumed."""
    kwargs = _valid_record_kwargs()
    del kwargs["doi"]
    with pytest.raises(ValidationError) as exc:
        SearchRecord(**kwargs)
    assert "doi" in str(exc.value)


def test_explicit_none_is_accepted():
    kwargs = _valid_record_kwargs()
    kwargs["doi"] = None
    assert SearchRecord(**kwargs).doi is None


def test_unknown_field_is_rejected():
    kwargs = _valid_record_kwargs()
    kwargs["epigenetic_effect_size"] = 0.3
    with pytest.raises(ValidationError):
        SearchRecord(**kwargs)


def test_unknown_source_db_is_rejected():
    kwargs = _valid_record_kwargs()
    kwargs["source_db"] = "google_scholar"
    with pytest.raises(ValidationError):
        SearchRecord(**kwargs)


def test_source_db_literal_matches_config():
    """SourceDB is spelled out literally; this keeps it in sync with config."""
    from typing import get_args

    from pipeline.config import SOURCE_DBS
    from pipeline.schema import SourceDB

    assert get_args(SourceDB) == tuple(SOURCE_DBS)
