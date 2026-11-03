# Google Drive approval auto-click

This helper clicks **Always allow** (or **始终允许**) on recognized Google
Drive approval cards on chatgpt.com. Installing or running it opts into that
persistent approval choice. It does not send chat messages or handle other
providers.

It requires the exact container class token `@container/approval-card`,
a first provider-title span equal to Google Drive, a recognizable named-tool
description, and exactly one matching button that is the form's first button.
It ignores code blocks, editable areas, and hidden cards.

## Install

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Choose **Load unpacked** and select this directory.
4. Reload the ChatGPT tab. To disable it, turn the extension off and reload.

No extra extension permissions, background process, or network requests are
used. The content script runs only in the top frame on chatgpt.com.

## Timing and verification

The first click waits a random 1–3 seconds. Each retry waits at least a
4-second cooldown plus another 1–3 seconds of jitter, with at most three clicks
per request. Every click rechecks the card, provider, tool, button, enabled state,
and page path. A replacement request or button gets a fresh full delay. A manual
click on a form action stops automatic handling for that request; Details does
not. All automatic actions use plain `.click()`.

There is one initial scan, then mutation-based checks of affected cards and
new subtrees. There is no polling timer when no card is pending. Background-tab
suspension can delay execution. An exhausted retry log means three attempts
were made; it is not proof of server rejection or success.

To verify, use a real Drive approval card: it should remain for at least one
second before an attempt, then normally disappear. Inspect the last 50 records
in the page's local storage under `gptidomath.drive-approval.log`, for example:

```js
JSON.parse(localStorage.getItem("gptidomath.drive-approval.log") || "[]")
```

Each record contains only time, tool name, page path, and attempt result.
Conversation text and tool arguments are never stored. Clear the local-storage
key to delete the log.

## Browser-agent fallback

Run the entire contents of `console-snippet.js` in the ChatGPT page through
your browser agent's JavaScript tool. It returns a short object such as
`{status: "watching", pending: 0}`; future cards are handled until stopped
or the page reloads. Running it again is idempotent. The page API exposes:

```js
window.__gptidomathDriveApproval.status()
window.__gptidomathDriveApproval.getLog()
window.__gptidomathDriveApproval.stop()
```

The extension uses an isolated JavaScript world, so its API is not normally
visible in the page console; its local-storage log is shared. Use one automatic
approval helper at a time.

## Built-in alternatives and follow-up

[GPT Voyager](https://chromewebstore.google.com/detail/gpt-voyager/ofhnmgjaffpdldimjdenjoneocicolfi)
has an opt-in **Auto allow Google Drive** setting
([source](https://github.com/TanChuping/chatgpt-voyager)).
[Voyager CLI](https://github.com/voyager-crew/voyager-cli) offers
`voyager ask --approve-apps always` with the Voyager extension 2.2.0 or later.

None of these paths is guaranteed. The sender still looks at the chat about
five minutes after sending and whenever the delivery watcher reports no
`test.txt`. If ChatGPT changes the approval card, save only its structural
shape as shown in [SAMPLE.md](SAMPLE.md), then update and verify the selectors.
