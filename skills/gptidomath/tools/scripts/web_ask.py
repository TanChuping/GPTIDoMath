#!/usr/bin/env python3
"""Receive local-run requests and publish replies. Never executes requested commands.

Exit 0: success/new request; 1: I/O or data error; 2: timeout or CLI usage;
130: interrupted. Attachments are published in the task root, then reply.txt.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from kit_config import load_config, workspace_root
from mirror_io import copy_atomic, held, inside, safe_segment, sha256, write_atomic
from channel_io import console, local_state, number, positive, read_state, save_state

REQ_NAME = "requestfromweb.txt"
REPLY_NAME = "reply.txt"
HEAD_RE = re.compile(r"^Version: (\d+)\s*$", re.M)
PART_BYTES = 192 * 1024 * 1024


def task_path(workspace: Path, tag: str) -> Path:
    return inside(workspace, workspace / safe_segment(tag, "task ID"))


def version(text: str) -> int:
    match = HEAD_RE.search(text.lstrip("\ufeff"))
    if not match:
        raise ValueError("expected a 'Version: N' header")
    return int(match.group(1))


def entries_after(text: str, seen: int) -> str:
    return "\n".join(part.rstrip() for part in re.split(r"\n(?=## Request )", text)
                     if (match := re.match(r"## Request (\d+)\b", part))
                     and int(match.group(1)) > seen)


def cmd_wait(task: Path, timeout: float, interval: float) -> int:
    request = task / REQ_NAME
    state_path = local_state(request, "requests")
    deadline = time.monotonic() + timeout
    while True:
        try:
            text = request.read_text(encoding="utf-8-sig")
            current = version(text)
        except (OSError, UnicodeError, ValueError):
            text, current = "", 0  # A placeholder or partly synced request is not a new request.
        if current:
            with held(state_path, "request receipt", 120):
                seen = int(read_state(state_path).get("seen", 0))
                if current > seen:
                    new = entries_after(text, seen)
                    # The version is committed last; do not consume a half-written last entry.
                    newest = next((part for part in re.split(r"\n(?=## Request )", new)
                                   if re.match(rf"## Request {current}\b", part)), "")
                    if newest.partition("\n")[2].strip():
                        print(f"NEW-REQUEST {task.name} Version: {current}\n{new}", flush=True)
                        save_state(state_path, {"seen": current})
                        return 0
        if time.monotonic() >= deadline:
            print("timeout: no unseen complete request", flush=True)
            return 2
        time.sleep(min(interval, max(0, deadline - time.monotonic())))


def publish_attachment(source: Path, task: Path, stem: str, created: list[Path],
                       part_bytes: int) -> dict:
    """Stream at most 1 MiB at once; never load a large attachment into memory."""
    size = source.stat().st_size
    record = {"original_name": source.name, "bytes": size, "sha256": "", "parts": []}
    whole = hashlib.sha256()
    with source.open("rb") as incoming, tempfile.TemporaryDirectory(prefix="reply-parts-") as td:
        index = 0
        while incoming.tell() < size or (size == 0 and index == 0):
            index += 1
            name = stem + (f".part{index:04d}" if size > part_bytes else "")
            target = inside(task, task / safe_segment(name, "attachment name"))
            if target.exists():
                raise ValueError(f"attachment already exists: {target.name}")
            staged = Path(td) / "part"
            count, digest = 0, hashlib.sha256()
            with staged.open("wb") as outgoing:
                while count < part_bytes:
                    block = incoming.read(min(1024 * 1024, part_bytes - count))
                    if not block:
                        break
                    outgoing.write(block)
                    count += len(block)
                    digest.update(block)
                    whole.update(block)
            copy_atomic(staged, target, prefix=".reply-")
            created.append(target)
            record["parts"].append({"name": name, "order": index, "bytes": count, "sha256": digest.hexdigest()})
            if count == 0:
                break
        if incoming.read(1) or incoming.tell() != size:
            raise ValueError(f"attachment changed size during copy: {source.name}")
    record["sha256"] = whole.hexdigest()
    return record


def append_reply(reply: Path, to: int, body: str, files: list[Path],
                 part_bytes: int = PART_BYTES) -> int:
    if to < 1 or not body.strip() or part_bytes < 1:
        raise ValueError("reply requires a positive request number and non-empty text")
    reply.parent.mkdir(parents=True, exist_ok=True)
    with held(reply, "reply", 120):
        old = reply.read_text(encoding="utf-8-sig") if reply.exists() else ""
        current = version(old) + 1 if old.strip() else 1
        entries = old.split("\n## ", 1)[1] if "\n## " in old else ""
        sources = [Path(p).expanduser().resolve(strict=True) for p in files]
        if any(not source.is_file() for source in sources):
            raise ValueError("attachments must be regular files")
        created, records = [], []
        try:
            for index, source in enumerate(sources, 1):
                stem = f"reply{current}-{index}-{source.name}"
                records.append(publish_attachment(source, reply.parent, stem, created, part_bytes))
            attachment_text = ""
            if records:
                manifest = reply.parent / f"reply{current}-attachments.json"
                if manifest.exists():
                    raise ValueError(f"attachment manifest already exists: {manifest.name}")
                data = {"reply": current, "request": to, "attachments": records,
                        "reassembly": "For each attachment, concatenate parts as raw bytes in ascending order. Verify each part and the reassembled SHA-256 before use. These are byte segments, not separate ZIP archives."}
                write_atomic(manifest, (json.dumps(data, indent=2) + "\n").encode(), prefix=".reply-")
                created.append(manifest)
                attachment_text = f"\nAttachment manifest in task root: {manifest.name}\n"
                for record in records:
                    attachment_text += (f"- {record['original_name']}: {record['bytes']} bytes; SHA-256 {record['sha256']}\n"
                                        + "  Ordered files: " + ", ".join(p["name"] for p in record["parts"]) + "\n")
                attachment_text += "Concatenate segments in manifest order as raw bytes; verify part and whole hashes.\n"
            now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            text = f"Version: {current}\nUpdated: {now}\n\nReplies to requestfromweb.txt; attachments are in this task's root.\n"
            if entries:
                text += "\n## " + entries.rstrip() + "\n"
            text += f"\n## Reply {current} (Request {to}, {now})\n\n{body.strip()}\n{attachment_text}"
            write_atomic(reply, text.encode("utf-8"), prefix=".reply-")
        except BaseException:
            for path in reversed(created):
                with contextlib.suppress(OSError):
                    path.unlink()
            raise
        return current


def selftest() -> int:
    with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {"GPTIDOMATH_HOME": td}):
        root = Path(td)
        task = root / "task"
        task.mkdir()
        request = task / REQ_NAME
        request.write_text("Version: 1\n\n## Request 1 (now)\n\n", encoding="utf-8-sig")
        with contextlib.redirect_stdout(io.StringIO()):
            assert cmd_wait(task, 0, 0.01) == 2
        assert read_state(local_state(request, "requests")) == {}
        request.write_text("Version: 1\n\n## Request 1 (now)\n\nRun a sample.\n", encoding="utf-8-sig")
        with contextlib.redirect_stdout(io.StringIO()):
            assert cmd_wait(task, 0, 0.01) == 0
            assert cmd_wait(task, 0, 0.01) == 2
        source = root / "result.bin"
        source.write_bytes(bytes(range(256)) * 3)
        reply = task / REPLY_NAME
        assert append_reply(reply, 1, "Measured result", [source], 300) == 1
        manifest = json.loads((task / "reply1-attachments.json").read_text())
        entry = manifest["attachments"][0]
        assert [p["bytes"] for p in entry["parts"]] == [300, 300, 168]
        rebuilt = b"".join((task / p["name"]).read_bytes() for p in entry["parts"])
        assert rebuilt == source.read_bytes() and hashlib.sha256(rebuilt).hexdigest() == entry["sha256"]
        assert all(sha256(task / p["name"]) == p["sha256"] for p in entry["parts"])
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda n: append_reply(reply, 1, f"Result {n}", []), [2, 3]))
        assert sorted(results) == [2, 3] and version(reply.read_text()) == 3
        old = reply.read_bytes()
        with patch("web_ask.write_atomic", side_effect=PermissionError("locked")):
            try:
                append_reply(reply, 1, "Must not publish", [source])
            except PermissionError:
                pass
            else:
                raise AssertionError("expected publish failure")
        assert reply.read_bytes() == old and not list(task.glob("reply4-*"))
        request.write_text("Version: 2\n\n## Request 1 (now)\n\nOld\n", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            assert cmd_wait(task, 0, 0.01) == 2
    print("selftest PASS: web_ask (requests, streaming splits, hashes, parallel replies, rollback)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("wait", "show", "reply"))
    parser.add_argument("tag", nargs="?")
    parser.add_argument("text", nargs="?")
    parser.add_argument("--to", type=int)
    parser.add_argument("--file", type=Path, action="append", default=[], help="attachment; repeat for several")
    parser.add_argument("--timeout", type=number, default=7000, help="seconds; 0 checks once")
    parser.add_argument("--interval", type=positive, default=20, help="seconds")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if not args.command or not args.tag:
        parser.error("provide wait|show|reply and a task ID")
    if args.command == "reply" and (not args.to or args.to < 1 or not (args.text or "").strip()):
        parser.error("reply requires --to N and conclusion text")
    try:
        task = task_path(workspace_root(load_config(args.config)), args.tag)
        if args.command == "wait":
            return cmd_wait(task, args.timeout, args.interval)
        if args.command == "show":
            for name in (REQ_NAME, REPLY_NAME):
                path = task / name
                print(f"---- {name} ----\n" + (path.read_text(encoding="utf-8-sig") if path.exists() else "(not yet written)"))
            return 0
        current = append_reply(task / REPLY_NAME, args.to, args.text, args.file)
        print(f"Wrote {task / REPLY_NAME}: Reply {current} to Request {args.to}; allow time for sync.")
        return 0
    except (OSError, ValueError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    console()
    # Keep patch targets stable when this file is run as a script.
    sys.modules.setdefault("web_ask", sys.modules[__name__])
    sys.exit(main())
