#!/usr/bin/env python3
"""Fail if a SKILL.md frontmatter breaks the Agent Skills spec limits.

Checks every skills/*/SKILL.md (and a root SKILL.md, if any):
- frontmatter is delimited by `---` lines;
- `name` is 1-64 chars of lowercase letters/digits/single hyphens and matches the directory;
- `description` is present, at most 1024 chars, and has no `<`/`>`;
- `compatibility`, when present, is at most 500 chars.

Standard library only. Supports the YAML subset used in SKILL.md frontmatter:
`key: value`, quoted scalars, and `>`/`|` block scalars (with optional `-`/`+` chomping).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
KEY_RE = re.compile(r"^([A-Za-z0-9_-]+):(?:\s+(.*))?$")
MAX_NAME = 64
MAX_DESCRIPTION = 1024
MAX_COMPATIBILITY = 500


class FrontmatterError(ValueError):
    pass


def _block_scalar(indicator: str, lines: list[str]) -> str:
    style, chomp = indicator[0], indicator[1:]
    if chomp not in {"", "-", "+"}:
        raise FrontmatterError(f"unsupported block scalar indicator {indicator!r}")
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    if not lines:
        return ""
    indent = min(len(line) - len(line.lstrip(" ")) for line in lines if line.strip())
    body = [line[indent:] if line.strip() else "" for line in lines]
    if style == "|":
        text = "\n".join(body)
    else:  # folded: single newlines become spaces, blank lines become newlines
        text, pending_blank = "", 0
        for line in body:
            if not line:
                pending_blank += 1
                continue
            if text:
                text += "\n" * pending_blank if pending_blank else " "
            text += line
            pending_blank = 0
    return text if chomp == "-" else text + "\n"


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("must start with a `---` frontmatter line")
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        raise FrontmatterError("frontmatter is not closed by a `---` line") from None
    fields: dict[str, str] = {}
    body = lines[1:end]
    i = 0
    while i < len(body):
        line = body[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        match = KEY_RE.match(line)
        if not match:
            raise FrontmatterError(f"unsupported frontmatter line: {line!r}")
        key, value = match.group(1), (match.group(2) or "").strip()
        i += 1
        continuation: list[str] = []
        while i < len(body) and (not body[i].strip() or body[i].startswith((" ", "\t"))):
            continuation.append(body[i])
            i += 1
        if value[:1] in {">", "|"}:
            fields[key] = _block_scalar(value, continuation)
        elif value[:1] in {'"', "'"}:
            if len(value) < 2 or value[-1] != value[0] or continuation:
                raise FrontmatterError(f"{key}: multi-line or unterminated quoted scalars are not supported")
            fields[key] = value[1:-1]
        else:
            # Plain scalar, possibly continued on indented lines (folded with spaces),
            # or a nested mapping/list (e.g. `metadata:`), kept as raw text.
            fields[key] = " ".join([value, *(c.strip() for c in continuation if c.strip())]).strip()
    return fields


def check(skill_md: Path) -> list[str]:
    try:
        fields = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    except FrontmatterError as exc:
        return [str(exc)]
    errors: list[str] = []
    name = fields.get("name", "")
    if not name:
        errors.append("missing `name`")
    else:
        if len(name) > MAX_NAME or not NAME_RE.fullmatch(name):
            errors.append(f"`name` {name!r} must be 1-{MAX_NAME} lowercase letters, digits and single hyphens")
        if skill_md.parent != ROOT and name != skill_md.parent.name:
            errors.append(f"`name` {name!r} must match its directory {skill_md.parent.name!r}")
    description = fields.get("description", "")
    if not description.strip():
        errors.append("missing `description`")
    if len(description) > MAX_DESCRIPTION:
        errors.append(f"`description` is {len(description)} chars; the limit is {MAX_DESCRIPTION}")
    if "<" in description or ">" in description:
        errors.append("`description` must not contain `<` or `>`")
    compatibility = fields.get("compatibility")
    if compatibility is not None and len(compatibility) > MAX_COMPATIBILITY:
        errors.append(f"`compatibility` is {len(compatibility)} chars; the limit is {MAX_COMPATIBILITY}")
    return errors


def main(argv: list[str]) -> int:
    targets = [Path(a).resolve() for a in argv] or sorted(ROOT.glob("skills/*/SKILL.md"))
    if not argv and (ROOT / "SKILL.md").is_file():
        targets.insert(0, ROOT / "SKILL.md")
    if not targets:
        print("FAIL: no SKILL.md found", file=sys.stderr)
        return 1
    failed = False
    for target in targets:
        display = target.relative_to(ROOT) if target.is_relative_to(ROOT) else target
        errors = check(target)
        for error in errors:
            print(f"FAIL: {display}: {error}", file=sys.stderr)
        if errors:
            failed = True
        else:
            desc = parse_frontmatter(target.read_text(encoding="utf-8"))["description"]
            print(f"OK: {display} (description {len(desc)}/{MAX_DESCRIPTION} chars)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
