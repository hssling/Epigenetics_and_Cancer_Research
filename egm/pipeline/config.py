"""Project constants. No logic lives here (spec sections 4.1, 4.4, 4.5)."""

DATE_START = "2015/01/01"
DATE_END = "2026/12/31"

SOURCE_DBS = ("pubmed", "embase", "wos", "central", "ctgov", "ictrp")

# Eligible epigenetic markers. ncRNA is deliberately excluded as a sole
# marker (spec section 4.4): it nearly doubles the corpus (11,965 -> 21,528)
# for low expected yield, and is definitionally contested.
ELIGIBLE_MARKERS = ("methylation", "histone", "chromatin", "clock")

NCBI_TOOL_NAME = "egm-pipeline"
NCBI_RATE_LIMIT_SECONDS = 0.34  # ~3 requests/sec without an API key
