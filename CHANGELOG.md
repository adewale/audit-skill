# Changelog

All notable changes to Audit Skill are documented in this file.

## [Unreleased]

### Changed

- Shortened the `SKILL.md` description from 1,064 to 1,007 characters (the Agent Skills limit is 1,024) and added `scripts/check_skill_frontmatter.py` to CI.
- `has-severity-verdict` eval assertions now require each case's expected verdict instead of accepting any label, with oracle self-tests in `tests/test_verdict_oracles.py`.
- Pinned the shared eval harness to `==0.6.0` and run its model-free manifest gate in CI; trigger cases declare `should_trigger`.

### Removed

- The committed `audit-skill.skill` bundle, a stale March 2026 snapshot of the whole repository (including `.git/` and `.claude/settings.local.json`). `scripts/check_install_boundary.py` now also scans every `*.skill`/`*.zip` in the repo and fails unless it is an exact copy of a declared skill directory.

## [1.0.2] - 2026-06-13

### Changed

- Removed the duplicate root `SKILL.md`; `skills/audit/SKILL.md` is now the only installable skill entrypoint.
- Updated package and Claude plugin metadata to point at the narrow `./skills/audit` skill directory.
- Added a package `files` allowlist so eval workspaces, run artifacts, and repo-only files are not included in install bundles.

## [1.0.0] - 2026-03-09

### Added

- **Branch audit** (default) with 8-category pre-push checklist and Clean/Minor/Blocking verdicts
  - Secrets and credentials
  - Unintended changes
  - Debug artifacts
  - Test coverage
  - Build and suite
  - Commit hygiene
  - Integration check
  - Merge conflicts and rebase state
- **13 deep-dive audits** run via sub-agents
  - Code quality (duplication, inconsistency, simplification)
  - Documentation brittleness (fragile refs, over-spec, staleness risk)
  - Documentation-code sync (API, setup, architecture, config, examples)
  - Language best practices (Python, JS/TS, Go, Rust, Java, Ruby, Shell)
  - Concurrency (shared state, race conditions, deadlock, thread leaks)
  - Resource management (file handles, connections, subprocesses, temp files)
  - Test quality (weak assertions, flakiness, isolation, negative tests)
  - Feature completeness (documented vs implemented)
  - Performance (N+1 queries, unbounded caches, hot-path allocations, blocking I/O)
  - Bug patterns (shallow merges, serialization, silent data loss, stale closures)
  - Design philosophy compliance (evaluate against project's stated principles)
  - Security vulnerabilities (injection, auth, data exposure, dependencies, config)
  - UI design (CRAP principles: Contrast, Repetition, Alignment, Proximity)
- Secret redaction guidance to prevent credential exposure in audit reports
- Plugin marketplace configuration (`.claude-plugin/`)
- Eval workspace with 3 iterations of benchmark data (93-100% pass rates)
- MIT license

[1.0.2]: https://github.com/adewale/audit-skill/releases/tag/v1.0.2
[1.0.0]: https://github.com/adewale/audit-skill/releases/tag/v1.0.0
