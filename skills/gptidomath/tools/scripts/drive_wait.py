#!/usr/bin/env python3
"""Wait for readable non-empty DONE, or ask for a review after new output goes quiet.

Exit 0 DONE; 1 I/O/data error; 2 quiet-output review (also CLI usage);
3 no start probe; 4 timeout; 130 interruption. Quiet and start are minutes.
"""
from __future__ import annotations

import argparse
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import threading
import time

from channel_io import console, marker_text, number, positive, snapshot


def listing(directory: Path) -> None:
    for name, (_, size) in sorted(snapshot(directory, recursive=True).items()):
        print(f"  {size:10d}  {name}", flush=True)


def wait(path: Path, every: float, quiet_min: float = 10, start_min: float = 6,
         timeout: float = 0, settle: float = 2) -> int:
    started = time.monotonic()
    directory = path.parent
    previous = snapshot(directory, recursive=True, exclude=path.name)
    last_change = None
    probe = directory / "test.txt"
    watch_start = bool(start_min) and not marker_text(probe)
    print(f"[drive_wait] {path}; poll {every:g}s; quiet {quiet_min:g}m; start {start_min:g}m", flush=True)
    while True:
        body = marker_text(path)
        if body:
            if settle:
                time.sleep(settle)
            if marker_text(path) == body:
                print(f"DONE\n{body}", flush=True)
                listing(directory)
                return 0
        now = time.monotonic()
        if watch_start:
            if marker_text(probe):
                watch_start = False
            elif now - started >= start_min * 60:
                print("NO-START: test.txt has no readable content. Check sync and the first-write approval in the conversation.", flush=True)
                return 3
        current = snapshot(directory, recursive=True, exclude=path.name)
        wrote_output = any(previous.get(name) != stamp for name, stamp in current.items())
        if wrote_output or (last_change is not None and current != previous):
            last_change = now
        previous = current
        if quiet_min and last_change is not None and now - last_change >= quiet_min * 60:
            print("QUIET: new outputs went quiet without readable DONE. Review the conversation, ZIP and NOTES.md; this is not proof of completion.", flush=True)
            listing(directory)
            return 2
        if timeout and now - started >= timeout:
            print("timeout: no completion event", flush=True)
            return 4
        time.sleep(every)


def selftest() -> int:
    with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
        root = Path(td)
        done = root / "DONE.txt"
        done.write_text("finished", encoding="utf-8-sig")
        assert wait(done, 0.005, 0, 0, 1, 0) == 0
        done.write_bytes(b"")
        assert wait(done, 0.005, 0, 0, 0.02, 0) == 4
        alias = root / "DONE.txt.gdoc"
        alias.write_text("finished through alias")
        assert wait(done, 0.005, 0, 0, 0.02, 0) == 0
        alias.write_text('{"url":"document-reference"}')
        assert wait(done, 0.005, 0, 0, 0.02, 0) == 4
        alias.unlink()
        timer = threading.Timer(0.02, lambda: done.write_text("finished"))
        timer.start()
        try:
            assert wait(done, 0.005, 0, 0, 1, 0) == 0
        finally:
            timer.join()
        done.unlink()
        assert wait(done, 0.005, 0, 0.0002, 1, 0) == 3
        probe_alias = root / "test.txt.gdoc"
        probe_alias.write_text("1")
        assert wait(done, 0.005, 0, 0.0002, 0.03, 0) == 4
        probe_alias.write_text('{"doc_id":"document-reference"}')
        assert wait(done, 0.005, 0, 0.0002, 1, 0) == 3
        probe_alias.unlink()
        (root / "test.txt").write_text("1")
        (root / "old.zip").write_text("old")
        assert wait(done, 0.005, 0.0002, 0.0002, 0.03, 0) == 4
        timer = threading.Timer(0.01, lambda: (root / "result.zip").write_bytes(b"output"))
        timer.start()
        try:
            assert wait(done, 0.005, 0.0002, 0, 1, 0) == 2
        finally:
            timer.join()
        def control_writes():
            for name in ("REQUEST.md", "reply2-data.zip", "TASK.md", ".DS_Store", "upload.tmp",
                         "REQUEST.md.gdoc", "TASK.md.gdoc", "reply.txt.gdoc", "test.txt.gdoc"):
                (root / name).write_text("local control")
        timer = threading.Timer(0.01, control_writes)
        timer.start()
        try:
            assert wait(done, 0.005, 0.0002, 0, 0.04, 0) == 4
        finally:
            timer.join()
    print("selftest PASS: drive_wait (DONE, gdoc aliases, empty marker, quiet output, controls, startup, timeout)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("marker", nargs="?", type=Path, help="local path to DONE.txt")
    parser.add_argument("--every", type=positive, default=20, help="poll seconds")
    parser.add_argument("--quiet", type=number, default=10, help="quiet minutes; 0 disables")
    parser.add_argument("--start", type=number, default=6, help="test.txt deadline in minutes; 0 disables")
    parser.add_argument("--timeout", type=number, default=0, help="seconds; 0 waits indefinitely")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if args.marker is None:
        parser.error("provide the task's local DONE.txt path")
    try:
        return wait(args.marker.expanduser(), args.every, args.quiet, args.start, args.timeout)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    console()
    sys.exit(main())
