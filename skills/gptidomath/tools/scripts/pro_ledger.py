#!/usr/bin/env python3
"""Count sent Pro messages locally; remaining counts are estimates, not quota data."""

import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

WEEK = timedelta(days=7)
DEFAULT_LIMIT = 50  # A guess, not a published allowance.


def data_home():
    return Path(os.environ.get("GPTIDOMATH_HOME") or Path.home() / ".gptidomath").expanduser()


def ledger_path():
    return data_home() / "pro-ledger.jsonl"


def doc_path():
    return data_home() / "pro-usage.md"


def now():
    return datetime.now().astimezone()


def parse_time(text):
    value = datetime.fromisoformat(text.strip())
    return value if value.tzinfo else value.astimezone()


def stamp(value):
    return value.isoformat(timespec="seconds")


def fmt(value):
    return value.astimezone().isoformat(sep=" ", timespec="minutes")


def load():
    if not ledger_path().exists():
        return []
    events = []
    with ledger_path().open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                event["_at"] = parse_time(event["at"])
                if event["type"] not in {"send", "wall", "limit"}:
                    raise ValueError("unknown event type")
                if "limit" in event and (type(event["limit"]) is not int or event["limit"] < 1):
                    raise ValueError("invalid limit")
                if event["type"] == "wall":
                    parse_time(event["resets_at"])
                events.append(event)
            except (ValueError, KeyError, TypeError) as error:
                print(f"[pro_ledger] Skipping unreadable line {number}: {error}", file=sys.stderr)
    return events


def latest(events, kind):
    return next((event for event in reversed(events) if event["type"] == kind), None)


def limit_of(events):
    for event in reversed(events):
        if event["type"] in {"wall", "limit"} and "limit" in event:
            source = "page-reported limit" if event["type"] == "wall" else "configured with set-limit"
            return event["limit"], source
    return DEFAULT_LIMIT, "GUESS: default limit; not verified"


def window(events, at):
    wall = latest(events, "wall")
    if wall:
        anchor = parse_time(wall["resets_at"])
        start = anchor + ((at - anchor) // WEEK) * WEEK
        return start, start + WEEK, "anchored to the page-reported reset; repeats every 7 days"
    start = at.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=at.weekday())
    return start, start + WEEK, "GUESS: Monday 00:00 local time, every 7 days"


def sends_between(events, start, end):
    return [event for event in events if event["type"] == "send"
            and event.get("tier", "pro") == "pro" and start <= event["_at"] < end]


def status(events, at=None):
    at = at or now()
    start, end, mode = window(events, at)
    used = len([event for event in sends_between(events, start, end) if event["_at"] <= at])
    limit, source = limit_of(events)
    wall = latest(events, "wall")
    lines = [f"[pro_ledger] Logged Pro messages in this window: {used}",
             f"  Window: {fmt(start)} -> {fmt(end)} ({mode})",
             f"  Limit: {limit} ({source})"]
    if wall and at < parse_time(wall["resets_at"]):
        lines.append(f"  LIMIT HIT: no Pro messages available until {fmt(parse_time(wall['resets_at']))}.")
    else:
        lines.append(f"  Estimated remaining: {max(0, limit - used)} (reference only).")
    if not wall:
        lines.append("  No real limit hit recorded. Every remaining count is a reference only.")
    else:
        reset = parse_time(wall["resets_at"])
        logged = sum(event["_at"] <= wall["_at"]
                     for event in sends_between(events, reset - WEEK, reset))
        wall_limit = wall.get("limit", wall.get("assumed_limit", limit))
        gap = wall_limit - logged
        certainty = "page-reported limit" if "limit" in wall else "estimate; limit was not page-confirmed"
        lines.append(f"  Outside-ledger messages at last limit hit: {max(0, gap)} ({certainty}; "
                     f"{wall_limit} limit minus {logged} logged).")
        lines.append(f"  Last exhausted window ended: {fmt(reset)}; this is not a count for later windows.")
        if gap < 0:
            lines.append(f"  Logged sends exceed that limit by {-gap}; review the records or limit.")
    lines.append("  Unlogged use can make the real remaining count lower.")
    lines.append(f"  Next {'projected ' if wall else 'guessed '}reset: {fmt(end)} "
                 f"(in {(end - at).total_seconds() / 86400:.1f} days).")
    return "\n".join(lines)


def cell(value):
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render():
    events = load()
    lines = ["# Pro message usage", "", "Generated by pro_ledger.py; use add/undo to correct sends.",
             "Times include the local UTC offset. Non-Pro tiers do not count toward Pro usage.",
             "", "```text", status(events), "```", "", "| Time | Tag | Tier | Note | Conversation |",
             "|---|---|---|---|---|"]
    for event in sorted((event for event in events if event["type"] == "send"),
                        key=lambda event: event["_at"], reverse=True):
        values = [fmt(event["_at"]), event.get("tag", ""), event.get("tier", "pro"),
                  event.get("note", ""), event.get("conv", "")]
        lines.append("| " + " | ".join(map(cell, values)) + " |")
    data_home().mkdir(parents=True, exist_ok=True)
    doc_path().write_text("\n".join(lines) + "\n", encoding="utf-8")


def append(event):
    data_home().mkdir(parents=True, exist_ok=True)
    with ledger_path().open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + "\n")
    render()


def cmd_add(args):
    at = parse_time(args.at) if args.at else now()
    event = {"type": "send", "at": stamp(at), "tag": args.tag, "tier": args.tier}
    for key in ("conv", "note"):
        if getattr(args, key):
            event[key] = getattr(args, key)
    append(event)
    print(f"[pro_ledger] Added {args.tier} message: {args.tag}")
    print(status(load()))


