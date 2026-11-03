# Agent hooks (optional)

## Principle

Two steps are easy for an agent to forget:
- After its context is compacted or the session restarts, it no longer knows that a ChatGPT job is still running. Nobody restarts the watchers, and the delivery sits unnoticed.
- After sending through a browser, it forgets to log the message in the Pro ledger.

A hook makes the agent's shell run a small script at that moment and puts what the script prints into the agent's context. Both scripts only print reminders: they add no ledger entries and block nothing. The send reminder keeps a small throttle file, `pro-send-hook-state.json` under `GPTIDOMATH_HOME`.

| Script | Runs | Prints |
|---|---|---|
| [`open_jobs_hook.py`](../scripts/open_jobs_hook.py) | session start, resume, after compaction | task folders whose newest `TASK*.md` is newer than any non-empty `DONE*.txt` (last three days), each with its watcher commands; nothing otherwise |
| [`pro_send_hook.py`](../scripts/pro_send_hook.py) | after a browser tool call that clicked send | a request to check the send and log it ([ledger manual](pro-ledger.md#optional-claude-code-reminder)) |

## Claude Code

Ask the user first: this changes their settings. Back up the settings file and merge the fragment into it; keep existing hooks. Use `~/.claude/settings.json` for every project, or the project's `.claude/settings.json` for one. Give the absolute path of the installed skill (forward slashes on Windows) and the Python the selftests ran with.

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|compact",
        "hooks": [
          {
            "type": "command",
            "command": "python \"/absolute/path/to/skill/tools/scripts/open_jobs_hook.py\""
          }
        ]
      }
    ]
  }
}
```

For the send reminder, add the `PostToolUse` fragment from the [ledger manual](pro-ledger.md#optional-claude-code-reminder).

Check it: run the command by hand. With an open task folder it prints the list; with none it prints nothing. Then start a new session and confirm the list reaches the agent. The hook finds the workspace the same way the other tools do, so if you rely on `GPTIDOMATH_CONFIG` or `GPTIDOMATH_WORKSPACE`, the hook process must see them too.

## Other agent shells

Untested by the authors. The idea carries over: run a command at an event and give its standard output to the model. Map each script to your shell's own hook format:

- `open_jobs_hook.py` ignores standard input, prints plain text or nothing, and always exits `0`. Attach it to whatever runs when a session starts, resumes or has its context compacted.
- `pro_send_hook.py` reads one JSON event on standard input with `tool_name`, `tool_input` and `tool_response`, and prints nothing or `{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "…"}}`. Attach it to an after-tool-call event, and adapt the field names, the output shape and `GPTIDOMATH_BROWSER_TOOLS` to your shell's tools.

If your shell has no hooks for these events, put the same steps in its standing project instructions (for example `AGENTS.md`): at the start of every session run `open_jobs_hook.py` and act on what it prints; after every message sent to ChatGPT, run `pro_ledger.py add`.
