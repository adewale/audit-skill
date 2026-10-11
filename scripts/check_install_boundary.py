#!/usr/bin/env python3
"""Fail if the declared installable skill directory contains repo-only artifacts."""
from __future__ import annotations

import json
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BANNED_DIR_NAMES = {
    ".claude",
    ".git",
    ".github",
    "__pycache__",
    "eval-runs",
    "evals",
    "node_modules",
    "research",
    "skill-development",
    "tests",
}
BANNED_FILE_SUFFIXES = {".pyc", ".pyo"}
BANNED_FILE_NAMES = {".DS_Store"}
# Packaged skills (e.g. a `.skill` upload bundle) are install artifacts too: scan every one in the repo.
ARCHIVE_SUFFIXES = {".skill", ".zip"}
ARCHIVE_SCAN_SKIP_DIRS = {".git", "node_modules"}


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        print(f"FAIL: {path.relative_to(ROOT)} is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(2)


def declared_skill_dirs() -> list[Path]:
    package = load_json(ROOT / "package.json")
    dirs: list[Path] = []
    entry = (package.get("skill") or {}).get("entry")
    if entry:
        dirs.append(ROOT / Path(entry).parent)
    for raw in (package.get("pi") or {}).get("skills") or []:
        path = ROOT / raw
        if path.name == "skills" and path.is_dir():
            dirs.extend(p for p in path.iterdir() if (p / "SKILL.md").is_file())
        else:
            dirs.append(path)
    marketplace = load_json(ROOT / ".claude-plugin" / "marketplace.json")
    for plugin in marketplace.get("plugins") or []:
        for raw in plugin.get("skills") or []:
            dirs.append(ROOT / raw)
    if not dirs:
        for candidate in [ROOT / "SKILL.md", *ROOT.glob("skills/*/SKILL.md"), ROOT / "swiss-poster/SKILL.md", ROOT / "testing-best-practices/SKILL.md"]:
            if candidate.is_file():
                dirs.append(candidate.parent)
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in dirs:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


def bad_files(skill_dir: Path) -> list[Path]:
    bad: list[Path] = []
    for path in skill_dir.rglob("*"):
        rel_parts = path.relative_to(skill_dir).parts
        if any(part in BANNED_DIR_NAMES for part in rel_parts) or path.is_file() and (path.suffix in BANNED_FILE_SUFFIXES or path.name in BANNED_FILE_NAMES):
            bad.append(path)
    return bad


def is_banned(rel_parts: tuple[str, ...]) -> bool:
    return any(part in BANNED_DIR_NAMES for part in rel_parts[:-1]) or (
        bool(rel_parts)
        and (rel_parts[-1] in BANNED_DIR_NAMES or rel_parts[-1] in BANNED_FILE_NAMES or Path(rel_parts[-1]).suffix in BANNED_FILE_SUFFIXES)
    )


def repo_archives() -> list[Path]:
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in ARCHIVE_SCAN_SKIP_DIRS)
        found.extend(Path(dirpath) / f for f in sorted(filenames) if Path(f).suffix.lower() in ARCHIVE_SUFFIXES)
    return found


def skill_snapshot(skill_dir: Path) -> dict[str, bytes]:
    return {
        path.relative_to(skill_dir).as_posix(): path.read_bytes()
        for path in skill_dir.rglob("*")
        if path.is_file() and not is_banned(path.relative_to(skill_dir).parts)
    }


def archive_errors(archive: Path, skill_dirs: list[Path]) -> list[str]:
    """An archive may only hold an exact, current copy of one declared skill directory."""
    display = archive.relative_to(ROOT)
    try:
        with zipfile.ZipFile(archive) as bundle:
            entries = {info.filename: bundle.read(info) for info in bundle.infolist() if not info.is_dir()}
    except (zipfile.BadZipFile, OSError) as exc:
        return [f"{display}: not a readable zip archive ({exc})"]
    errors: list[str] = []
    banned = sorted(name for name in entries if is_banned(tuple(name.split("/"))))
    if banned:
        sample = ", ".join(banned[:10])
        suffix = f"; +{len(banned) - 10} more" if len(banned) > 10 else ""
        errors.append(f"{display}: {len(banned)} repo-only entries: {sample}{suffix}")
    # `.skill` bundles usually wrap the skill in one top-level folder; compare relative to it.
    tops = {name.split("/", 1)[0] for name in entries}
    if len(tops) == 1 and all("/" in name for name in entries):
        entries = {name.split("/", 1)[1]: data for name, data in entries.items()}
    for skill_dir in skill_dirs:
        if skill_dir.is_dir() and entries == skill_snapshot(skill_dir):
            return errors
    closest = min(
        (d for d in skill_dirs if d.is_dir()),
        key=lambda d: len(set(entries) ^ set(skill_snapshot(d))),
        default=None,
    )
    if closest is None:
        errors.append(f"{display}: no declared skill directory to compare against")
        return errors
    current = skill_snapshot(closest)
    extra = sorted(set(entries) - set(current))
    missing = sorted(set(current) - set(entries))
    changed = sorted(name for name in set(entries) & set(current) if entries[name] != current[name])
    detail = "; ".join(
        f"{label}: {', '.join(names[:5])}{' ...' if len(names) > 5 else ''} ({len(names)})"
        for label, names in (("not in skill dir", extra), ("missing from archive", missing), ("stale", changed))
        if names
    )
    errors.append(
        f"{display}: is not an exact copy of {closest.resolve().relative_to(ROOT.resolve())} ({detail}); "
        "delete it or rebuild it from the skill directory"
    )
    return errors


def main() -> int:
    dirs = declared_skill_dirs()
    if not dirs:
        print("FAIL: no installable skill directory declared or discovered", file=sys.stderr)
        return 1
    errors: list[str] = []
    for skill_dir in dirs:
        try:
            display = skill_dir.resolve().relative_to(ROOT.resolve())
        except ValueError:
            display = skill_dir
        skill_file = skill_dir / "SKILL.md"
        if not skill_dir.is_dir():
            errors.append(f"{display}: directory does not exist")
            continue
        if not skill_file.is_file():
            errors.append(f"{display}: missing SKILL.md")
        bad = bad_files(skill_dir)
        if bad:
            sample = ", ".join(str(p.relative_to(ROOT)) for p in bad[:20])
            suffix = f"; +{len(bad) - 20} more" if len(bad) > 20 else ""
            errors.append(f"{display}: repo-only artifacts found: {sample}{suffix}")
    archives = repo_archives()
    for archive in archives:
        errors.extend(archive_errors(archive, dirs))
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("OK: installable skill boundary is clean: " + ", ".join(str(d.resolve().relative_to(ROOT.resolve())) for d in dirs))
    print(f"OK: {len(archives)} packaged skill archive(s) (*.skill, *.zip) checked" + "".join(f"\n  {a.relative_to(ROOT)}" for a in archives))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
