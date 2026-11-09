"""Authentication module for PeaCOBOL GUI."""

import secrets
from tkinter import simpledialog, messagebox
from typing import Optional


def authenticate(parent=None) -> str:
    """Prompt for credentials. Returns a token string or empty string on cancel."""
    root = parent or None
    try:
        if root is not None:
            root.withdraw()
        user = simpledialog.askstring(title="PeaCOBOL", prompt="Username:",
                                       initialvalue="peacobol")
        if user is None:
            return ""
        pwd = simpledialog.askstring("Password", "Enter password:", password=True)
        if pwd is None:
            return ""
        return secrets.token_urlsafe(24)
    finally:
        if root is not None:
            root.destroy()
