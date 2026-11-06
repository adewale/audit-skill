# Audit workspace

The dated iteration reports here are historical evidence. Their original local
test repositories were accidentally committed as four Gitlinks with no
`.gitmodules` fetch mapping. Those opaque pointers could not reconstruct the
source and also broke checkout's submodule authentication cleanup.

Create fresh repositories for exercising the current Git-state boundaries:

```sh
python scripts/create_audit_fixtures.py --output /tmp/audit-fixtures
```

The generator creates a clean main branch, an unstaged tracked edit, a feature
branch with an untracked file, and a repository with a small executable Python
test. It refuses to overwrite existing fixture paths. These are new maintained
fixtures, not reconstructions of the source behind the historical reports.
Review the generated behavior and source instead of refreshing commit hashes.
