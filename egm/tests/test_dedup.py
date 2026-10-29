from pipeline.dedup import deduplicate, normalise_doi, normalise_title
from pipeline.schema import SearchRecord


def _record(source_db, source_id, doi=None, pmid=None, title="A study", year=2020,
            authors=("Smith J",)):
    return SearchRecord(
        source_db=source_db, source_id=source_id, doi=doi, pmid=pmid, title=title,
        abstract=None, year=year, journal="J", authors=list(authors),
        retrieved_at="2026-09-13T10:00:00Z", query_hash="h" * 12,
    )


def test_normalise_doi_lowercases_and_strips_prefix():
    assert normalise_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"
    assert normalise_doi("  10.1000/ABC  ") == "10.1000/abc"


def test_normalise_doi_passes_through_none():
    assert normalise_doi(None) is None
    assert normalise_doi("   ") is None


def test_normalise_title_strips_punctuation_and_case():
    assert normalise_title("Epigenetics: A Review!") == "epigenetics a review"


def test_unique_records_all_survive():
    records = [_record("pubmed", "1", doi="10.1/a"), _record("embase", "2", doi="10.1/b")]
    kept, counts = deduplicate(records)
    assert len(kept) == 2
    assert counts["input"] == 2
    assert counts["removed_total"] == 0


def test_doi_duplicates_collapse():
    records = [
        _record("pubmed", "1", doi="10.1/a"),
        _record("embase", "2", doi="https://doi.org/10.1/A"),
    ]
    kept, counts = deduplicate(records)
    assert len(kept) == 1
    assert counts["removed_doi"] == 1
    assert kept[0].dedup_rule == "doi"
    assert sorted(kept[0].merged_from) == ["embase:2", "pubmed:1"]


def test_pmid_duplicates_collapse_when_doi_absent():
    records = [_record("pubmed", "1", pmid="999"), _record("central", "2", pmid="999")]
    kept, counts = deduplicate(records)
    assert len(kept) == 1
    assert counts["removed_pmid"] == 1


def test_fuzzy_title_duplicates_collapse():
    records = [
        _record("wos", "1", title="DNA methylation and diet in adults"),
        _record("embase", "2", title="DNA methylation and diet in adults."),
    ]
    kept, counts = deduplicate(records)
    assert len(kept) == 1
    assert counts["removed_fuzzy"] == 1


def test_same_title_different_year_kept_separate():
    records = [
        _record("wos", "1", title="Cohort study", year=2018),
        _record("embase", "2", title="Cohort study", year=2022),
    ]
    assert len(deduplicate(records)[0]) == 2


def test_counts_reconcile():
    records = [
        _record("pubmed", "1", doi="10.1/a"),
        _record("embase", "2", doi="10.1/a"),
        _record("wos", "3", doi="10.1/b"),
    ]
    kept, counts = deduplicate(records)
    assert counts["input"] - counts["removed_total"] == counts["output"] == len(kept)


def test_fuzzy_matches_when_only_one_record_has_an_identifier():
    """Absent identifiers must not block a fuzzy merge — only conflicting ones do.

    Real multi-database corpora mix records that carry a DOI with records
    that do not. Requiring both to be identifier-free would under-deduplicate.
    """
    records = [
        _record("embase", "1", doi=None, title="DNA methylation and diet in adults"),
        _record("wos", "2", doi="10.1/x", title="DNA methylation and diet in adults"),
    ]
    kept, counts = deduplicate(records)
    assert len(kept) == 1
    assert counts["removed_fuzzy"] == 1


def test_no_identifier_record_cannot_bridge_conflicting_identifiers():
    """A survivor must learn identifiers from records merged into it.

    Otherwise a record carrying no DOI acts as a bridge: the first
    DOI-bearing record merges into it, and a second record with a
    CONFLICTING DOI then merges too, because the survivor still looks
    identifier-free.
    """
    records = [
        _record("embase", "1", doi=None, title="DNA methylation and diet in adults"),
        _record("wos", "2", doi="10.1/x", title="DNA methylation and diet in adults"),
        _record("central", "3", doi="10.1/y", title="DNA methylation and diet in adults"),
    ]
    kept, counts = deduplicate(records)
    assert len(kept) == 2, "conflicting DOIs must not be bridged into one record"
    assert counts["input"] - counts["removed_total"] == counts["output"] == len(kept)


def test_empty_titles_never_fuzzy_match_each_other():
    """rapidfuzz.fuzz.ratio('', '') == 100.0, so two distinct records that both
    happen to have an empty title, same year, and same first-author surname
    must NOT be merged by the fuzzy-title rule.
    """
    records = [
        _record("pubmed", "1", title="", year=2021, authors=("Lee K",)),
        _record("embase", "2", title="", year=2021, authors=("Lee J",)),
    ]
    kept, counts = deduplicate(records)
    assert len(kept) == 2, "distinct untitled records must not collapse into one"
    assert counts["removed_fuzzy"] == 0


