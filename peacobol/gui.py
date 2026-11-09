"""Desktop GUI for PeaCOBOL project management."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from typing import Optional

from .auth import authenticate
from .i18n import I18N
from .ui_components import ErrorDialog, ResultFrame, StatusLabel


class PeaCOBOLGUI:
    WORKBENCHES = [
        ("scan", "Scan COBOL source"),
        ("assure", "Analyze COBOL source"),
        ("diagnose", "Diagnose spool output"),
        ("impact", "Compare copybooks"),
        ("tests", "Generate test cases"),
        ("golden", "Golden-master compare"),
        ("coverage", "Import coverage data"),
        ("resources", "Inventory DB2/CICS/MQ"),
        ("db2", "DB2 compatibility check"),
        ("sbom", "Create SBOM"),
    ]

    def __init__(self, root: tk.Tk, project_root: Optional[Path] = None):
        self.root = root
        self.project_root = project_root or Path.cwd()
        self.current_view = None
        self.i18n = I18N()
        self.result_frame = None
        self.token = None
        self.status_label = StatusLabel(root)
        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Card", borderwidth=1, padding=8, font=("Segoe UI", 10))
        style.configure("Title", font=("Segoe UI", 13, "bold"))
        style.configure("Badge", font=("Segoe UI", 9, "bold"))

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text=self.i18n.get("title"), style="Title").pack(fill=tk.X, pady=(0, 10))

        toolbar = ttk.Frame(main)
        toolbar.pack(fill=tk.X, pady=(0, 6))

        ttk.Button(toolbar, text="Open Project", command=self._open_project).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="New Project", command=self._create_project).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="Exit", command=self.root.quit).pack(side=tk.RIGHT)

        sidebar = ttk.Frame(main, relief="groove", bd=1, style="Card")
        sidebar.pack(fill=tk.Y, side=tk.LEFT, pady=(0, 6), expand=True)

        projects_frame = ttk.LabelFrame(sidebar, text=self.i18n.get("project"), style="Card")
        projects_frame.pack(fill=tk.BOTH, pady=(0, 6), padx=5)
        self.project_listbox = tk.Listbox(projects_frame, height=8, selectmode=tk.SINGLE,
                                          font=("Segoe UI", 10))
        self.project_listbox.pack(fill=tk.BOTH, pady=3)

        for view, desc in self.WORKBENCHES:
            ttk.Label(sidebar, text=f"{view}: {desc}", font=("Segoe UI", 9)).pack(anchor=tk.W, padx=10, pady=2)

        self.status_bar = ttk.Label(main, text=self.i18n.get("ready"),
                                    relief="sunken", anchor="w", style="Card")
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))

    # ---- Project management ----

    def _refresh_projects(self):
        if not self.project_root or not self.project_root.is_dir():
            return
        projs = []
        for r, _d, fs in self.project_root.rglob("*"):
            if r.is_dir() and r != self.project_root:
                continue
            for f in fs:
                if f.suffix in (".cbl", ".cob", ".copybook"):
                    projs.append(str(r / f))
        self.project_listbox.delete(*self.project_listbox.get(0, tk.END))
        for p in projs:
            self.project_listbox.insert(tk.END, p)

    # ---- Result display ----

    def _show_json(self, result, title: str = "Result"):
        if self.result_frame:
            try:
                self.result_frame.destroy()
            except Exception:
                pass
        import json
        self.result_frame = ResultFrame(self.root, title=title)
        if isinstance(result, dict):
            self.result_frame.display_json(result)
        else:
            self.result_frame.display_json({"ok": bool(result)})

    def _clear_results(self):
        if self.result_frame:
            try:
                self.result_frame.destroy()
            except Exception:
                pass
            self.result_frame = None

    # ---- Workbench entry points (local mode) ----

    def _run_local(self, func, *args, **kwargs):
        try:
            result = func(*args, **kwargs)
            self._show_json(result)
            self.status_bar.config(text=self.i18n.get("success"))
        except Exception as e:
            ErrorDialog(self.root, title=self.i18n.get("error"), message=e)
            self.status_bar.config(text=self.i18n.get("error"))

    # ---- Workbench entry points (network mode) ----

    def _run_network(self, endpoint: str, payload: dict):
        if not self.token:
            return self._run_local(lambda: {{"skipped": True, "error": "No authentication token"}} if False else {})
        try:
            resp = self._http_post(endpoint, payload)
            self._show_json(resp)
            self.status_bar.config(text=self.i18n.get("success"))
        except Exception as e:
            ErrorDialog(self.root, title=self.i18n.get("error"), message=e)
            self.status_bar.config(text=self.i18n.get("error"))

    def _switch_view(self, view: str):
        if self.current_view == view and self.result_frame:
            self._clear_results()
            return
        self.current_view = view
        self.status_label.set_text(view)
        self._clear_results()

    # ---- High-level workbench methods ----

    def workbench_scan(self, path: str = "."):
        self._run_local(lambda: __import__("peacobol.core", fromlist=["scan_project"]).scan_project(Path(path)))

    def workbench_assurance(self, path: str = ".", fail_on: str = "none"):
        self._run_local(lambda: __import__("peacobol.assurance", fromlist=["analyze_assurance"]).analyze_assurance(Path(path), fail_on))

    def workbench_diagnostics(self, path: str = ".", spool: str = "failure.log"):
        self._run_local(lambda: __import__("peacobol.investigation", fromlist=["failure_bundle"]).failure_bundle(Path(path), Path(spool)))

    def workbench_impact(self, before: str, after: str):
        self._run_local(lambda: __import__("peacobol.impact", fromlist=["compare_copybooks"]).compare_copybooks(Path(before), Path(after)))

    def workbench_tests(self, copybook: str, encoding: str = "ascii"):
        self._run_local(lambda: __import__("peacobol.testworkbench", fromlist=["generate_cases"]).generate_cases(Path(copybook), encoding))

    def workbench_golden(self, actual: str, expected: str):
        self._run_local(lambda: __import__("peacobol.testworkbench", fromlist=["compare_golden"]).compare_golden(Path(actual), Path(expected)))

    def workbench_resources(self, path: str = "."):
        self._run_local(lambda: __import__("peacobol.enterprise", fromlist=["resource_inventory"]).resource_inventory(Path(path)))

    def workbench_db2(self, copybook: str, ddl: str):
        self._run_local(lambda: __import__("peacobol.enterprise", fromlist=["db2_compatibility"]).db2_compatibility(Path(copybook), Path(ddl)))

    def workbench_sbom(self, path: str = "."):
        self._run_local(lambda: __import__("peacobol.supplychain", fromlist=["sbom"]).sbom(Path(path)))

    def workbench_attest(self, file: str, verify: bool = False):
        from peacobol.supplychain import attest, verify_attestation
        self._run_local(lambda: self._do_attest(file, verify))

    def _do_attest(self, file: str, verify: bool):
        envelope = attest(Path(file))
        if verify:
            return verify_attestation(envelope)
        return envelope

    def workbench_immutable_export(self, files: list, output: str):
        from peacobol.supplychain import immutable_export
        self._run_local(lambda: immutable_export(files, Path(output)))

    # ---- Auth ----

    def request_token(self):
        self.token = authenticate()
        return self.token


def start_gui(project_root=None):
    """Public entry point for launching the desktop GUI."""
    import tkinter as _tk
    from pathlib import Path
    root = _tk.Tk()
    root.title("PeaCOBOL Project Manager")
    app = PeaCOBOLGUI(root, project_root=project_root)
    auth = authenticate(app)
    if auth:
        app.request_token()
    root.mainloop()
