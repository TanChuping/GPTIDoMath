<!-- TASK.md skeleton. The task file is the real prompt; ChatGPT reads it after the opener.
How to fill it:
  - Replace every {{…}} and delete sections you do not need. Parts between BEGIN/END drive or BEGIN/END package lines belong
    to one route: drive_workspace.py keeps the drive parts and drive_mirror.py pack keeps the package parts. Both drop every
    HTML comment, and both refuse to write while a {{NAME}} outside a code block is left. drive_workspace.py fills
    {{WORKSPACE}}, {{WORKSPACE_ROOT}} and {{TASK_FILE}} itself, and {{PROJECT}} and {{COMMIT}} with --repo (pack fills those two as well), so leave them as placeholders. Other routes: python3 task_text.py --route package (or drive).
  - drive_workspace.py --task … --preface ../task/en/preface.md puts the preface on top; on the package route put it there yourself.
  - Write it as explanation (purpose + how to judge + trade-offs), not as commands. A model that is careful by nature turns
    "MUST / NEVER" into over-defensive work and late delivery.
  - Keep the "Time and wrap-up", "Delivery" and "Bookkeeping kept light" sections as they are: they are what makes long runs pay off.
-->
# {{TITLE}}

## What to do this time

{{MAIN_JOB}}
<!-- At most five lines: the main job in one sentence (read what, find what, build what) · what this run covers and what it does not ·
the deliverable in one sentence · the one or two criteria that matter most. Everything below is material for these lines. -->

{{PROJECT_HEADER}}
<!-- Paste the body of your project header (project-header.md) here, or delete this line. -->

## Material and setup

