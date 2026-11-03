#!/usr/bin/env python3
"""Small shared helpers for local task monitors. Python 3.10+, standard library."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
from unittest.mock import patch

from mirror_io import write_atomic


def local_state(target: Path, kind: str) -> Path:
    base = Path(os.environ.get("GPTIDOMATH_HOME", str(Path.home() / ".gptidomath")))
    key = hashlib.sha256(os.path.normcase(str(target.resolve())).encode()).hexdigest()
    return base / "state" / kind / (key + ".json")


def read_state(path: Path) -> dict:
    try:
        state = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return {}
    if not isinstance(state, dict):
        raise ValueError(f"invalid state object: {path}")
    return state


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(path, (json.dumps(state, sort_keys=True) + "\n").encode(), prefix=".state-")
    if os.name != "nt":
        path.chmod(0o600)


def canonical_name(name: str) -> str:
    """Drive may expose plain-text files with one additional .gdoc suffix."""
    low = name.lower()
    return low[:-5] if low.endswith(".gdoc") else low


def ignored(name: str, *, ignore_probe: bool = True) -> bool:
    low = canonical_name(name)
    return (low in {"request.md", "reply.txt", ".ds_store", "desktop.ini", "thumbs.db"}
            or (ignore_probe and low == "test.txt")
            or bool(re.match(r"reply\d+-", low))
            or low.startswith(("relay-", "._", "~$", ".~lock.", ".request-",
                               ".reply-", ".channel-", ".mirror-", ".tmp.drive"))
            or (low.startswith("task") and low.endswith(".md"))
            or low.endswith((".tmp", ".part", ".crdownload")))


def snapshot(directory: Path, *, recursive: bool = False, ignore_probe: bool = True,
             exclude: str = "") -> dict[str, list[int]]:
    """Only regular outputs; do not follow linked directories or silently hide read failures."""
    result = {}
    if not directory.exists():
        return result

    def onerror(error):
        raise error

    for root, dirs, names in os.walk(directory, onerror=onerror):
        dirs[:] = [n for n in dirs if recursive and not ignored(n, ignore_probe=ignore_probe)]
        for name in names:
            if canonical_name(name) == canonical_name(exclude) or ignored(name, ignore_probe=ignore_probe):
                continue
            path = Path(root) / name
            if path.is_symlink():
                continue
            try:
                info = path.stat()
            except FileNotFoundError:
                continue
            result[str(path.relative_to(directory))] = [info.st_mtime_ns, info.st_size]
    return result


def marker_text(path: Path) -> str:
    candidates = (path,) if path.name.lower().endswith(".gdoc") else (path, path.with_name(path.name + ".gdoc"))
    for candidate in candidates:
        try:
            body = candidate.read_text(encoding="utf-8-sig").strip()
        except (OSError, UnicodeError):
            continue
        if not body:
            continue
        try:
            metadata = json.loads(body)
        except ValueError:
            metadata = None
        # A Drive shortcut is metadata pointing to a document, not its text.
        shortcut_keys = {"url", "doc_id", "docid", "document_id", "documentid", "resource_id", "resourceid"}
        if isinstance(metadata, dict) and any(str(key).lower() in shortcut_keys for key in metadata):
            continue
        return body
    return ""


def number(value: str, *, positive: bool = False) -> float:
    try:
        result = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a number") from error
    if not math.isfinite(result) or result < 0 or (positive and result == 0):
        raise argparse.ArgumentTypeError("must be finite and " + ("positive" if positive else "nonnegative"))
    return result


def positive(value: str) -> float:
    return number(value, positive=True)


def console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def selftest() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for name in ("REQUEST.md", "reply3-result.zip", "TASK-two.md", "test.txt", "desktop.ini", "upload.tmp"):
            (root / name).write_text("x")
        assert snapshot(root) == {}
        (root / "NOTES.md").write_text("result")
        assert set(snapshot(root)) == {"NOTES.md"}
        (root / "nested").mkdir()
        (root / "nested" / "result.zip").write_bytes(b"x")
        assert len(snapshot(root, recursive=True)) == 2
        assert len(snapshot(root, ignore_probe=False)) == 2
        marker = root / "DONE.txt"
        marker.write_bytes(b"\xef\xbb\xbf \n")
        assert not marker_text(marker)
        marker.write_text("finished", encoding="utf-8-sig")
        assert marker_text(marker) == "finished"
        alias = root / "DONE.txt.gdoc"
        alias.write_text("alias finished", encoding="utf-8-sig")
        assert marker_text(marker) == "finished"  # Prefer the normal file when readable.
        marker.unlink()
        assert marker_text(marker) == "alias finished"
        marker.write_bytes(b"")
        assert marker_text(marker) == "alias finished"
        real_read = Path.read_text
        def locked_exact(path, *args, **kwargs):
            if path == marker:
                raise PermissionError("sync lock")
            return real_read(path, *args, **kwargs)
        with patch.object(Path, "read_text", locked_exact):
            assert marker_text(marker) == "alias finished"
        for key in ("url", "doc_id", "resource_id"):
            alias.write_text(json.dumps({key: "document-reference"}))
            assert not marker_text(marker)
        for name in ("REQUEST.md.gdoc", "TASK-two.md.gdoc", "reply.txt.gdoc", "test.txt.gdoc"):
            (root / name).write_text("control")
            assert ignored(name)
        assert "DONE.txt.gdoc" not in snapshot(root, exclude="DONE.txt")
        assert ignored("reply12-attachments.json") and ignored("reply12-result.zip")
        assert not ignored("REPLY-example-09-four-commits.zip")
        state = root / "state.json"
        assert read_state(state) == {}
        save_state(state, {"seen": 2})
        assert read_state(state) == {"seen": 2}
        for value in ("nan", "inf", "-1"):
            try:
                number(value)
            except argparse.ArgumentTypeError:
                pass
            else:
                raise AssertionError(value)
    print("selftest PASS: channel_io (filtering, BOM, gdoc aliases, shortcut rejection, state, intervals)")
    return 0


if __name__ == "__main__":
    console()
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(selftest())
    print(__doc__)
