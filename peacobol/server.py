from __future__ import annotations
import argparse
import html
import json
import secrets
import threading
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from .assurance import analyze_assurance
from .audit import append_event
from .core import scan_project
from .coverage import import_coverage
from .enterprise import db2_compatibility, resource_inventory
from .impact import compare_copybooks
from .investigation import failure_bundle
from .supplychain import sbom
from .testworkbench import cobol_check_stub, compare_golden, generate_cases
STYLE = """
:root{font-family:Segoe UI,Arial,sans-serif;background:#f4f7fb;color:#172033;line-height:1.45}*{box-sizing:border-box}body{margin:0}.top{background:linear-gradient(120deg,#102a43,#174f75);color:#fff;padding:20px 28px}.top h1{margin:0 0 4px}.layout{display:grid;grid-template-columns:230px minmax(0,1fr);max-width:1440px;margin:auto}.nav{padding:22px 14px}.nav a{display:block;color:#334e68;text-decoration:none;padding:10px 12px;border-radius:8px;margin:3px 0}.nav a:hover,.nav a.active{background:#d9eaf7;color:#102a43;font-weight:700}.main{padding:22px}.card{background:#fff;border:1px solid #d9e2ec;border-radius:12px;padding:18px;margin-bottom:16px;box-shadow:0 3px 12px #102a4310}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.metric{font-size:28px;font-weight:750}.muted{color:#627d98}.high,.error{color:#c92a2a}.medium,.warning{color:#d9480f}.low,.note{color:#1971c2}.ok{color:#087f5b}label{display:block;font-weight:650;margin:10px 0 4px}input,select{width:100%;padding:10px;border:1px solid #bcccdc;border-radius:7px;background:#fff}.row{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}button{padding:11px 17px;background:#087f5b;color:#fff;border:0;border-radius:8px;font-weight:700;margin-top:14px;cursor:pointer}table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:9px;border-bottom:1px solid #e9ecef;vertical-align:top}th{background:#f8fafc}code,pre{background:#edf2f7;border-radius:6px}code{padding:2px 5px}pre{padding:14px;overflow:auto;max-height:520px;white-space:pre-wrap}.pill{display:inline-block;padding:3px 8px;border-radius:99px;background:#e6fffa;color:#087f5b;font-size:12px;font-weight:700}.notice{border-left:4px solid #1971c2}.danger{border-left:4px solid #c92a2a}@media(max-width:800px){.layout{grid-template-columns:1fr}.nav{display:flex;overflow:auto;padding:10px}.nav a{white-space:nowrap}.main{padding:14px}}
"""
VIEWS = [("scan","Scan"),("assure","Assurance"),("diagnose","Diagnostics"),("impact","Change impact"),("tests","Test cases"),("golden","Golden compare"),("coverage","Coverage"),("resources","Enterprise resources"),("db2","DB2 compatibility"),("sbom","SBOM")]
def _e(value) -> str:
    return html.escape(str(value), quote=True)
def _json(value) -> str:
    return _e(json.dumps(value, indent=2, ensure_ascii=False))
def _safe_path(root: Path, raw: str, require: str) -> Path:
    if not raw or Path(raw).is_absolute():
        raise ValueError("Use a relative path beneath the configured root")
    candidate = root / raw
    current = root
    for part in Path(raw).parts:
        if part in ("", ".", ".."):
            raise ValueError("Invalid path")
        current = current / part
        if current.is_symlink():
            raise ValueError("Symlink paths are not allowed")
    resolved = candidate.resolve()
    resolved.relative_to(root)
    if require == "dir" and not resolved.is_dir():
        raise NotADirectoryError("Project directory was not found")
    if require == "file" and not resolved.is_file():
        raise FileNotFoundError("File was not found")
    return resolved
def _form(view: str, fields: list[tuple[str,str,str]], values: dict[str,str], token: str, select: tuple[str,list[str]] | None = None) -> str:
    controls=[]
    for name,label,placeholder in fields:
        controls.append(f"<div><label for='{_e(name)}'>{_e(label)}</label><input id='{_e(name)}' name='{_e(name)}' value='{_e(values.get(name,''))}' placeholder='{_e(placeholder)}' required></div>")
    if select:
        name, options=select
        opts=''.join(f"<option value='{_e(x)}'{' selected' if values.get(name)==x else ''}>{_e(x)}</option>" for x in options)
        controls.append(f"<div><label for='{_e(name)}'>{_e(name.replace('_',' ').title())}</label><select id='{_e(name)}' name='{_e(name)}'>{opts}</select></div>")
    return f"<form class='card' method='get'><input type='hidden' name='view' value='{_e(view)}'><div class='row'>{''.join(controls)}</div><button>Run {_e(dict(VIEWS)[view])}</button></form>"
