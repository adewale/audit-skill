"""The generated fixtures expose Git states rather than opaque commit pins."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "audit_fixtures", Path(__file__).resolve().parents[1] / "scripts/create_audit_fixtures.py"
)
fixtures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixtures)


class FixtureRepositoriesTests(unittest.TestCase):
    def test_generated_repositories_have_the_promised_states(self):
        with tempfile.TemporaryDirectory() as directory:
            clean, dirty, mixed, deep = fixtures.create_fixtures(Path(directory))
            self.assertEqual(fixtures.git(clean, "status", "--porcelain"), "")
            self.assertIn("app.py", fixtures.git(dirty, "diff", "--name-only"))
            self.assertEqual(fixtures.git(mixed, "branch", "--show-current"), "feature")
            self.assertEqual(fixtures.git(mixed, "rev-list", "--count", "main..HEAD"), "1")
            self.assertIn("?? untracked.txt", fixtures.git(mixed, "status", "--porcelain"))
            self.assertEqual(fixtures.git(deep, "status", "--porcelain"), "")
            self.assertIn("test_app.py", fixtures.git(deep, "ls-files"))
            with self.assertRaises(ValueError):
                fixtures.create_fixtures(Path(directory))


if __name__ == "__main__":
    unittest.main()
