# Watching for delivery and stalled work

## Principle

`drive_wait.py` waits for a readable, non-empty completion marker. `watch_job.py` also reports new ZIP files and long gaps without remote output. An event asks the coordinator to inspect the delivery or conversation; a ZIP or quiet folder does not prove that the task is complete. Neither script monitors a browser or survives a stopped computer/process without being restarted.

## Setup

User actions: connect Drive, configure local synchronization, create the workspace, and approve the first remote write when prompted. Your agent creates task folders locally, tells the remote agent to write non-empty `test.txt` first, then ZIP outputs and NOTES.md, and finally a non-empty DONE.txt listing completed/unfinished counts and filenames. Start the watcher in your agent's existing background-task mechanism so its exit can wake the coordinator. Ordinary shells only print the result; notification depends on the host.

For `watch_job.py`, configure the existing workspace via `~/.gptidomath/config.json`, `--config`, or `GPTIDOMATH_WORKSPACE`. `drive_wait.py` takes the exact local marker path directly. Re-arm watchers after an event or host timeout. For a continuation, use a new marker such as DONE-r2.txt and tell the remote agent that exact filename; otherwise an old DONE produces an immediate event.

## End-to-end dry run

Run from `tools`:

```sh
python -B scripts/drive_wait.py --selftest
python -B scripts/watch_job.py --selftest
python -c "from pathlib import Path; import json; p=Path('dry-workspace/example'); p.mkdir(parents=True,exist_ok=True); Path('dry-config.json').write_text(json.dumps({'workspace':'dry-workspace'}),encoding='utf-8'); (p/'test.txt').write_text('1'); (p/'DONE.txt').write_text('completed 1 / unfinished 0 / sample.txt')"
python -B scripts/drive_wait.py dry-workspace/example/DONE.txt --every 1 --timeout 10
python -B scripts/watch_job.py example --config dry-config.json --limit 10
```

Both commands print DONE. The isolated selftests also cover empty markers, ignored control files, startup checks, quiet-output review and persistence across restarts. For one small real task, ask your remote agent to summarize a short public text, save the summary and NOTES.md, and write DONE last. Verify the files locally when the watcher wakes, including completed/unfinished claims.

## Commands, semantics and exits

`python scripts/drive_wait.py PATH/TO/DONE.txt --every 20 --quiet 10 --start 6`

`--every` is seconds; `--quiet` and `--start` are minutes. Quiet fallback starts only after an output changes during this invocation, watches recursively, and ignores local controls and system/sync temporary files. A missing/empty/unreadable test.txt at the start arms the startup deadline; zero disables it. `--timeout SECONDS` defaults to 0 (unlimited). Exit 0 = stable readable DONE, 1 = I/O/data error, 2 = quiet-output review or CLI error, 3 = no startup probe, 4 = timeout, 130 = interrupted. Quiet review is not acceptance; inspect NOTES.md and the conversation.

`python scripts/watch_job.py TASK --stall 2100 --limit 7000 --every 60`

All values are seconds. `--stall 0` disables stall detection, `--limit 0` checks once. `--done NAME` selects a marker; `--zip-match TEXT` restricts new ZIP names. Exit 0 prints DONE, NEW-ZIP or STALL; 1 = I/O/data error; 2 = timeout or CLI error; 130 = interrupted. Only top-level files count, so keep remote deliveries in the task root. ZIPs already present at startup do not trigger NEW-ZIP; use new filenames for new stages. Empty/unreadable DONE never signals completion.

`REQUEST.md`, `reply.txt`, generated `reply<N>-*` attachments/manifests, `relay-*`, `TASK*.md`, system files and sync temporaries never count as activity, including their `.gdoc` aliases. Remote ZIPs named `REPLY-task-stage.zip` still count. Changes in subdirectories do not reset the watchdog. It stores observed output metadata and the last output write time locally under `~/.gptidomath/state/watch/` (or `GPTIDOMATH_HOME`), keyed by task path and marker. Restarting the same watcher never resets its stall clock, even with no output files. A stale task can therefore report STALL immediately. Output timestamps must be meaningful; copied files retaining old timestamps can trigger an early stall. Deletions alone do not reset it.

## Adaptation, privacy and limits

Windows uses Drive for desktop and `python`; macOS/Linux may need `python3` and an explicit workspace path. With rclone or another storage provider, supply a working local mount/sync and remote transfer route yourself. Without synchronization, watchers see only manually downloaded files. They do not query cloud APIs or prove that the cloud has received a local write. Preserve local state across restarts; deleting it discards the no-output history.

Budget approximately 55 MB/min for sync; that is a planning estimate. Observed connector reads have a 256 MiB per-file limit. Split large inputs, and do not infer a stall solely from a slow large transfer. Remote agents must write into pre-created folders, never create folders on Drive. Readable plain-text aliases `DONE.txt.gdoc` and `test.txt.gdoc` are accepted when the exact file has no readable non-empty content. Actual Google document shortcuts containing JSON URL/document references are rejected: export real text or correct the remote file type. First-write approval may need a manual click in the conversation; the NO-START event is a prompt to inspect it, not proof of the cause.

Logs print task names and completion text. Keep logs and local watcher state private. File activity is a hint: work that computes silently for more than 35 minutes can legitimately produce STALL. Inspect the actual conversation before deciding what to do next.

Tested on Windows 11 + Google Drive for desktop + Python 3.12; other setups untested
