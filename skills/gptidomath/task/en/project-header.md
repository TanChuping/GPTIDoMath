<!-- Project header: the part of every task file that is the same for one project. Fill it once per project, then paste the
part between the BEGIN / END lines into each TASK.md at {{PROJECT_HEADER}}. Text outside the markers is for you. -->

<!-- BEGIN project-header -->
## About this project (the same for every task)

**Project:** {{one or two sentences: what it is, language / framework, where the requirements or rules are written}}

**Source:** {{where the mirror or package lives; which subfolder is the project root; what paths are relative to}}

**Read first** (indexes; take the one or two this task needs):
- {{architecture or system index}}
- {{current status / documentation map}}
- {{which guides apply to which kind of work}}

**Tools in the sandbox** ({{WORKSPACE_ROOT}}/tools/, each folder has a README with checksum and unpack steps):
- {{tool folder: what it is, what this project uses it for}}
- {{headless commands to build / run tests / run analysis scripts, and noise that can be ignored}}
- {{missing dependencies: try installing; if that fails, list them in the delivery}}

**Project-wide red lines** (a task's own instructions take precedence):
- {{one per line: what not to do / what must hold, with the file that defines it}}

**Your workspace:** this task's own folder, created in advance. Never create folders on Drive; write only into existing ones. `repos/`, `tools/` and other tasks' folders are read-only. Put reusable results (indexes, measured baselines) in `evidence/` and say in `NOTES.md` what they are and which commit they are based on.
<!-- END project-header -->
