"""Abstract retrieval via efetch, and the corpus backfill that uses it.

The asymmetry tested here is deliberate and is the point of the module:

  - a record MISSING from the response raises, because a vanishing record
    corrupts the PRISMA count;
  - a record PRESENT but carrying no abstract yields None, because many
    PubMed records legitimately have none (editorials, some case reports,
    older indexing).

Silence on the second would be wrong too, so the backfill records the exact
count of missing abstracts in its manifest and raises when the share is high
enough to indicate a parsing fault rather than genuine absence.
"""
import json

import pytest

from pipeline import backfill_abstracts as ba
from pipeline import pubmed
from pipeline.integrity import IntegrityError

# --- fixtures ---------------------------------------------------------------

PLAIN = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle><MedlineCitation>
    <PMID Version="1">111</PMID>
    <Article><Abstract>
      <AbstractText>A plain unstructured abstract.</AbstractText>
    </Abstract></Article>
  </MedlineCitation></PubmedArticle>
</PubmedArticleSet>"""

STRUCTURED = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle><MedlineCitation>
    <PMID Version="1">222</PMID>
    <Article><Abstract>
      <AbstractText Label="BACKGROUND">Why we did it.</AbstractText>
      <AbstractText Label="METHODS">Illumina EPIC array, n=40.</AbstractText>
      <AbstractText Label="RESULTS">What we found.</AbstractText>
    </Abstract></Article>
  </MedlineCitation></PubmedArticle>
</PubmedArticleSet>"""

NO_ABSTRACT = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle><MedlineCitation>
    <PMID Version="1">333</PMID>
    <Article><ArticleTitle>An editorial with no abstract.</ArticleTitle></Article>
  </MedlineCitation></PubmedArticle>
</PubmedArticleSet>"""

OMITS_ONE = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle><MedlineCitation>
    <PMID Version="1">444</PMID>
    <Article><Abstract><AbstractText>Present.</AbstractText></Abstract></Article>
  </MedlineCitation></PubmedArticle>
</PubmedArticleSet>"""


class _FakeResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


def _patch_efetch(mocker, xml):
    mocker.patch.object(pubmed.time, "sleep")
    return mocker.patch.object(
        pubmed.requests, "get", return_value=_FakeResponse(xml)
    )


# --- fetch_abstracts --------------------------------------------------------


def test_plain_abstract_is_returned(mocker):
    _patch_efetch(mocker, PLAIN)
    assert pubmed.fetch_abstracts(["111"]) == {"111": "A plain unstructured abstract."}


def test_structured_abstract_keeps_its_section_labels(mocker):
    """Screening criteria often turn on the Methods section specifically."""
    _patch_efetch(mocker, STRUCTURED)
    result = pubmed.fetch_abstracts(["222"])["222"]
    assert "BACKGROUND: Why we did it." in result
    assert "METHODS: Illumina EPIC array, n=40." in result
    assert "RESULTS: What we found." in result


def test_record_present_without_abstract_yields_none_not_error(mocker):
    _patch_efetch(mocker, NO_ABSTRACT)
    assert pubmed.fetch_abstracts(["333"]) == {"333": None}


def test_record_absent_from_response_raises(mocker):
    """A vanishing record is unrecoverable and must never pass silently."""
    _patch_efetch(mocker, OMITS_ONE)
    with pytest.raises(pubmed.PubMedError, match="555"):
        pubmed.fetch_abstracts(["444", "555"])


def test_missing_pmids_are_listed_in_the_error(mocker):
    _patch_efetch(mocker, OMITS_ONE)
    with pytest.raises(pubmed.PubMedError) as exc:
        pubmed.fetch_abstracts(["444", "666", "777"])
    message = str(exc.value)
    assert "666" in message and "777" in message


def test_empty_pmid_list_makes_no_request(mocker):
    get = _patch_efetch(mocker, PLAIN)
    assert pubmed.fetch_abstracts([]) == {}
    get.assert_not_called()


