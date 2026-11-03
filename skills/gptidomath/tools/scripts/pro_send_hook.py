#!/usr/bin/env python3
"""Optional Claude Code PostToolUse reminder. Never adds ledger entries."""

import json
import os
import re
import sys
from datetime import timedelta

sys.dont_write_bytecode = True
import pro_ledger as ledger

DEFAULT_TOOLS = (
    "mcp__claude-in-chrome__javascript_tool",
    "mcp__claude-in-chrome__browser_batch",
)
CONVERSATION = re.compile(r"chatgpt\.com/c/([a-zA-Z0-9-]+)")
QUIET = timedelta(minutes=3)


def main():
    payload = json.load(sys.stdin)
    configured = os.environ.get("GPTIDOMATH_BROWSER_TOOLS")
    tools = tuple(part.strip() for part in configured.split(",")) if configured else DEFAULT_TOOLS
    if payload.get("tool_name") not in tools:
        return
    tool_input = json.dumps(payload.get("tool_input", {}), ensure_ascii=False)
    if "send-button" not in tool_input:
        return
    response = json.dumps(payload.get("tool_response", ""), ensure_ascii=False)
    match = CONVERSATION.search(response) or CONVERSATION.search(tool_input)
    if not match:
        return
    conversation = match.group(1)
    at = ledger.now()
    state_path = ledger.data_home() / "pro-send-hook-state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            state = {}
    except (OSError, ValueError):
        state = {}
    try:
        if conversation in state and at - ledger.parse_time(state[conversation]) < QUIET:
            return
    except (TypeError, ValueError):
        pass
    previous = "No recorded send for this conversation."
    for event in reversed(ledger.load()):
        stored = event.get("conv", "")
        stored_match = CONVERSATION.search(stored)
        stored_id = stored_match.group(1) if stored_match else stored
        if event["type"] == "send" and stored_id == conversation:
            previous = f"Last added send for this conversation: {event['at']} ({event.get('tier', 'pro')})."
            break
    state[conversation] = ledger.stamp(at)
    try:
        ledger.data_home().mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state), encoding="utf-8")
    except OSError:
        pass
    message = (
        f"Pro ledger reminder for conversation {conversation}: the browser tool referenced send-button. "
        f"{previous} Verify that a new message actually appeared and was sent to Pro; then record exactly "
        "one entry with pro_ledger.py add <tag> --conv <conversation URL or ID>. "
        "Follow-ups, corrections, and requests to package completed work each count. "
        "Use --tier for non-Pro efforts. This hook only reminds; it never logs a send."
    )
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                            "additionalContext": message}}, ensure_ascii=False))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        pass  # A reminder must not interrupt the browser operation.
