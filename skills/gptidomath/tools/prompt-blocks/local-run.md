## Local measurements when needed

If a necessary measurement needs hardware, software, network access or runtime that your sandbox lacks, ask for a local run in `{{WORKSPACE}}/requestfromweb.txt`. Do lightweight checks yourself. Explain the decision this measurement will resolve, the exact commands and inputs, expected outputs, success criteria and whether it blocks further work. This file requests work; it does not authorize additional access or execute commands automatically.

Use UTF-8 and this append-only format, rewriting the complete file while retaining earlier entries. Increase the version for every new request and publish the finished file as one update; when the connector requires separate edits, update the version last.

```text
Version: 1

## Request 1 (UTC timestamp)

Measurement, reason, commands, required inputs, output names, acceptance criteria.
Blocking: yes or no.
```

The local coordinator responds in `{{WORKSPACE}}/reply.txt`, starting with `Version: N` and a section `## Reply N (Request K, timestamp)`. Attachments are in the same task root and begin `replyN-`; do not search only subfolders. Read `replyN-attachments.json` for part order, byte counts and SHA-256 hashes. Files above 192 MiB are split into raw byte segments: download all segments, concatenate in listed order, then verify every part and the whole-file hash before use. Do not unzip segments separately. A reply may sync before its attachments; retry missing files after sync.

Continue independent work after requesting a run. At coordination checkpoints, the coordinator checks reply.txt and passes relevant results to workers. Record the reply version used. If results are still missing at delivery, list the pending request numbers, commands and decision criteria in NOTES.md.