def test_first_author_surname_handles_blank_author_string():
    """An author entry of '' (no name on record) must not raise IndexError."""
    records = [_record("pubmed", "1", authors=("",))]
    kept, counts = deduplicate(records)
    assert len(kept) == 1
    assert counts["removed_total"] == 0


def test_no_identifier_record_cannot_bridge_conflicting_pmids():
    """A survivor must learn PMID identifiers from records merged into it.

    Mirror test for PMID: a record carrying no PMID acts as a bridge for
    conflicting PMIDs if identifiers are not backfilled on merge.
    """
    records = [
        _record("embase", "1", pmid=None, title="Epigenetic study"),
        _record("pubmed", "2", pmid="111", title="Epigenetic study"),
        _record("central", "3", pmid="222", title="Epigenetic study"),
    ]
    kept, counts = deduplicate(records)
    assert len(kept) == 2, "conflicting PMIDs must not be bridged into one record"
    assert counts["input"] - counts["removed_total"] == counts["output"] == len(kept)


# ---------------------------------------------------------------------------
# Preprint / published-version year window (protocol/amendments.md, 2026-09-14)
# ---------------------------------------------------------------------------

_TITLE = "DNA methylation and diet in adults"


def test_preprint_merges_with_published_version_one_year_later():
    """A preprint and its journal version are the same study.

    The preprint is posted before publication, so the years never match and
    the exact-year gate double-counted the pair. PubMed is listed first
    because `deduplicate()` keeps the first record of a group as the survivor.
    """
    records = [
        _record("pubmed", "111", pmid="111", title=_TITLE, year=2021),
        _record("europepmc", "PPR:PPR1", title=_TITLE + ".", year=2020),
    ]
    kept, counts = deduplicate(records)
    assert len(kept) == 1
    assert counts["removed_fuzzy"] == 1
    assert kept[0].dedup_rule == "fuzzy_title"
    assert sorted(kept[0].merged_from) == ["europepmc:PPR:PPR1", "pubmed:111"]
    assert kept[0].source_db == "pubmed", "the peer-reviewed record must survive"


def test_two_non_preprints_a_year_apart_still_do_not_merge():
    """The original protection. The exact-year gate exists to stop annual
    reports, serial trials and cohort waves -- similar titles, different
    years -- from collapsing. The preprint window must not reach them.
    """
    records = [
        _record("pubmed", "1", title=_TITLE, year=2020),
        _record("embase", "2", title=_TITLE, year=2021),
    ]
    kept, counts = deduplicate(records)
    assert len(kept) == 2, "distinct-year non-preprint records must stay separate"
    assert counts["removed_fuzzy"] == 0


def test_preprint_three_years_apart_does_not_merge():
    """The window is bounded at +/-2 years; a 3-year gap stays separate.

    Without a bound the relaxation would collapse any same-title,
    same-surname preprint onto any published record whatever the interval.
    """
    records = [
        _record("pubmed", "1", title=_TITLE, year=2023),
        _record("europepmc", "PPR:PPR1", title=_TITLE, year=2020),
    ]
    kept, counts = deduplicate(records)
    assert len(kept) == 2
    assert counts["removed_fuzzy"] == 0


def test_preprint_with_conflicting_doi_DOES_merge():
    """REVERSAL, 2026-09-14. This test previously asserted the opposite.

    It was written on the assumption that the identifier-conflict guard should
    outrank the widened year window. Measurement against the real corpus showed
    that assumption was wrong: a preprint and its published version always carry
    different DOIs (preprint-server against journal), so the guard fired on 136
    of the 137 preprint/article pairs that shared an exact normalised title, an
    identical first author, and a publication year 0-2 apart -- and every one of
    those 136 was double-counted as two studies.

    The guard is therefore scoped to non-preprint pairs rather than removed.
    Its original job is pinned by test_two_journal_articles_with_conflicting_
    dois_still_do_not_merge, and the PMID half of it by
    test_preprint_with_conflicting_pmid_still_does_not_merge.
    """
    records = [
        _record("pubmed", "1", doi="10.1/a", title=_TITLE, year=2021),
        _record("europepmc", "PPR:PPR1", doi="10.1/b", title=_TITLE, year=2020),
    ]
    kept, counts = deduplicate(records)
    assert len(kept) == 1
    assert counts["removed_fuzzy"] == 1
    assert kept[0].source_db == "pubmed"


