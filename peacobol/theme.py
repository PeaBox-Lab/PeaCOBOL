"""Theme and accessibility settings for the PeaCOBOL desktop GUI."""

from __future__ import annotations

from typing import Dict

THEMES: Dict[str, Dict[str, str]] = {
    "light": {
        "bg": "#f4f7fb",
        "fg": "#172033",
        "card": "#ffffff",
        "border": "#d9e2ec",
        "accent": "#087f5b",
        "status_ok": "#087f5b",
        "status_error": "#c92a2a",
        "status_info": "#1971c2",
        "muted": "#627d98",
    },
    "dark": {
        "bg": "#102a43",
        "fg": "#d9e2ec",
        "card": "#243b53",
        "border": "#334e68",
        "accent": "#30b98a",
        "status_ok": "#30b98a",
        "status_error": "#ff6b6b",
        "status_info": "#74c0fc",
        "muted": "#829ab1",
    },
    "high-contrast": {
        "bg": "#000000",
        "fg": "#ffffff",
        "card": "#1a1a1a",
        "border": "#ffffff",
        "accent": "#ffff00",
        "status_ok": "#00ff00",
        "status_error": "#ff0000",
        "status_info": "#00ffff",
        "muted": "#cccccc",
    },
}

FONT_SCALES = {"small": 9, "normal": 10, "large": 12, "extra-large": 14}

MIN_FONT_SCALE = "small"
MAX_FONT_SCALE = "extra-large"


class ThemeManager:
    """Applies palette, font scale, and accessibility options to a Tk UI."""

    def __init__(self, theme: str = "light", font_scale: str = "normal"):
        if theme not in THEMES:
            raise ValueError(f"Unknown theme: {theme!r}. Available: {', '.join(THEMES)}")
        if font_scale not in FONT_SCALES:
            raise ValueError(f"Unknown font scale: {font_scale!r}. Available: {', '.join(FONT_SCALES)}")
        self._theme = theme
        self._font_scale = font_scale
        self._high_contrast = theme == "high-contrast"
        self._colors = THEMES[theme]

    @property
    def colors(self) -> Dict[str, str]:
        return dict(self._colors)

    @property
    def font_size(self) -> int:
        return FONT_SCALES[self._font_scale]

    @property
    def font_family(self) -> str:
        return "Segoe UI"

    @property
    def high_contrast(self) -> bool:
        return self._high_contrast

    def scale_font(self, step: int) -> int:
        """Step the font size up or down, clamped to the supported range."""
        ordered = available_font_scales()
        index = ordered.index(self._font_scale)
        index = max(0, min(index + step, len(ordered) - 1))
        self._font_scale = ordered[index]
        return self.font_size

    def apply(self, root):
        """Apply palette and base fonts to the root window's ttk styles."""
        colors = self._colors
        size = self.font_size
        family = self.font_family
        root.configure(bg=colors["bg"])

        from tkinter import ttk
        style = ttk.Style(root)
        style.configure(".", background=colors["bg"], foreground=colors["fg"],
                        font=(family, size))
        style.configure("TFrame", background=colors["bg"])
        style.configure("TLabel", background=colors["bg"], foreground=colors["fg"])
        style.configure("Title", font=(family, size + 3, "bold"),
                        foreground=colors["fg"], background=colors["bg"])
        style.configure("Card", background=colors["card"], bordercolor=colors["border"])
        style.configure("Card.TLabelframe", background=colors["card"],
                        bordercolor=colors["border"])
        style.configure("Card.TLabelframe.Label", background=colors["card"],
                        foreground=colors["fg"], font=(family, size + 1, "bold"))
        style.configure("TButton", background=colors["accent"], foreground="#ffffff",
                        font=(family, size, "bold"))
        style.configure("Status.Success.TLabel", background=colors["bg"],
                        foreground=colors["status_ok"])
        style.configure("Status.Error.TLabel", background=colors["bg"],
                        foreground=colors["status_error"])
        style.configure("Status.Info.TLabel", background=colors["bg"],
                        foreground=colors["status_info"])


def available_themes():
    return sorted(THEMES)


def available_font_scales():
    return sorted(FONT_SCALES, key=lambda name: FONT_SCALES[name])
