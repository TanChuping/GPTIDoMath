---
name: gptidomath
description: Hand a large, self-contained job (code audit, survey, spec, patch design, data analysis, headless experiments, image work) to ChatGPT Pro on the web so that one message runs for hours. Send a mathematical-research opener, keep the real task in a file (Google Drive, an uploaded package or a repository), steer the job while it runs, then collect and check the result. Use when the user wants to send work to ChatGPT Pro or GPT Pro on the web, make the most of their Pro messages, or set up GPTIDoMath.
---

# GPTIDoMath

ChatGPT Pro on the web is billed per message, not per token, and one message can keep working for hours with its own Linux sandbox and subagents. This skill helps you, the user's agent, get the most out of each message:

- The **message** is a mathematical-research opener plus a short fixed footer ([`openers/`](openers/)).
- The **real task** waits in a file, `TASK.md`, written from [`task/`](task/) and placed on Google Drive, in an uploaded package, or in a repository.
- **Tools** ([`tools/`](tools/)) publish the repository, create the task folder, steer a running job without a new message, let the web side ask this machine to run things, wake you on delivery or stall, count Pro messages, and answer the Drive approval card.

This is experimental (see the disclaimer in the repository README). Talk to the user in their language, keep it plain, and never make them read these files: ask, explain the trade-off, then do the work. If the user asks how this compares with reverse proxies of the web app or MCP bridges to their computer, the repository README has a section on it: normal web use and normal quota, and the web side never gets a direct line into this machine.

## 1. First-time setup: interview the user

Explain in two or three sentences what this does, then ask the questions below, one at a time, with the pros and cons shown. Record the answers in `~/.gptidomath/setup.md` so later sessions do not ask again.

**Q1. Who sends the message?**

| Choice | What the user does | Extra setup | Pros | Cons |
|---|---|---|---|---|
| **By hand** ([`send/by-hand.md`](send/by-hand.md)) | Pastes the message into ChatGPT and clicks the Drive approval card | None | Nothing to install; the user sees everything | User must be at the computer to send and approve; steering and local runs still need this agent session kept open |
| **Voyager CLI** ([`send/voyager-cli.md`](send/voyager-cli.md)) | Installs it once and pairs it | Node.js, Voyager CLI, the Voyager browser extension | Fully scriptable; several jobs at once | Third-party tool to keep updated; depends on its extension keeping up with ChatGPT |
| **You, through the browser** ([`send/browser-relay.md`](send/browser-relay.md)) | Lets you act on chatgpt.com | A browser-control extension or computer use for you | Most tested; you adapt when the page changes | Costs some of your tokens for watching; uses the user's logged-in browser |

**Q2. How does the material reach ChatGPT?**

| Choice | Extra setup | Pros | Cons |
|---|---|---|---|
| **Google Drive** (recommended) | ChatGPT's Google Drive connector, plus Google Drive for desktop or rclone on this machine | Large material once, reused by every chat; steering, local-run requests and delivery wake-up work | One-time setup; sync delay; the first write in each chat shows an approval card |
| **Uploaded package** | None | Simplest | No steering, no local-run requests, no wake-up; re-upload for every follow-up; size limits |
| **GitHub repository** | ChatGPT's GitHub app | Version-controlled tasks | **Untested by the authors**: delivery, steering and wake-up need scripts you write yourself |

Then tell the user plainly what their combination supports. Who sends does not matter here; the material route and whether you keep running do:

| | Steering a running job (`REQUEST.md`) | Local-run requests | Wake-up on delivery / stall |
|---|---|---|---|
| **Drive**, any sender | Yes. Whenever the user asks, you write the request. | Yes, only while you are running with the listener started | Yes, only while you are running with the watchers started |
| **Uploaded package**, any sender | No: a change means a new message | No | No: the user downloads the ZIPs by hand |
| **GitHub** | Untested | Untested | Untested |

So "send by hand + Drive" keeps every feature, provided this agent session stays open while the job runs. If the user closes it, steering waits until they reopen it, local-run requests go unanswered (the web side lists them in its notes and carries on), and nobody is woken.

**Q3. Which language?** Openers exist in English and Chinese ([`openers/en`](openers/en), [`openers/zh`](openers/zh)); the task file says which language to answer in.

**Q4. Extras.** The Pro ledger is recommended: ChatGPT does not show how many messages are left ([`tools/manuals/pro-ledger.md`](tools/manuals/pro-ledger.md)). For the Drive approval card, pick one helper: the GPT Voyager extension's opt-in auto-allow, Voyager CLI's `--approve-apps always`, this repository's [`tools/drive-auth-autoclick/`](tools/drive-auth-autoclick/), or clicking by hand. Hooks: a reminder at session start that lists jobs still running, and one after each browser send to log it ([`tools/manuals/hooks.md`](tools/manuals/hooks.md)); recommended for Claude Code, and other shells can set up the same from the manual.

