"""Check terminal input without connecting to AWS."""

import importlib
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch


class TerminalInputTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        source_directory = Path(__file__).resolve().parents[1] / "src"
        sys.path.insert(0, str(source_directory))
        try:
            cls.module = importlib.import_module("architecture_review.mcp_probe")
        finally:
            sys.path.pop(0)

    def test_description_is_trimmed_and_passed_to_probe(self) -> None:
        with (
            patch("builtins.input", return_value="  EC2 with a public RDS database  "),
            patch("builtins.print"),
            patch.object(self.module, "probe", new_callable=AsyncMock) as probe,
        ):
            self.assertEqual(self.module.main(), 0)
            probe.assert_awaited_once_with("EC2 with a public RDS database")

    def test_blank_input_does_not_start_probe(self) -> None:
        with (
            patch("builtins.input", return_value="   "),
            patch("builtins.print"),
            patch.object(self.module, "probe", new_callable=AsyncMock) as probe,
            self.assertLogs(level="ERROR"),
        ):
            self.assertEqual(self.module.main(), 1)
            probe.assert_not_called()

    def test_cancelled_input_does_not_start_probe(self) -> None:
        for error in (EOFError, KeyboardInterrupt):
            with (
                self.subTest(error=error.__name__),
                patch("builtins.input", side_effect=error),
                patch("builtins.print"),
                patch.object(self.module, "probe", new_callable=AsyncMock) as probe,
            ):
                self.assertEqual(self.module.main(), 1)
                probe.assert_not_called()
