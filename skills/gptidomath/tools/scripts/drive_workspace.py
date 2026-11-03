#!/usr/bin/env python3
"""Prepare task folders and task files, then render the short message to send."""
from __future__ import annotations

import argparse
import contextlib
import io
import os
import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from kit_config import load_config, workspace_root
from mirror_io import inside, safe_segment, write_atomic


def task_directory(root: Path, tag: str) -> Path:
    safe_segment(tag, "tag")
    if tag.lower() in {"repos", "tools"}:
        raise ValueError("repos and tools are reserved; choose a task tag")
    target = root / tag
    inside(root, target, "task folder")
    return target


def subdirectory(task: Path, value: str) -> Path:
    parts = value.replace("\\", "/").split("/")
    for part in parts:
        safe_segment(part, "subdirectory component")
    target = task.joinpath(*parts)
    inside(task, target, "subdirectory")
    return target


def strip_leading_comments(text: str) -> str:
    text = text.lstrip("\ufeff \t\r\n")
    while text.startswith("<!--"):
        end = text.find("-->")
        if end < 0:
            raise ValueError("Unclosed leading HTML comment in message template")
        text = text[end + 3:].lstrip()
    return text


def render_message(opener: str, footer: str, workspace: str, task_file: str, round_number: int) -> str:
    text = "\n\n".join(part for part in (strip_leading_comments(opener).strip(),
                                         strip_leading_comments(footer).strip()) if part)
    values = {"WORKSPACE": workspace, "TASK_FILE": task_file, "ROUND": str(round_number)}
    return re.sub(r"\{\{(WORKSPACE|TASK_FILE|ROUND)\}\}", lambda match: values[match[1]], text) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", nargs="?")
    parser.add_argument("subdirs", nargs="*", help="Relative folders to create below the task folder")
    parser.add_argument("--config")
    parser.add_argument("--check", action="store_true", help="Check only; exit 1 if any folder is missing")
    parser.add_argument("--task", type=Path, help="UTF-8 task source")
    parser.add_argument("--round", type=int, help="Continuation number, starting at 2")
    parser.add_argument("--preface", type=Path, help="UTF-8 text to prepend to the task")
    parser.add_argument("--opener", type=Path)
    parser.add_argument("--footer", type=Path)
    parser.add_argument("--out", type=Path, help="Also save the rendered message here")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.tag:
        parser.error("tag is required")
    if args.round is not None and args.round < 2:
        parser.error("--round must be 2 or greater; omit it for the first task")
    if args.preface and not args.task:
        parser.error("--preface requires --task")
    if bool(args.opener) != bool(args.footer):
        parser.error("--opener and --footer must be supplied together")
    if args.out and not args.opener:
        parser.error("--out requires --opener and --footer")
    if args.check and any((args.task, args.preface, args.opener, args.footer, args.out)):
        parser.error("--check cannot write a task or render a message")
    try:
        config = load_config(args.config)
        root = workspace_root(config)
        task = task_directory(root, args.tag)
        directories = [task, *(subdirectory(task, name) for name in args.subdirs)]
        if args.check:
            missing = [directory for directory in directories if not directory.is_dir()]
            for directory in missing:
                print(f"MISSING {directory}")
            if not missing:
                print(f"READY {task}")
            return int(bool(missing))
        task_file = f"TASK-{args.round}.md" if args.round is not None else "TASK.md"
        destination = task / task_file
        if args.task:
            inside(task, destination, "task file")
            if destination.resolve() in {source.resolve() for source in (args.task, args.preface, args.opener, args.footer) if source}:
                raise ValueError("Task destination must not overwrite an input file; use a separate task source")
        body = None
        if args.task:
            body = args.task.read_text(encoding="utf-8-sig")
            if not body.strip():
                raise ValueError("Task source is empty")
            if args.preface:
                preface = args.preface.read_text(encoding="utf-8-sig").strip()
                body = (preface + "\n\n" if preface else "") + body
        message = None
        if args.opener:
            message = render_message(args.opener.read_text(encoding="utf-8-sig"),
                                     args.footer.read_text(encoding="utf-8-sig"),
                                     f"{config['workspace_name']}/{args.tag}", task_file, args.round or 1)
        message_destination = args.out.expanduser().resolve() if args.out else None
        if message_destination:
            if message_destination in {source.resolve() for source in (args.task, args.preface, args.opener, args.footer) if source}:
                raise ValueError("--out must not overwrite an input file")
            if message_destination == (task / task_file).resolve():
                raise ValueError("--out must not overwrite the task file")
        # Read and validate every input before creating anything.
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"READY {directory}", file=sys.stderr)
        if body is not None:
            write_atomic(destination, body.encode("utf-8"), prefix=".task-")
            print(f"WROTE {destination}", file=sys.stderr)
        if message is not None:
            if message_destination:
                message_destination.parent.mkdir(parents=True, exist_ok=True)
                write_atomic(message_destination, message.encode("utf-8"), prefix=".opener-")
                print(f"WROTE {message_destination}", file=sys.stderr)
            print(message, end="")
        return 0
    except (OSError, ValueError, TimeoutError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def selftest() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        workspace = root / "workspace"
        workspace.mkdir()
        task = root / "input.md"
        task.write_text("Do the small task.\n", encoding="utf-8-sig")
        preface = root / "preface.md"
        preface.write_text("Read this first.\n", encoding="utf-8")
        opener, footer = root / "opener.md", root / "footer.md"
        opener.write_text("<!-- private drafting note -->\n<!-- second -->\nRead {{WORKSPACE}}/{{TASK_FILE}}.", encoding="utf-8-sig")
        footer.write_text("<!-- footer note -->\nRound {{ROUND}}.", encoding="utf-8")
        out = root / "message.md"
        config = root / "config.json"
        config.write_text('{"workspace_name":"Research"}', encoding="utf-8")
        with patch.dict(os.environ, {"GPTIDOMATH_CONFIG": str(config), "GPTIDOMATH_WORKSPACE": str(workspace)}), \
                contextlib.redirect_stdout(io.StringIO()) as stdout, contextlib.redirect_stderr(io.StringIO()):
            assert main(["demo", "evidence/nested", "--check"]) == 1
            assert not (workspace / "demo").exists()
            assert main(["demo", "evidence/nested", "--task", str(task), "--preface", str(preface),
                         "--opener", str(opener), "--footer", str(footer), "--out", str(out)]) == 0
            assert (workspace / "demo" / "TASK.md").read_text(encoding="utf-8") == "Read this first.\n\nDo the small task.\n"
            assert out.read_text(encoding="utf-8") == "Read Research/demo/TASK.md.\n\nRound 1.\n"
            assert "private drafting note" not in stdout.getvalue()
            assert main(["demo", "--task", str(task), "--round", "2"]) == 0
            assert (workspace / "demo" / "TASK-2.md").is_file()
            assert main(["demo", "evidence/nested", "--check"]) == 0
            for tag in ("..", "repos", "tools", "../escape"):
                assert main([tag]) == 2
            assert main(["demo", "../escape"]) == 2
            assert main(["demo", "--task", str(task), "--opener", str(opener), "--footer", str(footer), "--out", str(task)]) == 2
            assert task.read_text(encoding="utf-8-sig") == "Do the small task.\n"
            published = workspace / "demo" / "TASK.md"
            before = published.read_bytes()
            assert main(["demo", "--task", str(published), "--preface", str(preface)]) == 2
            assert published.read_bytes() == before
    print("selftest PASS: drive_workspace (check, task, round, templates, path boundaries)")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