<!-- BEGIN drive -->
- **Source:** `{{WORKSPACE_ROOT}}/repos/{{PROJECT}}/` is a mirror of our repository at commit `{{COMMIT}}`. Read `MIRROR.json` there, then download `{{PROJECT}}-text.zip` into a **new, empty** directory (code, docs, data, plus `INDEX/` file and symbol tables and `_mirror/` version stamp). Fetch `{{PROJECT}}-bin*.zip` into the same directory only if you need images, audio or other binaries. Check that `commit` in `_mirror/STAMP.json` equals the commit above; if it does not, Drive has not finished syncing, so wait a few minutes and fetch again. `<user>`, `<email>` and `<redacted…>` in the text are our redaction marks, not the code's own spelling.
- **Your workspace:** `{{WORKSPACE}}/` already exists. Write files only into existing folders and never create folders on Drive (Drive's automated review can block that); put any structure inside your ZIPs. `repos/`, `tools/` and other tasks' folders are read-only.
<!-- END drive -->
<!-- BEGIN package -->
- **Source:** the package you unzipped contains this file, the repository snapshot at commit `{{COMMIT}}` in `repo/`, `INDEX/` and `_mirror/`. Check `_mirror/STAMP.json` against the commit above.
<!-- END package -->

**Preparation, before the main work:**
1. Note the time you start, in the sandbox. You keep your own clock (see "Time and wrap-up").
<!-- BEGIN drive -->
2. Set up the change reminder and read `{{WORKSPACE}}/REQUEST.md` (see "Changes while you work" below). Skim "Asking us to run something" too, so you know when to use it.
<!-- END drive -->

## Full work list (you set the order)

{{WORK_LIST}}
<!-- List EVERYTHING you want done before you next look at the results, main tasks first and then a backlog, each with one line of
     "why it matters". Do not write "this round only does X": it becomes the finish line and the run stops early.
     Under-filling is the usual mistake; a list that cannot be finished in four hours is fine. -->

Order the list by dependency and value yourself; we would rather you spend the session on what matters most than follow our order. When everything on it is done, first ask a subagent that produced none of the work to re-check every deliverable's core logic, then look for further useful work in {{MORE_WORK_SOURCE}}, and only then deliver the final version.

## Red lines

{{RED_LINES}}
<!-- Settled decisions and things not to do, one per line, each followed by what it means in practice. -->

## Scenario and defaults

{{SCENARIO}}
<!-- Who uses this, on what hardware or network, and the real default settings of the parts under study, so consequences are judged
     against reality and not against an extreme configuration. -->

## Subagents

Please split this work across subagents and run them in parallel, using the strongest model available to you for every subagent: the same quality of judgement matters more than the time a smaller model would save.

- On our side this whole session counts as one message, so every subagent running in parallel is extra work at no extra cost. Ask for as many as the environment allows (try six, including the reviewer below); if fewer are allowed, use what you get and note the number in the delivery. In earlier runs at most three ran at the same time, so plan in waves: when one finishes, start the next.
- A suggested split, adjust as you see fit and say why: one builds shared indexes (function tables, call graphs, state lists) unless `INDEX/` already covers it; several each take one area of the work list; **one reviewer only reviews**, re-checking each reported finding for a real trigger path, a reproduction or minimal counterexample, and whether it would actually happen; one merges, de-duplicates and writes the reply.
- Every subagent's instructions must stand on their own: it cannot see this conversation or the other subagents. Give it the criteria, red lines and checklists it needs, its exact scope and what to hand back.
- Work in complete units: finish one item before the next, assign whole items rather than phases, and stop after a third failed attempt at the same item, note it and move on.
- If subagents are not available, do the same steps yourself, including the review.

<!-- BEGIN drive -->
## Changes while you work

We may add work or change a requirement while you are running. A new message from us would end your turn, so instead we append to `{{WORKSPACE}}/REQUEST.md`. Its first line is `Version: N`. Each update raises N by one; a later update wins over an earlier one, and the file wins over this one where they conflict. If the file does not exist yet, nothing has changed.

To be reminded, copy `channel.py`, `README.txt` and `VERSION` from `{{WORKSPACE_ROOT}}/tools/request-channel/` into your sandbox, then run `python3 channel.py --selftest` and `python3 channel.py install --sandbox-home "$HOME"`. This installs a reminder in the sandbox only: once 15 minutes have passed since your last check, the next new shell or Python cell prints `CHANNEL_CHECK_DUE`. A shell or Python kernel that was already running does not see it until you activate it as `README.txt` describes; where you do not, call `python3 channel.py due` at each checkpoint. If the install does not work, skip it and check at the points below anyway.

You, the coordinator, do the checking; subagents do not read the file. Check at the start, before handing out or merging work, before a big decision, whenever the reminder says so, at every stage save and before the final delivery:
- If the file's Drive modification time is the same as last time, nothing is new.
- If it changed, read the whole file. When `Version` went up, apply what is new. When only the time changed, we are still writing; look again at the next check.
- Record a check once you have read a higher version, or found the file unchanged since your last record: `python3 channel.py record --version N --mtime '<Drive modification time>'`. Recording resets the reminder. Do not record while only the time changed or while the file does not exist yet; look again later.
- Pass each new requirement to the subagents it affects, and re-check work they finished under the old version before you merge it.
- Write the version you applied into each `NOTES.md`, with what it changed.

## Asking us to run something

Some checks need what your sandbox does not have: a GPU, a display, a real device, network access, our local platform, or a run too long or too large for the sandbox. When a decision depends on one, ask us to run it on our machine; this needs no new message. Anything you can settle in a few minutes in the sandbox, or by reading the code, do yourself.

- **Asking:** write `{{WORKSPACE}}/requestfromweb.txt` in UTF-8. The first line is `Version: N`. Each request is a section `## Request N (UTC time)` that says what the result will decide, the exact commands and inputs, which outputs to send back and under what names, how to tell success, and `Blocking: yes` or `no`. Keep the `Version:` and `## Request` lines exactly in this form; our tools look for them. Rewrite the whole file each time and keep the earlier requests. Raise the version by one per new request; if you have to edit in several steps, change the version line last. We read every request before running it, so write it the way you would for a colleague.
- **Answer:** usually within a few minutes to half an hour, in `{{WORKSPACE}}/reply.txt`: `Version: N`, then sections `## Reply N (Request K, time)`. Attachments sit next to it in the task folder, not in subfolders, and start with `reply<N>-`; `reply<N>-attachments.json` lists their parts, sizes and SHA-256. Files over 192 MiB come as raw byte segments: download every segment, join them in the listed order and check the hashes; do not unzip segments one by one. A reply can sync before its attachments, so if one is missing, look again a little later.
- **Keep going:** do not wait for the answer. Work on other items, look at `reply.txt` whenever you check `REQUEST.md`, and pass results to the subagents that need them. If an answer is still missing at delivery, list the open requests in `NOTES.md` with their commands and what each would decide.
<!-- END drive -->

## How we will use your reply

- We take every finding back to the full project and check it before acting. The fastest to check are those that state location, trigger sequence and the original text; a bare conclusion makes us re-derive everything.
- You see the material; callers and runtime data outside it you may not. Write "would this happen" only as far as the material proves it, state the assumptions, and leave reachability to us.
- We apply fixes ourselves on the current code, so patches are references. Attach a unified diff for anything that must change; for a large restructuring a function-level plan is enough.

## Output format

Findings, most important first:

```
F1  <one-line title>
    Location: <path:line>
    Trigger: <a sequence a person can follow>
    Evidence: <the original lines, not a paraphrase>
    Severity: must fix / should fix / good to know
    Fix: <one sentence>
```

Severity is about how soon it would really happen in our scenario: by default, would a careless but not malicious person on an ordinary machine run into it within a month? If not, it is not a finding; list it in one line under "seen but judged unlikely". When more than three items are "must fix", re-check them. Removable safeguards, records nobody reads and duplicated logic are worth reporting too: removing often beats adding.

Add a final section, "Not visible to me, please check", listing what you could not confirm because of the material's boundary, each with what to check and where. That list is work for us, not a disclaimer.

## Time and wrap-up

These sessions have no fixed length (runs of several hours are common), but they can disconnect, and after a disconnect nothing more is delivered. So there is no time limit, only staged saving:

- Note your start time in the sandbox and keep your own clock; do not rely on the platform's scheduled tasks or reminders. **Count only real working time:** time spent stuck, waiting for an approval, for Drive, or for a stalled tool does not count; resume the count when work resumes.
- **0–70 minutes:** work normally down the list.
- **At 70 minutes:** spend about ten minutes packaging a complete safety delivery (structure below), good enough to use even if the session drops right after. **This is not the end.** Keep working.
- **After 70 minutes:** no upper limit. Prepare as if you will work at least two hours and keep going for as long as the list is not done carefully and completely. The only difference from the first 70 minutes is saving more often: after each stage, or every 15–20 minutes, save a new numbered stage ZIP and handover notes (where you are, what is next, how to resume). Do not shrink or split large items to save time.
<!-- BEGIN drive -->
- At each stage save, also check `REQUEST.md` and `reply.txt`.
<!-- END drive -->
- If the platform shows signs of stopping you (tools failing repeatedly, responses slowing sharply, warnings about context or length), stop and deliver the latest stage at once.
- Subagents follow the same rhythm: they hand back what they have before the safety delivery and before each stage save.
- The finish line is a list done carefully and completely, not a number of items. When the list is done, strengthen evidence and polish; deliver the final version only when nothing useful is left.

## Delivery

- One ZIP per stage, numbered, never overwriting an earlier one, laid out as `finished/` (passed its checks), `unfinished/` (how far it got, what is missing), `METHOD.md` (how you worked, how you checked, what did not work) and `REPLY.md`, whose first line reads `finished N / unfinished M / about X minutes`.
- Give a download link in the conversation for every ZIP; files in the sandbox stop being downloadable a few minutes after a turn ends, so do not run anything that clears them after delivering.
<!-- BEGIN drive -->
- Also save each ZIP into `{{WORKSPACE}}/` under a new file name, and save `NOTES.md` separately: source commit, request version applied, work done, checks, remaining work.
- After everything else is saved, write `DONE.txt` into `{{WORKSPACE}}/` as the **very last** step, one line: `finished N / unfinished M / <ZIP file name>`. We are woken by that file, so nothing may be written after it.
<!-- END drive -->

## Bookkeeping kept light

- The material has been checked on our side: the snapshot matches the commit and `INDEX/` was built from the same bytes. No need to re-hash files, correct the index, or produce function-level coverage tables.
- One coverage table is enough, if any: `evidence/coverage-lines.tsv` with the header `path category total unread deep_ranges`, one row per file.
- Every file `REPLY.md` mentions must be inside the ZIP.
- If the sandbox was reset during the run, say so and redo what is needed.
