---
name: audit
description: >
  Systematic audit toolkit for code, docs, security, and UI. Includes a pre-push
  branch audit (8-category checklist with Clean/Minor/Blocking verdicts) plus six
  deep-dive audits: code quality (duplication, inconsistency, simplification),
  documentation brittleness, documentation–code sync, language best practices,
  security vulnerability analysis, and UI design review using CRAP principles.
  ALWAYS use this skill when the user wants to audit, review before pushing, check
  their branch, sanity-check before a PR, look for duplication or dead code, check
  docs are up to date, review code against best practices, analyse security
  vulnerabilities, review UI design, or apply design principles — even if they
  don't say "audit" explicitly.
---

# Audit

This skill provides two modes:

1. **Branch audit** (default) — a pre-push review of the branch diff, checking 8
   categories and producing a Clean/Minor/Blocking verdict.
2. **Deep-dive audits** — project-wide analyses that use sub-agents to examine
   code quality, documentation brittleness, security, or UI design in depth.

If the user says "audit" without further context and there's a branch with changes,
run the branch audit. If they ask for something specific (e.g., "audit for security
vulnerabilities", "check our docs", "review the UI"), run the relevant deep-dive.
They can also request multiple audits at once.

---

# Branch Audit

## Step 1: Gather context

Determine the base branch (`main`, `master`, or the upstream tracking branch), then:

1. Run `git diff <base>...HEAD` to get the full branch diff
2. Run `git diff` and `git diff --cached` for any uncommitted/staged changes
3. Run `git log --oneline <base>..HEAD` to see the commit list
4. Note which files changed and what the branch is trying to accomplish

Start your report with a brief **branch summary**: branch name, base, number of
commits, and a one-sentence description of the purpose of the changes.

## Step 2: Audit each category

Work through each category below. Report only categories that have findings — omit
categories with nothing to report (don't include "No findings" sections).

Each finding should appear once. If something could fit multiple categories, put it
in the most relevant one and don't repeat it elsewhere.

### Secrets and credentials

Check this first — it's the most critical category.

- API keys, tokens, passwords, connection strings in the diff
- Private keys or certificates
- `.env` files or equivalents staged for commit
- Hard-coded URLs pointing to internal/staging environments

### Unintended changes

- Files modified that don't relate to the branch's purpose (infer the purpose from
  the branch name, commit messages, and the bulk of the diff)
- Formatting-only diffs in files the branch didn't otherwise need to touch
- Changes to generated files (lock files are fine if dependencies changed)

Be specific: name each file you think is unrelated and explain why.

### Debug artifacts

- `console.log`, `debugger`, `print()`, `pp`, `binding.pry`, `dbg!` left in
  production code (test files are fine)
- Commented-out code blocks (small explanatory comments are fine)
- `TODO`, `FIXME`, `HACK`, `XXX` introduced in this branch

### Test coverage

- New or modified production code without corresponding test changes
- Skipped or disabled tests (`.skip`, `@pytest.mark.skip`, `#[ignore]`)
- Test files that import but don't exercise new code paths

### Build and suite

Try to run the project's test suite, linter, and type checker. If the project
doesn't have the tooling set up, or dependencies aren't installed, note that and
move on — don't spend time troubleshooting environment issues. Report what you can.

### Commit hygiene

- Commit messages that don't follow the project's conventions
- Fixup commits that should be squashed
- Commits containing unrelated changes that should be split

### Integration check

- New modules that aren't imported anywhere
- New routes or endpoints that aren't registered
- New migrations that aren't referenced
- New dependencies that are imported but not declared in the project's dependency file

### Merge conflicts and rebase state

- Unresolved conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)
- Stale branch: base branch has moved significantly since branch point

## Step 3: Verdict

End with a summary table of findings (file, line, issue, severity) and one of
these verdicts:

- **Clean** — no findings, safe to push
- **Minor** — cosmetic or low-risk issues found (list them), push at your discretion
- **Blocking** — issues that should be fixed before pushing (list them)

Secrets and unresolved conflict markers are always Blocking. Debug artifacts and
missing tests are Blocking. TODO/FIXME comments, commit hygiene, and minor
integration issues are typically Minor.

If the user asks you to fix any findings, fix them. Otherwise, just report.

---

# Deep-Dive Audits

Each deep-dive audit should be delegated to a sub-agent so it can explore the
codebase thoroughly without bloating the main conversation. Launch them in parallel
when multiple are requested. Each sub-agent should produce a written report saved
to a file, then summarize the key findings back to the user.

## Code quality audit

Spawn a sub-agent to audit the project for:

- **Duplication** — repeated logic, copy-pasted code blocks, near-identical
  functions or components that could be consolidated
- **Internal inconsistency** — naming conventions that vary across files, mixed
  patterns (e.g., callbacks in some places, promises in others), conflicting
  approaches to the same problem
- **Simplification and subtraction** — dead code, unused exports, over-abstracted
  layers that add indirection without value, features or config that nobody uses.
  The goal is to identify things that can be removed or simplified. Less code is
  better code — every line is a liability.

The report should group findings by theme (not by file) and suggest concrete actions.

## Documentation brittleness audit

Spawn a sub-agent to audit documentation (READMEs, doc comments, guides, wikis,
SKILL.md files, onboarding docs) for:

- **Fragile references** — line numbers, specific function signatures, or exact
  file paths that will break when code changes. Prefer linking to symbols, sections,
  or concepts instead.
- **Over-specified details** — documentation that mirrors the code so closely that
  any refactor makes the docs wrong. Good docs explain *why* and *how to use*,
  not *what each line does*.
- **Staleness risk** — instructions that reference specific versions, temporary
  workarounds, or "current" states that will age poorly. Flag anything that reads
  like it was written for a moment in time rather than for the long term.

The report should recommend specific rewrites, not just flag problems.

## Documentation–code sync audit

Spawn a sub-agent to verify that documentation actually matches the current state
of the code. The brittleness audit (above) asks whether docs *will* break — this
one asks whether they *already have*.

- **API docs vs implementation** — do documented endpoints, parameters, return
  types, and error codes match what the code actually does? Check REST routes,
  GraphQL schemas, CLI flags, library APIs.
- **Setup and install instructions** — do the steps in the README or getting-started
  guide actually work? Are prerequisites listed correctly? Are environment variables
  documented that the code actually reads?
- **Architecture descriptions** — do diagrams or written descriptions of the system
  architecture reflect the current module structure, data flow, and dependencies?
  Flag components described in docs that no longer exist, and components in code
  that docs don't mention.
- **Config and feature flags** — are all configuration options documented? Are there
  documented options that the code no longer reads, or code that reads undocumented
  config?
- **Examples and code snippets** — do inline examples in docs compile/run against
  the current codebase? Flag examples that use deprecated APIs or deleted functions.

For each discrepancy, show the doc excerpt and the conflicting code side by side,
and recommend which one should change.

## Language best practices audit

Spawn a sub-agent to review the codebase against idiomatic best practices for
each programming language used in the project. The agent should first identify
which languages are present, then check each against its community standards:

- **Python** — PEP 8 style, type hints on public APIs, context managers for
  resources, dataclasses/attrs over raw dicts, avoiding mutable default arguments,
  proper use of `__init__.py`, virtual environments
- **JavaScript/TypeScript** — strict mode, `const`/`let` over `var`, async/await
  over raw promises, proper error handling in async code, avoiding `any` in TS,
  ESM over CommonJS where appropriate
- **Go** — error handling (no ignored errors), proper use of goroutines and channels,
  effective Go naming conventions, avoiding package-level state, using `context.Context`
- **Rust** — ownership patterns, avoiding unnecessary `clone()`, proper error types
  over `unwrap()`, using `clippy` suggestions, derive macros for common traits
- **Java/Kotlin** — null safety, resource management (try-with-resources), immutable
  collections where possible, avoiding raw types, proper logging frameworks
- **Ruby** — Ruby style guide conventions, frozen string literals, proper use of
  blocks/procs/lambdas, avoiding monkey-patching in production code
- **Shell** — `set -euo pipefail`, quoting variables, avoiding eval, using `shellcheck`
  patterns

Only audit languages actually present in the project. The report should distinguish
between style preferences (informational) and genuine anti-patterns that cause bugs
or maintenance burden (actionable). Focus on the actionable ones.

## Security vulnerability audit

Spawn a sub-agent to step back from the current task and analyse the codebase for
security vulnerabilities. This is not the quick secrets-in-diff check from the
branch audit — it's a deeper review of the project's security posture:

- **Injection** — SQL injection, command injection, XSS, template injection.
  Trace user input from entry points through to database queries, shell commands,
  and rendered output.
- **Authentication and authorization** — missing auth checks on sensitive endpoints,
  insecure session handling, hardcoded credentials, weak password policies
- **Data exposure** — sensitive data in logs, error messages that leak internals,
  overly permissive API responses, missing field-level access control
- **Dependency risks** — known vulnerable packages, outdated dependencies with
  published CVEs, unnecessary dependencies that increase attack surface
- **Configuration** — debug mode enabled in production config, permissive CORS,
  missing security headers, insecure defaults

The report should rate each finding by severity (Critical/High/Medium/Low) with
the affected file and a recommended fix.

## UI design audit (CRAP principles)

Spawn a sub-agent to review the project's UI using Robin Williams' four
fundamental design principles — **Contrast, Repetition, Alignment, and Proximity**
(CRAP). This applies to web interfaces, CLI output, terminal UIs, documentation
layouts, or any visual/textual output the project produces.

- **Contrast** — Are different elements visually distinct? Do headings stand out
  from body text? Are interactive elements (buttons, links) clearly differentiated
  from static content? Is there enough contrast between foreground and background?
  Weak contrast makes interfaces feel flat and hard to scan.
- **Repetition** — Is there a consistent visual language? Are colors, fonts, spacing,
  and component styles reused consistently throughout? Repetition creates unity — if
  every page/screen uses different styling, the interface feels disjointed.
- **Alignment** — Is every element visually connected to something else on the page?
  Nothing should be placed arbitrarily. Check for elements that are "almost but not
  quite" aligned — these are worse than clearly different placements because they
  look like mistakes.
- **Proximity** — Are related items grouped together? Are unrelated items separated?
  Physical closeness implies relationship. Check for cases where labels are far from
  their fields, or where unrelated controls are clustered together.

The report should include specific examples with file paths and, where possible,
screenshots or descriptions of the visual issues. Suggest concrete improvements
for each finding.
