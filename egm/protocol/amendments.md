# Protocol amendments

Every deviation from the registered protocol (OSF 3xtf2) is recorded here with
its date and rationale. Nothing is changed silently.

| Date | Section | Change | Rationale |
|---|---|---|---|
| — | — | No amendments enacted to date | — |

## Pending amendment: database access

**Raised 2026-09-13. Not yet enacted — drafted here so it is not lost.**

The registration lists, under Databases, four bibliographic sources to be
searched: PubMed/MEDLINE (executed), **Embase (Elsevier)**, **Web of Science
Core Collection (Clarivate)**, and **Cochrane CENTRAL**.

The investigator does not have institutional access to Embase, Web of Science,
or Scopus. Those searches therefore cannot be executed as registered.

This requires an amendment before screening concludes, because the registered
search strategy is a public commitment and a review that silently searches
fewer databases than it registered has overstated its coverage.

### Proposed substitution, all freely accessible

| Registered | Status | Proposed |
|---|---|---|
| PubMed/MEDLINE | Executed 2026-09-13, 9,088 records | unchanged |
| Embase | No access | **Europe PMC** — free API; indexes MEDLINE plus PMC, preprints, patents and theses, with substantial coverage beyond PubMed |
| Web of Science | No access | **OpenAlex** — free API; open bibliographic graph with citation data, the closest freely available analogue for coverage and citation chasing |
| Cochrane CENTRAL | Access uncertain | Attempt; if unavailable, record as not searched |
| ClinicalTrials.gov | Free | unchanged |
| WHO ICTRP | Free | unchanged |

### What the amendment must say

1. Which registered databases were not searched, and that the reason was lack
   of institutional access — not a judgement that they were unnecessary.
2. Which free sources replaced them, and that the substitution was made before
   screening concluded rather than after seeing results.
3. That coverage is consequently not equivalent to a review with full
   commercial database access, stated in the limitations rather than implied.

Europe PMC and OpenAlex are genuine sources, not a face-saving gesture: between
them they index a large majority of what Embase and Web of Science cover for
biomedical literature. But "a large majority" is not "all", and the difference
belongs in the limitations section where a reader can weigh it.

### Sequencing

This does not block Plan B. Screening the existing 9,088-record PubMed corpus
proceeds; the additional sources add records that enter the same screening
pipeline. The amendment must be filed on OSF before the review reports its
final PRISMA counts.
