# Publish a repository or upload package

## What it does and why

`drive_mirror.py` exports committed `HEAD` with `git archive`. The text ZIP includes a file/function index and commit stamp, so the receiver can identify exactly which snapshot it read. Uncommitted and untracked changes stay local. `code_index.py` builds or verifies indexes against the actual archive bytes.

## Set it up

Tell your agent: "Configure this toolkit, inspect the committed files I intend to share, add exclusions I request, preview the export with `--out`, and show me the kept-back-file report."

By hand, choose the repository and files to share. For Drive publishing, complete [workspace setup](workspace.md), sign in to the same account in Drive for desktop and ChatGPT, and handle any first-write approval card. Offline `--out` and `pack` need Python and Git, without a Drive account.

Run from this toolkit directory, replacing `<repo>` with the repository path:

```sh
python scripts/drive_mirror.py push --repo "<repo>" --name sample --out ./mirror-preview
python scripts/drive_mirror.py push --repo "<repo>" --name sample
python scripts/drive_mirror.py status --repo "<repo>" --name sample
```

The Drive destination is `<workspace>/repos/sample/`. `--out` selects an exact local directory. Add `--assets` to include binary files. `--force` rebuilds a current mirror; use `--force --assets` after changing sharing/redaction policy. `--report private-report.json` saves a local report with full kept-back paths; keep it outside shared storage.

The publisher writes `sample-text.zip`, optional `sample-bin*.zip`, and `MIRROR.json` last. It replaces its own archives, removes obsolete binary volumes, and reuses unchanged layers. Local writer locks prevent two local publishers from mixing versions; they do not coordinate separate machines. Each output directory belongs to one repository mirror. Archive publication retries when Drive briefly holds a file and verifies the bytes before replacing it.

Tell the receiver to match the full commit in your task, `MIRROR.json`, and `_mirror/STAMP.json`, verify archive hashes, and extract into a new empty folder. Retrieve binary layers only when needed and check their commit relationship in the manifest. ZIP contents include `INDEX/`, `_mirror/binary-files.tsv`, `_mirror/redactions.tsv`, and `_mirror/excluded-files.json`.

Without Drive, make one upload-ready package:

```sh
python scripts/drive_mirror.py pack --repo "<repo>" --name sample --task task-body.md --out ./upload
```

This produces `upload/sample-package.zip`: `TASK.md` at the root, the committed snapshot in `repo/`, plus `INDEX/` and `_mirror/`. Add `--assets` only for required binaries. The command prints the package size. Large binaries belong on the Drive route; `pack` does not split a package to fit a chat upload allowance. It checks/redacts task text too; inspect the packaged `TASK.md` before uploading.

Exit codes: mirror commands use `0` for success and `2` for an error. `status` uses `1` for a missing, outdated, or damaged text layer. For an unindexed ZIP, `code_index.py --zip <file> --must 'path/to/file::literal'` checks the required text and appends `INDEX/` in place. It uses `0` for success, `1` for a failed content check, and `2` for invalid usage or an already indexed archive. Mirror/package commands already build their indexes; do not run this command on them. Run either script with `--selftest` for local checks.

## Try it end to end

Without ChatGPT, make a disposable Git repository with one committed source file, one binary, and one `export-ignore` path. Ask your agent to set `core.autocrlf false` in that temporary repository, leaving global Git settings alone. Run the preview command with `--assets`, inspect the ZIP paths, manifest hashes, redactions, and omissions, then run `pack` with a short task. Open the package and confirm its root `TASK.md` points to the included repository.

For one small real task, publish the previewed repository, wait for synchronization, and ask the web side to name the commit and explain one function. Supply the exact Drive path and commit. Have it write `NOTES.md` and a non-empty `DONE.txt` to a locally prepared task folder. Compare the answer against the local source before sharing a larger repository.

## Adapt it

Windows and macOS can use Drive for desktop. Use `python3` on systems where `python` is unavailable. Linux needs an explicit mount such as rclone, or manual transfer from `--out`. With manual transfer, upload every archive before `MIRROR.json`. No Drive: use `pack` and attach its one ZIP. Another storage service: set its mounted workspace path, then change the receiver's connector instructions; the archive format stays the same.

## Privacy

Commit exclusions in `.gitattributes` before export:

```gitattributes
private/ export-ignore
private/** export-ignore
local-settings.json export-ignore
build/ export-ignore
build/** export-ignore
```

Exclude credential files unless the task truly needs them: `.env*`, `.npmrc`, `.pypirc`, `.netrc`, `credentials*.json`, `*.pem`, `*.key`, `id_rsa*`, cloud CLI config. Put private names, identifiers, or literal secrets in the local config's `redact` list. The text redactor also masks home paths, local/Git identities, emails, credential patterns, and secret assignments. Inspect `--out` before publishing: patterns cannot infer every private fact. Filename paths and binary content need review too.

Files whose names or encodings cannot be sanitized safely are kept back and listed; sensitive path strings are withheld from the shared report. `--report` gives your agent the full paths locally. Binaries are not rewritten: matching identity/config terms of at least five characters keep the entire file back. Binary contents do not get the text credential scan, and compressed contents are not inspected. Use `export-ignore` for binaries that should never leave the machine. Symbolic links, submodules, and external assets need explicit preparation.

Redacted files differ from the real repository bytes. Archive hashes describe exported ZIP bytes; index line ranges describe the redacted text. `_mirror/redactions.tsv` names changed files. A local-run verifier must account for those entries instead of rejecting the original source as the wrong version.

## Limits seen in practice

Drive synchronization has run at about 55 MB/min; the CLI finishes before cloud synchronization does. The connector reads at most 256 MiB per file. Binary volumes group about 200 MB of input; a single larger file is not split by the mirror. Check the manifest's archive sizes and split oversized archives into parts no larger than 192 MiB, with hashes and reassembly instructions, before sharing. The text layer rejects ZIPs larger than 250 MiB; exclude generated data or use a separate transfer. Never let the web side create Drive folders. `.txt` uploads sometimes arrive as `.txt.gdoc`, and the first Drive write can trigger an approval card.

Tested on Windows 11 + Google Drive for desktop + Python 3.12; other setups untested.
