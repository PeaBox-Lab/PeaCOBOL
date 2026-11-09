"""Headless tests for the theme manager and result export (0.9.x)."""

import json
import tempfile
import threading
import unittest
from pathlib import Path

from peacobol.theme import ThemeManager, THEMES, available_themes, available_font_scales
from peacobol.exportui import export_report, list_exports
from peacobol.audit import verify_log


class ThemeManagerTests(unittest.TestCase):
    def test_all_themes_have_required_colors(self):
        for name, palette in THEMES.items():
            for key in ("bg", "fg", "card", "border", "accent", "status_ok", "status_error"):
                self.assertIn(key, palette, f"{name}.{key}")
                self.assertTrue(palette[key].startswith("#"), f"{name}.{key}")

    def test_invalid_theme_is_rejected(self):
        with self.assertRaises(ValueError):
            ThemeManager("neon")

    def test_invalid_font_scale_is_rejected(self):
        with self.assertRaises(ValueError):
            ThemeManager("light", "gigantic")

    def test_font_scale_steps_are_clamped(self):
        from peacobol.theme import FONT_SCALES
        manager = ThemeManager("light", "normal")
        self.assertEqual(manager.scale_font(-99), min(FONT_SCALES.values()))
        manager = ThemeManager("light", "normal")
        self.assertEqual(manager.scale_font(+99), max(FONT_SCALES.values()))

    def test_available_theme_and_scale_lists(self):
        self.assertIn("dark", available_themes())
        scales = available_font_scales()
        self.assertEqual(scales[0], "small")
        self.assertEqual(scales[-1], "extra-large")

    def test_high_contrast_flag(self):
        self.assertTrue(ThemeManager("high-contrast").high_contrast)
        self.assertFalse(ThemeManager("light").high_contrast)


class ExportTests(unittest.TestCase):
    def test_export_writes_report_and_audits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = export_report(root, "scan", {"ok": True, "findings": []})
            self.assertTrue(path.is_file())
            self.assertEqual(path.relative_to(root).as_posix(), "reports/gui/scan.json")
            written = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(written["ok"])
            audit = root / ".peacobol" / "audit.jsonl"
            self.assertTrue(verify_log(audit)["ok"])

    def test_export_rejects_missing_project(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "nowhere"
            with self.assertRaises(NotADirectoryError):
                export_report(missing, "scan", {"ok": True})

    def test_export_rejects_oversized_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            huge = {"blob": "x" * (11 * 1024 * 1024)}
            with self.assertRaises(ValueError):
                export_report(root, "scan", huge)

    def test_exports_are_listed_newest_first(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            export_report(root, "scan", {"one": True})
            export_report(root, "sbom", {"two": True})
            listed = list_exports(root)
            self.assertEqual([item["view"] for item in listed], ["sbom", "scan"])
            self.assertEqual(list_exports(root / "empty"), [])

    def test_export_atomic_replace_leaves_no_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = export_report(root, "coverage", {"percent": 50})
            self.assertTrue(path.is_file())
            leftovers = list((root / "reports" / "gui").glob("*.tmp"))
            self.assertEqual(leftovers, [])


class GuiExportIntegrationTests(unittest.TestCase):
    """Verify the GUI save handler delegates to export_report (headless)."""

    def test_save_without_result_reports_hint(self):
        from peacobol.gui import PeaCOBOLGUI
        import tkinter as tk

        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("No display available in this environment")
            return
        try:
            with tempfile.TemporaryDirectory() as directory:
                app = PeaCOBOLGUI(root, project_root=Path(directory))
                app._save_result()
                self.assertIn("Run a workbench first", app.status_bar.cget("text"))
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