def test_preprint_with_none_year_does_not_crash():
    """Resolution: an absent year BLOCKS the merge, for preprints too.

    `abs(None - 2021)` would raise, and the two silent alternatives are both
    wrong: treating None as 0 invents a year, and treating it as "matches
    anything" would merge a preprint onto any same-titled record. Absence is
    stated, not substituted, so a pair with an absent year falls back to the
    strict rule -- None never equals 2021 -- and the records stay separate.
    """
    records = [
        _record("pubmed", "1", title=_TITLE, year=2021),
        _record("europepmc", "PPR:PPR1", title=_TITLE, year=None),
    ]
    kept, counts = deduplicate(records)
    assert len(kept) == 2
    assert counts["removed_fuzzy"] == 0

    # Two records that BOTH state no year still compare equal under the strict
    # rule, exactly as they did before the window existed. Pinned here so the
    # fallback cannot be "fixed" into rejecting every None pair.
    both_absent = [
        _record("pubmed", "1", title=_TITLE, year=None),
        _record("europepmc", "PPR:PPR1", title=_TITLE, year=None),
    ]
    kept_absent, counts_absent = deduplicate(both_absent)
    assert len(kept_absent) == 1
    assert counts_absent["removed_fuzzy"] == 1


def test_preprint_with_different_surname_does_not_merge():
    """The first-author surname requirement is untouched by the window."""
    records = [
        _record("pubmed", "1", title=_TITLE, year=2021, authors=("Smith J",)),
        _record("europepmc", "PPR:PPR1", title=_TITLE, year=2020,
                authors=("Jones A",)),
    ]
    kept, counts = deduplicate(records)
    assert len(kept) == 2
    assert counts["removed_fuzzy"] == 0


# --- preprint/published pairs: the DOI-conflict guard is scoped, not removed ---
#
# A preprint and its published version ALWAYS carry different DOIs. Applying the
# "conflicting identifiers block a merge" rule to that pair double-counted 136
# studies in the real corpus. These tests pin both halves: the guard must stop
# applying to preprint pairs, and must keep applying to everything else.


def test_preprint_merges_with_published_version_despite_conflicting_dois():
    """The real case: bioRxiv DOI against the journal DOI, one year apart."""
    published = _record("pubmed", "39000001", doi="10.1038/s41398-026-03961-3",
                        pmid="39000001", title="Epigenome-wide association study "
                        "of psilocybin-induced methylome change", year=2026)
    preprint = _record("europepmc", "PPR:PPR123456", doi="10.1101/2025.07.18.664368",
                       title="Epigenome-wide association study of "
                       "psilocybin-induced methylome change", year=2025)

    kept, counts = deduplicate([published, preprint])

    assert len(kept) == 1, "the preprint survived as a separate study"
    assert counts["removed_fuzzy"] == 1
    assert kept[0].source_db == "pubmed", "the preprint outranked the journal article"
    assert kept[0].doi == "10.1038/s41398-026-03961-3"
    assert sorted(kept[0].merged_from) == [
        "europepmc:PPR:PPR123456", "pubmed:39000001"]


def test_two_journal_articles_with_conflicting_dois_still_do_not_merge():
    """The guard's original job. Neither record is a preprint, so it still bites."""
    a = _record("pubmed", "1", doi="10.1/a", title="A shared title", year=2020)
    b = _record("europepmc", "PMC:PMC9", doi="10.1/b", title="A shared title", year=2020)

    kept, _ = deduplicate([a, b])

    assert len(kept) == 2, "the DOI-conflict guard stopped protecting non-preprints"


def test_preprint_with_conflicting_pmid_still_does_not_merge():
    """The PMID guard is NOT relaxed, even for a preprint pair."""
    published = _record("pubmed", "111", doi="10.1/a", pmid="111",
                        title="A shared title", year=2021)
    preprint = _record("europepmc", "PPR:PPR1", doi="10.1101/x", pmid="222",
                       title="A shared title", year=2020)

    kept, _ = deduplicate([published, preprint])

    assert len(kept) == 2


def test_preprint_four_years_apart_does_not_merge_even_with_no_doi_conflict():
    """Relaxing the DOI guard must not make the year window unbounded."""
    published = _record("pubmed", "1", doi="10.1/a", title="A shared title", year=2025)
    preprint = _record("europepmc", "PPR:PPR1", doi=None, title="A shared title", year=2021)

    kept, _ = deduplicate([published, preprint])

    assert len(kept) == 2


def test_preprint_with_different_first_author_does_not_merge():
    """Surname equality is now load-bearing, so pin it for preprints explicitly."""
    published = _record("pubmed", "1", doi="10.1/a", title="A shared title",
                        year=2021, authors=("Smith J",))
    preprint = _record("europepmc", "PPR:PPR1", doi="10.1101/x", title="A shared title",
                       year=2020, authors=("Jones A",))

    kept, _ = deduplicate([published, preprint])

    assert len(kept) == 2


def test_preprint_with_unrelated_title_does_not_merge():
    """Fuzzy title is the other load-bearing signal once the DOI guard steps aside."""
    published = _record("pubmed", "1", doi="10.1/a",
                        title="Methylation and glaucoma progression", year=2021)
    preprint = _record("europepmc", "PPR:PPR1", doi="10.1101/x",
                       title="Histone acetylation in liver fibrosis", year=2020)

    kept, _ = deduplicate([published, preprint])

    assert len(kept) == 2
