"""Run manifests binding every artefact to the query that produced it."""
import hashlib
import json
import pathlib
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

TOOL_VERSION = "0.1.0"


def query_hash(query_string: str) -> str:
    """Stable 12-character identifier for a query string."""
    return hashlib.sha256(query_string.encode("utf-8")).hexdigest()[:12]


class RunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_version: str
    run_at: str
    query_string: str
    query_hash: str
    source_db: str
    record_count: int = Field(ge=0)
    notes: Optional[str]

    @classmethod
    def create(
        cls, query_string: str, source_db: str, record_count: int, notes: Optional[str]
    ) -> "RunManifest":
        """`notes` is positional-required so absence is stated, not defaulted."""
        return cls(
            tool_version=TOOL_VERSION,
            run_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            query_string=query_string,
            query_hash=query_hash(query_string),
            source_db=source_db,
            record_count=record_count,
            notes=notes,
        )


def write_artefact(
    path: pathlib.Path, records: list[dict[str, Any]], manifest: RunManifest
) -> None:
    """Write records plus manifest. Refuses overwrite; verifies the count."""
    if len(records) != manifest.record_count:
        raise ValueError(
            f"manifest.record_count={manifest.record_count} but got {len(records)} records"
        )
    path = pathlib.Path(path)
    if path.exists():
        raise FileExistsError(f"{path} exists; raw artefacts are append-only")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"manifest": manifest.model_dump(), "records": records}, indent=2),
        encoding="utf-8",
    )
