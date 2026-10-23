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
            'Invoke-Git push origin main',
            'WriteAllText',
        ):
            with self.subTest(required=required):
                self.assertIn(required, source)

    def test_png_dimensions_use_full_big_endian_values(self):
        # Previously Windows PowerShell returned 46x22 for 1070x790:
        # the first three bytes had been lost by byte-sized -shl.
        src = SCRIPT.read_text(encoding="ascii")
        self.assertNotIn("-shl", src)
        self.assertIn("([uint64]$Data[$Offset + 2] * 256)", src)
        import re
        import shutil
        import subprocess

        shell = next((exe for exe in ("pwsh", "powershell.exe", "powershell")
                      if shutil.which(exe)), None)
        if shell is None:
            self.skipTest("PowerShell not installed here")
        match = re.search(r"(?ms)^function Read-UInt32BE\([^\n]+\) \{.*?^\}", src)
        self.assertIsNotNone(match)
        header = [137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 13,
                  73, 72, 68, 82, 0, 0, 4, 46, 0, 0, 3, 22]
        command = (match.group(0) + "; $Data = [byte[]](" +
                   ",".join(map(str, header)) +
                   "); Write-Output ((Read-UInt32BE $Data 16).ToString() + ',' + " +
                   "(Read-UInt32BE $Data 20).ToString())")
        result = subprocess.run([shell, "-NoProfile", "-Command", command],
                                capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), "1070,790")


if __name__ == "__main__":
    unittest.main()
