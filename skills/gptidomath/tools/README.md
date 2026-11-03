# Toolkit index

Keep this directory together. Local tools use Python 3.10+ and the standard library; mirroring also needs Git. Run commands from this directory or give your agent the installed script paths.

- [`drive_mirror.py`](scripts/drive_mirror.py): publish a committed repository or build one upload package; [mirror manual](manuals/mirror.md).
- [`code_index.py`](scripts/code_index.py): add an index to an unindexed source ZIP after checking required text; [mirror manual](manuals/mirror.md).
- [`drive_workspace.py`](scripts/drive_workspace.py): create task folders, write task files, and render the short message; [workspace manual](manuals/workspace.md).
- [`task_text.py`](scripts/task_text.py): keep one route's parts of a task, drop comments, refuse unfilled placeholders (used by `drive_workspace.py` and `pack`); [workspace manual](manuals/workspace.md).
- [`drive_request.py`](scripts/drive_request.py): append a versioned instruction during a running task; [interjection manual](manuals/interject.md).
- [`request-channel/`](request-channel/README.txt): install the sandbox checkpoint reminder; [interjection manual](manuals/interject.md).
- [`web_ask.py`](scripts/web_ask.py): receive local-run requests and publish replies with attachments; [local-run manual](manuals/local-run.md).
- [`drive_wait.py`](scripts/drive_wait.py): wait for a readable completion marker or quiet output; [watch manual](manuals/watch.md).
- [`watch_job.py`](scripts/watch_job.py): report delivery, a new ZIP, a stall, or timeout; [watch manual](manuals/watch.md).
- [`kit_config.py`](scripts/kit_config.py): resolve the configured workspace or discover Drive; [workspace manual](manuals/workspace.md).
- [`secret_patterns.py`](scripts/secret_patterns.py): shared text-redaction and kept-back-file rules; [mirror manual](manuals/mirror.md).
- [`mirror_io.py`](scripts/mirror_io.py): shared atomic publication, path checks, and local writer locks; [mirror manual](manuals/mirror.md).
- [`channel_io.py`](scripts/channel_io.py): shared monitor filtering and local state; [watch manual](manuals/watch.md).
- [`selftest_all.py`](scripts/selftest_all.py): run every script's selftest, including the sandbox channel and `pro_ledger.py` when present; [workspace manual](manuals/workspace.md).
- [`pro_ledger.py`](scripts/pro_ledger.py): track web messages and task status; [ledger manual](manuals/pro-ledger.md).
- [`pro_send_hook.py`](scripts/pro_send_hook.py): optional local send-event ledger hook; [ledger manual](manuals/pro-ledger.md).
- [`open_jobs_hook.py`](scripts/open_jobs_hook.py): optional session-start hook listing jobs that may still be running; [hooks manual](manuals/hooks.md).
- [`drive-auth-autoclick/`](drive-auth-autoclick/README.md): optional browser extension for Drive approval cards; [extension manual](drive-auth-autoclick/README.md).

Start with [workspace setup](manuals/workspace.md). Local settings belong in `~/.gptidomath/config.json`; [config.example.json](config.example.json) shows the three settings. Run `python scripts/selftest_all.py --selftest` before adapting the tools. The task skeleton (`../task/`) tells the web side how to use the two file channels. See [NOTICE.md](NOTICE.md) for included-code attribution.
