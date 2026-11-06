#!/usr/bin/env python3
"""Create local repositories with observable clean, dirty and branch states."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-c", "user.name=Audit fixture", "-c", "user.email=fixture@example.invalid", *args],
        cwd=root, text=True, stderr=subprocess.STDOUT,
    ).strip()


def create_fixtures(destination: Path) -> list[Path]:
    names = ["test-repo-clean", "test-repo-dirty", "test-repo-mixed", "test-repo-deepdive"]
    if any((destination / name).exists() for name in names):
        raise ValueError("fixture paths already exist; choose a fresh output directory")
    roots = []
    for name in names:
        root = destination / name
        root.mkdir(parents=True)
        git(root, "init", "--initial-branch=main")
        (root / "README.md").write_text("# Audit fixture\n\nLocal Git-state fixture, generated from maintained source.\n")
        (root / "app.py").write_text("def total(values):\n    return sum(values)\n")
        git(root, "add", ".")
        git(root, "commit", "-m", "Create fixture")
        if name == "test-repo-dirty":
            (root / "app.py").write_text("def total(values):\n    return sum(values) + 1\n")
        elif name == "test-repo-mixed":
            git(root, "switch", "-c", "feature")
            (root / "feature.txt").write_text("committed feature\n")
            git(root, "add", ".")
            git(root, "commit", "-m", "Add feature")
            (root / "untracked.txt").write_text("untracked work\n")
        elif name == "test-repo-deepdive":
            (root / "test_app.py").write_text(
                "from app import total\n\ndef test_total():\n    assert total([2, 5]) == 7\n"
            )
            git(root, "add", ".")
            git(root, "commit", "-m", "Add executable behavior test")
        roots.append(root)
    return roots


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    for root in create_fixtures(parser.parse_args().output):
        print(root)


if __name__ == "__main__":
    main()
