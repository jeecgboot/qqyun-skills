#!/usr/bin/env python3
"""
Resolve the per-skill temp directory (or a file inside it) and print the absolute path.

The directory is `<system_temp>/<skill_name>/`, created if missing. The OS handles
cleanup; this script never deletes anything.

Examples:
    # Print just the skill temp dir
    python skill_temp_path.py

    # Print full path for a specific config file (also creates the dir if missing)
    python skill_temp_path.py -f sk_audit_create.json

    # Override the skill name (defaults to "jeecg-desform")
    python skill_temp_path.py --skill some-other-skill -f cfg.json

Output:
    On success: a single line containing the absolute path, written to stdout.
    On failure: a one-line error message to stderr; exit code 1.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile

DEFAULT_SKILL_NAME = "jeecg-desform"


def resolve(skill: str, filename: str | None) -> str:
    if not skill or any(sep in skill for sep in ("/", "\\", "..")):
        raise ValueError(f"invalid skill name: {skill!r}")
    if filename and any(sep in filename for sep in ("/", "\\", "..")):
        raise ValueError(f"filename must be a bare name, not a path: {filename!r}")

    skill_dir = os.path.join(tempfile.gettempdir(), skill)
    os.makedirs(skill_dir, exist_ok=True)
    return os.path.join(skill_dir, filename) if filename else skill_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve per-skill temp dir/file path (cross-platform).",
    )
    parser.add_argument(
        "-f", "--filename",
        default=None,
        help="Optional file name appended to the skill temp dir (bare name only).",
    )
    parser.add_argument(
        "--skill",
        default=DEFAULT_SKILL_NAME,
        help=f"Skill name used as subdirectory (default: {DEFAULT_SKILL_NAME}).",
    )
    args = parser.parse_args()

    try:
        path = resolve(args.skill, args.filename)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
