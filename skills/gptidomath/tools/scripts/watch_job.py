#!/usr/bin/env python3
"""Watch a task for DONE, NEW-ZIP, STALL or timeout.

Exit 0: DONE/NEW-ZIP/STALL (read the printed event); 1: I/O/data error;
2: timeout or CLI usage; 130: interruption. Stall defaults to 35 quiet minutes.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

from kit_config import load_config, workspace_root
from mirror_io import held, inside, safe_segment
from channel_io import console, local_state, marker_text, number, positive, read_state, save_state, snapshot


def activity(task: Path, marker: str, now: float) -> tuple[dict, float]:
    """Persist observed output metadata and the real write time, never the restart time."""
    state_path = local_state(task / marker, "watch")
    with held(state_path, "watch state", 120):
        state = read_state(state_path)
        current = snapshot(task, ignore_probe=False, exclude=marker)
        if state:
            previous = state["files"]
            last = float(state["last_activity"])
            changed = [stamp[0] / 1e9 for name, stamp in current.items() if previous.get(name) != stamp]
            if changed:
                last = max(last, min(now, max(changed)))
        else:
            last = min(now, max((stamp[0] / 1e9 for stamp in current.values()), default=now))
        updated = {"files": current, "last_activity": last}
        if updated != state:
            save_state(state_path, updated)
        return current, last


def zip_names(files: dict, match: str) -> set[str]:
    return {name for name in files if name.lower().endswith(".zip") and match in name}


def check(task: Path, marker: str, match: str, baseline: set[str], files: dict,
          last_activity: float, now: float, stall: float) -> tuple[str, str] | None:
    body = marker_text(task / marker)
    if body:
        return "DONE", body
    new = sorted(zip_names(files, match) - baseline)
    if new:
        return "NEW-ZIP", " ".join(new)
    if stall and now - last_activity >= stall:
        return "STALL", f"No remote output writes for {int((now - last_activity) / 60)} minutes; inspect the conversation."
    return None


def watch(task: Path, marker: str, match: str, stall: float, limit: float, every: float) -> int:
    started = time.monotonic()
    current, last = activity(task, marker, time.time())
    baseline = zip_names(current, match)
    while True:
        event = check(task, marker, match, baseline, current, last, time.time(), stall)
        if event:
            print(f"{event[0]} {event[1]}", flush=True)
            return 0
        if time.monotonic() - started >= limit:
            print("timeout: re-arm the watcher; the saved stall clock is unchanged", flush=True)
            return 2
        time.sleep(min(every, max(0, limit - (time.monotonic() - started))))
        current, last = activity(task, marker, time.time())


def selftest() -> int:
    with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {"GPTIDOMATH_HOME": td}):
        root = Path(td) / "task"
        root.mkdir()
        current, last = activity(root, "DONE.txt", 1000)
        assert last == 1000 and current == {}
        current, again = activity(root, "DONE.txt", 5000)
        assert again == last  # A restart with no outputs must not reset the stall clock.
        for name in ("REQUEST.md", "reply.txt", "reply1-data.zip", "TASK-a.md", "upload.tmp",
                     "REQUEST.md.gdoc", "reply.txt.gdoc", "TASK-a.md.gdoc"):
            (root / name).write_text("ours")
        (root / "DONE.txt.gdoc").write_bytes(b"")
        (root / "inputs").mkdir()
        (root / "inputs" / "reference.zip").write_bytes(b"x")
        current, again = activity(root, "DONE.txt", 5001)
        assert current == {} and again == last
        assert check(root, "DONE.txt", "", set(), current, last, 5001, 2100)[0] == "STALL"
        output = root / "stage.zip"
        output.write_bytes(b"zip")
        os.utime(output, (5100, 5100))
        current, last = activity(root, "DONE.txt", 5101)
        assert last == 5100 and check(root, "DONE.txt", "", set(), current, last, 5101, 2100)[0] == "NEW-ZIP"
        remote_reply = root / "REPLY-example-09-four-commits.zip"
        remote_reply.write_bytes(b"remote delivery")
        os.utime(remote_reply, (5150, 5150))
        baseline = zip_names(current, "")
        current, last = activity(root, "DONE.txt", 5151)
        assert last == 5150
        assert check(root, "DONE.txt", "", baseline, current, last, 5151, 2100) == ("NEW-ZIP", remote_reply.name)
        (root / "DONE.txt").write_bytes(b"")
        (root / "DONE.txt.gdoc").write_text('{"resource_id":"document-reference"}')
        assert check(root, "DONE.txt", "other", set(), current, last, 5101, 2100) is None
        (root / "DONE.txt.gdoc").write_text("finished through alias")
        assert check(root, "DONE.txt", "", set(), current, last, 9999, 2100)[0] == "DONE"
        (root / "DONE.txt.gdoc").unlink()
        (root / "DONE.txt").write_text("finished", encoding="utf-8-sig")
        assert check(root, "DONE.txt", "", set(), current, last, 9999, 2100)[0] == "DONE"
        (root / "DONE.txt").unlink()
        with contextlib.redirect_stdout(io.StringIO()):
            assert watch(root, "DONE.txt", "", 0, 0, 0.01) == 2
        _, last = activity(root, "DONE.txt", 8000)
        assert last == 5150
    print("selftest PASS: watch_job (events, controls, empty marker, restart persistence, timeout)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", nargs="?")
    parser.add_argument("--done", default="DONE.txt", help="marker basename; use a new name for a new round")
    parser.add_argument("--zip-match", default="", help="case-sensitive substring")
    parser.add_argument("--stall", type=number, default=2100, help="quiet seconds; 0 disables")
    parser.add_argument("--limit", type=number, default=7000, help="runtime seconds; 0 checks once")
    parser.add_argument("--every", type=positive, default=60, help="poll seconds")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if not args.tag:
        parser.error("provide a task ID")
    try:
        root = workspace_root(load_config(args.config))
        task = inside(root, root / safe_segment(args.tag, "task ID"))
        return watch(task, safe_segment(args.done, "marker"), args.zip_match, args.stall, args.limit, args.every)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    console()
    sys.exit(main())
