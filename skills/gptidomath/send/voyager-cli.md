# Send from the terminal with Voyager CLI

[Voyager CLI](https://github.com/voyager-crew/voyager-cli) (`voyager`) is a separate open-source project: a command-line client that talks to ChatGPT on the web through the Voyager browser extension in your own browser. Your agent can open a chat, send the message with files, wait for the reply and save it, all from the shell. It is not part of this repository; read its README for the current details.

**Good for:** agents that should send and collect without clicking in a browser; several jobs at once.
**Costs and risks:** Node.js plus the Voyager extension, paired with the CLI; it depends on the extension keeping up with ChatGPT's page; Drive approval cards still appear (see below).

## Set up (once)

1. `npm install -g @voyager-crew/cli` (Node.js 20.3 or later).
2. Install the Voyager extension (links in Voyager CLI's README; 2.2.0 or later for `--approve-apps`), then `voyager pair` and enter the code in the extension's Local Bridge settings.
3. Optional for agents: `npx skills add voyager-crew/voyager-cli` teaches your agent the CLI.
4. `voyager status` should report a paired extension. Any `voyager` command starts its local server; `voyager serve --stop` stops it.

## Send

Build the task and the message as on the other routes (Drive: `drive_workspace.py … --out message.md`; package: `drive_mirror.py pack …`). Then:

```sh
# Drive route: only the message goes out
voyager ask --json --no-wait --approve-apps always "$(cat message.md)"
# Package route: attach the zip
voyager ask --json --no-wait --attach send/<name>-package.zip "$(cat message.md)"
voyager job wait <job-id> --timeout 10m --json   # exit 4 = still running: wait again, never resend
```

- `--preset <file>` prepends a text file to the prompt, so `voyager ask --preset opener.md "$(cat footer.md)"` also works. Its built-in `--preset math` is a short generic framing, not one of these openers.
- **Do not add `--timebox`.** It tells ChatGPT to wrap up at 70 minutes, which contradicts the task file's "safety delivery at 70 minutes, then keep going".
- `--approve-apps always` lets the extension answer the Drive approval card. The card can come back for another Drive tool later in the same chat, and the option depends on the extension's support, so keep the 5-minute check: the delivery watcher's `--start` check tells you when `test.txt` did not appear.
- `--attach` has a size limit (64 MiB at the time of writing); larger material belongs on the Drive route.
- `--repo owner/name` asks ChatGPT's GitHub app to read a repository: one way to try the GitHub material route.
- Follow-ups go to the same conversation with `--chat <link>`; every message is one Pro request, so log it.

The request channel, local-run requests and the watchers work the same as with any other sender; they only need Drive. Watching and troubleshooting: [`browser-relay.md`](browser-relay.md#watching).
