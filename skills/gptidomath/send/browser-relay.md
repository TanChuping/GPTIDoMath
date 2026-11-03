# Your agent sends through the browser

An agent that can drive a browser (for example Claude in Chrome, Codex with its browser extension, or any computer-use agent) opens ChatGPT in its own tab, pastes the message, sends, watches the job and collects the result. This is the route with the most field experience behind it.

**Good for:** running jobs while you do something else. The agent adapts when the page changes, finds the model picker, and recovers from most errors listed below.
**Costs and risks:** the agent spends some of its own tokens on watching; it works in your logged-in browser profile; you must allow it to act on chatgpt.com. Send only when you have said so, and ask before running unattended (overnight).

## Sending

1. Open a **new tab** of your own, and a **new chat** for every task. Never type into a tab the person is using.
2. Use the normal chat view with the **Pro** model. Do not switch to other modes (agent or work modes may draw on a different quota).
3. **Paste, do not type.** Typing a newline sends a half message. Put the message on the clipboard and paste it into the composer, or dispatch a paste event with the text. Then read the composer back and compare its length and its first and last lines with the file. If the person may be using the clipboard, check the clipboard's length right before pasting.
4. Attach files through the page's general file input if this route uses a package. Browser tools often cap one upload call (around 10 MB for some); split larger material or use Drive.
5. Click send, confirm that a reply started, and **log the message** in the ledger with the chat link (`pro_ledger.py add <tag> --conv <link>`). Every follow-up is logged too.
6. Start the watchers right away: the delivery watcher with its `test.txt` start check, the stall watchdog, and the local-run listener if the task allows requests (see [`../tools/manuals/watch.md`](../tools/manuals/watch.md) and [`../tools/manuals/local-run.md`](../tools/manuals/local-run.md)).

## The Drive approval card

On a chat's first write to Drive, and sometimes again later for another Drive tool, ChatGPT stops on a card: "Allow ChatGPT to use Google Drive?" with **Always allow**, **Deny** and **Allow once**. Nothing happens until someone answers it. The footer makes the model write `test.txt` first, so the card shows up in the first minutes.

Ways to answer it, from least to most effort:
- **GPT Voyager** extension ([Chrome Web Store](https://chromewebstore.google.com/detail/gpt-voyager/ofhnmgjaffpdldimjdenjoneocicolfi), [source](https://github.com/TanChuping/chatgpt-voyager)): turn on its opt-in setting for auto-allowing Google Drive.
- **Voyager CLI**: `voyager ask --approve-apps always` (see [`voyager-cli.md`](voyager-cli.md)).
- **This repository's auto-click**: [`../tools/drive-auth-autoclick/`](../tools/drive-auth-autoclick/), as an unpacked extension or as a console snippet your agent runs in the tab. It waits a few seconds before clicking and gives up after three tries.
- **By hand**: click **Always allow**.

None of these is guaranteed to keep working when ChatGPT changes its page. So after every send, **look at the chat about 5 minutes later**, and again whenever the delivery watcher reports that `test.txt` has not appeared. A spinning page does not mean the model is working: a new file on Drive does. A Google sign-in or permission window may also open somewhere else (a red "Unknown error" box is one sign); look for it in another tab or window. A person types any password, never the agent.

## Watching

- Wake-ups come from the watchers, not from staring at the page: a new stage ZIP, `DONE.txt`, a local-run request, or **STALL** (no new file for 35 minutes).
- On a new stage ZIP, read its progress notes. If the job is going well and the list is running low, add work through the request channel (no new message, no extra quota). The task file already says to keep going after 70 minutes; jobs sent with an older task file that stops at a fixed time can be released the same way.
- Check the page by hand every 30 minutes or so as a backstop; the watchers only know about files.

## When things go wrong

| You see | What it usually means | Do |
|---|---|---|
| Red bar "Invalid conversation body" with a Retry button | A display error; the job often keeps running. | Do not click Retry (it regenerates the turn). Reload the same URL, wait a minute or two, reload again. Watch Drive for new files. |
| "Connection interrupted, waiting for the full reply" | The page lost the stream; the backend may still be working. | Judge by Drive: if files keep arriving, wait. Treat it as dead only when nothing new has appeared for well past the expected time, then about ten more minutes. |
| "Unable to load conversation" after a reload | Often temporary. | Wait a few minutes and click "Try again"; repeat once or twice. |
| The chat is dead (no new files for a long time, it will not load, or Stop and send do nothing) | The session is gone. | Start a **new chat** with a new task folder (`<tag>-b`). Its task file says: the old folder is read-only, resume from its latest stage ZIP, write new deliveries here. Send `restart.md` + `footer-drive.md`. Move the watchers to the new tag. A message that never actually went out did not cost a request; do not log it. |
| Red box `cloudflare_challenge` under a message, with Retry | This generation was blocked; it is not a captcha. | Wait a minute or two, then click the **Retry inside that red box**. Other "Retry" buttons on the page (for example in the sidebar) do something else. |
| A Cloudflare "verify you are human" page | A real human check. | Stop. Never solve captchas. Ask the person; if it persists, move the remaining work to another route. |
| "Unable to load your account" | Temporary. | Reload a few times. Never click "Log out". |
| You reloaded several times in a row | Repeated full reloads can trigger checks that break **other** running chats. | With one job already running, open the second job from the sidebar's "New chat" in the same tab instead of reloading. |
| A background tab does not respond | Browsers freeze background tabs. | Navigate the tab to the same URL once more. |
| Two uploads with the same name | ChatGPT appends "(1)". | Say in the message that a "(1)" suffix means the same file. |
| A ZIP from ChatGPT has garbled non-ASCII folder names | Names are UTF-8 without the UTF-8 flag. | Decode entries without flag 0x800 as `name.encode('cp437').decode('utf-8')`. |

## Material from GitHub (untested)

ChatGPT's GitHub app can read repositories you connect. In principle the task file can live in a repository (for example a `tasks/<tag>/TASK.md` on a branch) and `footer-github.md` points the model there. The authors have not run this path. Open questions you would need to solve with your own scripts: how the model writes deliveries back (a branch it commits to, or a ZIP link), how to steer a running job without Drive, and how to wake your agent on delivery.