def _findings_table(findings) -> str:
    rows=''.join(f"<tr><td><code>{_e(x['rule'])}</code></td><td class='{_e(x['severity'])}'>{_e(x['severity'])}</td><td>{_e(x['file'])}:{x['line']}</td><td>{_e(x['message'])}</td><td>{_e(x['remediation'])}</td></tr>" for x in findings)
    return f"<div class='card'><h2>Findings</h2><table><thead><tr><th>Rule</th><th>Severity</th><th>Location</th><th>Finding</th><th>Remediation</th></tr></thead><tbody>{rows or '<tr><td colspan=5>No findings</td></tr>'}</tbody></table></div>"
def _render(view: str, query: dict[str,list[str]], root: Path, token: str) -> tuple[str, Path | None, dict]:
    values={key:value[0] for key,value in query.items()}
    project_raw=values.get("project", ".")
    result=""; audit_project=None; audit_details={"view":view}
    if view == "scan":
        form=_form(view,[("project","Project",".")],values,token)
        if "project" in values:
            project=_safe_path(root, project_raw, "dir"); report=scan_project(project); audit_project=project
            counts=report["summary"]["findings"]
            result=f"<div class='grid'><div class='card'><div>Programs</div><div class='metric'>{len(report['programs'])}</div></div><div class='card'><div>Copybooks</div><div class='metric'>{len(report['copybooks'])}</div></div><div class='card'><div>Calls</div><div class='metric'>{len(report['calls'])}</div></div><div class='card'><div>High risks</div><div class='metric high'>{counts['high']}</div></div></div>"+_findings_table(report["findings"])
            audit_details["findings"]=len(report["findings"])
        return form+result,audit_project,audit_details
    if view == "assure":
        form=_form(view,[("project","Project",".")],values,token,("fail_on",["none","critical","high","medium","low"]))
        if "project" in values:
            project=_safe_path(root,project_raw,"dir"); report=analyze_assurance(project,values.get("fail_on","none")); audit_project=project
            s=report["summary"]
            result=f"<div class='grid'><div class='card'><div>Program edges</div><div class='metric'>{len(report['program_graph']['edges'])}</div></div><div class='card'><div>Copy edges</div><div class='metric'>{len(report['copybook_graph']['edges'])}</div></div><div class='card'><div>Field accesses</div><div class='metric'>{s['field_accesses']}</div></div><div class='card'><div>Gate</div><div class='metric {'ok' if report['ok'] else 'high'}'>{'PASS' if report['ok'] else 'FAIL'}</div></div></div>"+_findings_table(report["findings"])+f"<div class='card'><h2>Graph and inventories</h2><pre>{_json({'program_graph':report['program_graph'],'copybook_graph':report['copybook_graph'],'field_access':report['field_access'],'control_flow':report['control_flow'],'data_flow':report['data_flow']})}</pre></div>"
            audit_details["findings"]=len(report["findings"])
        return form+result,audit_project,audit_details
    if view == "diagnose":
        form=_form(view,[("project","Project","."),("spool","Spool file","failure.log")],values,token)
        if "spool" in values:
            project=_safe_path(root,project_raw,"dir"); spool=_safe_path(root,values["spool"],"file"); report=failure_bundle(project,spool,None,3); audit_project=project
            d=report["diagnosis"]; result=f"<div class='grid'><div class='card'><div>Max return code</div><div class='metric'>{_e(d['spool']['max_return_code'])}</div></div><div class='card'><div>ABEND markers</div><div class='metric'>{len(d['spool']['abends'])}</div></div><div class='card'><div>File statuses</div><div class='metric'>{len(d['spool']['file_statuses'])}</div></div><div class='card'><div>Bundle hash</div><code>{_e(report['bundle_hash'][:16])}…</code></div></div><div class='card'><h2>Investigation checklist</h2><ol>{''.join(f'<li><b>{_e(x["action"])}</b><br><span class=muted>{_e(x["reason"])}</span></li>' for x in d['checklist'])}</ol></div><div class='card'><h2>Diagnosis details</h2><pre>{_json(d)}</pre></div>"
        return form+result,audit_project,audit_details
    if view == "impact":
        form=_form(view,[("before","Before copybook","old.cpy"),("after","After copybook","new.cpy")],values,token)
        if "before" in values and "after" in values:
            before=_safe_path(root,values["before"],"file"); after=_safe_path(root,values["after"],"file"); report=compare_copybooks(before,after)
            result=f"<div class='grid'><div class='card'><div>Compatible</div><div class='metric {'ok' if report['compatible'] else 'high'}'>{'YES' if report['compatible'] else 'NO'}</div></div><div class='card'><div>Breaking changes</div><div class='metric'>{report['summary']['breaking']}</div></div><div class='card'><div>Length delta</div><div class='metric'>{report['record_length_delta']:+d}</div></div><div class='card'><div>Impact hash</div><code>{_e(report['impact_hash'][:16])}…</code></div></div><div class='card'><h2>Field changes</h2><pre>{_json(report['changes'])}</pre></div>"
        return form+result,None,audit_details
    if view == "tests":
        form=_form(view,[("copybook","Copybook","copybooks/ACCOUNT.cpy"),("program","COBOL Check program","PAYMENT")],values,token,("encoding",["ascii","utf-8","cp037","cp500"]))
        if "copybook" in values:
            copybook=_safe_path(root,values["copybook"],"file"); report=generate_cases(copybook,values.get("encoding","ascii")); stub=cobol_check_stub(values.get("program","PROGRAM"),report)
            result=f"<div class='grid'><div class='card'><div>Record length</div><div class='metric'>{report['record_length']}</div></div><div class='card'><div>Fields</div><div class='metric'>{report['fields']}</div></div><div class='card'><div>Cases</div><div class='metric'>{len(report['cases'])}</div></div><div class='card'><div>Cases hash</div><code>{_e(report['cases_hash'][:16])}…</code></div></div><div class='card'><h2>Generated cases</h2><pre>{_json(report['cases'])}</pre></div><div class='card'><h2>COBOL Check-compatible starter</h2><pre>{_e(stub)}</pre></div>"
        return form+result,None,audit_details
    if view == "golden":
        form=_form(view,[("actual","Actual file","actual.dat"),("expected","Expected file","expected.dat")],values,token)
        if "actual" in values and "expected" in values:
            report=compare_golden(_safe_path(root,values["actual"],"file"),_safe_path(root,values["expected"],"file"))
            result=f"<div class='card'><div>Comparison</div><div class='metric {'ok' if report['ok'] else 'high'}'>{'MATCH' if report['ok'] else 'DIFFERENT'}</div><pre>{_json(report)}</pre></div>"
        return form+result,None,audit_details
    if view == "coverage":
        form=_form(view,[("coverage","Coverage JSON","coverage.json"),("project","Project root","project"),("evidence_manifest","Evidence manifest","project/reports/evidence.json")],values,token)
        if "coverage" in values:
            evidence=_safe_path(root,values["evidence_manifest"],"file") if values.get("evidence_manifest") else None
            project=_safe_path(root,values["project"],"dir") if evidence else None
            report=import_coverage(_safe_path(root,values["coverage"],"file"),evidence,project); summary=report["summary"]
            result=f"<div class='grid'><div class='card'><div>Covered</div><div class='metric'>{summary['covered']}</div></div><div class='card'><div>Missed</div><div class='metric'>{summary['missed']}</div></div><div class='card'><div>Coverage</div><div class='metric'>{summary['percent']:.2f}%</div></div><div class='card'><div>Coverage hash</div><code>{_e(report['coverage_hash'][:16])}…</code></div></div><div class='card'><h2>Coverage details</h2><pre>{_json(report)}</pre></div>"
        return form+result,None,audit_details
    if view == "resources":
        form=_form(view,[("project","Project",".")],values,token)
        if "project" in values:
            project=_safe_path(root,project_raw,"dir"); report=resource_inventory(project); audit_project=project; summary=report["summary"]
            result=f"<div class='grid'><div class='card'><div>DB2 references</div><div class='metric'>{summary['db2']}</div></div><div class='card'><div>CICS commands</div><div class='metric'>{summary['cics']}</div></div><div class='card'><div>MQ calls</div><div class='metric'>{summary['mq']}</div></div><div class='card'><div>Inventory hash</div><code>{_e(report['inventory_hash'][:16])}…</code></div></div><div class='card'><h2>Resource inventory</h2><pre>{_json(report)}</pre></div>"
        return form+result,audit_project,audit_details
    if view == "db2":
        form=_form(view,[("copybook","Copybook","copybooks/ACCOUNT.cpy"),("ddl","DB2 DDL","schema.sql")],values,token)
        if "copybook" in values and "ddl" in values:
            report=db2_compatibility(_safe_path(root,values["copybook"],"file"),_safe_path(root,values["ddl"],"file")); summary=report["summary"]
            result=f"<div class='grid'><div class='card'><div>Columns</div><div class='metric'>{summary['columns']}</div></div><div class='card'><div>Compatible</div><div class='metric ok'>{summary['compatible']}</div></div><div class='card'><div>Incompatible</div><div class='metric high'>{summary['incompatible']}</div></div><div class='card'><div>Manifest hash</div><code>{_e(report['manifest_hash'][:16])}…</code></div></div><div class='card'><h2>Compatibility details</h2><pre>{_json(report)}</pre></div>"
        return form+result,None,audit_details
    if view == "sbom":
        form=_form(view,[("project","Project",".")],values,token)
        if "project" in values:
            project=_safe_path(root,project_raw,"dir"); report=sbom(project); audit_project=project
            result=f"<div class='grid'><div class='card'><div>Files</div><div class='metric'>{len(report['components'])}</div></div><div class='card'><div>Version</div><div class='metric'>{_e(report['metadata']['component']['version'])}</div></div><div class='card'><div>SBOM hash</div><code>{_e(report['bom_hash'][:16])}…</code></div></div><div class='card'><h2>Software inventory</h2><pre>{_json(report)}</pre></div>"
        return form+result,audit_project,audit_details
    raise ValueError("Unknown workbench")
