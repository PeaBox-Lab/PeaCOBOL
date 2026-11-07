from __future__ import annotations

from typing import Any


def evaluate_policy(profile: dict[str, Any], scan: dict[str, Any] | None = None, build: dict[str, Any] | None = None, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = profile["policy"]
    checks: list[dict[str, Any]] = []
    limits = policy.get("max_findings", {})
    counts = (scan or {}).get("summary", {}).get("findings", {})
    for severity in ("critical", "high", "medium", "low"):
        limit = limits.get(severity)
        actual = int(counts.get(severity, 0))
        if limit is not None:
            checks.append({
                "id": f"findings-{severity}",
                "passed": actual <= limit,
                "actual": actual,
                "limit": limit,
                "message": f"{severity.title()} findings: {actual}; allowed: {limit}",
            })
    if build is not None:
        checks.append({"id": "build-success", "passed": bool(build.get("ok")), "message": "Build completed successfully." if build.get("ok") else "Build did not complete successfully."})
        if policy.get("fail_on_build_warning"):
            warnings = int(build.get("diagnostic_summary", {}).get("warning", 0))
            checks.append({"id": "build-warnings", "passed": warnings == 0, "actual": warnings, "limit": 0, "message": f"Normalized build warnings: {warnings}; allowed: 0"})
    if policy.get("require_evidence"):
        valid = bool(evidence and evidence.get("manifest_hash"))
        checks.append({"id": "evidence-required", "passed": valid, "message": "Evidence manifest is present." if valid else "Evidence manifest is required but missing."})
    failed = [check for check in checks if not check["passed"]]
    return {
        "schema": "peacobol-policy-1",
        "profile": profile["name"],
        "ok": not failed,
        "checks": checks,
        "failed_checks": [check["id"] for check in failed],
    }
