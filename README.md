English | [简体中文](README.zh-CN.md)

# GPTIDoMath

**Make one ChatGPT Pro message work for hours.** You send ChatGPT Pro (on the web) a short opener that reads like a long mathematical research session; the real task waits in a file the model reads first. Small tools keep the job going: a safety delivery at 70 minutes and staged saves after it, steering without spending another message, the web side asking your computer to run things, and your agent being woken when the work lands.

> [!WARNING]
> **Experimental.** In a small group of users this made long ChatGPT Pro runs noticeably steadier and longer. It is not 100% reliable: disconnects still happen, and it may stop working at any time. Read the [disclaimer](#disclaimer) before using it.

## Start here (you do not need to read the rest)

1. You need a **coding agent** that can run commands (Claude Code, Codex, or similar) and a **ChatGPT Pro** subscription.
2. Install the skill folder `skills/gptidomath` where your agent loads skills:
   ```sh
   git clone https://github.com/TanChuping/GPTIDoMath
   # Claude Code
   cp -r GPTIDoMath/skills/gptidomath ~/.claude/skills/
   # Codex
   cp -r GPTIDoMath/skills/gptidomath ~/.codex/skills/
   ```
   With the [skills CLI](https://github.com/vercel-labs/skills): `npx skills add TanChuping/GPTIDoMath`. Any other agent: tell it to read `skills/gptidomath/SKILL.md`.
3. Tell your agent: **"Set up GPTIDoMath for me."** It asks you a few questions (who sends the message, whether to use Google Drive, which language), explains the pros and cons of each choice, installs and tests what you picked, and runs a small trial.
4. From then on: **"Send this to ChatGPT Pro with GPTIDoMath: …"** and describe the job.

## What is in it

| Part | What it does |
|---|---|
| **Math openers** ([`openers/`](skills/gptidomath/openers/)) | Four example openers (spectral theory, directed topology, statistical physics, logic and rewriting), plus a continuation and a restart, in English and Chinese, with footers for each route. They look like a big, hard, valuable research problem and contain no task at all. You are encouraged to write your own. |
| **Task skeleton** ([`task/`](skills/gptidomath/task/)) | The real prompt: what to do, full work list, subagents, the 70-minute schedule, delivery format. Starts with a short note telling the model that the opener was a framing and this file is the task. |
| **Repository mirror** | One command publishes your last commit to Google Drive (or into one upload-ready zip), with a file and symbol index and automatic redaction of recognisable private data. |
| **Request channel** | You add or change requirements while the job runs by writing a file. No new message, no extra quota. |
| **Local-run requests** | The web side asks your computer to run what its sandbox cannot (GPU, real device, your OS), and keeps working while it waits. |
| **Watchers** | Your agent is woken when `DONE.txt` or a new stage ZIP appears, or when nothing has been written for 35 minutes. |
| **Pro ledger** | Counts every Pro message, because ChatGPT does not show how many are left. |
| **Drive approval auto-click** | Clicks "Always allow" on ChatGPT's Google Drive permission card after a short random delay. |

Everything is a reference implementation with a manual, tested on one setup (Windows 11, Google Drive for desktop, Python 3.12). Your agent adapts it to your system; each manual explains the idea first so it can.

## Choose a route

Your agent asks you this during setup. Two choices: **who sends** and **how the material gets there**.

| Who sends | You need | Good | Not so good |
|---|---|---|---|
| **You, by hand** | Nothing extra | Simple; you see everything | You must be there to send and to approve the Drive card |
| **[Voyager CLI](https://github.com/voyager-crew/voyager-cli)** (a separate open-source tool) | Node.js, Voyager CLI, the Voyager browser extension, paired | Fully automatic from the terminal; several jobs at once | Third-party tool to install and keep updated |
| **Your agent, through the browser** | A browser-control extension for your agent (for example Claude in Chrome, or Codex's browser extension) | Most tested; the agent adapts when ChatGPT's page changes | Uses some of your agent's tokens; acts in your logged-in browser |

| Material | You need | Good | Not so good |
|---|---|---|---|
| **Google Drive** (recommended) | ChatGPT's Google Drive connector and Google Drive for desktop (or rclone) | Upload once, reuse in every chat; steering, local runs and wake-up all work | One-time setup; a permission card on each chat's first Drive write |
| **Uploaded zip** | Nothing | Easiest | No steering, local runs or wake-up; re-upload for each follow-up |
| **GitHub repository** | ChatGPT's GitHub app | Tasks under version control | **Not tested by the author.** You would need to build the delivery and steering scripts yourself |

**The Drive permission card.** In every new chat, the first time ChatGPT writes to Drive it stops on "Allow ChatGPT to use Google Drive?" until someone answers. Options:
- The [GPT Voyager](https://chromewebstore.google.com/detail/gpt-voyager/ofhnmgjaffpdldimjdenjoneocicolfi) extension ([source](https://github.com/TanChuping/chatgpt-voyager)) has an opt-in auto-allow setting.
- Voyager CLI has `--approve-apps always`.
- This repository has a small extension and console script.
- You can click it by hand.

None is guaranteed, so whoever sends should look at the chat about 5 minutes after sending.

## How a long run works

- **One message, hours of work.** ChatGPT Pro is billed per message, not per token. A five-minute question and a five-hour job cost the same, so put a whole batch of work into one task.
- **The 70-minute safety net.** Heavy sessions used to drop at about 80 minutes and deliver nothing. The task file asks for a complete, usable delivery at 70 minutes of real working time. After that there is no limit: the model keeps going down the list and saves a numbered stage ZIP every 15–20 minutes. If the session drops, the latest stage is already yours.
- **Fill the list.** Give it everything you want done before you next look, plus a backlog. Never write "only do X this round": it becomes the finish line, and the model stops early.
- **Keep adding work for free.** While it runs, your agent can add requirements or new work through the request channel. The model reads it at checkpoints and when stage ZIPs are saved. This costs no message.
- **Let it ask for help.** When something needs your machine, the model writes a request file and keeps working; your agent runs it and writes back.
- **Subagents.** The task asks for as many subagents as allowed, plus one that only reviews. In our runs at most three ran at the same time.
- **When a chat dies,** start a new chat with the restart opener. The new task file points at the latest stage ZIP, so little is lost.
- **Counting messages.** ChatGPT shows no remaining count. It only tells you when you hit the limit, along with the reset time. The ledger's numbers are estimates until you hit the limit once; after that, record the reset time it showed and the count lines up with reality.

## Good for, not for

**Good:** auditing a whole subsystem, surveys across many files, design decisions, specifications, test design, patch proposals with reasoning, data analysis on files you supply, headless experiments (tests, simulations, ablations) with a runnable kit, image restyling with reference images.

**Not good:** anything that needs a window, a GPU, a real device, live services or credentials; quick questions; back-and-forth conversations; things you can judge at a glance.

## What we have seen

- Longest single session on the author's machine: about **6 hours**. Typical: **2–4 hours**, stable. Occasionally a session still drops at around **70 minutes**.
- A read-heavy job with subagents read about **200,000 lines** of code in one message.
- Other people using the same flow report a **20-hour** session and **7 subagents** running at once. The author has not reproduced either.

## What you will still see

- "Connection interrupted, waiting for the full reply". Often the job is still running in the background; look for new files on Drive.
- "Unable to load conversation" and "Try again". Often temporary; wait and click "Try again".
- A red "Invalid conversation body" bar. Usually only a display error; reload the page, do not click "Retry".
- Sessions that stop early, especially after heavy use or very long runs.

The [browser guide](skills/gptidomath/send/browser-relay.md#when-things-go-wrong) has a full table of these and what to do.

## Repository layout

```
skills/gptidomath/
  SKILL.md      what your agent follows: setup interview, each job, checking results
  openers/      math openers, continuation, restart, footers; how to write your own
  task/         preface, task skeleton, project header (en, zh)
  send/         by hand, Voyager CLI, browser relay (with troubleshooting)
  tools/        scripts, sandbox request channel, prompt blocks, manuals,
                Drive approval auto-click, Pro ledger
```

## Disclaimer

By using anything in this repository you accept the following. If you do not, do not use it.

1. **Experimental, no warranty.** Everything here is provided "as is", without warranty of any kind, as stated in the [MIT License](LICENSE). It is an exploratory method, not a product.
2. **No promised effect.** Nothing here guarantees steadier or longer sessions, more compute, better answers, or any result at all. What we report comes from a small number of users and runs. It is anecdotal, not a controlled study, and the opener may not be the cause of what we saw. Results vary by account, region, time, load and model version.
3. **It can stop working at any time.** OpenAI can change the page, the models, limits, billing or detection at any moment, including after this method becomes widely used. If ChatGPT Pro on the web moves from a per-message count to usage-based billing (possibly as early as December 2026), this method loses its point.
4. **Your account, your responsibility.** You are responsible for complying with OpenAI's Terms of Use and usage policies, and with the terms of Google, GitHub and any other service involved. Automating a browser or a client may conflict with some services' terms. Nothing here is legal advice. The author and contributors are not liable for any consequence, including but not limited to account suspension or termination, temporary limits or soft bans, rate limiting, lost or unloadable conversations, lost work, or used-up messages and quota.
5. **Not a way around safety rules.** The opener frames long reasoning work; it is not meant to disguise anything. The task file is read by the same model under the same policies. Do not use this to request anything those policies prohibit.
6. **Your data.** Using this sends your code, documents and data to third parties (OpenAI, and Google if you use Drive). The redaction in the mirror tool is best effort: it can miss secrets and personal data, and it does not decide what you are allowed to share. You alone decide what to upload. You are responsible for your employer's policies, confidentiality agreements, licences of third-party code, privacy law and export rules.
7. **AI output can be wrong.** Answers, patches and analyses may be incorrect, incomplete or harmful to your project. Review everything and keep your work under version control before applying anything.
8. **The tools act on your machine and accounts.** The scripts read and write files, run git, and access your local Drive folder. The browser helpers act in your logged-in browser, and clicking "Always allow" gives ChatGPT continuing access to your Google Drive, which you can revoke in ChatGPT's and Google's settings. Your coding agent may run commands and click things on your behalf. Read what you run. You are responsible for what your agent does.
9. **Third-party tools are separate.** Voyager CLI, the Voyager extension and GPT Voyager are independent projects with their own licences, terms and maintainers. This repository makes no promise about them.
10. **No affiliation.** This project is not affiliated with, endorsed by or sponsored by OpenAI, Google, GitHub, Anthropic or any other company. ChatGPT, GPT, Google Drive and other names are trademarks of their owners.
11. **Numbers are reports, not specifications.** Durations, subagent counts, line counts and limits quoted here were observed or reported at the time of writing, partly by other people and unverified. They are not commitments.
12. **Languages.** If the English and Chinese versions of this disclaimer differ, the English version prevails.

## Credits and license

- Thanks to [Voyager CLI](https://github.com/voyager-crew/voyager-cli). Parts of the Drive tools are adapted from its MIT-licensed `contrib/web-pro-kit` (see [`tools/NOTICE.md`](skills/gptidomath/tools/NOTICE.md)).
- Thanks to [GPT Voyager](https://github.com/TanChuping/chatgpt-voyager), whose delayed Drive auto-allow logic the auto-click helper follows.
- [MIT License](LICENSE).
