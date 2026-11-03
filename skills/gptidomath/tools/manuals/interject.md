# Request updates

## Principle

`drive_request.py` appends a numbered update to a task's `REQUEST.md`. The remote coordinator reads it at coordination checkpoints, passes changes to affected workers and records the version applied. Later requests take precedence. This does not interrupt a running tool or revive a finished conversation.

## Setup

User actions: connect Google Drive in the remote conversation, install/configure your sync client, create a local `AI-workspace` folder, and approve the first write when asked. Your agent sets `workspace` in `~/.gptidomath/config.json` to that existing folder, or uses `GPTIDOMATH_WORKSPACE`; `--config` and `GPTIDOMATH_CONFIG` select another JSON configuration. The default workspace name is `AI-workspace`.

Your agent creates the task folder locally, shares `request-channel/` in the tools folder, and keeps the task skeleton's "Changes while you work" section, whose paths `drive_workspace.py` fills in. The remote coordinator installs the reminder only in its temporary sandbox. It checks at task start, before delegation/integration/major decisions, at safe checkpoints when the 15-minute reminder is due, and before delivery. Workers do not independently poll Drive.

## End-to-end dry run

Run from this `tools` directory. These commands create an ordinary local test folder; no cloud access is needed.

```sh
python -B scripts/drive_request.py --selftest
python -B request-channel/channel.py --selftest
python -c "from pathlib import Path; import json; Path('dry-workspace').mkdir(exist_ok=True); Path('dry-config.json').write_text(json.dumps({'workspace':'dry-workspace'}),encoding='utf-8')"
python -B scripts/drive_request.py example "Report the measured result and remaining uncertainty." --config dry-config.json
python -B scripts/drive_request.py example --show --config dry-config.json
python -B scripts/drive_request.py example "Keep the original input unchanged." --config dry-config.json
```

Confirm `Version: 2` and both ordered entries in `dry-workspace/example/REQUEST.md`. The channel selftest installs hooks only inside an automatically removed temporary directory. Never test `install --sandbox-home` against your regular home directory.

For one small real task, ask your remote agent to summarize a short public text in the prepared task folder. While it works, append one changed output requirement. Have it include the applied request version in NOTES.md and write a non-empty DONE.txt last. Verify the actual change in its delivery.

## Commands and exits

`python scripts/drive_request.py TASK "text"` appends; `--file update.md` reads UTF-8 text (BOM allowed); `--show` displays the current file. Exit 0 means written/shown, 2 means usage/I/O/data error, 130 means interrupted. Malformed existing headers are rejected instead of resetting numbering.

`channel.py record --version N --mtime ISO_TIME` records a confirmed Drive check. An unchanged modification time can reuse the confirmed version; a changed file must carry a higher version before recording it. `due` and `status` inspect local state. See request-channel/README.txt for hook activation and exit codes. Failure of an optional hook means checkpoint checks remain necessary.

## Adaptation and limits

Windows uses `python`; macOS/Linux may use `python3`. Choose your actual Drive Desktop path, including localized folder names. On Linux or with rclone, point `workspace` at a writable mounted or synchronized folder and arrange transfers yourself; these scripts do not launch rclone. With no sync client, manually upload/download files; the reminder still works, but timely file-based updates require a transfer route. Other storage can work if both sides can read/write the same folder and the local view refreshes; connector behavior must be checked separately.

Plan roughly 55 MB/min for cloud sync; it is an estimate, not a guarantee. The observed connector read limit is 256 MiB per file. Pre-create all folders locally: the remote agent must not create folders. A connector can expose text as `.txt.gdoc`. Delivery/startup monitors accept readable plain-text aliases for DONE.txt and test.txt, but reject actual Google document shortcut JSON; export shortcut content to plain text if needed. Request files still use their exact agreed names. The first write may require user approval; request a non-empty `test.txt` at startup.

Review what you put into requests: these files are sent verbatim, with no automatic redaction. Atomic writes and local process locks prevent half-written files and lost updates between writers on this computer; they do not lock writers on another computer or guarantee cloud sync ordering. Two computers should not append the same channel at once.

Tested on Windows 11 + Google Drive for desktop + Python 3.12; other setups untested