def cmd_wall(args):
    at = now()
    reset = parse_time(args.resets_at)
    if reset <= at:
        raise ValueError("reset must be the future local time shown on the page")
    event = {"type": "wall", "at": stamp(at), "resets_at": stamp(reset),
             "assumed_limit": limit_of(load())[0]}
    if args.limit is not None:
        event["limit"] = args.limit
    if args.note:
        event["note"] = args.note
    append(event)
    print("[pro_ledger] Real limit hit recorded; switched to the reset-anchored window.")
    print(status(load()))


def cmd_undo(_args):
    if not ledger_path().exists():
        raise ValueError("no sent message to undo")
    lines = ledger_path().read_text(encoding="utf-8").splitlines(keepends=True)
    for index in range(len(lines) - 1, -1, -1):
        try:
            event = json.loads(lines[index])
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") == "send":
            del lines[index]
            ledger_path().write_text("".join(lines), encoding="utf-8")
            render()
            print(f"[pro_ledger] Removed last added send: {event.get('tag', '')}")
            return
    raise ValueError("no sent message to undo")


def cmd_list(args):
    cutoff = now() - timedelta(days=args.days)
    for event in load():
        if event["_at"] >= cutoff:
            print(json.dumps({key: value for key, value in event.items() if key != "_at"},
                             ensure_ascii=False))


def cmd_set_limit(args):
    event = {"type": "limit", "at": stamp(now()), "limit": args.limit}
    if args.note:
        event["note"] = args.note
    append(event)
    print(status(load()))


def positive(text):
    value = int(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return value


def selftest():
    previous = os.environ.get("GPTIDOMATH_HOME")
    try:
        with tempfile.TemporaryDirectory() as directory:
            os.environ["GPTIDOMATH_HOME"] = directory
            at = now().replace(microsecond=0)
            start, end, _ = window([], at)
            assert start.weekday() == 0 and end - start == WEEK
            assert "GUESS" in status([], at) and "reference only" in status([], at)
            print("PASS default limit and weekly window are labelled guesses")
            send = {"type": "send", "at": stamp(at), "tag": "example"}
            append(send)
            append({**send, "tier": "extra-high"})
            old = min(start, at - WEEK) - timedelta(seconds=1)
            append({**send, "at": stamp(old), "tag": "earlier"})
            assert len(sends_between(load(), start, end)) == 1
            print("PASS backdated sends and non-Pro tier accounting")
            reset = at + timedelta(days=2)
            append({"type": "wall", "at": stamp(at), "resets_at": stamp(reset), "limit": 4})
            assert window(load(), at)[:2] == (reset - WEEK, reset)
            assert "LIMIT HIT" in status(load(), at)
            assert "Outside-ledger messages at last limit hit: 3 (page-reported limit" in status(load(), at)
            assert window(load(), reset + timedelta(days=1))[:2] == (reset, reset + WEEK)
            print("PASS real reset anchoring, exhausted window, and outside-ledger count")
            append({"type": "limit", "at": stamp(at), "limit": 8})
            assert limit_of(load())[0] == 8
            assert "last limit hit: 3" in status(load(), reset + timedelta(days=1))
            with contextlib.redirect_stdout(io.StringIO()):
                cmd_undo(None)
            assert len([event for event in load() if event["type"] == "send"]) == 2
            assert doc_path().is_file() and "extra-high" in doc_path().read_text(encoding="utf-8")
            print("PASS newer configured limit, historical calibration, undo, and Markdown render")
            append({"type": "wall", "at": stamp(at), "resets_at": stamp(reset), "assumed_limit": 8})
            assert "limit was not page-confirmed" in status(load(), at)
            print("PASS missing page limit keeps outside-ledger count an estimate")
    finally:
        if previous is None:
            os.environ.pop("GPTIDOMATH_HOME", None)
        else:
            os.environ["GPTIDOMATH_HOME"] = previous
    print("selftest PASS")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true", help="test with temporary data only")
    sub = parser.add_subparsers(dest="command")
    add = sub.add_parser("add", help="record one message that was actually sent")
    add.add_argument("tag")
    add.add_argument("--at", help="ISO timestamp; no offset means local time")
    add.add_argument("--tier", default="pro", type=str.lower, help="only pro counts; e.g. extra-high")
    add.add_argument("--conv", help="optional conversation URL or ID")
    add.add_argument("--note")
    for name in ("undo", "status", "render"):
        sub.add_parser(name)
    listing = sub.add_parser("list", help="list recent events in insertion order")
    listing.add_argument("--days", type=positive, default=7)
    limit = sub.add_parser("set-limit", help="configure an assumed weekly limit")
    limit.add_argument("limit", type=positive)
    limit.add_argument("--note")
    wall = sub.add_parser("wall", help="record the reset time displayed when the limit is hit")
    wall.add_argument("--resets-at", required=True)
    wall.add_argument("--limit", type=positive, help="only supply a limit actually stated on the page")
    wall.add_argument("--note")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.command:
        parser.error("choose a command or --selftest")
    try:
        if args.command == "status":
            print(status(load()))
        elif args.command == "render":
            render()
            print(f"[pro_ledger] Rendered {doc_path()}")
        else:
            {"add": cmd_add, "undo": cmd_undo, "list": cmd_list,
             "set-limit": cmd_set_limit, "wall": cmd_wall}[args.command](args)
    except (ValueError, OSError) as error:
        parser.exit(1, f"[pro_ledger] {error}\n")
    return 0


if __name__ == "__main__":
    for output in (sys.stdout, sys.stderr):
        if hasattr(output, "reconfigure"):
            output.reconfigure(encoding="utf-8")
    sys.exit(main())
