#!/usr/bin/env python3
"""Optional SessionStart hook: after a restart or compaction, list task folders that may still be running.

A folder counts as open when its newest TASK*.md is newer than its newest DONE*.txt that the watchers
would accept (readable, not blank; Drive's .gdoc aliases count) and was
written in the last three days. The hook prints the watcher commands for each open folder, prints
nothing when nothing is open or no workspace is configured, and never fails the session start.
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from channel_io import canonical_name, marker_text
from kit_config import load_config, workspace_root

MAX_AGE = 3 * 24 * 3600
HERE = Path(__file__).resolve().parent


def open_jobs(root: Path, now: float) -> list[tuple[str, str, float, bool]]:
    """(tag, newest task file, its mtime, an older marker exists) for each open task folder."""
    jobs = []
    for folder in sorted(path for path in root.iterdir() if path.is_dir()):
        if folder.name.lower() in {"repos", "tools"}:
            continue
        tasks = [path for path in folder.glob("TASK*.md") if path.is_file()]
        if not tasks:
            continue
        task = max(tasks, key=lambda path: path.stat().st_mtime)
        written = task.stat().st_mtime
        if now - written > MAX_AGE:
            continue
        markers = accepted_markers(folder)
        if markers and max(markers) >= written:
            continue
        jobs.append((folder.name, task.name, written, bool(markers)))
    return jobs


def accepted_markers(folder: Path) -> list[float]:
    """Modification times of the DONE*.txt markers the watchers accept (readable text, .gdoc aliases included)."""
    times = []
    for path in folder.iterdir():
        name = canonical_name(path.name)
        if name.startswith("done") and name.endswith(".txt") and path.is_file() and marker_text(path):
            times.append(path.stat().st_mtime)
    return times


def message(root: Path, jobs: list[tuple[str, str, float, bool]], now: float) -> str:
    def q(value: object) -> str:
        return f'"{value}"'

    python = q(sys.executable)
    lines = [f"GPTIDoMath: {len(jobs)} task folder(s) in {root} have a task file but no delivery marker yet, "
             "so the ChatGPT job may still be running. If you were watching them before this session restarted, "
             "start the watchers again, each as a background task, and re-arm each one after it wakes you. "
             "The commands are for a POSIX shell such as Git Bash; in PowerShell put & in front of each:"]
    for tag, task, written, older_marker in jobs:
        marker = f"<the marker {task} names>" if older_marker else "DONE.txt"
        lines.append(f"- {tag}: {task} written {(now - written) / 3600:.1f} h ago")
        lines.append(f"    {python} {q(HERE / 'drive_wait.py')} {q(root / tag / marker)} --every 20 --quiet 10 --start 0")
        done = f" --done {q(marker)}" if older_marker else ""
        lines.append(f"    {python} {q(HERE / 'watch_job.py')} {q(tag)} --stall 2100 --limit 7000 --every 60{done}")
    lines.append(f"If the task allows local-run requests, also run {python} {q(HERE / 'web_ask.py')} wait \"<tag>\". "
                 f"Ignore folders you have abandoned. Manual: {HERE.parent / 'manuals' / 'watch.md'}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--selftest"]:
        return selftest()
    try:
        root = workspace_root(load_config())
        now = time.time()
        jobs = open_jobs(root, now)
        if jobs:
            print(message(root, jobs, now))
    except Exception:  # A reminder must never block the session from starting.
        pass
    return 0


def selftest() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / "AI-workspace"
        now = time.time()

        def put(relative: str, age_hours: float, text: str = "x") -> None:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            os.utime(path, (now - age_hours * 3600,) * 2)

        put("running/TASK.md", 2)
        put("delivered/TASK.md", 3)
        put("delivered/DONE.txt", 1)
        put("second-part/TASK.md", 5)
        put("second-part/DONE.txt", 4)
        put("second-part/TASK-2.md", 1)
        put("blank-marker/TASK.md", 2)
        put("blank-marker/DONE.txt", 1, "  \n")
        put("drive-alias/TASK.md", 3)
        put("drive-alias/DONE.txt.gdoc", 1, "finished 1 / unfinished 0 / stage.zip")
        put("audit math/TASK.md", 1)
        put("abandoned/TASK.md", 24 * 4)
        put("repos/project/TASK.md", 1)
        (root / "no-task").mkdir()
        jobs = open_jobs(root, now)
        assert [job[0] for job in jobs] == ["audit math", "blank-marker", "running", "second-part"], jobs
        assert [job[3] for job in jobs] == [False, False, False, True], jobs
        text = message(root, jobs, now)
        assert "running: TASK.md written 2.0 h ago" in text and '--done "<the marker TASK-2.md names>"' in text
        assert f'"{root / "running" / "DONE.txt"}"' in text and '"audit math" --stall' in text
        assert "- delivered:" not in text and "- abandoned:" not in text and "- drive-alias:" not in text

        config = Path(temporary) / "config.json"
        config.write_text("{}", encoding="utf-8")
        for workspace, expect in ((root, "4 task folder(s)"), (Path(temporary) / "missing", "")):
            with patch.dict(os.environ, {"GPTIDOMATH_CONFIG": str(config), "GPTIDOMATH_WORKSPACE": str(workspace)}), \
                    contextlib.redirect_stdout(io.StringIO()) as out:
                assert main([]) == 0
            assert (expect in out.getvalue()) if expect else out.getvalue() == "", out.getvalue()
    print("selftest PASS: open_jobs_hook (open, delivered, continuation, blank marker, Drive alias, quoting, age, reserved, no workspace)")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
