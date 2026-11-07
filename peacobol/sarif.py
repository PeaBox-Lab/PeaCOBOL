from __future__ import annotations

from typing import Any

LEVELS = {"critical": "error", "high": "error", "medium": "warning", "low": "note"}


def to_sarif(report: dict[str, Any]) -> dict[str, Any]:
    findings = report.get("findings", [])
    rules: dict[str, dict[str, Any]] = {}
    results = []
    for finding in findings:
        rule_id = finding["rule"]
        rules.setdefault(rule_id, {
            "id": rule_id,
            "name": rule_id,
            "shortDescription": {"text": finding["message"]},
            "help": {"text": finding["remediation"]},
            "properties": {"defaultSeverity": finding["severity"]},
        })
        results.append({
            "ruleId": rule_id,
            "level": LEVELS.get(finding["severity"], "warning"),
            "message": {"text": finding["message"]},
            "locations": [{"physicalLocation": {"artifactLocation": {"uri": finding["file"]}, "region": {"startLine": finding["line"]}}}],
            "properties": {"severity": finding["severity"], "remediation": finding["remediation"]},
        })
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "PeaCOBOL", "rules": [rules[key] for key in sorted(rules)]}},
            "results": results,
            "properties": {"sourceSchema": report.get("schema"), "project": report.get("project"), "gate": report.get("gate")}, 
        }],
    }
