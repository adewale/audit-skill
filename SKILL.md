---
name: audit
description: >
  Systematic pre-push branch audit with an 8-category security and quality checklist
  (secrets, unintended changes, debug artifacts, test coverage, build validation,
  commit hygiene, integration checks, merge conflicts) that produces a structured
  report with Clean/Minor/Blocking verdicts. ALWAYS use this skill when the user wants
  to review their branch before pushing, check what they're about to push, audit their
  changes, do a pre-push check, sanity-check before a PR, look over their diff, or
  verify their branch is ready to merge. This includes any request to review local
  branch changes for issues, sweep a branch for problems, or get a final check before
  code leaves the machine — even if the user doesn't use the word "audit" explicitly.
---

# Audit

A manual, on-demand review of all changes on the current branch before they leave
your machine. This is not an incremental check — it's a holistic sweep of the entire
branch delta, the kind of review you'd do yourself before opening a PR.

---

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
