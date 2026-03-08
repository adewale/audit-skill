# Audit Skill for Claude Code

A systematic audit toolkit for code, docs, security, and UI. Catches issues before you push.

## What it does

**Branch audit** (default) — Reviews your branch diff against 8 categories and gives a Clean/Minor/Blocking verdict:

- Secrets and credentials
- Unintended changes
- Debug artifacts
- Test coverage
- Build and suite
- Commit hygiene
- Integration check
- Merge conflicts and rebase state

**Deep-dive audits** — Project-wide analyses using sub-agents:

- **Code quality** — duplication, inconsistency, simplification opportunities
- **Documentation brittleness** — fragile references, over-specified details, staleness risk
- **Documentation-code sync** — docs that have already drifted from the code
- **Language best practices** — idiomatic patterns for Python, JS/TS, Go, Rust, Java, Ruby, Shell
- **Security vulnerabilities** — injection, auth, data exposure, dependency risks, config
- **UI design** — review using CRAP principles (Contrast, Repetition, Alignment, Proximity)

## Installation

Copy `SKILL.md` into your project's `.claude/skills/` directory:

```bash
mkdir -p .claude/skills/audit
cp SKILL.md .claude/skills/audit/SKILL.md
```

Or clone this repo and symlink:

```bash
git clone https://github.com/adewale/audit-skill.git
ln -s "$(pwd)/audit-skill/SKILL.md" your-project/.claude/skills/audit/SKILL.md
```

## Usage

The skill triggers automatically when you ask Claude Code to audit or review your work:

```
> audit
> review my changes before I push
> check what I'm about to push
> audit for security vulnerabilities
> review the UI design
> check our docs are up to date
```

## Example output

### Blocking verdict

```
## Summary

| #  | Category                | Finding                                        | Severity |
|----|-------------------------|------------------------------------------------|----------|
| 1  | Secrets and credentials | Live Stripe secret key hard-coded in source    | Blocking |
| 2  | Debug artifacts         | print() debug statement on line 7              | Blocking |
| 3  | Test coverage           | No tests for any new payment code              | Blocking |

Verdict: **Blocking** — issues that should be fixed before pushing.
```

### Clean verdict

```
Verdict: **Clean** — no findings, safe to push.
```

## Eval results

Tested across 3 scenarios (dirty branch, clean branch, mixed branch) with and without the skill:

| Configuration  | Pass rate | Avg time | Avg tokens |
|----------------|-----------|----------|------------|
| With skill     | 100%      | 100s     | 18,855     |
| Without skill  | 62%       | 94s      | 18,057     |

The skill's value is consistent structured output — Clean/Minor/Blocking verdicts, category-based reporting, and catching unrelated changes. Detection of issues like leaked keys and debug statements is similar either way since Claude is already good at finding problems. The skill ensures they're reported in a reliable, actionable format.

## License

MIT
