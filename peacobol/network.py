"""Network integration layer for PeaCOBOL Desktop GUI.

Connects the desktop GUI to the loopback server (peacobol.server) so
workbenches can run either locally (in-process) or through the server
API. Long-running calls execute on worker threads via TaskRunner to
keep the Tk main loop responsive.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Optional


class NetworkError(Exception):
    """Raised when a request to the PeaCOBOL server fails."""


class NetworkClient:
    """Minimal HTTP client for the token-protected loopback server."""

    BASE_URL = "http://127.0.0.1:8765"

    def __init__(self, session_token: str, timeout: int = 60):
        self.session_token = session_token
        self.timeout = timeout

    def _request(self, endpoint: str) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/?view={endpoint}"
        request = urllib.request.Request(url)
        request.add_header("Cookie", f"PeaCOBOLSession={self.session_token}")
        request.add_header("Host", "127.0.0.1")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise NetworkError(f"Server returned HTTP {response.status}")
                return {"status": response.status, "body": response.read().decode("utf-8", errors="replace")}
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                raise NetworkError("Session rejected by the server (403). Restart the server and retry.") from exc
            raise NetworkError(f"Server error: HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise NetworkError(f"Cannot reach the PeaCOBOL server: {exc}") from exc


class TaskRunner:
    """Runs callables on a background thread and reports through callbacks.

    The GUI stays responsive because workbench execution never blocks the
    Tk main loop. All callbacks are marshalled back onto the main thread
    with ``root.after(0, ...)``.
    """

    def __init__(self, root, on_done: Callable[[Any], None], on_error: Callable[[Exception], None]):
        self.root = root
        self.on_done = on_done
        self.on_error = on_error
        self._thread: Optional[threading.Thread] = None

    @property
    def busy(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def submit(self, func: Callable[[], Any], *args, **kwargs):
        if self.busy:
            raise RuntimeError("A task is already running")

        def _worker():
            try:
                result = func(*args, **kwargs)
            except Exception as exc:  # marshalled to UI thread
                self.root.after(0, lambda e=exc: self.on_error(e))
            else:
                self.root.after(0, lambda r=result: self.on_done(r))

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()

    def wait(self, timeout: Optional[float] = None):
        """Blocking join — used by tests, never by the GUI."""
        if self._thread is not None:
            self._thread.join(timeout)
