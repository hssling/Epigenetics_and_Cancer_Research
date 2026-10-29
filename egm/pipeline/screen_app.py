"""Local keyboard-driven app for human title/abstract screening.

Two properties matter more than features:

  - Durability. Each decision is appended and fsynced before the next record
    renders, because 1,300 screening judgements are irreplaceable and a
    buffered write is a lost afternoon.
  - Blindness. This module never loads AI decisions. The registration's
    blind-screening commitment is therefore structural rather than a matter
    of discipline: there is no code path by which an AI decision could reach
    the page.
"""
import argparse
import html
import json
import pathlib
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from pipeline import highlight
from pipeline.screen_schema import (
    CRITERIA,
    CRITERION_LABELS,
    ScreeningDecision,
    Stage,
    append_decision,
    read_decisions,
)


def _identifier(record: dict) -> str:
    """Label the record by PMID, falling back to its source id.

    Europe PMC preprints and PMC-only deposits are not indexed in MEDLINE and
    carry no PMID at all (698 records in the current corpus). Rendering
    `record["pmid"]` unguarded raised TypeError on the first such record, which
    would have stopped human screening dead partway through a session.
    """
    pmid = record.get("pmid")
    if pmid:
        return f"PMID {pmid}"
    source_id = record.get("source_id")
    return str(source_id) if source_id else "no identifier"


def load_queue(
    sample_path: pathlib.Path, out_path: pathlib.Path
) -> list[dict[str, Any]]:
    """Records not yet screened BY A HUMAN, in sample order.

    Filtering on screener matters: if this log ever contained AI decisions,
    counting them as done would silently drop those records from the queue and
    shrink the sample without anyone noticing.
    """
    records = json.loads(pathlib.Path(sample_path).read_text(encoding="utf-8"))
    done = {
        d.record_id for d in read_decisions(out_path) if d.screener == "human"
    }
    return [r for r in records if r["record_id"] not in done]


def record_decision(
    out_path: pathlib.Path,
    record: dict[str, Any],
    decision: str,
    criterion: Optional[str],
    stage: Stage,
) -> ScreeningDecision:
    """Append one human decision. Amends append with `supersedes` set."""
    previous = [
        d for d in read_decisions(out_path)
        if d.record_id == record["record_id"] and d.screener == "human"
    ]
    entry = ScreeningDecision(
        record_id=record["record_id"],
        pmid=record["pmid"],
        decision=decision,
        criterion=criterion,
        confidence=None,
        reason=None,
        screener="human",
        model_id=None,
        prompt_sha256=None,
        stage=stage,
        decided_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        supersedes=previous[-1].decided_at if previous else None,
    )
    append_decision(out_path, entry)
    return entry


