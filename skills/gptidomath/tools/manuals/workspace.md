# Prepare a task workspace

## What it does and why

`drive_workspace.py` creates the task folder locally, writes `TASK.md` or `TASK-<N>.md`, and joins an opener with a footer. The web side writes files into existing Drive folders; never ask it to create folders. `kit_config.py` gives all local tools the same workspace.

## Set it up

Tell your agent: "Keep the toolkit together, locate Python 3.10+ and Git, configure my existing synchronized workspace, and run the selftests. Use the supplied opener, footer, and task-preface paths."

By hand, install and sign in to Drive for desktop, connect the same Drive account in ChatGPT, and create `AI-workspace` in your Drive root. Copy `config.example.json` to `~/.gptidomath/config.json`. Ask your agent to set `workspace` to that existing local folder and add private terms to `redact`. JSON paths can use forward slashes. A relative configured path resolves beside the config file.

`workspace_name` is the Drive-visible folder name used in messages; its default is `AI-workspace`. Change it if the remote folder has another name. Set `GPTIDOMATH_CONFIG` or pass `--config` to select another config. `GPTIDOMATH_WORKSPACE` overrides the local path; a relative environment path resolves from the current directory.

Without an explicit path, discovery checks Windows drive letters and profile folders, or macOS `~/Library/CloudStorage/GoogleDrive-*`, for English and localized Drive folder names. If discovery finds no root or several accounts, give your agent the exact path. Discovery does not create the root.

```sh
python scripts/kit_config.py
python scripts/selftest_all.py --selftest
python scripts/drive_workspace.py sample-task evidence
python scripts/drive_workspace.py sample-task evidence --check
```

To prepare the task and the message, pass your own files:

```sh
python scripts/drive_workspace.py sample-task --task task-body.md --preface task-preface.md --opener opener.md --footer footer.md --out message.md
```

The task gets the preface, a blank line, then its body. The opener and footer each lose leading HTML comments. The message replaces `{{WORKSPACE}}` with `AI-workspace/sample-task`, `{{TASK_FILE}}` with `TASK.md`, and `{{ROUND}}` with `1`. Only the message goes to standard output; status goes to standard error. Template files are inputs, never rewritten.

For a continuation, add `--round 2`; this writes `TASK-2.md` and uses round `2` in the message. Keep each round's source file separately. Omitting `--opener` and `--footer` writes only the task; provide both to render a message. `--out` saves the message as well as printing it.

Exit codes: `0` success; `1` a folder is missing during `--check`; `2` invalid input, configuration, or I/O failure. `--check` creates nothing and cannot be combined with task/message writing.

## Try it end to end

For a dry run without ChatGPT, create a disposable local directory and point `GPTIDOMATH_WORKSPACE` at it. Create four short UTF-8 files for the task, preface, opener, and footer; put the placeholders above in the opener. Run the preparation command, read `sample-task/TASK.md` and `message.md`, then repeat with `--round 2`. Verify both task files remain. Clear the environment override afterward.

For one small real task, prepare a fresh tag with a task that asks for a one-line calculation, `NOTES.md`, and `DONE.txt` written last. Ask the web side to first write a non-empty `test.txt` containing `1`. Send the rendered message, handle the first-write approval card, and run the [start/delivery watcher](watch.md). Confirm all three files synchronize back before using larger tasks.

## Adapt it

On Windows use `python` or `py -3`; in PowerShell set the override with `$env:GPTIDOMATH_WORKSPACE = '<local-folder>'`. On macOS/Linux use `python3` if needed and `export GPTIDOMATH_WORKSPACE='<local-folder>'`. Quote paths with spaces. No tool changes your shell or global Git settings.

Drive for desktop supplies two-way synchronization on Windows/macOS. On Linux use an explicit rclone mount or a two-way transfer workflow maintained by your agent. A plain directory also works for offline preparation; it does not upload anything. Without Drive use [the upload-package command](mirror.md). For different storage, point `workspace` at its local mount and replace the remote connector instructions and `workspace_name` with the actual remote folder.

## Privacy

Task, preface, opener, and footer contents are copied as supplied; they are not redacted. Review them before preparing a shared folder. Keep local config and private inputs outside the repository snapshot. The mirror's exclusions and redaction rules are described in [mirror.md](mirror.md).

## Limits seen in practice

Allow about 55 MB/min for Drive synchronization; a local write does not prove a remote upload finished. The connector reads at most 256 MiB per file. It may expose a `.txt` upload locally as `.txt.gdoc`; the watchers handle either spelling, but a cloud-document shortcut is not proof that its contents are readable. Never let the web side create folders. Its first Drive write may need a person to approve a card in the conversation.

Tested on Windows 11 + Google Drive for desktop + Python 3.12; other setups untested.
