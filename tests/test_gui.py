"""Automated tests for the PeaCOBOL desktop GUI layer (1.1.0).

These tests are headless-safe: they never call mainloop() and never
require a display, exercising import wiring, i18n, and background
task dispatch instead.
"""

import tempfile
import threading
import time
import unittest
from pathlib import Path

from peacobol.gui import PeaCOBOLGUI, WORKBENCH_KEYS
from peacobol.i18n import I18N
from peacobol.network import TaskRunner, NetworkError
from peacobol import ui_components


class ImportWiringTests(unittest.TestCase):
    def test_package_exports_gui_api(self):
        import peacobol
        self.assertTrue(hasattr(peacobol, "PeaCOBOLGUI"))
        self.assertTrue(hasattr(peacobol, "start_gui"))

    def test_workbench_keys_cover_all_ten_views(self):
        self.assertEqual(len(WORKBENCH_KEYS), 10)
        for key in ("scan", "assure", "diagnose", "impact", "tests",
                    "golden", "coverage", "resources", "db2", "sbom"):
            self.assertIn(key, WORKBENCH_KEYS)

    def test_ui_components_define_required_widgets(self):
        for name in ("ProgressBar", "StatusLabel", "ErrorDialog", "ResultFrame"):
            self.assertTrue(hasattr(ui_components, name), name)


class I18NTests(unittest.TestCase):
    def test_default_language_english(self):
        i18n = I18N()
        self.assertEqual(i18n.get("ready"), "Ready")
        self.assertEqual(i18n.get("title"), "PeaCOBOL Project Manager")

    def test_switch_language_translates_keys(self):
        i18n = I18N()
        i18n.set_language("Spanish")
        self.assertNotEqual(i18n.get("ready"), "Ready")
        i18n.set_language("Unknown")
        self.assertEqual(i18n.get("ready"), "Ready")

    def test_unknown_key_falls_back_to_key_name(self):
        i18n = I18N()
        self.assertEqual(i18n.get("no_such_key"), "no_such_key")

    def test_all_supported_languages_define_title(self):
        from peacobol.i18n import _TRANSLATIONS
        for language, table in _TRANSLATIONS.items():
            self.assertIn("title", table, language)


class TaskRunnerTests(unittest.TestCase):
    def setUp(self):
        self.passed = threading.Event()
        self.failed = threading.Event()
        self.result = None
        self.error = None

    def _on_done(self, value):
        self.result = value
        self.passed.set()

    def _on_error(self, exc):
        self.error = exc
        self.failed.set()

    def test_success_callback_marshals_value(self):
        runner = TaskRunner(None, self._on_done, self._on_error)
        # Patch root.after to execute immediately (headless mode).
        runner.root = type("FakeRoot", (), {"after": staticmethod(lambda delay, fn: fn())})()
        runner.submit(lambda: {"ok": True})
        self.assertTrue(self.passed.wait(5))
        self.assertEqual(self.result, {"ok": True})

    def test_error_callback_marshals_exception(self):
        runner = TaskRunner(None, self._on_done, self._on_error)
        runner.root = type("FakeRoot", (), {"after": staticmethod(lambda delay, fn: fn())})()
        runner.submit(self._raise)
        self.assertTrue(self.failed.wait(5))
        self.assertIsInstance(self.error, ValueError)

    @staticmethod
    def _raise():
        raise ValueError("boom")

    def test_busy_flag_blocks_concurrent_submit(self):
        runner = TaskRunner(None, self._on_done, self._on_error)
        runner.root = type("FakeRoot", (), {"after": staticmethod(lambda delay, fn: fn())})()
        release = threading.Event()
        runner.submit(lambda: (release.wait(5), None))
        time.sleep(0.05)
        self.assertTrue(runner.busy)
        with self.assertRaises(RuntimeError):
            runner.submit(lambda: None)
        release.set()
        runner.wait(5)


class LocalModeTests(unittest.TestCase):
    def test_scan_resolves_to_callable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "A.cbl").write_text("       GOBACK.\n", encoding="utf-8")
            from peacobol.core import scan_project
            report = scan_project(root)
            self.assertIn("programs", report)


class NetworkErrorTests(unittest.TestCase):
    def test_network_error_is_exception(self):
        error = NetworkError("offline")
        self.assertEqual(str(error), "offline")


if __name__ == "__main__":
    unittest.main()
