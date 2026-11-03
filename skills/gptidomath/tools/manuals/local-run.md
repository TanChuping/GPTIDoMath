# Local runs requested by the remote agent

## Principle

The remote coordinator writes numbered requests in `requestfromweb.txt`; your local agent reviews each request, runs appropriate authorized work, and publishes a numbered reply. `web_ask.py` transfers messages and files only. It never executes a command found in a request. Use prompt-blocks/local-run.md in the task prompt.

## Setup

User actions: connect the remote agent to Drive, configure Drive for desktop or your own transfer route, create the workspace and handle first-write approval. Your agent configures `~/.gptidomath/config.json` with an existing `workspace`, creates the task folder locally, and starts `web_ask.py wait TASK` in its normal background-task facility. Use `--config FILE` or `GPTIDOMATH_CONFIG` for another config, or `GPTIDOMATH_WORKSPACE` for a direct path.

On a request event, inspect the commands, inputs, resource needs and privacy implications within the user's authorized task before running it. Keep your existing project entry points. Reply with the measurement, source/input version, limitations and relevant files, then restart the listener. Continue independent work while the remote agent waits.

## End-to-end dry run

From `tools`, with ordinary local files:

```sh
python -B scripts/web_ask.py --selftest
python -c "from pathlib import Path; import json; p=Path('dry-workspace/example'); p.mkdir(parents=True,exist_ok=True); Path('dry-config.json').write_text(json.dumps({'workspace':'dry-workspace'}),encoding='utf-8'); (p/'requestfromweb.txt').write_text('Version: 1\n\n## Request 1 (sample)\n\nCount the lines in the provided text.\n',encoding='utf-8')"
python -B scripts/web_ask.py wait example --timeout 1 --config dry-config.json
python -B scripts/web_ask.py reply example "Measured 3 lines in the sample." --to 1 --config dry-config.json
python -B scripts/web_ask.py show example --config dry-config.json
```

The first wait prints NEW-REQUEST; another wait for that version times out because receipt is saved locally. Use a new request version to repeat. The selftest also verifies split-file reassembly, hashes, parallel replies and failed-publication cleanup.

For one small real task, ask the remote agent to prepare a public five-line text and request a local line count. Run the count using your existing local tools. Reply with the actual result and its log using `--file result.log`, then verify the remote agent cites the reply number. This exercises both sync directions without a long computation.

## Commands and exits

```sh
python scripts/web_ask.py wait TASK --timeout 7000 --interval 20
python scripts/web_ask.py show TASK
python scripts/web_ask.py reply TASK "Conclusion" --to 1 --file result.log --file result.zip
```

Exit 0 means success or a new request; 1 means I/O/data failure; 2 means timeout or CLI usage error; 130 means interrupted. `--timeout 0` checks once. Receipt state is keyed by the full task path under `~/.gptidomath/state/requests/`, isolated by `GPTIDOMATH_HOME` when set. `show` does not consume a request. Keep request versions increasing when reusing a task folder.

Replies are appended under a local process lock. Attachments get unique `replyN-index-name` names in the task ROOT, because connector search may miss binaries in subfolders. Files larger than 192 MiB are streamed into numbered byte segments; memory use is bounded by 1 MiB copy blocks. `replyN-attachments.json` lists original size/hash and each part's order/size/hash. Concatenate in that order and verify the whole SHA-256 before opening. These are raw segments, not independent ZIP files. Text is published last, but cloud sync may reorder uploads; retry missing attachments after sync. Failed publication keeps the prior reply and removes files created by that failed attempt where possible.

## Adaptation, privacy and limits

Windows: use `python` with your Drive for desktop folder. macOS/Linux: use `python3` if needed and set your actual path. An rclone mount or other storage must provide readable local files and a corresponding remote connector or manual transfer route; no rclone process is started for you. Without Drive, exchange these text files and attachments manually; `wait` only sees local changes. Choose one writing computer per task; the lock does not span machines.

The workspace name defaults to `AI-workspace`. Plan about 55 MB/min for sync, with substantial variation. Observed connector reads are limited to 256 MiB per file; the 192 MiB split leaves room below that limit. Pre-create task folders locally; the remote agent must not create cloud folders. Ask it to write a non-empty test.txt first and handle approval manually. The request/reply channel requires its exact filenames: if those files appear as `.txt.gdoc`, export plain UTF-8 under the agreed channel names. Delivery/startup monitors separately accept readable text aliases for DONE.txt and test.txt; actual Google document shortcut JSON is not their content.

Request/reply text and attachments are copied verbatim, not redacted. Select only task-relevant outputs; keep credentials and personal configuration out. A request file is input to review, not permission for unrelated actions.

Tested on Windows 11 + Google Drive for desktop + Python 3.12; other setups untested
