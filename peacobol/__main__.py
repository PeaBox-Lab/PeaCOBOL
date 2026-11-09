"""Entry point for the PeaCOBOL desktop GUI application."""

import sys
from tkinter import tk
from pathlib import Path

from .auth import authenticate
from .i18n import I18N
from .gui import PeaCOBOLGUI


def main():
    """Launch the PeaCOBOL desktop GUI."""
    root = tk.Tk()
    root.title("PeaCOBOL Project Manager")
    app = PeaCOBOLGUI(root, project_root=Path.cwd())
    token = authenticate(app)
    if token:
        app.token = token
    else:
        messagebox.showwarning("PeaCOBOL", "Authentication cancelled.")
        root.destroy()
        return 1
    app.root = root
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