def handler_for(root: Path, token: str):
    root=root.resolve()
    session_token=secrets.token_urlsafe(32)
    bootstrap_lock=threading.Lock()
    bootstrap_used=False
    class Handler(BaseHTTPRequestHandler):
        def _headers(self,length:int,status:int=200):
            self.send_response(status); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(length)); self.send_header("Content-Security-Policy","default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"); self.send_header("X-Content-Type-Options","nosniff"); self.send_header("Referrer-Policy","no-referrer"); self.send_header("Cache-Control","no-store"); self.end_headers()
        def do_GET(self):
            nonlocal bootstrap_used
            host=self.headers.get("Host","").split(":",1)[0].strip("[]").lower()
            if host not in {"127.0.0.1","localhost","::1"}:
                data=b"Forbidden"; self.send_response(403); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data); return
            parsed=urlparse(self.path)
            if parsed.path not in ("/","/index.html"):
                data=b"Not found"; self.send_response(404); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data); return
            query=parse_qs(parsed.query,keep_blank_values=True)
            supplied=query.get("token",[""])[0]
            if supplied:
                with bootstrap_lock:
                    accepted=not bootstrap_used and secrets.compare_digest(supplied,token)
                    if accepted: bootstrap_used=True
                if not accepted:
                    data=b"Forbidden"; self.send_response(403); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data); return
                clean={key:values for key,values in query.items() if key!="token"}
                location=parsed.path+("?"+urlencode([(key,value) for key,values in clean.items() for value in values]) if clean else "")
                self.send_response(303); self.send_header("Location",location); self.send_header("Set-Cookie",f"PeaCOBOLSession={session_token}; Path=/; HttpOnly; SameSite=Strict"); self.send_header("Cache-Control","no-store"); self.end_headers(); return
            cookie=SimpleCookie(self.headers.get("Cookie","")); session=cookie.get("PeaCOBOLSession")
            if session is None or not secrets.compare_digest(session.value,session_token):
                data=b"Forbidden"; self.send_response(403); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data); return
            view=query.get("view",["scan"])[0]
            try:
                content,project,details=_render(view,query,root,token)
                if project is not None: append_event(project/".peacobol"/"audit.jsonl",f"ui-{view}",project.name,"success",details)
                error=""
            except Exception as exc:
                content=""; error=f"<div class='card danger'><h2>Unable to complete request</h2><p>{_e(str(exc))}</p></div>"
            nav=''.join(f"<a class='{'active' if key==view else ''}' href='/?{urlencode({'view':key})}'>{_e(label)}</a>" for key,label in VIEWS)
            body=f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>PeaCOBOL 1.3.0</title><style>{STYLE}</style></head><body><header class='top'><h1>PeaCOBOL 1.3.0</h1><div>Local COBOL Enterprise, Test, Diagnostics and Assurance Workbench <span class='pill'>Loopback only</span></div></header><div class='layout'><nav class='nav'>{nav}</nav><main class='main'><div class='card notice'><b>{_e(dict(VIEWS).get(view,'Workbench'))}</b><div class='muted'>All paths are relative to the administrator-configured root. Symlinks and paths outside that root are rejected.</div></div>{error}{content}</main></div></body></html>"
            data=body.encode("utf-8"); self._headers(len(data)); self.wfile.write(data)
        def log_message(self,*_): pass
    return Handler
def main(argv=None):
    parser=argparse.ArgumentParser(prog="peacobol-ui"); parser.add_argument("--root",default=".",help="Only projects and files under this directory may be analyzed"); parser.add_argument("--port",type=int,default=8765); parser.add_argument("--open-browser",action="store_true")
    args=parser.parse_args(argv); root=Path(args.root)
    if root.is_symlink() or not root.resolve().is_dir(): raise SystemExit("Server root must be a regular directory")
    root=root.resolve(); token=secrets.token_urlsafe(24)
    url=f"http://127.0.0.1:{args.port}/?token={token}"
    print(f"PeaCOBOL UI: {url} (root: {root})")
    if args.open_browser:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass
    ThreadingHTTPServer(("127.0.0.1",args.port),handler_for(root,token)).serve_forever()
if __name__=="__main__": main()
