"""Project constants. No logic lives here (spec sections 4.1, 4.4, 4.5)."""

DATE_START = "2015/01/01"
DATE_END = "2026/12/31"

# "europepmc" is the recorded substitution for Embase, to which the
# investigator has no access (protocol/amendments.md). "embase" stays listed:
# the registration named it, and dropping it here would erase the fact that a
# registered database went unsearched.
SOURCE_DBS = (
    "pubmed", "embase", "wos", "central", "ctgov", "ictrp", "europepmc",
)

# Eligible epigenetic markers. ncRNA is deliberately excluded as a sole
# marker (spec section 4.4): it nearly doubles the corpus (11,965 -> 21,528)
# for low expected yield, and is definitionally contested.
ELIGIBLE_MARKERS = ("methylation", "histone", "chromatin", "clock")

NCBI_TOOL_NAME = "egm-pipeline"
NCBI_RATE_LIMIT_SECONDS = 0.34  # ~3 requests/sec without an API key

# Europe PMC composes `source_id` as "<SRC>:<id>" (pipeline/europepmc.py
# `_to_record`), where SRC is the Europe PMC source code. "PPR" is its
# preprint source. Both the builder and the deduplicator need this
# convention, so it is stated once here rather than as a bare string in each.
SOURCE_ID_SEPARATOR = ":"
EUROPEPMC_PREPRINT_SOURCE = "PPR"
PREPRINT_SOURCE_ID_PREFIX = f"{EUROPEPMC_PREPRINT_SOURCE}{SOURCE_ID_SEPARATOR}"
