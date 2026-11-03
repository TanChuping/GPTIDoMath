#!/usr/bin/env python3
"""Run each local tool's selftest, including optional tools installed alongside it."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true", help="Run the full suite (also the default)")
    args = parser.parse_args(argv)
    del args
    here = Path(__file__).resolve().parent
    required = {"kit_config.py", "secret_patterns.py", "code_index.py", "drive_mirror.py",
                "drive_workspace.py", "drive_request.py", "web_ask.py", "drive_wait.py", "watch_job.py"}
    files = sorted(path for path in here.glob("*.py") if path.name != Path(__file__).name)
    channel = here.parent / "request-channel" / "channel.py"
    missing = sorted(required - {path.name for path in files})
    if not channel.is_file():
        missing.append("request-channel/channel.py")
    if missing:
        print("selftest_all FAIL: missing " + ", ".join(missing))
        return 1
    files.append(channel)
    failures: list[str] = []
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    for path in files:
        label = path.relative_to(here.parent).as_posix()
        try:
            result = subprocess.run([sys.executable, "-B", str(path), "--selftest"],
                                    cwd=here.parent, env=env, capture_output=True, stdin=subprocess.DEVNULL,
                                    text=True, encoding="utf-8", errors="replace", timeout=180)
            for line in (result.stdout + result.stderr).splitlines():
                print(f"{label}: {line}", flush=True)
            if result.returncode:
                failures.append(label)
                print(f"{label}: FAIL (exit {result.returncode})", flush=True)
            elif not result.stdout.strip():
                print(f"{label}: PASS", flush=True)
        except (OSError, subprocess.TimeoutExpired) as exc:
            failures.append(label)
            print(f"{label}: FAIL ({exc})", flush=True)
    print(f"selftest_all {'FAIL' if failures else 'PASS'}: {len(files) - len(failures)}/{len(files)} tools")
    return int(bool(failures))


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
