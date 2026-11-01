from __future__ import annotations
import argparse, json
from pathlib import Path
from .core import create_project, doctor, scan_project, parse_copybook, build, evidence

def emit(x, output=None):
    data=json.dumps(x,indent=2)
    if output: Path(output).write_text(data); print(output)
    else: print(data)

def main(argv=None):
    p=argparse.ArgumentParser(prog="peacobol",description="User-friendly COBOL development and assurance toolkit")
    sub=p.add_subparsers(dest="cmd",required=True)
    x=sub.add_parser("init"); x.add_argument("path"); x.add_argument("--name")
    sub.add_parser("doctor")
    for name in ("scan","build","evidence"):
        x=sub.add_parser(name); x.add_argument("path",nargs="?",default="."); x.add_argument("-o","--output")
    x=sub.add_parser("copybook"); x.add_argument("file"); x.add_argument("-o","--output")
    a=p.parse_args(argv)
    if a.cmd=="init": create_project(Path(a.path),a.name or Path(a.path).name); print(f"Created {a.path}")
    elif a.cmd=="doctor": emit(doctor())
    elif a.cmd=="scan": emit(scan_project(Path(a.path)),a.output)
    elif a.cmd=="copybook": emit([f.__dict__ for f in parse_copybook(Path(a.file))],a.output)
    elif a.cmd=="build": emit(build(Path(a.path)),a.output)
    elif a.cmd=="evidence":
        root=Path(a.path); emit(evidence(root,scan_project(root)),a.output)
if __name__=="__main__": main()
