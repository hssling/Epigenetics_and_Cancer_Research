"""Guards the remediation of the superseded pipelines (spec section 9.4)."""
import pathlib
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github" / "workflows" / "python-living-review.yml"


def test_deprecated_notice_exists_and_is_specific():
    notice = REPO / "DEPRECATED.md"
    assert notice.exists(), "DEPRECATED.md must exist at repository root"
    text = notice.read_text(encoding="utf-8")
    # The notice must name the concrete defects, not merely say "outdated".
    for required in ["random.random", "0.3", "200", "prisma_counts.csv", "not research findings"]:
        assert required in text, f"DEPRECATED.md must mention {required!r}"


def test_living_review_workflow_has_no_schedule_trigger():
    assert WORKFLOW.exists(), "workflow file should be retained, not deleted"
    spec = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    # PyYAML parses the bare key `on:` as boolean True.
    triggers = spec.get("on", spec.get(True, {})) or {}
    assert "schedule" not in triggers, (
        "scheduled trigger must be removed: it regenerates fabricated outputs weekly"
    )


def test_authors_file_lists_no_ai_author():
    authors = (REPO / "re_research_2025" / "AUTHORS").read_text(encoding="utf-8")
    for banned in ["Automation Agent", "DeepMind"]:
        assert banned not in authors, f"AI systems are not authors (found {banned!r})"
