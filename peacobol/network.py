"""Network integration layer for PeaCOBOL Desktop GUI."""

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests

from .gui import PeaCOBOLGUI, start_gui
from .core import scan_project
from .enterprise import resource_inventory, db2_compatibility
from .supplychain import sbom, attest, immutable_export


class NetworkError(Exception):
    """Custom exception for network-related errors."""


class NetworkClient:
    """Client for interacting with the PeaCOBOL server."""

    _BASE_URL = "http://127.0.0.1:8765"

    def __init__(self, session_token: str, timeout: int = 30):
        self.session_token = session_token
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Cookie": f"PeaCOBOLSession={session_token}",
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self._BASE_URL}/{endpoint}"
        try:
            response = self.session.request(
                method,
                url,
                timeout=self.timeout,
                **kwargs,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Network request failed: {e}") from e

    def run_scan(self, root_path: str) -> Dict[str, Any]:
        return self._request("POST", "scan", json={"project": root_path})

    def run_assurance(self, root_path: str, fail_on: str = "none") -> Dict[str, Any]:
        return self._request("POST", "assure", json={"project": root_path, "fail_on": fail_on})

    def run_diagnostics(self, root_path: str, spool: str) -> Dict[str, Any]:
        return self._request("POST", "diagnose", json={"project": root_path, "spool": spool})

    def run_impact(self, before: str, after: str) -> Dict[str, Any]:
        return self._request("POST", "impact", json={"before": before, "after": after})

    def run_test_cases(self, copybook: str, encoding: str = "ascii") -> Dict[str, Any]:
        return self._request("POST", "tests", json={"copybook": copybook, "encoding": encoding})

    def run_golden(self, actual: str, expected: str) -> Dict[str, Any]:
        return self._request("POST", "golden", json={"actual": actual, "expected": expected})

    def run_coverage(self, coverage: str, project: str) -> Dict[str, Any]:
        return self._request("POST", "coverage", json={"coverage": coverage, "project": project})

    def run_resources(self, project: str) -> Dict[str, Any]:
        return self._request("POST", "resources", json={"project": project})

    def run_db2(self, copybook: str, ddl: str) -> Dict[str, Any]:
        return self._request("POST", "db2", json={"copybook": copybook, "ddl": ddl})

    def run_sbom(self, project: str) -> Dict[str, Any]:
        return self._request("POST", "sbom", json={"project": project})

    def run_attest(self, file: str, verify: bool = False) -> Dict[str, Any]:
        return self._request("POST", "attest", json={"file": file, "verify": verify})

    def run_immutable_export(self, files: List[str], output: str) -> Dict[str, Any]:
        return self._request("POST", "immutable-export", json={"files": files, "output": output})

    def run_retention(self, directory: str, days: int) -> Dict[str, Any]:
        return self._request("POST", "retention-plan", json={"directory": directory, "days": days})


class GUIWrapper:
    """Wrapper that connects GUI with network functionality."""

    def __init__(self, gui: PeaCOBOLGUI, network_client: NetworkClient):
        self.gui = gui
        self.network = network_client
        self._current_task = None
        self._task_thread = None

    def _start_task(self, task_func):
        """Start a task in a separate thread to keep GUI responsive."""
        self._current_task = task_func
        self._task_thread = threading.Thread(target=self._execute_task, daemon=True)
        self._task_thread.start()

    def _execute_task(self):
        try:
            result = self._current_task()
            self.gui.root.after(0, lambda: self._handle_result(result))
        except Exception as e:
            self.gui.root.after(0, lambda: self._show_error(e))

    def _handle_result(self, result):
        self.gui.root.after(0, lambda: self.gui.root.title(f"PeaCOBOL - Success"))
        self.gui.root.after(0, lambda: self.gui.status_bar.config(text=f"Success: {result.get('status', 'Completed')}"))

    def _show_error(self, error):
        self.gui.root.after(0, lambda: ErrorDialog(self.gui.root, title="Error", message=str(error)))
        self.gui.root.after(0, lambda: self.gui.status_bar.config(text=f"Error: {str(error)[:50]}..."))

    def run_scan(self, root_path: str):
        self._start_task(lambda: self.network.run_scan(root_path))

    def run_assurance(self, root_path: str, fail_on: str = "none"):
        self._start_task(lambda: self.network.run_assurance(root_path, fail_on))

    def run_diagnostics(self, root_path: str, spool: str):
        self._start_task(lambda: self.network.run_diagnostics(root_path, spool))

    def run_impact(self, before: str, after: str):
        self._start_task(lambda: self.network.run_impact(before, after))

    def run_test_cases(self, copybook: str, encoding: str = "ascii"):
        self._start_task(lambda: self.network.run_test_cases(copybook, encoding))

    def run_golden(self, actual: str, expected: str):
        self._start_task(lambda: self.network.run_golden(actual, expected))

    def run_coverage(self, coverage: str, project: str):
        self._start_task(lambda: self.network.run_coverage(coverage, project))

    def run_resources(self, project: str):
        self._start_task(lambda: self.network.run_resources(project))

    def run_db2(self, copybook: str, ddl: str):
        self._start_task(lambda: self.network.run_db2(copybook, ddl))

    def run_sbom(self, project: str):
        self._start_task(lambda: self.network.run_sbom(project))

    def run_attest(self, file: str, verify: bool = False):
        self._start_task(lambda: self.network.run_attest(file, verify))

    def run_immutable_export(self, files: List[str], output: str):
        self._start_task(lambda: self.network.run_immutable_export(files, output))

    def run_retention(self, directory: str, days: int):
        self._start_task(lambda: self.network.run_retention(directory, days))