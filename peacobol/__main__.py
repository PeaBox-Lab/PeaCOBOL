"""Entry point for the PeaCOBOL desktop GUI application (``peacobol-gui``)."""

import tkinter as tk
from tkinter import messagebox
from pathlib import Path

from .gui import PeaCOBOLGUI


def main(argv=None) -> int:
    """Launch the PeaCOBOL desktop GUI."""
    root = tk.Tk()
    root.title("PeaCOBOL")
    try:
        app = PeaCOBOLGUI(root, project_root=Path.cwd())
    except Exception as exc:  # show a window-level failure, keep the process observable
        messagebox.showerror("PeaCOBOL", f"Unable to start the GUI: {exc}")
        raise
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
