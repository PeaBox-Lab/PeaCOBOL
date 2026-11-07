from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

PROFILE_SCHEMA = "peacobol-profile-1"

BUILTIN_PROFILES: dict[str, dict[str, Any]] = {
    "development": {
        "description": "Fast local feedback with portable defaults.",
        "compiler": {"dialect": "default", "flags": ["-Wall"], "optimize": False},
        "data": {"encoding": "ascii", "binary_byteorder": "big", "binary_signed": True},
        "policy": {"max_findings": {"critical": 0, "high": None, "medium": None, "low": None}, "fail_on_build_warning": False, "require_evidence": False},
        "jcl": {"compiler": "IGYCRCTL", "linker": "IEWL", "compiler_library": "IGY.V6R4M0.SIGYCOMP", "runtime": "CEE.RUNLIB.LOAD", "compiler_parms": ["LIB", "OBJECT", "RENT"]},
    },
    "release": {
        "description": "Reproducible release build with warning and evidence gates.",
        "compiler": {"dialect": "default", "flags": ["-Wall", "-Wextra"], "optimize": True},
        "data": {"encoding": "ascii", "binary_byteorder": "big", "binary_signed": True},
        "policy": {"max_findings": {"critical": 0, "high": 0, "medium": None, "low": None}, "fail_on_build_warning": True, "require_evidence": True},
        "jcl": {"compiler": "IGYCRCTL", "linker": "IEWL", "compiler_library": "IGY.V6R4M0.SIGYCOMP", "runtime": "CEE.RUNLIB.LOAD", "compiler_parms": ["LIB", "OBJECT", "RENT", "SSRANGE"]},
    },
    "banking": {
        "description": "EBCDIC and decimal-focused controls for financial workloads.",
        "compiler": {"dialect": "ibm", "flags": ["-Wall", "-Wextra"], "optimize": True},
        "data": {"encoding": "cp037", "binary_byteorder": "big", "binary_signed": True},
        "policy": {"max_findings": {"critical": 0, "high": 0, "medium": 0, "low": None}, "fail_on_build_warning": True, "require_evidence": True},
        "jcl": {"compiler": "IGYCRCTL", "linker": "IEWL", "compiler_library": "IGY.V6R4M0.SIGYCOMP", "runtime": "CEE.RUNLIB.LOAD", "compiler_parms": ["LIB", "OBJECT", "RENT", "SSRANGE", "NUMCHECK"]},
    },
    "aerospace": {
        "description": "Strict deterministic controls for safety-oriented workloads.",
        "compiler": {"dialect": "ibm", "flags": ["-Wall", "-Wextra"], "optimize": False},
        "data": {"encoding": "cp037", "binary_byteorder": "big", "binary_signed": True},
        "policy": {"max_findings": {"critical": 0, "high": 0, "medium": 0, "low": 0}, "fail_on_build_warning": True, "require_evidence": True},
        "jcl": {"compiler": "IGYCRCTL", "linker": "IEWL", "compiler_library": "IGY.V6R4M0.SIGYCOMP", "runtime": "CEE.RUNLIB.LOAD", "compiler_parms": ["LIB", "OBJECT", "RENT", "SSRANGE", "NUMCHECK", "INITCHECK"]},
    },
}


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _validate(name: str, profile: dict[str, Any]) -> None:
    compiler = profile.get("compiler", {})
    flags = compiler.get("flags")
    allowed_flags = {"-Wall", "-Wextra", "-O0", "-O1", "-O2", "-O3"}
    if compiler.get("dialect") not in {"default", "ibm"}:
        raise ValueError(f"Profile {name!r} has an unsupported compiler dialect")
    if not isinstance(compiler.get("optimize"), bool):
        raise ValueError(f"Profile {name!r} requires a boolean compiler optimize setting")
    if not isinstance(flags, list) or any(not isinstance(flag, str) or flag not in allowed_flags for flag in flags):
        raise ValueError(f"Profile {name!r} contains unsupported compiler flags")
    data = profile.get("data", {})
    if data.get("encoding") not in {"ascii", "utf-8", "cp037", "cp500"}:
        raise ValueError(f"Profile {name!r} has an unsupported encoding")
    if data.get("binary_byteorder") not in {"big", "little"}:
        raise ValueError(f"Profile {name!r} must use big or little binary byte order")
    limits = profile.get("policy", {}).get("max_findings", {})
    for severity in ("critical", "high", "medium", "low"):
        value = limits.get(severity)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
            raise ValueError(f"Profile {name!r} has an invalid {severity} finding limit")
    jcl = profile.get("jcl", {})
    member = re.compile(r"^[A-Z#$@][A-Z0-9#$@]{0,7}$")
    dataset = re.compile(r"^[A-Z#$@][A-Z0-9#$@-]{0,7}(?:\.[A-Z#$@][A-Z0-9#$@-]{0,7})*$")
    option = re.compile(r"^[A-Z0-9][A-Z0-9()+-]{0,31}$")
    for key in ("compiler", "linker"):
        if not isinstance(jcl.get(key), str) or not member.fullmatch(jcl[key].upper()):
            raise ValueError(f"Profile {name!r} has an invalid JCL {key}")
    for key in ("compiler_library", "runtime"):
        if not isinstance(jcl.get(key), str) or not dataset.fullmatch(jcl[key].upper()):
            raise ValueError(f"Profile {name!r} has an invalid JCL {key}")
    parms = jcl.get("compiler_parms")
    if not isinstance(parms, list) or not parms or any(not isinstance(value, str) or not option.fullmatch(value.upper()) for value in parms):
        raise ValueError(f"Profile {name!r} has invalid JCL compiler parameters")


def load_profile(root: Path | None = None, name: str = "development") -> dict[str, Any]:
    if name not in BUILTIN_PROFILES:
        raise ValueError(f"Unknown build profile: {name}. Available: {', '.join(sorted(BUILTIN_PROFILES))}")
    profile = copy.deepcopy(BUILTIN_PROFILES[name])
    source = "builtin"
    if root is not None:
        config_path = root.resolve() / "peacobol.json"
        if config_path.exists():
            config = json.loads(config_path.read_text(encoding="utf-8"))
            override = config.get("profiles", {}).get(name)
            if override is not None:
                if not isinstance(override, dict):
                    raise ValueError(f"Profile override {name!r} must be an object")
                profile = _merge(profile, override)
                source = config_path.name
    _validate(name, profile)
    return {"schema": PROFILE_SCHEMA, "name": name, "source": source, **profile}


def resolve_profile_name(root: Path | None, requested: str | None, fallback: str) -> str:
    if requested:
        return requested
    if root is not None:
        config_path = root.resolve() / "peacobol.json"
        if config_path.exists():
            config = json.loads(config_path.read_text(encoding="utf-8"))
            selected = config.get("default_profile")
            if selected is not None:
                if selected not in BUILTIN_PROFILES:
                    raise ValueError(f"Unknown default profile: {selected}")
                return selected
    return fallback


def list_profiles(root: Path | None = None) -> dict[str, Any]:
    return {
        "schema": "peacobol-profile-list-1",
        "profiles": [load_profile(root, name) for name in BUILTIN_PROFILES],
    }
