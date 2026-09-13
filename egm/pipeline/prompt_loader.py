"""Load the frozen screening prompt and hash it.

The hash is written into every AI decision, so a decision traces to the exact
instruction text that produced it. A changed prompt changes the hash, which
makes drift detectable in the decision log rather than a matter of trust.
"""
import hashlib
import pathlib

PROMPT_DIR = pathlib.Path(__file__).resolve().parent / "prompts"


def load_prompt(version: str = "v1") -> tuple[str, str]:
    """Return (prompt_text, sha256_hex) for the named prompt version."""
    path = PROMPT_DIR / f"screening_{version}.md"
    if not path.exists():
        raise FileNotFoundError(
            f"no screening prompt for version {version!r} at {path}"
        )
    text = path.read_text(encoding="utf-8")
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()
