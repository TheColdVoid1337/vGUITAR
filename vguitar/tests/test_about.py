"""Regression tests for About resources without requiring a GUI display."""
import unittest

from vguitar_about import AUTHOR, AUTHOR_URL, REPOSITORY_URL, ICON_PATH, app_version


class AboutMetadataTests(unittest.TestCase):
    def test_version_uses_root_version_file(self):
        self.assertEqual(app_version(), "0.5.5")

    def test_links_point_to_project(self):
        self.assertEqual(AUTHOR, "TheColdVoid1337")
        self.assertEqual(AUTHOR_URL, "https://github.com/TheColdVoid1337")
        self.assertEqual(REPOSITORY_URL, "https://github.com/TheColdVoid1337/vGUITAR")

    def test_icon_is_a_square_png(self):
        contents = ICON_PATH.read_bytes()
        self.assertEqual(contents[:8], b"\x89PNG\r\n\x1a\n")
        width = int.from_bytes(contents[16:20], "big")
        height = int.from_bytes(contents[20:24], "big")
        self.assertEqual(width, height)
        self.assertGreaterEqual(width, 128)


if __name__ == "__main__":
    unittest.main()
