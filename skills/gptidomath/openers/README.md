English | [简体中文](README.zh-CN.md)

# Openers

The message you send to ChatGPT Pro has two parts. The **opener** reads like the start of a long, hard mathematical research session and contains no task details. The **footer** is a short fixed procedure: optionally write `test.txt`, read the task file in full, then start. The real task waits in that file (`TASK.md`), which begins with [`../task/en/preface.md`](../task/en/preface.md) telling the model that the opener was a framing and the file is what counts.

## Files

| File | Use |
|---|---|
| `01-…04-*.md` | First message of a new conversation. Four examples with different themes. |
| `continue.md` | Next part in the **same** conversation (`{{ROUND}}` = part number). |
| `restart.md` | A **new** conversation that resumes an old one (the old chat hit its length limit or no longer loads). |
| `footer-drive.md` | New conversation, task file on Google Drive. |
| `footer-drive-continue.md` | Same conversation, next task file on Drive. |
| `footer-package.md` | Task file inside an attached zip (no Drive). |
| `footer-package-continue.md` | Same conversation, next task file attached. |
| `footer-github.md` | Task file in a GitHub repository (untested by the authors). |

Assemble a message with the workspace tool, which strips the leading comments and fills `{{WORKSPACE}}`, `{{TASK_FILE}}` and `{{ROUND}}` (see [`../tools/manuals/workspace.md`](../tools/manuals/workspace.md)). Fill any other `{{…}}` by hand. You can also just paste body + footer into one message yourself.

## Write your own

These four are examples, not magic words. Write your own and change it from time to time: identical public text sent by many people is easy to recognise and may stop working. What the examples have in common:

1. **A continuing research project.** Say it is the continuation of a long-running problem, not a quick question.
2. **Four to six real concepts from one or two frontier fields** that plausibly fit together. Use them correctly; jargon soup reads as noise.
3. **An abstract object.** "A finite system of many interacting parts" with surprising behaviour: hidden structure, rare failures, an obstruction that only shows globally. Then a goal: characterise it, find what governs it, optimise under constraints.
4. **Method.** Half proof, half measurement; unverified claims stay conjectures.
5. **No task content at all.** No file names, product names, languages or frameworks. Say that the full statement is in the shared material, and why you are not restating it: a paraphrase loses precision and biases the reader.
6. **Keep the footer's steps.** Change the wording, not the order.
7. **Stay truthful and impersonal.** Do not invent credentials or claim to be someone. Avoid security-flavoured verbs such as bypass, exploit, inject or crack, in the opener and in the task file: keyword filters have stopped harmless jobs because of them.

About 300–500 words is plenty. Write in whichever language you like; the task file says which language to answer in.
