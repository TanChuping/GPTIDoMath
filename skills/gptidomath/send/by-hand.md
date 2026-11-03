# Send by hand

You paste the message into ChatGPT yourself; your agent prepares everything and checks the result. Two ways to hand over the material.

## With Google Drive (recommended)

Needs ChatGPT connected to Google Drive and Google Drive for desktop (or another sync, see [`../tools/manuals/mirror.md`](../tools/manuals/mirror.md)). Then the message is all you paste, and the extras work: steering a running job, the web side asking your machine to run things, being woken on delivery.

1. Your agent publishes the repository mirror, creates the task folder, writes `TASK.md` and prints the message (`drive_workspace.py … --out message.md`; see [`../tools/manuals/workspace.md`](../tools/manuals/workspace.md)). It waits until Drive has synced.
2. You open chatgpt.com, start a **new chat** in the normal chat view, pick **Pro**, paste the message and send. Other modes may draw on a different quota; check before using them.
3. About 3 minutes later, look at the chat: on the first Drive write ChatGPT shows "Allow ChatGPT to use Google Drive?". Click **Always allow** (or let an auto-click tool do it, see [`browser-relay.md`](browser-relay.md#the-drive-approval-card)). Tell your agent you sent it, with the chat link.
4. Your agent watches the Drive folder, steers the job if needed, and checks the delivery when `DONE.txt` appears.

## With an uploaded package (no Drive)

The simplest setup, with nothing to install. Your agent builds one zip with the task inside; you upload it.

**You give up:** steering a running job, local-run requests and automatic wake-up (there is no shared folder). Every follow-up needs a new upload, and big binaries make uploads slow or exceed ChatGPT's file limits.

1. **Your agent writes `TASK.md`** from [`../task/en/task-skeleton.md`](../task/en/task-skeleton.md). It uses the package variant of "Material and setup", deletes the request-channel, local-run and `DONE.txt` lines, and puts [`../task/en/preface.md`](../task/en/preface.md) on top.
2. **Your agent builds the package:**
   ```sh
   python3 <skill>/tools/scripts/drive_mirror.py pack --repo . --task TASK.md --out ./send
   ```
   It exports the last commit (uncommitted changes are not included), redacts what it recognises, adds `INDEX/` and puts `TASK.md` at the archive root. Check the printed size and the privacy notes in [`../tools/manuals/mirror.md`](../tools/manuals/mirror.md) before uploading anything.
3. **Your agent writes the message:** one opener body from [`../openers/`](../openers/) plus `footer-package.md`, with `{{PACKAGE}}` replaced by the zip's name.
4. **You send it:** new chat, Pro, attach the zip, paste the message, send.
5. **Collect promptly:** download every ZIP link as soon as it appears; files in ChatGPT's sandbox stop being downloadable a few minutes after a turn ends. Unzip into a new empty folder and hand it to your agent.

Next part in the same chat: attach the new `TASK-2.md` (and a new package only if the code changed), then send `continue.md` + `footer-package-continue.md`. If the chat no longer loads, start a new one with `restart.md` + `footer-package.md` and a package that also contains the earlier deliverables.

## Either way

- Every message you send to Pro counts against your quota, follow-ups included. Tell your agent so it can log it (`pro_ledger.py add <tag> --note "sent by user"`).
- **ChatGPT Projects** are another way to hand over material: files added to a project are readable by every chat in it.
- **GitHub** material is untested by the authors; see [`browser-relay.md`](browser-relay.md#material-from-github-untested).
