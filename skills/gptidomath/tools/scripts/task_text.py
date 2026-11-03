#!/usr/bin/env python3
"""Turn a filled task skeleton into the text the web side reads.

Keeps the parts between BEGIN/END lines of the chosen route (drive or package), drops the other
route's parts and every HTML comment outside fenced code, fills the given placeholders, and refuses
a text that still has an unfilled {{NAME}} outside fenced code. drive_workspace.py and
drive_mirror.py pack call this themselves; run it directly for other routes:

  python3 task_text.py --route package TASK-source.md --out TASK.md [--set NAME=VALUE ...]
"""
from __future__ import annotations

import argparse
import contextlib
import io
import re
import sys
import tempfile
from pathlib import Path

from mirror_io import write_atomic

ROUTES = ("drive", "package")
MARKER = re.compile(r"<!--\s*(BEGIN|END)\s+(drive|package)\s*-->")
# A fence may sit in a list (any indentation) or a blockquote ("> ```").
FENCE = re.compile(r"(?:[ \t]*>)*[ \t]*(`{3,}|~{3,})(.*)")
PLACEHOLDER = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
COMMENT = re.compile(r"<!--.*?-->", re.S)


def _fence(line: str) -> tuple[str, str] | None:
    match = FENCE.match(line)
    if not match or (match[1][0] == "`" and "`" in match[2]):  # ```x``` on one line is inline code
        return None
    return match[1], match[2]


def _comment_open_after(line: str, inside: bool) -> bool:
    """Whether an HTML comment is still open at the end of `line`."""
    position = 0
    while True:
        if inside:
            end = line.find("-->", position)
            if end < 0:
                return True
            inside, position = False, end + 3
        else:
            start = line.find("<!--", position)
            if start < 0:
                return False
            inside, position = True, start + 4


def _runs(text: str, route: str) -> list[tuple[bool, str]]:
    """(is_code, text) runs of the lines that belong to `route`; marker lines themselves are dropped."""
    runs: list[tuple[bool, list[str]]] = []
    fence = None
    comment = False
    part = None
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        if fence is None:
            # Inside an HTML comment, fence-like and marker-like lines are just comment text.
            opening = None if comment else _fence(line)
            if not comment and not opening:
                marker = MARKER.fullmatch(line.strip())
                if marker:
                    kind, name = marker.groups()
                    if kind == "BEGIN" and part is None:
                        part = name
                    elif kind == "END" and part == name:
                        part = None
                    else:
                        where = f" inside the {part} part" if part else ""
                        raise ValueError(f"line {number}: unexpected '{kind} {name}' marker{where}")
                    continue
            code = bool(opening)
            if opening:
                fence = opening[0]
            else:
                comment = _comment_open_after(line, comment)
        else:
            code = True
            closing = _fence(line)
            if closing and closing[0][0] == fence[0] and len(closing[0]) >= len(fence) and not closing[1].strip():
                fence = None
        if part in (None, route):
            if runs and runs[-1][0] == code:
                runs[-1][1].append(line)
            else:
                runs.append((code, [line]))
    if part:
        raise ValueError(f"the {part} part has no 'END {part}' line")
    return [(code, "".join(lines)) for code, lines in runs]


def finalize(text: str, route: str, values: dict[str, str] | None = None) -> str:
    if route not in ROUTES:
        raise ValueError(f"route must be one of: {', '.join(ROUTES)}")
    values = values or {}

    def fill(chunk: str) -> str:
        return PLACEHOLDER.sub(lambda match: values.get(match[1], match[0]), chunk)

    text = text.lstrip("\ufeff").replace("\r\n", "\n")
    out: list[str] = []
    left: list[str] = []
    for code, chunk in _runs(text, route):
        if not code:
            chunk = COMMENT.sub("", chunk)
            if "<!--" in chunk:
                raise ValueError("an HTML comment is not closed")
            chunk = re.sub(r"\n{3,}", "\n\n", re.sub(r"^[ \t]+$", "", chunk, flags=re.M))
            chunk = fill(chunk)
            left += [match[0] for match in PLACEHOLDER.finditer(chunk)]
        else:
            chunk = fill(chunk)
        out.append(chunk)
    if left:
        raise ValueError("unfilled placeholders: " + ", ".join(dict.fromkeys(left))
                         + ". Fill them, delete their section, or put another route's parts between"
                           " '<!-- BEGIN drive -->' / '<!-- BEGIN package -->' and matching END lines")
    return "".join(out).strip("\n") + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", nargs="?", type=Path)
    parser.add_argument("--route", choices=ROUTES)
    parser.add_argument("--out", type=Path, help="Write here instead of standard output")
    parser.add_argument("--set", action="append", default=[], metavar="NAME=VALUE")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.source or not args.route:
        parser.error("a source file and --route are required")
    try:
        values = {}
        for item in args.set:
            name, sep, value = item.partition("=")
            if not sep or not PLACEHOLDER.fullmatch("{{" + name + "}}"):
                raise ValueError(f"--set expects NAME=VALUE with an upper-case NAME, got {item!r}")
            values[name] = value
        text = finalize(args.source.read_text(encoding="utf-8-sig"), args.route, values)
        if args.out:
            if args.out.resolve() == args.source.resolve():
                raise ValueError("--out must differ from the source")
            write_atomic(args.out, text.encode("utf-8"), prefix=".task-")
            print(f"WROTE {args.out}", file=sys.stderr)
        else:
            print(text, end="")
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _raises(call, needle: str) -> None:
    try:
        call()
    except ValueError as exc:
        assert needle in str(exc), exc
    else:
        raise AssertionError(f"expected an error containing {needle!r}")


