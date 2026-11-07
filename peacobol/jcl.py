from __future__ import annotations
import re
from pathlib import Path
from typing import Any
from .profiles import load_profile
MEMBER_RE = re.compile(r"^[A-Z#$@][A-Z0-9#$@]{0,7}$")
DATASET_RE = re.compile(r"^[A-Z#$@][A-Z0-9#$@-]{0,7}(?:\.[A-Z#$@][A-Z0-9#$@-]{0,7})*$")
def _name(value: str, kind: str, pattern: re.Pattern[str]) -> str:
    value = value.upper()
    if not pattern.fullmatch(value):
        raise ValueError(f"Invalid {kind}: {value}")
    return value
def generate_jcl(root: Path, program: str, profile_name: str = "release", source_dataset: str = "USER.COBOL.SOURCE", load_dataset: str = "USER.COBOL.LOAD", copybook_dataset: str | None = None, run: bool = True) -> dict[str, Any]:
    root = root.resolve()
    profile = load_profile(root, profile_name)
    member = _name(program, "program member", MEMBER_RE)
    source_dataset = _name(source_dataset, "source dataset", DATASET_RE)
    load_dataset = _name(load_dataset, "load dataset", DATASET_RE)
    if copybook_dataset:
        copybook_dataset = _name(copybook_dataset, "copybook dataset", DATASET_RE)
    jcl_settings = profile["jcl"]
    compiler = jcl_settings["compiler"].upper()
    linker = jcl_settings["linker"].upper()
    compiler_library = jcl_settings["compiler_library"].upper()
    runtime = jcl_settings["runtime"].upper()
    parms = ",".join(value.upper() for value in jcl_settings["compiler_parms"])
    lines = [
        f"//{member:<8} JOB (PEACOBOL),'PEACOBOL BUILD',CLASS=A,MSGCLASS=X,NOTIFY=&SYSUID",
        f"//COMPILE  EXEC PGM={compiler},PARM='{parms}'",
        f"//STEPLIB  DD DISP=SHR,DSN={compiler_library}",
        f"//SYSIN    DD DISP=SHR,DSN={source_dataset}({member})",
    ]
    if copybook_dataset:
        lines.append(f"//SYSLIB   DD DISP=SHR,DSN={copybook_dataset}")
    lines.extend([
        "//SYSLIN   DD DSN=&&OBJECT,UNIT=SYSDA,DISP=(MOD,PASS),SPACE=(TRK,(3,3))",
        "//SYSPRINT DD SYSOUT=*",
        "//SYSUT1   DD UNIT=SYSDA,SPACE=(CYL,(1,1))",
        f"//LINK     EXEC PGM={linker},COND=(8,LT,COMPILE)",
        "//SYSLIN   DD DSN=&&OBJECT,DISP=(OLD,DELETE)",
        f"//SYSLMOD  DD DISP=SHR,DSN={load_dataset}({member})",
        "//SYSPRINT DD SYSOUT=*",
    ])
    if run:
        lines.extend([
            "//RUN      EXEC PGM=" + member + ",COND=(4,LT,LINK)",
            f"//STEPLIB  DD DISP=SHR,DSN={load_dataset}",
            f"//         DD DISP=SHR,DSN={runtime}",
            "//SYSOUT   DD SYSOUT=*",
            "//CEEDUMP  DD SYSOUT=*",
        ])
    return {
        "schema": "peacobol-jcl-1",
        "profile": profile_name,
        "program": member,
        "source_dataset": source_dataset,
        "load_dataset": load_dataset,
        "copybook_dataset": copybook_dataset,
        "includes_run_step": run,
        "jcl": "\n".join(lines) + "\n",
    }