def build_page(
    record: dict[str, Any], position: int, total: int, elapsed_s: float
) -> str:
    """Render one record. No AI information is available to this function."""
    has_abstract = bool(record.get("abstract"))
    abstract = record.get("abstract") or "[no abstract available for this record]"
    year_warning = highlight.year_flag(record.get("year"))
    rate =f"{elapsed_s / position:.0f}s/record" if position else "-"
    remaining = total - position + 1
    eta = f"{(elapsed_s / position) * remaining / 60:.0f} min left" if position else "-"

    buttons = "\n".join(
        f'<li><b>{i + 1}</b> &nbsp;{html.escape(CRITERION_LABELS[c])} '
        f'<code>{html.escape(c)}</code></li>'
        for i, c in enumerate(CRITERIA)
    )

    return f"""<!doctype html><meta charset="utf-8">
<title>Screening {position}/{total}</title>
<style>
 body {{ font: 16px/1.55 system-ui, sans-serif; max-width: 46rem;
        margin: 2rem auto; padding: 0 1rem; }}
 .bar {{ height: 6px; background: #eee; border-radius: 3px; margin: .5rem 0 1.5rem; }}
 .bar > i {{ display:block; height:6px; background:#2563eb; border-radius:3px;
             width: {100 * position / max(total, 1):.1f}%; }}
 .meta {{ color:#666; font-size:.85rem; display:flex; justify-content:space-between; }}
 h1 {{ font-size: 1.25rem; line-height:1.35; margin:.5rem 0 .25rem; }}
 .j {{ color:#666; font-size:.9rem; margin-bottom:1rem; }}
 .a {{ white-space: pre-wrap; background:#fafafa; padding:1rem;
       border-left:3px solid #ddd; }}
 ul {{ list-style:none; padding:0; font-size:.9rem; }}
 li {{ padding:.15rem 0; }}
 kbd {{ background:#eee; border-radius:3px; padding:.1rem .4rem; font-size:.85rem; }}
 #crit {{ display:none; margin-top:1rem; }}
 table.sig {{ font-size:.82rem; border-collapse:collapse; margin:0 0 1rem; width:100%; }}
 table.sig td {{ padding:.15rem .5rem .15rem 0; vertical-align:top; }}
 table.sig td.c {{ color:#666; white-space:nowrap; }}
 p.sig {{ font-size:.85rem; color:#666; }}
 .warn {{ color:#b91c1c; font-weight:600; }}
 .note {{ color:#888; font-size:.75rem; margin-top:-.5rem; }}
{highlight.styles()}
</style>
<div class="meta"><span>{position} / {total}</span><span>{rate} &middot; {eta}</span></div>
<div class="bar"><i></i></div>
<h1>{highlight.mark(record["title"])}</h1>
<div class="j">{html.escape(str(record.get("journal") or "-"))} &middot;
 {html.escape(str(record.get("year") or "-"))} &middot; {html.escape(_identifier(record))}
 {f'&middot; <span class="warn">{html.escape(year_warning)}</span>' if year_warning else ''}</div>
{highlight.signal_strip(record["title"], record.get("abstract") or "") if has_abstract else ''}
<p class="note">Keyword matches are places to look, not judgements.</p>
<div class="a">{highlight.mark(abstract) if has_abstract else html.escape(abstract)}</div>
<p><kbd>i</kbd> include &nbsp; <kbd>e</kbd> exclude &nbsp; <kbd>u</kbd> unclear</p>
<div id="crit"><b>Exclusion criterion:</b><ul>{buttons}</ul></div>
<script>
let awaiting = false;
document.addEventListener("keydown", (ev) => {{
  const k = ev.key.toLowerCase();
  if (!awaiting) {{
    if (k === "i") go("include", "");
    else if (k === "u") go("unclear", "");
    else if (k === "e") {{ awaiting = true; document.getElementById("crit").style.display = "block"; }}
  }} else {{
    const n = parseInt(k, 10);
    const crits = {json.dumps(list(CRITERIA))};
    if (n >= 1 && n <= crits.length) go("exclude", crits[n - 1]);
    else if (k === "escape") {{ awaiting = false; document.getElementById("crit").style.display = "none"; }}
  }}
}});
function go(decision, criterion) {{
  window.location = "/decide?record_id={html.escape(record["record_id"])}"
    + "&decision=" + decision + "&criterion=" + criterion;
}}
</script>"""


def serve(
    sample_path: pathlib.Path, out_path: pathlib.Path, stage: Stage, port: int
) -> None:
    """Run the screening server until the queue is empty."""
    total = len(json.loads(pathlib.Path(sample_path).read_text(encoding="utf-8")))
    started = time.monotonic()
    state: dict[str, Any] = {"queue": load_queue(sample_path, out_path)}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # noqa: A003 - silence per-request logging
            return

        def _send(self, body: str, status: int = 200) -> None:
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802 - stdlib naming
            url = urlparse(self.path)

            if url.path == "/decide":
                params = parse_qs(url.query)
                submitted_id = params.get("record_id", [""])[0]
                if not state["queue"]:
                    self._send("<p>Queue is empty; nothing to record.</p>", status=409)
                    return
                record = state["queue"][0]
                if submitted_id != record["record_id"]:
                    self._send(
                        "<!doctype html><meta charset='utf-8'>"
                        "<p style='font:16px system-ui;margin:3rem'>Stale submission ignored: "
                        f"this decision was for <code>{html.escape(submitted_id)}</code> but the "
                        f"current record is <code>{html.escape(record['record_id'])}</code>. "
                        "Nothing was written. <a href='/'>Continue</a>.</p>",
                        status=409,
                    )
                    return
                decision = params["decision"][0]
                criterion = params.get("criterion", [""])[0] or None
                record_decision(out_path, record, decision, criterion, stage)
                state["queue"] = state["queue"][1:]
                self.send_response(303)
                self.send_header("Location", "/")
                self.end_headers()
                return

            if not state["queue"]:
                self._send(
                    "<!doctype html><meta charset='utf-8'>"
                    f"<p style='font:16px system-ui;margin:3rem'>All {total} records "
                    f"screened. Decisions are in <code>{html.escape(str(out_path))}</code>.</p>"
                )
                return

            done = total - len(state["queue"])
            self._send(build_page(
                state["queue"][0], done + 1, total, time.monotonic() - started
            ))

    print(f"Screening {len(state['queue'])} of {total} records.")
    print(f"Open http://127.0.0.1:{port}/  —  keys: i / e / u, then 1-7 on exclude")
    print(f"Keyword highlighting: pipeline.highlight TERMS_VERSION {highlight.TERMS_VERSION}")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Human title/abstract screening")
    parser.add_argument("--sample", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument(
        "--stage", choices=["calibration", "screening", "validation"], required=True
    )
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    serve(args.sample, args.out, args.stage, args.port)


if __name__ == "__main__":
    main()
