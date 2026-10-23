"""Regression checks for screenshot publishing scripts.

Windows PowerShell 5.1 decodes UTF-8 .ps1 files without BOM using the active
ANSI code page; non-ASCII script literals previously caused a parser failure.
"""
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publish_screenshot.ps1"


class ScreenshotPublishingScriptTests(unittest.TestCase):
    def test_powershell_5_1_safe_ascii_source(self):
        raw = SCRIPT.read_bytes()
        self.assertTrue(raw.isascii(), "The script must be ASCII for Windows PowerShell 5.1")

    def test_screenshot_and_bilingual_readme_steps_present(self):
        source = SCRIPT.read_text(encoding="ascii")
        for required in (
            'screenshot-main.png',
            'README.md',
            'README.en.md',
            'git diff --cached --name-only',
            'git push origin main',
            'WriteAllText',
        ):
            with self.subTest(required=required):
                self.assertIn(required, source)


if __name__ == "__main__":
    unittest.main()
