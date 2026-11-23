#!/usr/bin/env python3
"""Bootstrap the pinned local Visual C++ 7.1 (13.10.3077) compiler and support headers.

Fetches only the required sparse subtrees outside this Git checkout:
- MSVC 7.1 (13.10.3077) from Open-BFME/Open-BFME-1 (inputs/toolchains/vs2003)
- STLport 4.6, overlays, DXSDK Aug 2005, shims, and runner tools from Open-BFME/Open-BFME-2

Writes machine- and shell-readable environment files under the judge cache directory
(~/.cache/bfme2-judge by default) so contributors and coding agents can pre-check
translation units against baseline/game.dat before opening or updating a PR.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

VC71_REPO = "https://github.com/Open-BFME/Open-BFME-1.git"
VC71_COMMIT = "946f3c05a1b1e60448734e874a8f47f8017cfdb9"
VC71_SPARSE_PATHS = ("inputs/toolchains/vs2003",)
VC71_SUBDIR = Path("inputs/toolchains/vs2003/Program Files/Microsoft Visual Studio .NET 2003")
CL_EXE_SHA256 = "2ecf86a3edfd3deae498e08298e210e984537ce9e11759930561e43f40bd2515"

SUPPORT_REPO = "https://github.com/Open-BFME/Open-BFME-2.git"
SUPPORT_COMMIT = "39cdd2ca5c409c01b9c08d5dae7b3835c59a8b25"
SUPPORT_SPARSE_PATHS = (
    "tools",
    "vendor/stlport",
    "vendor/stlport-4.6",
    "vendor/stlport-4.6-bfme",
    "vendor/dxsdk-aug2005",
    "reference/shims",
)

BASE_CL_FLAGS = [
    "-nologo",
    "-c",
    "-O2",
    "-GR-",
    "-EHsc-",
    "-O1",
    "-arch:SSE",
    "-G7",
    "-DNDEBUG",
    "-MD",
    "-EHsc",
    "-Gy",
]


def _run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd is not None else None,
        text=True,
        capture_output=True,
        check=check,
    )


def _git_head(repo_dir: Path) -> str | None:
    if not (repo_dir / ".git").exists():
        return None
    proc = _run(["git", "-C", str(repo_dir), "rev-parse", "HEAD"], check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None


def _sparse_fetch(repo_url: str, commit: str, sparse_paths: tuple[str, ...], dest: Path) -> None:
    if _git_head(dest) == commit and all((dest / p).exists() for p in sparse_paths):
        return

    dest.mkdir(parents=True, exist_ok=True)
    if not (dest / ".git").exists():
        _run(["git", "init", str(dest)])
        _run(["git", "-C", str(dest), "remote", "add", "origin", repo_url])
    else:
        _run(["git", "-C", str(dest), "remote", "set-url", "origin", repo_url])

    _run(["git", "-C", str(dest), "config", "core.longpaths", "true"])
    _run(["git", "-C", str(dest), "sparse-checkout", "init", "--cone"])
    _run(["git", "-C", str(dest), "sparse-checkout", "set", *sparse_paths])
    _run(["git", "-C", str(dest), "fetch", "--depth", "1", "--filter=blob:none", "origin", commit])
    _run(["git", "-C", str(dest), "checkout", "--force", "FETCH_HEAD"])


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _detect_existing_vc71(repo_root: Path) -> Path | None:
    candidates = []
    if os.environ.get("VC71_ROOT"):
        candidates.append(Path(os.environ["VC71_ROOT"]))
    sibling = repo_root.parent / "Open-BFME-2" / "reference" / "open-bfme-1" / VC71_SUBDIR
    candidates.append(sibling)
    for cand in candidates:
        if (cand / "Vc7" / "bin" / "cl.exe").is_file():
            return cand.resolve()
    return None


def _detect_existing_runner(repo_root: Path) -> Path | None:
    candidates = []
    if os.environ.get("BFME_JUDGE_RUNNER"):
        candidates.append(Path(os.environ["BFME_JUDGE_RUNNER"]))
    sibling = repo_root.parent / "Open-BFME-2"
    candidates.append(sibling)
    for cand in candidates:
        if all((cand / p).exists() for p in ("vendor/stlport-4.6/stlport", "vendor/dxsdk-aug2005/Include", "tools")):
            return cand.resolve()
    return None


def _verify_vc71(vc71_root: Path) -> dict[str, str]:
    cl_exe = vc71_root / "Vc7" / "bin" / "cl.exe"
    required = [
        cl_exe,
        vc71_root / "Vc7" / "bin" / "c1xx.dll",
        vc71_root / "Vc7" / "bin" / "c2.dll",
        vc71_root / "Vc7" / "include" / "stdio.h",
        vc71_root / "Vc7" / "PlatformSDK" / "Include" / "Windows.h",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise RuntimeError("Incomplete VC7.1 installation; missing: " + ", ".join(missing))

    digest = _sha256(cl_exe)
    if digest != CL_EXE_SHA256:
        raise RuntimeError(
            f"Unexpected cl.exe SHA-256 at {cl_exe}: got {digest}, expected {CL_EXE_SHA256} (VC7.1 13.10.3077)"
        )
    return {
        "vc71_root": str(vc71_root),
        "cl_exe": str(cl_exe),
        "cl_exe_sha256": digest,
        "vc7_bin": str(vc71_root / "Vc7" / "bin"),
        "common7_ide": str(vc71_root / "Common7" / "IDE"),
        "runtime_dll_dir": str(vc71_root.parents[1]),
        "vc7_include": str(vc71_root / "Vc7" / "include"),
        "platformsdk_include": str(vc71_root / "Vc7" / "PlatformSDK" / "Include"),
        "vc7_lib": str(vc71_root / "Vc7" / "lib"),
    }


def _verify_runner(runner_root: Path) -> dict[str, str]:
    required = [
        runner_root / "tools",
        runner_root / "vendor" / "stlport-4.6" / "stlport",
        runner_root / "vendor" / "stlport-4.6-bfme",
        runner_root / "vendor" / "dxsdk-aug2005" / "Include",
        runner_root / "reference" / "shims",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise RuntimeError("Incomplete support tree; missing: " + ", ".join(missing))
    return {
        "runner_root": str(runner_root),
        "stlport46_include": str(runner_root / "vendor" / "stlport-4.6" / "stlport"),
        "stlport46_overlay": str(runner_root / "vendor" / "stlport-4.6-bfme"),
        "dxsdk_include": str(runner_root / "vendor" / "dxsdk-aug2005" / "Include"),
        "shims_root": str(runner_root / "reference" / "shims"),
    }


def _smoke_check_cl(vc_info: dict[str, str]) -> tuple[bool, str]:
    cl_exe = vc_info["cl_exe"]
    if os.name == "nt":
        env = dict(os.environ)
        env["PATH"] = os.pathsep.join(
            [vc_info["vc7_bin"], vc_info["common7_ide"], vc_info["runtime_dll_dir"], env.get("PATH", "")]
        )
        proc = subprocess.run([cl_exe], text=True, capture_output=True, env=env, check=False)
        banner = (proc.stderr or proc.stdout).strip().splitlines()
        line = banner[0] if banner else ""
        return ("13.10.3077" in (proc.stderr + proc.stdout)), line

    wine = shutil.which("wine")
    if not wine:
        return True, "wine not installed; skipped compiler banner probe"
    env = dict(os.environ)
    env["WINEDEBUG"] = "-all"
    proc = subprocess.run([wine, cl_exe], text=True, capture_output=True, env=env, check=False)
    banner = (proc.stderr or proc.stdout).strip().splitlines()
    line = banner[0] if banner else ""
    return ("13.10.3077" in (proc.stderr + proc.stdout)), line


def _write_env_files(state_dir: Path, repo_root: Path, vc_info: dict[str, str], runner_info: dict[str, str]) -> dict[str, str]:
    state_dir.mkdir(parents=True, exist_ok=True)
    retail = repo_root / "baseline" / "game.dat"
    default_include = os.pathsep.join(
        [runner_info["stlport46_include"], vc_info["vc7_include"], vc_info["platformsdk_include"]]
    )
    payload = {
        "vc71": vc_info,
        "support": runner_info,
        "judge_env": {
            "VC71_ROOT": vc_info["vc71_root"],
            "BFME_JUDGE_RUNNER": runner_info["runner_root"],
            "BFME_JUDGE_RETAIL": str(retail),
            "BFME_JUDGE_STATE": str(state_dir),
            "BFME_JUDGE_WINEPREFIX": str(state_dir / "wine"),
        },
        "native_cl_env": {
            "INCLUDE": default_include,
            "LIB": vc_info["vc7_lib"],
            "PATH_PREFIX": [vc_info["vc7_bin"], vc_info["common7_ide"], vc_info["runtime_dll_dir"]],
        },
        "base_cl_flags": BASE_CL_FLAGS,
        "sources": {
            "vc71_repo": VC71_REPO,
            "vc71_commit": VC71_COMMIT,
            "support_repo": SUPPORT_REPO,
            "support_commit": SUPPORT_COMMIT,
        },
    }

    json_path = state_dir / "toolchain.json"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    sh_path = state_dir / "toolchain-env.sh"
    sh_lines = [
        "# Generated by tools/setup_local_toolchain.py",
        f'export VC71_ROOT="{vc_info["vc71_root"]}"',
        f'export BFME_JUDGE_RUNNER="{runner_info["runner_root"]}"',
        f'export BFME_JUDGE_RETAIL="{retail}"',
        f'export BFME_JUDGE_STATE="{state_dir}"',
        f'export BFME_JUDGE_WINEPREFIX="{state_dir / "wine"}"',
        "",
    ]
    sh_path.write_text("\n".join(sh_lines), encoding="utf-8", newline="\n")

    ps1_path = state_dir / "toolchain-env.ps1"
    ps1_lines = [
        "# Generated by tools/setup_local_toolchain.py",
        f'$env:VC71_ROOT = "{vc_info["vc71_root"]}"',
        f'$env:BFME_JUDGE_RUNNER = "{runner_info["runner_root"]}"',
        f'$env:BFME_JUDGE_RETAIL = "{retail}"',
        f'$env:BFME_JUDGE_STATE = "{state_dir}"',
        f'$env:INCLUDE = "{default_include}"',
        f'$env:LIB = "{vc_info["vc7_lib"]}"',
        f'$env:PATH = "{vc_info["vc7_bin"]};{vc_info["common7_ide"]};{vc_info["runtime_dll_dir"]};" + $env:PATH',
        "",
    ]
    ps1_path.write_text("\n".join(ps1_lines), encoding="utf-8", newline="\n")

    return {
        "toolchain_json": str(json_path),
        "env_sh": str(sh_path),
        "env_ps1": str(ps1_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path(os.environ.get("BFME_JUDGE_STATE", str(Path.home() / ".cache" / "bfme2-judge"))),
        help="Cache directory outside Git for toolchains and generated env files (default: ~/.cache/bfme2-judge)",
    )
    parser.add_argument("--vc71-root", type=Path, help="Use an existing Visual Studio .NET 2003 directory instead of downloading")
    parser.add_argument("--runner-root", type=Path, help="Use an existing Open-BFME-2 support checkout instead of downloading")
    parser.add_argument("--force-download", action="store_true", help="Always fetch pinned sparse checkouts into --state-dir")
    parser.add_argument("--no-smoke", action="store_true", help="Skip running cl.exe to verify the 13.10.3077 banner")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON summary")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    state_dir = args.state_dir.expanduser().resolve()
    toolchains_dir = state_dir / "toolchains"

    vc71_root = args.vc71_root.expanduser().resolve() if args.vc71_root else None
    if vc71_root is None and not args.force_download:
        vc71_root = _detect_existing_vc71(repo_root)
    if vc71_root is None:
        vc71_checkout = toolchains_dir / "open-bfme-1"
        if not args.json:
            print(f"Fetching VC7.1 (13.10.3077) sparse checkout into {vc71_checkout} ...", file=sys.stderr)
        _sparse_fetch(VC71_REPO, VC71_COMMIT, VC71_SPARSE_PATHS, vc71_checkout)
        vc71_root = (vc71_checkout / VC71_SUBDIR).resolve()

    runner_root = args.runner_root.expanduser().resolve() if args.runner_root else None
    if runner_root is None and not args.force_download:
        runner_root = _detect_existing_runner(repo_root)
    if runner_root is None:
        runner_checkout = toolchains_dir / "open-bfme-2-support"
        if not args.json:
            print(f"Fetching STLport/DXSDK/shims sparse checkout into {runner_checkout} ...", file=sys.stderr)
        _sparse_fetch(SUPPORT_REPO, SUPPORT_COMMIT, SUPPORT_SPARSE_PATHS, runner_checkout)
        runner_root = runner_checkout.resolve()

    vc_info = _verify_vc71(vc71_root)
    runner_info = _verify_runner(runner_root)
    written = _write_env_files(state_dir, repo_root, vc_info, runner_info)

    smoke_ok = True
    smoke_detail = "skipped"
    if not args.no_smoke:
        smoke_ok, smoke_detail = _smoke_check_cl(vc_info)
        if not smoke_ok:
            raise RuntimeError(f"cl.exe smoke check failed (expected 13.10.3077 banner): {smoke_detail}")

    summary = {
        "status": "ok",
        "vc71_root": vc_info["vc71_root"],
        "cl_exe": vc_info["cl_exe"],
        "cl_exe_sha256": vc_info["cl_exe_sha256"],
        "runner_root": runner_info["runner_root"],
        "smoke_check": smoke_detail,
        **written,
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print("Local VC7.1 toolchain ready:")
        print(f"  VC71_ROOT         = {vc_info['vc71_root']}")
        print(f"  cl.exe            = {vc_info['cl_exe']} (sha256 {vc_info['cl_exe_sha256'][:12]}...)")
        print(f"  BFME_JUDGE_RUNNER = {runner_info['runner_root']}")
        print(f"  Smoke check       = {smoke_detail}")
        print(f"  Env files         = {written['toolchain_json']}")
        print(f"                      {written['env_sh']}")
        print(f"                      {written['env_ps1']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
