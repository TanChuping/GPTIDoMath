<!-- TASK.md skeleton. The task file is the real prompt; ChatGPT reads it after the opener.
How to fill it:
  - Replace every {{…}}. Delete sections you do not need and every HTML comment before sending.
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

<!-- Drive route: keep this block. -->
- **Source:** `{{WORKSPACE_ROOT}}/repos/{{PROJECT}}/` is a mirror of our repository at commit `{{COMMIT}}`. Read `MIRROR.json` there, then download `{{PROJECT}}-text.zip` into a **new, empty** directory (code, docs, data, plus `INDEX/` file and symbol tables and `_mirror/` version stamp). Fetch `{{PROJECT}}-bin*.zip` into the same directory only if you need images, audio or other binaries. Check that `commit` in `_mirror/STAMP.json` equals the commit above; if it does not, Drive has not finished syncing, so wait a few minutes and fetch again. `<user>`, `<email>` and `<redacted…>` in the text are our redaction marks, not the code's own spelling.
- **Your workspace:** `{{WORKSPACE}}/` already exists. Write files only into existing folders and never create folders on Drive (Drive's automated review can block that); put any structure inside your ZIPs. `repos/`, `tools/` and other tasks' folders are read-only.
<!-- Package route: replace the block above with this one. -->
<!-- - **Source:** the package you unzipped contains this file, the repository snapshot at commit `{{COMMIT}}` in `repo/`, `INDEX/` and `_mirror/`. Check `_mirror/STAMP.json` against the commit above. -->

**Preparation, before the main work:**
1. Note the time you start, in the sandbox. You keep your own clock (see "Time and wrap-up").
2. {{REQUEST_CHANNEL_BLOCK}}
3. {{LOCAL_RUN_BLOCK}}
<!-- 2: paste tools/request-channel/PROMPT-BLOCK.md with {{WORKSPACE}} and {{TOOLS}} filled (Drive route only; delete otherwise).
     3: paste tools/prompt-blocks/local-run.md (Drive route only; delete otherwise). -->

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

- Ask for as many as the environment allows (try six, including the reviewer below); if fewer are allowed, use what you get and note the number in the delivery. In earlier runs at most three ran at the same time, so plan in waves: when one finishes, start the next.
- A suggested split, adjust as you see fit and say why: one builds shared indexes (function tables, call graphs, state lists) unless `INDEX/` already covers it; several each take one area of the work list; **one reviewer only reviews**, re-checking each reported finding for a real trigger path, a reproduction or minimal counterexample, and whether it would actually happen; one merges, de-duplicates and writes the reply.
- Every subagent's instructions must stand on their own: it cannot see this conversation or the other subagents. Give it the criteria, red lines and checklists it needs, its exact scope and what to hand back.
- Work in complete units: finish one item before the next, assign whole items rather than phases, and stop after a third failed attempt at the same item, note it and move on.
- If subagents are not available, do the same steps yourself, including the review.

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
- **After 70 minutes:** no upper limit. Prepare as if you will work at least two hours and keep going for as long as the list is not done carefully and completely. The only difference from the first 70 minutes is saving more often: after each stage, or every 15–20 minutes, save a new numbered stage ZIP and handover notes (where you are, what is next, how to resume), and check the request channel when you do. Do not shrink or split large items to save time.
- If the platform shows signs of stopping you (tools failing repeatedly, responses slowing sharply, warnings about context or length), stop and deliver the latest stage at once.
- Subagents follow the same rhythm: they hand back what they have before the safety delivery and before each stage save.
- The finish line is a list done carefully and completely, not a number of items. When the list is done, strengthen evidence and polish; deliver the final version only when nothing useful is left.

## Delivery

- One ZIP per stage, numbered, never overwriting an earlier one, laid out as `finished/` (passed its checks), `unfinished/` (how far it got, what is missing), `METHOD.md` (how you worked, how you checked, what did not work) and `REPLY.md`, whose first line reads `finished N / unfinished M / about X minutes`.
- Give a download link in the conversation for every ZIP; files in the sandbox stop being downloadable a few minutes after a turn ends, so do not run anything that clears them after delivering.
<!-- Drive route: keep the next three lines. -->
- Also save each ZIP into `{{WORKSPACE}}/` under a new file name, and save `NOTES.md` separately: source commit, request version applied, work done, checks, remaining work.
- After everything else is saved, write `DONE.txt` into `{{WORKSPACE}}/` as the **very last** step, one line: `finished N / unfinished M / <ZIP file name>`. We are woken by that file, so nothing may be written after it.

## Bookkeeping kept light

- The material has been checked on our side: the snapshot matches the commit and `INDEX/` was built from the same bytes. No need to re-hash files, correct the index, or produce function-level coverage tables.
- One coverage table is enough, if any: `evidence/coverage-lines.tsv` with the header `path category total unread deep_ranges`, one row per file.
- Every file `REPLY.md` mentions must be inside the ZIP.
- If the sandbox was reset during the run, say so and redo what is needed.
