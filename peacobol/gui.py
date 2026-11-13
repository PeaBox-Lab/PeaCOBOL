"""Desktop GUI for PeaCOBOL project management.

Features
--------
- Local workbench execution on background threads (UI stays responsive).
- Progress indicators while a workbench is running.
- Bilingual UI strings through the i18n layer.
- Optional server mode through the loopback NetworkClient.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path
from typing import Optional

from .auth import authenticate
from .i18n import I18N
from .network import NetworkClient, TaskRunner
from .theme import ThemeManager, available_font_scales, available_themes
from .ui_components import ErrorDialog, ResultFrame, StatusLabel
from .exportui import export_report


WORKBENCH_KEYS = ("scan", "assure", "diagnose", "impact", "tests",
                  "golden", "coverage", "resources", "db2", "sbom")


class PeaCOBOLGUI:
    """Main application window with workbench execution."""

    WORKBENCHES = [
        ("scan", 1),
        ("assure", 1),
        ("diagnose", 2),
        ("impact", 2),
        ("tests", 1),
        ("golden", 2),
        ("coverage", 2),
        ("resources", 1),
        ("db2", 2),
        ("sbom", 1),
    ]

    def __init__(self, root: tk.Tk, project_root: Optional[Path] = None):
        self.root = root
        self.project_root = project_root or Path.cwd()
        self.i18n = I18N()
        self.theme = ThemeManager()
        self.result_frame: Optional[ResultFrame] = None
        self._last_result: Any = None
        self.token: Optional[str] = None
        self.current_view: Optional[str] = None
        self._runner: Optional[TaskRunner] = None
        self._apply_theme()
        self._build_ui()

    # ---------- theming ----------

    def _apply_theme(self):
        from tkinter import font as tkfont
        self.root.configure(bg=self.theme.colors["bg"])
        self.theme.apply(self.root)
        base = tkfont.Font(family=self.theme.font_family, size=self.theme.font_size)
        self.root.option_add("*Font", (self.theme.font_family, self.theme.font_size))
        self._base_font = base

    def cycle_theme(self):
        theme_names = available_themes()
        index = (theme_names.index(self.theme._theme) + 1) % len(theme_names)
        self.theme = ThemeManager(theme_names[index], self.theme._font_scale)
        self._apply_theme()
        self.status_bar.config(text=f"Theme: {theme_names[index]}")

    def bump_font(self, step: int):
        size = self.theme.scale_font(step)
        self._apply_theme()
        self.status_bar.config(text=f"Font size: {size}")

    # ---------- styling ----------

    def _setup_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Card", borderwidth=1, padding=8, font=("Segoe UI", 10))
        style.configure("Title", font=("Segoe UI", 13, "bold"))
        style.configure("Status.Success.TLabel", foreground="#087f5b")
        style.configure("Status.Error.TLabel", foreground="#c92a2a")

    # ---------- layout ----------

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text=self.i18n.get("title"), font=("Segoe UI", 14, "bold")).pack(fill=tk.X, pady=(0, 10))

        toolbar = ttk.Frame(main)
        toolbar.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(toolbar, text="Open Directory", command=self._open_directory).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="Theme", command=self.cycle_theme).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="A+", command=lambda: self.bump_font(+1)).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="A-", command=lambda: self.bump_font(-1)).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="Save Result", command=self._save_result).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="Exit", command=self.root.quit).pack(side=tk.RIGHT)

        body = ttk.Frame(main)
        body.pack(fill=tk.BOTH, expand=True)

        # Sidebar: workbench buttons
        sidebar = ttk.LabelFrame(body, text="Workbenches")
        sidebar.pack(fill=tk.Y, side=tk.LEFT, padx=(0, 10))
        for view, _arg_count in self.WORKBENCHES:
            button = ttk.Button(sidebar, text=view.title(), width=18,
                                command=lambda v=view: self._launch(v))
            button.pack(anchor=tk.W, padx=6, pady=3)

        # Right side: results area
        self._results_host = ttk.Frame(body)
        self._results_host.pack(fill=tk.BOTH, side=tk.LEFT, expand=True)

        # Progress + status bar
        self.progress = ttk.Progressbar(main, mode="indeterminate", length=200)
        self.status_bar = ttk.Label(main, text=self.i18n.get("ready"),
                                    relief="sunken", anchor="w")
        self.progress.pack(fill=tk.X, side=tk.BOTTOM, pady=(4, 0))
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(4, 0))
        self.progress.pack_forget()  # hidden until a task runs

    # ---------- project management ----------

    def _open_directory(self):
        directory = filedialog.askdirectory(title=self.i18n.get("select_project"),
                                            initialdir=str(self.project_root))
        if directory:
            self.project_root = Path(directory).resolve()
            self.status_bar.config(text=f"{self.i18n.get('ready')} — {self.project_root.name}")

    # ---------- workbench execution ----------

    @property
    def runner(self) -> TaskRunner:
        if self._runner is None:
            self._runner = TaskRunner(self.root, on_done=self._on_task_done,
                                      on_error=self._on_task_error)
        return self._runner

    def _launch(self, view: str):
        if self.runner.busy:
            self.status_bar.config(text="A workbench is already running…")
            return
        try:
            func, args = self._resolve(view)
        except Exception as exc:
            ErrorDialog(self.root, title=self.i18n.get("error"), message=str(exc))
            return
        self.current_view = view
        self.progress.pack(fill=tk.X, side=tk.BOTTOM, pady=(4, 0))
        self.progress.start(10)
        self.status_bar.config(text=f"Running {view}…")
        self.runner.submit(func, *args)

    def _resolve(self, view: str):
        """Return (callable, args) for the selected workbench, executing in-process."""
        project = str(self.project_root)

        if view == "scan":
            from .core import scan_project
            return scan_project, (Path(project),)
        if view == "assure":
            from .assurance import analyze_assurance
            return analyze_assurance, (Path(project), "none")
        if view == "diagnose":
            from .investigation import failure_bundle
            from tkinter import filedialog as fd
            spool = fd.askopenfilename(title="Select spool file",
                                       initialdir=project) if True else ""
            if not spool:
                raise ValueError("A spool file is required for diagnostics")
            return failure_bundle, (Path(project), Path(spool))
        if view == "impact":
            from .impact import compare_copybooks
            from tkinter import filedialog as fd
            before = fd.askopenfilename(title="Before copybook", initialdir=project)
            after = fd.askopenfilename(title="After copybook", initialdir=project)
            if not before or not after:
                raise ValueError("Two copybooks are required for impact analysis")
            return compare_copybooks, (Path(before), Path(after))
        if view == "tests":
            from .testworkbench import generate_cases
            from tkinter import filedialog as fd
            copybook = fd.askopenfilename(title="Select copybook", initialdir=project)
            if not copybook:
                raise ValueError("A copybook is required for test generation")
            return generate_cases, (Path(copybook), "ascii")
        if view == "golden":
            from .testworkbench import compare_golden
            from tkinter import filedialog as fd
            actual = fd.askopenfilename(title="Actual file", initialdir=project)
            expected = fd.askopenfilename(title="Expected file", initialdir=project)
            if not actual or not expected:
                raise ValueError("Actual and expected files are required")
            return compare_golden, (Path(actual), Path(expected))
        if view == "coverage":
            from .coverage import import_coverage
            from tkinter import filedialog as fd
            coverage = fd.askopenfilename(title="Coverage JSON", initialdir=project)
            if not coverage:
                raise ValueError("A coverage JSON file is required")
            return import_coverage, (Path(coverage),)
        if view == "resources":
            from .enterprise import resource_inventory
            return resource_inventory, (Path(project),)
        if view == "db2":
            from .enterprise import db2_compatibility
            from tkinter import filedialog as fd
            copybook = fd.askopenfilename(title="Copybook", initialdir=project)
            ddl = fd.askopenfilename(title="DB2 DDL", initialdir=project)
            if not copybook or not ddl:
                raise ValueError("A copybook and a DDL file are required")
            return db2_compatibility, (Path(copybook), Path(ddl))
        if view == "sbom":
            from .supplychain import sbom
            return sbom, (Path(project),)
        raise ValueError(f"Unknown workbench: {view}")

    # ---------- task callbacks (main thread) ----------

    def _on_task_done(self, result):
        self.progress.stop()
        self.progress.pack_forget()
        self._last_result = result
        if self.result_frame is not None:
            self.result_frame.destroy()
            self.result_frame = None
        self.result_frame = ResultFrame(self._results_host, title=self.current_view or "Results")
        if isinstance(result, dict):
            self.result_frame.display_json(result)
        else:
            self.result_frame.display_json({"result": str(result)})
        self.status_bar.config(text=self.i18n.get("success"), style="Status.Success.TLabel")

    def _save_result(self):
        if self._last_result is None or self.current_view is None:
            self.status_bar.config(text="Run a workbench first.")
            return
        try:
            output = export_report(self.project_root, self.current_view, self._last_result)
        except Exception as exc:
            ErrorDialog(self.root, title=self.i18n.get("error"), message=str(exc))
            self.status_bar.config(text=self.i18n.get("error"))
            return
        relative = output.relative_to(self.project_root)
        self.status_bar.config(text=f"Exported to {relative}")

    def _on_task_error(self, exc: Exception):
        self.progress.stop()
        self.progress.pack_forget()
        ErrorDialog(self.root, title=self.i18n.get("error"), message=str(exc))
        self.status_bar.config(text=self.i18n.get("error"), style="Status.Error.TLabel")

    # ---------- i18n ----------

    def apply_language(self, lang: str):
        self.i18n.set_language(lang)
        self.status_bar.config(text=self.i18n.get("ready"))


def start_gui(project_root: Optional[Path] = None):
    """Public entry point for launching the desktop GUI (v1.1.1)."""
    root = tk.Tk()
    root.title("PeaCOBOL 1.1.1")
    root.geometry("1100x720")
    app = PeaCOBOLGUI(root, project_root=project_root)
    root.mainloop()
