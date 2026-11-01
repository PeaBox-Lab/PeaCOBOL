from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import json, html
from .core import scan_project, doctor

PAGE='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>PeaCOBOL</title><style>
:root{font-family:Segoe UI,Arial;background:#f4f7fb;color:#172033}body{margin:0}.top{background:#102a43;color:white;padding:18px 28px}.wrap{max-width:1180px;margin:24px auto;padding:0 18px}.bar,.card{background:white;border:1px solid #d9e2ec;border-radius:12px;padding:16px;margin-bottom:16px;box-shadow:0 3px 12px #102a4312}input{width:70%;padding:12px;border:1px solid #bcccdc;border-radius:8px}button{padding:12px 18px;background:#087f5b;color:white;border:0;border-radius:8px;font-weight:600}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}.metric{font-size:30px;font-weight:700}.high{color:#c92a2a}.medium{color:#e67700}.low{color:#1971c2}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px;border-bottom:1px solid #e9ecef}code{background:#edf2f7;padding:2px 5px}</style></head><body><div class="top"><h1>PeaCOBOL</h1><div>COBOL development and assurance workspace</div></div><main class="wrap"><form class="bar"><input name="path" value="{path}" aria-label="Project path"><button>Analyze project</button></form>{content}</main></body></html>'''
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  q=parse_qs(urlparse(self.path).query); path=Path(q.get('path',['.'])[0]); content='<div class="card">Enter a local COBOL project path. No source leaves this machine.</div>'
  if 'path' in q:
   if not path.exists(): content='<div class="card high">Path not found.</div>'
   else:
    r=scan_project(path); f=r['findings']; counts={s:sum(x['severity']==s for x in f) for s in ('high','medium','low')}
    rows=''.join(f"<tr><td><code>{html.escape(x['rule'])}</code></td><td class='{x['severity']}'>{x['severity']}</td><td>{html.escape(x['file'])}:{x['line']}</td><td>{html.escape(x['message'])}</td><td>{html.escape(x['remediation'])}</td></tr>" for x in f) or '<tr><td colspan=5>No findings</td></tr>'
    content=f'''<div class="grid"><div class="card"><div>Programs</div><div class="metric">{len(r['programs'])}</div></div><div class="card"><div>Copybooks</div><div class="metric">{len(r['copybooks'])}</div></div><div class="card"><div>Calls</div><div class="metric">{len(r['calls'])}</div></div><div class="card"><div>High risks</div><div class="metric high">{counts['high']}</div></div></div><div class="card"><h2>Assurance findings</h2><table><thead><tr><th>Rule</th><th>Severity</th><th>Location</th><th>Finding</th><th>Remediation</th></tr></thead><tbody>{rows}</tbody></table></div>'''
  data=PAGE.format(path=html.escape(str(path)),content=content).encode(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
 def log_message(self,*a): pass

def main():
 print('PeaCOBOL UI: http://127.0.0.1:8765'); ThreadingHTTPServer(('127.0.0.1',8765),Handler).serve_forever()
if __name__=='__main__': main()
