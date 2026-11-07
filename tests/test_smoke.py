"""Smoke test for the source package without requiring installation."""

import importlib
from pathlib import Path
import sys
import unittest


class PackageImportTest(unittest.TestCase):
    def test_application_package_can_be_imported(self) -> None:
        source_directory = Path(__file__).resolve().parents[1] / "src"
        sys.path.insert(0, str(source_directory))
        try:
            package = importlib.import_module("architecture_review")
            self.assertEqual(
                Path(package.__file__).resolve(),
                source_directory / "architecture_review" / "__init__.py",
            )
        finally:
            sys.path.pop(0)
