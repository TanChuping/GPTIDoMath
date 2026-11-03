# Pro message ledger

ChatGPT does not show how many Pro messages remain. It reports the limit only
when it is hit, with a reset time. This local ledger counts sends and estimates
the rest; it does not query an account or read a conversation.

Record **every message actually sent to Pro**, immediately after sending: a new
task, a follow-up in the same chat, a correction, or a request to zip completed
work each counts once. Log a person's sends when confirmed, too. A click without
a sent message does not count. Check `status` before sending.

## Commands

Run these from the skill directory with Python 3.9 or later; no packages needed:

```sh
python tools/scripts/pro_ledger.py add review --conv "https://chatgpt.com/c/CONVERSATION-ID"
python tools/scripts/pro_ledger.py add follow-up --note "Package completed work"
python tools/scripts/pro_ledger.py add earlier --at "YYYY-MM-DD HH:MM"
python tools/scripts/pro_ledger.py add comparison --tier extra-high
python tools/scripts/pro_ledger.py undo
python tools/scripts/pro_ledger.py list --days 14
python tools/scripts/pro_ledger.py status
python tools/scripts/pro_ledger.py set-limit 50 --note "Configured estimate"
python tools/scripts/pro_ledger.py wall --resets-at "YYYY-MM-DD HH:MM" --limit 50
python tools/scripts/pro_ledger.py render
python tools/scripts/pro_ledger.py --selftest
```

Replace the uppercase time placeholders with real local timestamps. An explicit
UTC offset is also accepted. `--tier` accepts an effort label; only `pro` counts
toward Pro usage. `undo` removes the last **added send**, including a backdated
or non-Pro send, and leaves limit/reset events alone. `list` includes all event
types in insertion order.

Data lives in `~/.gptidomath/pro-ledger.jsonl` and a generated `pro-usage.md`
beside it. Set `GPTIDOMATH_HOME` to another directory to move both. Each change
refreshes the Markdown; `render` refreshes its time-sensitive status later.
These are private usage records; keep them out of shared skill packages.
Use one writer at a time.

## Guesses and the real limit

The initial **50-message limit and Monday 00:00 local weekly window are guesses**,
not product guarantees. `status` labels both. Before the first real limit hit,
every remaining count is a reference only. `set-limit` changes the configured
limit; it does not verify it or establish a real reset.

When the page reports the limit, **tell the user at once**, copy the displayed
reset time into local time, and run:

```sh
python tools/scripts/pro_ledger.py wall --resets-at "YYYY-MM-DD HH:MM"
```

Add `--limit N` only if the page states N. This switches to a window anchored to
the real reset. Subsequent windows repeat every seven days as a projection;
record a new `wall` if the page gives a different reset.

`status` then reports outside-ledger messages in the last exhausted window:
the limit minus Pro sends logged before the hit in that window. With a
page-reported limit this is the inferred number of missing sends; without one,
it is explicitly an estimate using the limit configured at the hit. The exact
number is unknown without a confirmed limit. Backfilling or undoing sends
updates the calculation. This historical number does not describe later
windows, and any remaining estimate can still be too high because of unlogged
use. During an active wall the tool reports that Pro is unavailable until reset.

## Optional Claude Code reminder

`pro_send_hook.py` is a PostToolUse hook. It notices `send-button` in a known
browser tool's input plus a `chatgpt.com/c/…` URL in input or output. It supplies
additional context asking the agent to verify the send and log it. **It never
adds a ledger entry.** It cannot detect coordinate clicks or verify the model.
Reminders are throttled per conversation for three minutes; every actual send
still needs its own ledger entry.

Merge this fragment into Claude Code's settings, replacing the absolute script
path with your installed location. Preserve existing hooks:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "mcp__claude-in-chrome__javascript_tool|mcp__claude-in-chrome__browser_batch",
        "hooks": [
          {
            "type": "command",
            "command": "python \"/absolute/path/to/skill/tools/scripts/pro_send_hook.py\""
          }
        ]
      }
    ]
  }
}
```

On Windows use a quoted absolute script path with forward slashes. For other
browser integrations, adapt the matcher and set `GPTIDOMATH_BROWSER_TOOLS` to
the matching comma-separated tool names in the hook process's environment.
Other agents can call the ledger directly or adapt the reminder payload.
Throttle state is stored in `pro-send-hook-state.json` under `GPTIDOMATH_HOME`.