# --- backfill ---------------------------------------------------------------


def _corpus(tmp_path, records):
    path = tmp_path / "raw" / "corpus.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"manifest": {"record_count": len(records)}, "records": records}),
        encoding="utf-8",
    )
    return path


def _record(pmid):
    return {
        "source_db": "pubmed", "source_id": pmid, "doi": None, "pmid": pmid,
        "title": f"Study {pmid}", "abstract": None, "year": 2020,
        "journal": "J Epi", "authors": ["Smith J"],
        "retrieved_at": "2026-09-13T10:00:00Z", "query_hash": "h" * 12,
        "record_id": f"egm-{pmid}", "merged_from": [f"pubmed:{pmid}"],
        "dedup_rule": "unique",
    }


def test_backfill_writes_new_artefact_and_leaves_original_untouched(tmp_path, mocker):
    """Raw exports are append-only: the backfill writes a NEW file."""
    source = _corpus(tmp_path, [_record("111"), _record("222")])
    original = source.read_text(encoding="utf-8")
    mocker.patch.object(
        ba.pubmed, "fetch_abstracts",
        return_value={"111": "Abstract one.", "222": "Abstract two."},
    )

    out = tmp_path / "raw" / "corpus_with_abstracts.json"
    counts = ba.backfill(source, out, batch_size=200)

    assert counts == {"records": 2, "with_abstract": 2, "without_abstract": 0}
    assert source.read_text(encoding="utf-8") == original

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["manifest"]["record_count"] == 2
    assert {r["pmid"]: r["abstract"] for r in payload["records"]} == {
        "111": "Abstract one.", "222": "Abstract two.",
    }


def test_genuinely_absent_abstracts_are_counted_not_hidden(tmp_path, mocker):
    source = _corpus(tmp_path, [_record(str(n)) for n in range(10)])
    returned = {str(n): (None if n == 0 else f"Abstract {n}.") for n in range(10)}
    mocker.patch.object(ba.pubmed, "fetch_abstracts", return_value=returned)

    out = tmp_path / "raw" / "out.json"
    counts = ba.backfill(source, out, batch_size=200)

    assert counts["without_abstract"] == 1
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "without_abstract=1" in payload["manifest"]["notes"]


def test_too_many_missing_abstracts_raises_as_probable_parsing_fault(tmp_path, mocker):
    """Genuine absence is a minority; a high share means the parser is wrong."""
    source = _corpus(tmp_path, [_record(str(n)) for n in range(10)])
    returned = {str(n): (None if n < 3 else f"Abstract {n}.") for n in range(10)}
    mocker.patch.object(ba.pubmed, "fetch_abstracts", return_value=returned)

    out = tmp_path / "raw" / "out.json"
    with pytest.raises(IntegrityError, match="30"):
        ba.backfill(source, out, batch_size=200)
    assert not out.exists(), "must not write an artefact it has rejected"


def test_threshold_boundary_is_not_exceeded_at_exactly_twenty_percent(tmp_path, mocker):
    source = _corpus(tmp_path, [_record(str(n)) for n in range(10)])
    returned = {str(n): (None if n < 2 else f"Abstract {n}.") for n in range(10)}
    mocker.patch.object(ba.pubmed, "fetch_abstracts", return_value=returned)

    out = tmp_path / "raw" / "out.json"
    counts = ba.backfill(source, out, batch_size=200)
    assert counts["without_abstract"] == 2


def test_backfilled_records_still_validate_against_the_schema(tmp_path, mocker):
    source = _corpus(tmp_path, [_record("111")])
    mocker.patch.object(
        ba.pubmed, "fetch_abstracts", return_value={"111": "An abstract."}
    )
    out = tmp_path / "raw" / "out.json"
    ba.backfill(source, out, batch_size=200)

    from pipeline.schema import DedupedRecord

    payload = json.loads(out.read_text(encoding="utf-8"))
    record = DedupedRecord(**payload["records"][0])
    assert record.abstract == "An abstract."
