"""The AI screener. Structured output, provenance, resumability, fail-loud."""
import json

import pytest

from pipeline import ai_screener as ais
from pipeline.screen_schema import ScreeningDecision, read_decisions


def _record(pmid="111", title="Diet and DNA methylation", abstract="We measured..."):
    return {
        "record_id": f"egm-{pmid}", "pmid": pmid, "title": title,
        "abstract": abstract, "year": 2020, "journal": "J Epi",
    }


class _FakeParsed:
    def __init__(self, parsed, usage=None):
        self.parsed_output = parsed
        self.usage = usage or _FakeUsage()


class _FakeUsage:
    input_tokens = 500
    output_tokens = 120
    cache_read_input_tokens = 1300
    cache_creation_input_tokens = 0


def _client(mocker, parsed):
    client = mocker.MagicMock()
    client.messages.parse.return_value = _FakeParsed(parsed)
    return client


def test_include_decision_carries_full_provenance(mocker):
    parsed = ais.ScreenerOutput(
        decision="include", criterion=None, confidence=0.92,
        reason="Measures methylation after a dietary intervention.",
    )
    client = _client(mocker, parsed)

    decision, usage = ais.screen_record(
        client, _record(), "claude-opus-5", "PROMPT TEXT", "b" * 64, "calibration"
    )

    assert isinstance(decision, ScreeningDecision)
    assert decision.decision == "include"
    assert decision.model_id == "claude-opus-5"
    assert decision.prompt_sha256 == "b" * 64
    assert decision.confidence == 0.92
    assert decision.screener == "ai"
    assert decision.stage == "calibration"
    assert usage.output_tokens == 120


def test_exclude_decision_carries_its_criterion(mocker):
    parsed = ais.ScreenerOutput(
        decision="exclude", criterion="not_primary", confidence=0.97,
        reason="Narrative review.",
    )
    decision, _ = ais.screen_record(
        _client(mocker, parsed), _record(), "claude-opus-5", "P", "c" * 64, "screening"
    )
    assert decision.criterion == "not_primary"


def test_exclude_without_a_criterion_from_the_model_raises(mocker):
    """The model returned something the schema forbids; that must not be stored."""
    parsed = ais.ScreenerOutput(
        decision="exclude", criterion=None, confidence=0.8, reason="No reason given.",
    )
    with pytest.raises(ais.ScreenerError, match="criterion"):
        ais.screen_record(
            _client(mocker, parsed), _record(), "claude-opus-5", "P", "d" * 64, "screening"
        )


def test_api_failure_raises_and_records_nothing(mocker, tmp_path):
    """A failure must never become an exclusion in the decision log."""
    client = mocker.MagicMock()
    client.messages.parse.side_effect = RuntimeError("connection reset")

    out = tmp_path / "decisions.jsonl"
    with pytest.raises(ais.ScreenerError, match="111"):
        ais.screen_sample(
            client, [_record("111")], "claude-opus-5", out,
            tmp_path / "usage.jsonl", "screening",
        )
    assert read_decisions(out) == []


def test_run_is_resumable_and_skips_completed_records(mocker, tmp_path):
    parsed = ais.ScreenerOutput(
        decision="include", criterion=None, confidence=0.9, reason="Eligible.",
    )
    client = _client(mocker, parsed)
    out, usage = tmp_path / "d.jsonl", tmp_path / "u.jsonl"

    ais.screen_sample(client, [_record("111")], "claude-opus-5", out, usage, "screening")
    first_calls = client.messages.parse.call_count

    counts = ais.screen_sample(
        client, [_record("111"), _record("222")], "claude-opus-5", out, usage, "screening"
    )

    assert counts == {"total": 2, "screened": 1, "skipped": 1}
    assert client.messages.parse.call_count == first_calls + 1
    assert len(read_decisions(out)) == 2


def test_system_prompt_is_cached_and_carries_the_frozen_text(mocker):
    parsed = ais.ScreenerOutput(
        decision="unclear", criterion=None, confidence=0.3, reason="Abstract absent.",
    )
    client = _client(mocker, parsed)
    ais.screen_record(client, _record(), "claude-opus-5", "FROZEN", "e" * 64, "screening")

    kwargs = client.messages.parse.call_args.kwargs
    system = kwargs["system"]
    assert system[0]["text"] == "FROZEN"
    assert system[0]["cache_control"] == {"type": "ephemeral"}
    assert kwargs["output_format"] is ais.ScreenerOutput
    assert kwargs["model"] == "claude-opus-5"


def test_record_content_reaches_the_model(mocker):
    parsed = ais.ScreenerOutput(
        decision="include", criterion=None, confidence=0.9, reason="ok",
    )
    client = _client(mocker, parsed)
    ais.screen_record(
        client, _record(title="Unique Title Here", abstract="Unique Abstract Here"),
        "claude-opus-5", "P", "f" * 64, "screening",
    )
    content = client.messages.parse.call_args.kwargs["messages"][0]["content"]
    assert "Unique Title Here" in content
    assert "Unique Abstract Here" in content


def test_usage_is_recorded_per_record(mocker, tmp_path):
    parsed = ais.ScreenerOutput(
        decision="include", criterion=None, confidence=0.9, reason="ok",
    )
    out, usage = tmp_path / "d.jsonl", tmp_path / "u.jsonl"
    ais.screen_sample(
        _client(mocker, parsed), [_record("111")], "claude-opus-5", out, usage, "screening"
    )

    lines = [json.loads(l) for l in usage.read_text(encoding="utf-8").splitlines()]
    assert lines[0]["record_id"] == "egm-111"
    assert lines[0]["output_tokens"] == 120
    assert lines[0]["cache_read_input_tokens"] == 1300


def test_missing_abstract_is_sent_as_an_explicit_marker(mocker):
    """5 of 9,088 records genuinely have no abstract; the model must be told."""
    parsed = ais.ScreenerOutput(
        decision="unclear", criterion=None, confidence=0.2, reason="No abstract.",
    )
    client = _client(mocker, parsed)
    ais.screen_record(
        client, _record(abstract=None), "claude-opus-5", "P", "a" * 64, "screening"
    )
    content = client.messages.parse.call_args.kwargs["messages"][0]["content"]
    assert "[no abstract available]" in content


def test_record_missing_the_abstract_key_raises(mocker):
    """A malformed record must not be screened as though it lacked an abstract."""
    parsed = ais.ScreenerOutput(
        decision="include", criterion=None, confidence=0.9, reason="ok",
    )
    client = _client(mocker, parsed)
    record = _record()
    del record["abstract"]
    with pytest.raises(ais.ScreenerError, match="abstract"):
        ais.screen_record(client, record, "claude-opus-5", "P", "a" * 64, "screening")
    client.messages.parse.assert_not_called()


def test_empty_string_abstract_is_treated_as_absent(mocker):
    parsed = ais.ScreenerOutput(
        decision="unclear", criterion=None, confidence=0.2, reason="No abstract.",
    )
    client = _client(mocker, parsed)
    ais.screen_record(
        client, _record(abstract=""), "claude-opus-5", "P", "a" * 64, "screening"
    )
    content = client.messages.parse.call_args.kwargs["messages"][0]["content"]
    assert "[no abstract available]" in content
