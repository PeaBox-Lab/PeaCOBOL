"""Reusable Tkinter widget components for PeaCOBOL Desktop GUI."""

import json
import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk


class ProgressBar(ttk.Progressbar):
    """Custom progress bar with label and indeterminate mode support."""

    def __init__(self, parent, length=300, mode="determinate", **kwargs):
        super().__init__(parent, length=length, mode=mode, **kwargs)
        self._value = 0
        self._maximum = 100

    def set_progress(self, value: int):
        self._value = max(0, min(int(value), int(self._maximum)))
        self["value"] = self._value

    def set_range(self, minimum: int, maximum: int):
        self._minimum = minimum
        self._maximum = maximum
        self.configure(maximum=maximum)
        if self._value > maximum:
            self.set_progress(maximum)

    def set_indeterminate(self):
        self._mode = self.mode
        self.config(mode="indeterminate")

    def reset(self):
        self._value = 0
        self.config(value=0, maximum=max(self._maximum, 1))


class LoadingOverlay(ttk.Frame):
    """Transparent overlay that blocks user interaction while processing."""

    def __init__(self, parent, text="Working...", **kwargs):
        super().__init__(parent, bg="#ffffff", bd=0, relief="solid", **kwargs)
        style = ttk.Style()
        style.theme_use("clam")
        try:
            style.configure("Overlay.TLabel", font=("Segoe UI", 11, "bold"))
            label = ttk.Label(self, text=text, style="Overlay.TLabel")
            label.pack(padx=30, pady=30, expand=True)
            # Semi-transparent background
            overlay_bg = "rgba(244,247,251,0.85)" if kwargs.get("font", ("Segoe UI", 12))[0] != "Inter" else "#ffffff"
            self.configure(background=overlay_bg if tk.call("tk", "windowingsystem") == "win32" else overlay_bg)
        except Exception:
            pass


class StatusLabel(ttk.Label):
    """Status label that auto-updates style based on status text."""

    _STATUS_COLORS = {
        "ok": "#087f5b",
        "warn": "#d9480f",
        "error": "#c92a2a",
        "info": "#1971c2",
    }

    def __init__(self, parent, width=20, **kwargs):
        super().__init__(parent, text="Ready", width=width, relief="sunken", anchor="w", justify="left", **kwargs)
        self._colors = self._STATUS_COLORS

    def set_text(self, text: str):
        self.config(text=text)
        prefix = text[:4]
        color = self._STATUS_COLORS.get(prefix.lower(), "#627d98")
        self.configure(foreground=color)

    def set_status(self, status: str, text: str = None):
        full_text = text or status
        self.set_text(full_text)


class ErrorDialog(tk.Toplevel):
    """Modal dialog for displaying errors with actionable suggestions."""

    _SUGGESTIONS = {
        "FileNotFoundError": ("Check that the file or directory path is correct.", "Verify the path exists before running the operation."),
        "ValueError": ("Ensure the input values are valid.", "Review field constraints and limits."),
        "PermissionError": ("Insufficient permissions to access this resource.", "Run the application with appropriate privileges."),
        "ImportError": ("Required dependency may be missing.", "Install the missing Python package."),
        "SystemExit": ("Operation was intentionally cancelled.", "Press OK to continue without processing this item."),
    }

    def __init__(self, parent, title: str = "Error", message: str = "", *_):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(cursor="hand2")

        frame = ttk.Frame(self, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        error_header = ttk.Label(frame, text=title, font=("Segoe UI", 12, "bold"), foreground="#c92a2a")
        error_header.pack(anchor=tk.W)

        message_label = ttk.Label(frame, text=message, wraplength=500, justify=tk.LEFT, foreground="#495057",
                                 font=("Segoe UI", 10))
        message_label.pack(anchor=tk.W, pady=(5, 10))

        suggestion = self._SUGGESTIONS.get(type(message).__name__ if isinstance(message, Exception) else type(message).__name__)
        show_help = suggestion is not None and len(message) < 500
        if show_help:
            hint_label = ttk.Label(frame, text=f"Tip: {suggestion[1]}", wraplength=500,
                                   foreground="#6c757d", font=("Segoe UI", 9),
                                   justify=tk.LEFT)
            hint_label.pack(anchor=tk.W, padx=20)
        else:
            tip_label = ttk.Label(frame, text="No additional guidance available.", fg="#adb5bb", font=("Segoe UI", 9))
            tip_label.pack(anchor=tk.W)

        btn = ttk.Button(frame, text="OK", command=self.destroy, width=12)
        btn.pack(pady=10)


class ResultFrame(ttk.Frame):
    """Frame for displaying structured results from workbench operations."""

    def __init__(self, parent, title: str, **kwargs):
        super().__init__(parent, padding=10, **kwargs)
        self._title = title
        self.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(self, text=title, font=("Segoe UI", 11, "bold"), foreground="#102a43")
        header.pack(anchor=tk.W, padx=5, pady=(0, 8))

        self._body = scrolledtext.ScrolledText(self, wrap=tk.WORD, state="disabled", height=20)
        self._body.pack(fill=tk.BOTH, expand=True, padx=5)

    def display_json(self, data: dict):
        import json
        self._body.config(state="normal")
        self._body.delete("1.0", tk.END)
        if isinstance(data, dict):
            text = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            text = str(data)
        self._body.insert(tk.END, text)
        self._body.see(tk.END)
        self._body.config(state="disabled")


from tkinter import scrolledtext
