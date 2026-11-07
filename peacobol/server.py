from __future__ import annotations
import argparse
import html
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from .audit import append_event
from .core import scan_project
PAGE = """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>PeaCOBOL</title><style>
:root{font-family:Segoe UI,Arial;background:#f4f7fb;color:#172033}body{margin:0}.top{background:#102a43;color:white;padding:18px 28px}.wrap{max-width:1180px;margin:24px auto;padding:0 18px}.bar,.card{background:white;border:1px solid #d9e2ec;border-radius:12px;padding:16px;margin-bottom:16px;box-shadow:0 3px 12px #102a4312}input{width:70%;padding:12px;border:1px solid #bcccdc;border-radius:8px}button{padding:12px 18px;background:#087f5b;color:white;border:0;border-radius:8px;font-weight:600}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}.metric{font-size:30px;font-weight:700}.high{color:#c92a2a}.medium{color:#e67700}.low{color:#1971c2}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px;border-bottom:1px solid #e9ecef}code{background:#edf2f7;padding:2px 5px}</style></head><body><div class='top'><h1>PeaCOBOL 0.4.0</h1><div>Local COBOL data and assurance workspace</div></div><main class='wrap'><form class='bar'><input name='path' value='{path}' aria-label='Project path relative to server root'><button>Analyze project</button></form>{content}</main></body></html>"""
def handler_for(root: Path):
    root = root.resolve()
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            relative = query.get("path", ["."])[0]
            content = "<div class='card'>Enter a project path beneath the configured server root.</div>"
            if "path" in query:
                try:
                    requested = (root / relative).resolve()
                    requested.relative_to(root)
                    if not requested.is_dir():
                        raise NotADirectoryError("Project path was not found")
                    report = scan_project(requested)
                    findings = report["findings"]
                    counts = report["summary"]["findings"]
                    rows = "".join(f"<tr><td><code>{html.escape(x['rule'])}</code></td><td class='{x['severity']}'>{x['severity']}</td><td>{html.escape(x['file'])}:{x['line']}</td><td>{html.escape(x['message'])}</td><td>{html.escape(x['remediation'])}</td></tr>" for x in findings) or "<tr><td colspan='5'>No findings</td></tr>"
                    content = f"<div class='grid'><div class='card'><div>Programs</div><div class='metric'>{len(report['programs'])}</div></div><div class='card'><div>Copybooks</div><div class='metric'>{len(report['copybooks'])}</div></div><div class='card'><div>Calls</div><div class='metric'>{len(report['calls'])}</div></div><div class='card'><div>High risks</div><div class='metric high'>{counts['high']}</div></div></div><div class='card'><h2>Assurance findings</h2><table><thead><tr><th>Rule</th><th>Severity</th><th>Location</th><th>Finding</th><th>Remediation</th></tr></thead><tbody>{rows}</tbody></table></div>"
                    append_event(requested / ".peacobol" / "audit.jsonl", "ui-scan", requested.name, "success", {"findings": len(findings)})
                except Exception as exc:
                    content = f"<div class='card high'>{html.escape(str(exc))}</div>"
            data = PAGE.format(path=html.escape(relative), content=content).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(data)
        def log_message(self, *_):
            pass
    return Handler
def main(argv=None):
    parser = argparse.ArgumentParser(prog="peacobol-ui")
    parser.add_argument("--root", default=".", help="Only projects under this directory may be analyzed")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if not root.is_dir():
        raise SystemExit("Server root is not a directory")
    print(f"PeaCOBOL UI: http://127.0.0.1:{args.port} (root: {root})")
    ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(root)).serve_forever()
if __name__ == "__main__":
    main()