def selftest() -> int:
    sample = ("\ufeff<!-- note for the agent {{IGNORED}} -->\r\n# {{TITLE}}\r\n\r\nShared.\n"
              "<!-- BEGIN drive -->\nRead {{WORKSPACE}}/REQUEST.md.\n<!-- END drive -->\n"
              "<!-- BEGIN package -->\nRead repo/.\n<!-- END package -->\n\n\n\nTail <!-- inline -->\n"
              "```text\n<!-- kept -->\n{{KEPT}}\n<!-- END drive -->\n```\n")
    drive = finalize(sample, "drive", {"TITLE": "T", "WORKSPACE": "AI-workspace/demo"})
    assert drive == ("# T\n\nShared.\nRead AI-workspace/demo/REQUEST.md.\n\nTail \n"
                     "```text\n<!-- kept -->\n{{KEPT}}\n<!-- END drive -->\n```\n"), repr(drive)
    package = finalize(sample, "package", {"TITLE": "T"})
    assert "REQUEST.md" not in package and "Read repo/." in package and "<!-- kept -->" in package
    _raises(lambda: finalize(sample, "drive", {"TITLE": "T"}), "{{WORKSPACE}}")
    commented = "<!-- Draft example, END drive:\n```python\nprint(1)\n```\n-->\nReview it.\n"
    assert finalize(commented, "drive") == "Review it.\n"
    nested = ("1. Quote this:\n\n    ```text\n    {{NAME}} <!-- kept -->\n    ```\n"
              "> ~~~\n> {{OTHER}}\n> ~~~\n\nUse ```{{X}}``` inline? No: {{DONE}}\n")
    _raises(lambda: finalize(nested, "drive"), "unfilled placeholders: {{X}}, {{DONE}}")
    out = finalize(nested, "drive", {"X": "x", "DONE": "d"})
    assert "    {{NAME}} <!-- kept -->" in out and "> {{OTHER}}" in out and "```x```" in out
    _raises(lambda: finalize("a\n<!-- END drive -->\n", "drive"), "line 2")
    _raises(lambda: finalize("<!-- BEGIN drive -->\n<!-- BEGIN package -->\n", "drive"), "inside the drive part")
    _raises(lambda: finalize("<!-- BEGIN package -->\nx\n", "drive"), "no 'END package'")
    _raises(lambda: finalize("a <!-- open\n", "drive"), "not closed")
    _raises(lambda: finalize("x", "github"), "route must be")

    # The shipped skeletons must come out clean on both routes.
    skill = Path(__file__).resolve().parents[2]
    skeletons = sorted(skill.glob("task/*/task-skeleton.md"))
    for path in skeletons:
        raw = path.read_text(encoding="utf-8")
        auto = {"WORKSPACE": "AI-workspace/demo", "WORKSPACE_ROOT": "AI-workspace", "TASK_FILE": "TASK.md"}
        manual = {name: "x" for name in PLACEHOLDER.findall(COMMENT.sub("", raw)) if name not in auto}
        for route, values in (("drive", {**manual, **auto}), ("package", manual)):
            out = finalize(raw, route, values)
            assert "<!--" not in out and "{{" not in out, (path, route)
            assert ("REQUEST.md" in out) == (route == "drive") and ("DONE.txt" in out) == (route == "drive"), (path, route)
            assert ("repo/" in out) == (route == "package"), (path, route)
            assert ("requestfromweb.txt" in out) == (route == "drive"), (path, route)

    with tempfile.TemporaryDirectory() as temporary, contextlib.redirect_stderr(io.StringIO()) as errors:
        source, target = Path(temporary) / "in.md", Path(temporary) / "out.md"
        source.write_text("<!-- BEGIN drive -->\nD {{WORKSPACE}}\n<!-- END drive -->\nP\n", encoding="utf-8")
        assert main([str(source), "--route", "package", "--out", str(target)]) == 0
        assert target.read_text(encoding="utf-8") == "P\n"
        assert main([str(source), "--route", "drive", "--out", str(target), "--set", "WORKSPACE=W"]) == 0
        assert target.read_text(encoding="utf-8") == "D W\nP\n"
        assert main([str(source), "--route", "drive", "--out", str(source), "--set", "WORKSPACE=W"]) == 2
        assert main([str(source), "--route", "package", "--set", "lower=x"]) == 2
        assert "--out must differ" in errors.getvalue() and "upper-case NAME" in errors.getvalue()
    print(f"selftest PASS: task_text (routes, comments, nested fences, placeholders, {len(skeletons)} skeletons)")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