Then set up what was chosen. Commands below run from this skill's folder (the one containing this file):

1. Copy `tools/config.example.json` to `~/.gptidomath/config.json` and fill in the workspace (the local folder that syncs to Drive's `AI-workspace/`) and any private terms to redact.
2. Run `python3 tools/scripts/selftest_all.py`. Everything must pass. Fix or adapt the tools for this OS (each manual has an "Adapt it" section), then run it again.
3. Drive route: create `AI-workspace/` with `repos/`, `tools/` and `tools/request-channel/` (a copy of [`tools/request-channel/`](tools/request-channel/)), and ask the user to connect Google Drive in ChatGPT's settings with the same Google account.
4. Read the privacy section of [`tools/manuals/mirror.md`](tools/manuals/mirror.md) with the user. Agree what never leaves the machine (`export-ignore`, `redact`). Run `drive_mirror.py push --out <temp>` and show the user what would be uploaded before the first real push.
5. If the user chose hooks, add them as [`tools/manuals/hooks.md`](tools/manuals/hooks.md) describes (back up the settings first) and run each hook command once by hand.
6. Run one small trial end to end, for example "summarise the README and list three questions". To save Pro messages, the trial may use a cheaper model. Check that `test.txt`, the approval card, the request channel and `DONE.txt` all behave as the manuals say.

## 2. Is a job a good fit?

Write down what you yourself would open to do the job, then ask:

1. **Is everything on that list a file, document, data, image, or a command that runs headless on Linux?** If any item needs a window, a GPU, a real device, a live service, credentials, or human feel, it does not fit (or that part goes back to this machine through a local-run request).
2. **Can you draw the boundary now** ("these areas, not those")? Areas are enough; the model searches inside them.
3. **Is it one big task?** Pro is billed per message, so a ten-minute question and a five-hour task cost the same. Bundle work; do not send small questions.

Not a fit: many tool or MCP calls, live monitoring, multi-turn back-and-forth, answers that depend on this machine's live state, git operations, and anything the user can judge at a glance. When unsure, look first: list the files, why each one matters, and the rough size.

Good fits: auditing a whole subsystem, a cross-file survey, a design decision, a specification, test design, patch proposals with reasoning, data analysis on supplied files, headless experiments with a runnable kit (tests, simulations, ablations; a few iterations, not dozens of long compile–debug cycles), and image restyling or layered cut-outs with reference images.

## 3. Each job

1. **Tag.** A short folder-safe name, new for each new conversation (`audit-net`, `audit-net-b` for a restart).
2. **Task file.** Start from [`task/en/task-skeleton.md`](task/en/task-skeleton.md) (or `task/zh/`) and the project header ([`task/en/project-header.md`](task/en/project-header.md), filled once per project). Rules that matter:
   - The first screen says what to do in at most five lines.
   - Keep the `BEGIN/END drive` and `BEGIN/END package` lines. The tools keep the parts for the route in use (the Drive parts teach mid-run changes, local-run requests and `DONE.txt`), drop every HTML comment, and refuse to write while a `{{NAME}}` is unfilled.
   - Leave `{{PROJECT}}` and `{{COMMIT}}` as placeholders: `drive_workspace.py --repo` and `pack` fill them from what is actually published, so a reused task cannot carry an old commit.
   - Put **all** the work you want done before the next check into the list, then a backlog. Never write "this round only does X": it becomes the finish line. Under-filling is the usual mistake.
   - Explain purpose, criteria and trade-offs instead of issuing orders. A careful model turns "MUST/NEVER" into over-defensive work and late delivery.
   - Do not presuppose the answer: ask "judge whether X holds", not "confirm X".
   - Give the real default settings and the usage scenario, so severity is judged by "would this happen within a month", not by extremes.
   - Avoid security-flavoured verbs (bypass, exploit, inject, crack, attack, payload) in everything you write. Harmless jobs have been stopped by keyword filters. Words like crash, memory or race are fine.
   - Leave out internal chatter, command words you use with the user, and your own history. A stranger must understand every sentence.
3. **Material.**
   - Drive: commit first, then `drive_mirror.py push` (add `--assets` for binaries) and wait for sync.
   - Package: `drive_mirror.py pack --task TASK.md --out send/`.
   - Anything the mirror does not contain (screenshots, data files, uncommitted work) goes into the task folder as plain files.
4. **Workspace and message.** On Drive, `drive_workspace.py <tag> evidence --task TASK.md --repo <repository> --preface task/en/preface.md --opener openers/en/<body>.md --footer openers/en/footer-drive.md --out message.md` creates the folder, writes `TASK.md` and prints the message. `--repo` fills `{{PROJECT}}` and `{{COMMIT}}` from the published mirror and stops if the mirror is behind the repository's HEAD (push it again). The command also refuses a task with unfilled placeholders ([`tools/manuals/workspace.md`](tools/manuals/workspace.md)). Use one of the opener bodies, or better, one the user wrote ([`openers/README.md`](openers/README.md)).
5. **Before sending, check** what the tools cannot: every folder the task names exists, and the task text is private-data clean.
6. **Send** on the chosen route. **Log every Pro message** in the ledger, follow-ups included.
7. **Watch** ([`tools/manuals/watch.md`](tools/manuals/watch.md)). Start the delivery watcher with its `test.txt` start check and the stall watchdog as soon as the message is sent, and the local-run listener if requests are allowed. When one wakes you, handle it and start it again. Look at the chat about 5 minutes after sending (approval card), then every 30 minutes or so.
8. **Steer and add work** ([`tools/manuals/interject.md`](tools/manuals/interject.md)). Writing to `REQUEST.md` costs no message. When stage ZIPs show steady progress and the list is running low, add more work. Do not add more after `DONE.txt` or a final delivery.
9. **Answer local-run requests** ([`tools/manuals/local-run.md`](tools/manuals/local-run.md)) when they need this machine (a window, GPU, real device, local platform). Do not run things the web side can run in its own sandbox or with its own subagents.
10. **Collect and check** (section 5). Before another part in the same folder, either delete `DONE.txt` or name a new marker (`DONE-r2.txt`) in `TASK-2.md` and pass it to the watchers (`--done`); continuations have no `test.txt` step, so start the delivery watcher with `--start 0`.
11. **Next part:** same chat → `TASK-<N>.md` + `continue.md` + `footer-drive-continue.md`. Dead chat → new tag, `restart.md` + `footer-drive.md`, and a task file that points at the old folder's latest stage ZIP.

## 4. Why long runs work, and how to keep them going

- **One message, hours of work.** The opener frames a long research session. The task file asks for a complete list, no fixed stopping point, a safety delivery at 70 minutes of real working time, then staged ZIPs every 15–20 minutes for as long as the list lasts. If the session drops, the latest stage is already saved.
- **Why 70 minutes.** Heavy sessions used to drop at around 80 minutes with nothing delivered. A safety delivery just before that point means a drop costs little; the work after it is a bonus.
- **Only working time counts**, so time stuck on an approval card or a stalled tool does not eat into the schedule.
- **Steering is free.** The model re-reads `REQUEST.md` at checkpoints, so new requirements, corrections and extra work reach it without spending a message. Subagents do not see it; the coordinating model forwards it.
- **The web side can ask for help.** When something needs this machine, it writes `requestfromweb.txt` and keeps working while you answer in `reply.txt`.
- **Subagents multiply the work per message.** The task asks for as many as allowed, plus one reviewer that only reviews. In our runs at most three ran at once.

Observed in our runs, with no guarantee: the longest single session was about 6 hours, and 2–4 hours is typical. Occasionally a session still drops at around 70 minutes. A read-heavy job with subagents went through roughly 200,000 lines of code in one message. Other users of the same flow report a 20-hour session and 7 concurrent subagents; we have not reproduced either.

## 5. Checking the result

Treat the reply like any cold reader's report: real problems mixed with confident mistakes. Check each item against the code before using it, and write down accept or reject with one line of evidence. Three gates:

1. **Real:** can you write the actual trigger sequence?
2. **Valuable:** does fixing it make something better for users (or for future maintainers)?
3. **Likely:** would it happen within a month in the real scenario? If not, reject it as over-defensive.

Known tendencies: line references and quotes are usually right, and judgements about semantics, ordering and false premises are strong. Severity, though, tends to run about one and a half levels high, because the model cannot see the whole project and so counts "a bad state can be written down" as "it will happen". Its "not visible to me" list is work for you. Apply fixes yourself on the current code; its patches are references, except diffs it already ran inside a runnable kit, which you can use as a base after `git apply --check` and your own tests.

## 6. Files

| Path | What |
|---|---|
| [`openers/`](openers/) | Opener bodies, continuation and restart, footers per route, how to write your own |
| [`task/`](task/) | Preface, task skeleton, project header (English and Chinese) |
| [`send/`](send/) | By hand, Voyager CLI, browser relay with troubleshooting |
| [`tools/`](tools/) | Scripts, sandbox request channel, manuals, Drive approval auto-click, Pro ledger |
