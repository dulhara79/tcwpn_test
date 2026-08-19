#!/usr/bin/env python3
"""Pre-mirror guards for the TC-WPN component repository.

Run in two places:

  * ci.yml           - on every pull request, so violations are caught at review
                       time rather than at sync time.
  * sync-to-monorepo - immediately before the mirror is materialised, so nothing
                       restricted can reach the PUBLIC monorepo even if branch
                       protection was bypassed.

Checks
------
1. Forbidden paths     - MIMIC-IV / NHSL artefacts, raw tabular data, model
                         weights, key material. R26-DS-012 is public.
2. File size           - anything over the configured limit belongs in DVC or
                         the HF Hub, not in git history.
3. Notebook outputs    - a clinical NLP notebook's outputs can contain patient
                         note text; outputs must be stripped before commit.
4. Credential patterns - fast pre-flight for obvious token shapes.

Usage
-----
    python .github/sync/guards.py --config .github/sync/sync.config.yml
    python .github/sync/guards.py --config ... --strict
    python .github/sync/guards.py --config ... --print-manifest
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

# Paths never mirrored regardless of config; mirrors exclude.txt section 2/6.
INFRA_EXCLUDES = (
    ".git/**",
    ".github/**",
    "**/__pycache__/**",
    "**/.pytest_cache/**",
    "**/.ruff_cache/**",
    "**/.mypy_cache/**",
    "**/.ipynb_checkpoints/**",
    "**/.venv/**",
    "**/venv/**",
)

TEXT_SUFFIXES = {
    ".py",
    ".pyi",
    ".md",
    ".txt",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".cfg",
    ".ini",
    ".sh",
    ".ipynb",
    ".rst",
    ".tex",
    ".bib",
    ".dockerfile",
}


# ---------------------------------------------------------------------------
# Glob matching
# ---------------------------------------------------------------------------
def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a gitignore-flavoured glob into a regex.

    Supports ``**`` (any number of path segments), ``*`` (within a segment)
    and ``?``. Anchored at both ends.
    """
    out: list[str] = []
    i = 0
    while i < len(pattern):
        ch = pattern[i]
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif ch == "*":
            out.append("[^/]*")
            i += 1
        elif ch == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(ch))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def matches_any(path: str, patterns: list[str]) -> str | None:
    """Return the first pattern matching ``path``, or None."""
    for pattern in patterns:
        if glob_to_regex(pattern).match(path):
            return pattern
    return None


# ---------------------------------------------------------------------------
# Repository inspection
# ---------------------------------------------------------------------------
def tracked_files() -> list[str]:
    """Every file git tracks, repo-relative, POSIX separators."""
    raw = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [p for p in raw.split("\0") if p]


def mirrored_files(files: list[str], cfg: dict) -> list[str]:
    """Subset of tracked files that the mirror would actually copy."""
    guards = cfg.get("guards", {})
    forbidden = guards.get("forbidden_paths", [])
    allow = guards.get("allowlist", [])
    result = []
    for f in files:
        if matches_any(f, list(INFRA_EXCLUDES)):
            continue
        if matches_any(f, allow):
            result.append(f)
            continue
        if matches_any(f, forbidden):
            continue
        result.append(f)
    return result


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------
def check_forbidden(files: list[str], cfg: dict) -> list[str]:
    guards = cfg["guards"]
    forbidden = guards.get("forbidden_paths", [])
    allow = guards.get("allowlist", [])
    errors = []
    for f in files:
        if matches_any(f, list(INFRA_EXCLUDES)) or matches_any(f, allow):
            continue
        hit = matches_any(f, forbidden)
        if hit:
            errors.append(
                f"{f}: matches forbidden pattern '{hit}'. "
                f"R26-DS-012 is public — this must not be mirrored. "
                f"Remove it from git, or add an explicit allowlist entry if it "
                f"is genuinely synthetic/config."
            )
    return errors


def check_sizes(files: list[str], cfg: dict) -> list[str]:
    limit = int(cfg["guards"].get("max_file_bytes", 10 * 1024 * 1024))
    errors = []
    for f in files:
        p = Path(f)
        if not p.is_file():
            continue
        size = p.stat().st_size
        if size > limit:
            errors.append(
                f"{f}: {size / 1_048_576:.1f} MiB exceeds the "
                f"{limit / 1_048_576:.0f} MiB limit. Track it with DVC or push "
                f"it to the HF Hub instead of committing it."
            )
    return errors


def check_notebooks(files: list[str], cfg: dict) -> list[str]:
    if not cfg["guards"].get("require_stripped_notebooks", True):
        return []
    errors = []
    for f in files:
        if not f.endswith(".ipynb"):
            continue
        try:
            nb = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{f}: could not parse notebook ({exc}).")
            continue
        for idx, cell in enumerate(nb.get("cells", [])):
            if cell.get("outputs") or cell.get("execution_count") is not None:
                errors.append(
                    f"{f}: cell {idx} still has outputs. Clinical note text can "
                    f"leak through notebook outputs. Run `nbstripout {f}` before "
                    f"committing."
                )
                break
    return errors


def check_credentials(files: list[str], cfg: dict) -> list[str]:
    guards = cfg["guards"]
    patterns = [re.compile(p) for p in guards.get("credential_patterns", [])]
    skip = guards.get("scan_skip", [])
    errors = []
    for f in files:
        if matches_any(f, skip):
            continue
        p = Path(f)
        if not p.is_file() or p.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                line = text[: match.start()].count("\n") + 1
                errors.append(
                    f"{f}:{line}: matches credential pattern "
                    f"/{pattern.pattern}/. Rotate the credential and move it to "
                    f"an Actions secret."
                )
                break
    return errors


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on warnings as well as errors (used by the sync workflow).",
    )
    parser.add_argument(
        "--print-manifest",
        action="store_true",
        help="Print '<bytes>\\t<path>' for every file the mirror would copy.",
    )
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    files = tracked_files()

    if args.print_manifest:
        for f in sorted(mirrored_files(files, cfg)):
            size = Path(f).stat().st_size if Path(f).is_file() else 0
            print(f"{size}\t{f}")
        return 0

    checks = {
        "forbidden paths": check_forbidden(files, cfg),
        "file sizes": check_sizes(files, cfg),
        "notebook outputs": check_notebooks(files, cfg),
        "credential patterns": check_credentials(files, cfg),
    }

    failed = False
    for name, errors in checks.items():
        if errors:
            failed = True
            print(f"\n::group::FAILED — {name} ({len(errors)})")
            for err in errors:
                print(f"::error::{err}")
            print("::endgroup::")
        else:
            print(f"OK — {name}")

    if failed:
        print(
            "\nGuards failed. Nothing will be mirrored to the public monorepo.",
            file=sys.stderr,
        )
        return 1

    print(
        f"\nAll guards passed. {len(mirrored_files(files, cfg))} files eligible for mirror."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
