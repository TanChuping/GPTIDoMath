English | [简体中文](README.zh-CN.md)

# Openers

The message you send to ChatGPT Pro has two parts. The **opener** reads like a working researcher in the middle of a hard mathematical problem and contains no task details. The **footer** carries the opening steps: on Drive, first write `test.txt`; read the task file in full; then start. The real task waits in that file (`TASK.md`), which begins with [`../task/en/preface.md`](../task/en/preface.md) telling the model that the opener was a framing and the file is what counts.

Your agent writes a new opener for every new conversation, following the routine below. The files here are examples of the range, not text to send.

## Files

| File | Use |
|---|---|
| `01-letter-fluid-dynamics.md` | Example: a letter to a collaborator (Navier–Stokes regularity). |
| `02-abstract-quantum-many-body.md` | Example: a short seminar-style abstract with numbered questions (spectral gaps). |
| `03-notebook-extremal-combinatorics.md` | Example: a notebook page that starts from a failed counterexample. |
| `04-survey-hamiltonian-dynamics.md` | Example: a formal survey note that opens with history (KAM, hyperbolicity). |
| `05-objections-complexity.md` | Example: three objections to one's own approach (complexity barriers). |
| `continue.md` | Example for the next part in the **same** conversation (`{{ROUND}}` = part number). |
| `restart.md` | Example for a **new** conversation that resumes an old one (the old chat hit its length limit or no longer loads). |
| `footer-drive.md` | Footer: new conversation, task file on Google Drive. |
| `footer-drive-continue.md` | Footer: same conversation, next task file on Drive. |
| `footer-package.md` | Footer: task file inside an attached zip (no Drive). |
| `footer-package-continue.md` | Footer: same conversation, next task file attached. |
| `footer-github.md` | Footer: task file in a GitHub repository (untested by the authors). |

Assemble a message with the workspace tool, which strips the comments and fills `{{WORKSPACE}}`, `{{TASK_FILE}}` and `{{ROUND}}` (see [`../tools/manuals/workspace.md`](../tools/manuals/workspace.md)). It refuses a message with any other `{{…}}` left, or one that does not name the task folder and task file.

## Write a new opener for every conversation

This is a step of every job, not an extra. When many people send the same text, or the same text with a few nouns swapped, their messages share a fingerprint that is easy to spot in bulk, and the method can stop working for everyone. So no two openers should look alike: not in wording, not in structure. The five examples differ in form, voice, way in, field and length to show how far that goes. Never send one as is, and never reuse their sentences.

**An opener has to do three things, and only these:**

1. **Say where the real task is.** The full statement is in the shared material (or the attached package) and it governs. The footer then gives the exact path.
2. **Rest on real, current mathematics or physics.** Open problems, recent breakthroughs, active research programmes, a few concepts that genuinely belong together, every name and result correct. If you are unsure of a detail, use a broader term you are sure of; invented theorems read as noise.
3. **Sound like a serious researcher at work.** Precise, rigorous, academic. A reader should believe a professor is in the middle of this research.

**It must not contain:** task details (file names, product names, programming languages, frameworks); invented credentials, or a claim to be a particular person; security-flavoured verbs such as bypass, exploit, inject, crack, attack or payload. Keyword filters have stopped harmless jobs because of them.

**Everything else is free, and should change from one opener to the next:**

- **Form:** a letter to a collaborator, a seminar abstract, a notebook page, a survey note, objections to one's own approach, a list of open questions, a grant-style problem statement, a single dense paragraph, or something else.
- **Voice:** I, we, or impersonal; confident, puzzled or sceptical; formal or conversational.
- **Way in:** a failed proof, a counterexample, an anomaly in the data, a historical thread, a definition, a question.
- **Field:** chosen by likeness to the job (next section), and not the same field twice in a row when another one fits.
- **Length and layout:** 150 to 600 words; with or without a title; paragraphs, bullets or numbered questions; the pointer to the material at the start, in the middle or at the end.

### Choosing the field

Pick mathematics or physics whose objects have the same **shape** as the real job, so the model sees the likeness once it reads the task file: what accumulates, what must stay invariant, where things break, what is being optimised. The likeness stays in the structure. Name mathematical objects, never the real tool, product or file format: "polyhedral surfaces", not "Blender meshes". A loose fit is fine. The task file's preface tells the model not to spend time reconciling the two.

Then make it **current**: build on open problems and results from roughly the last fifteen years, with the classical results they rest on as background. Check every name, date and claim. If you are not sure of one, leave it out.

Starting points, all real:

| The job is mostly about | Field with the same shape | Why it fits | Frontier to draw on |
|---|---|---|---|
| 3D modelling, meshes, surfaces | Discrete differential geometry | a mesh is a discrete surface; curvature, smoothness and distortion are its quantities | discrete uniformisation of polyhedral surfaces (Gu–Luo–Sun–Wu, 2018); the Willmore conjecture (Marques–Neves, 2014); circle packings approximating conformal maps (Rodin–Sullivan) |
| Fluid, smoke, cloth or other physics simulation | Navier–Stokes and turbulence | energy moving between scales, numerical blow-up | 3D Navier–Stokes regularity (open); Onsager's conjecture (settled, Isett 2018); Tao's averaged blow-up (2016); computer-assisted blow-up for Boussinesq and 3D Euler with boundary (Chen–Hou, 2022) |
| Rendering, lighting, sampling noise | Integral geometry, discrepancy, harmonic analysis | light is an integral over rays; noise is discrepancy | the Kakeya conjecture in three dimensions (Wang–Zahl, 2025); Fourier restriction (open); ℓ² decoupling (Bourgain–Demeter, 2015) |
| Animation, rigging, robots, cameras | Rigidity theory, geometric mechanics | poses live on rotation groups; joints are constraints | generic global rigidity (Gortler–Healy–Thurston, 2010); the bellows conjecture for flexible polyhedra (Connelly–Sabitov–Walz) |
| Concurrency, multiplayer sync, distributed state | Directed algebraic topology, sheaves | deadlocks are holes in the space of schedules; local agreement that will not glue is a cohomology class | directed homotopy (Fajstrup–Goubault–Raussen); the topological proofs of wait-free impossibility (Herlihy–Shavit, Saks–Zaharoglou; Gödel Prize 2004) |
| Game logic, big state machines, rule systems | Markov chains on huge finite state spaces, metastability | rare long-lived states and bottlenecks that show only at full size | the cutoff phenomenon (Lubetzky–Sly; Salez for non-negatively curved chains); metastability and Eyring–Kramers formulas (Bovier–den Hollander) |
| Performance, scheduling, parameter tuning | Optimal transport, sharp thresholds | moving mass at least cost; performance that collapses past a point | Wasserstein gradient flows (Jordan–Kinderlehrer–Otto); the Kahn–Kalai conjecture (Park–Pham, 2022) |
| Data analysis, statistics, model evaluation | Random matrix theory, high-dimensional probability | separating signal from noise in large matrices | the BBP transition (Baik–Ben Arous–Péché); eigenvalue universality (Erdős–Schlein–Yau, Tao–Vu) |
| Networks, routing, load balancing | Expander graphs, percolation | robustness and bottlenecks of large networks | bipartite Ramanujan graphs of every degree (Marcus–Spielman–Srivastava, 2015); critical percolation in three dimensions (open) |
| Compilers, type checkers, refactoring, rule engines | Rewriting, type theory | confluence, termination, equality up to coherence | univalence made computational in cubical type theory (Cohen–Coquand–Huber–Mörtberg) |
| Image generation, style consistency | Optimal transport, score-based diffusion | carrying one distribution of images onto another | convergence guarantees for score-based sampling (Chen–Chewi–Li–Li–Salim–Zhang, 2023); Schrödinger bridges |
| Edge cases, test generation, large search spaces | Extremal and additive combinatorics | counterexamples that appear only at scale | the cap set bound (Ellenberg–Gijswijt, 2016); sunflower bounds (Alweiss–Lovett–Wu–Zhang, 2019); Erdős–Hajnal (open) |

When a job spans several rows, take the one at its heart. When nothing fits closely, take the nearest shape (a large finite system, its invariants, its bottlenecks) and let the preface absorb the gap.

**Routine, for each new conversation:**

1. Look at the shape of the task. Pick a field by likeness (table above) and three to six real, current concepts or open problems from it.
2. Pick a form, a voice and a way in that differ from the previous opener. The Pro ledger keeps the record: log the send with `pro_ledger.py add <tag> --note "opener: letter, fluid PDE"`, and look at earlier notes with `pro_ledger.py list`.
3. Write the opener from scratch in the language you will send.
4. Check it: the field has the shape of the job; the three requirements hold; nothing from the exclusion list appears; no sentence comes from an example or from an earlier opener; every name and result is real.
5. Reword the footer as well, keeping its steps and their order.
6. Save the opener next to the task source, outside the synced workspace, and pass it with the footer to `drive_workspace.py --opener … --footer …`.

Continuations and restarts follow the same rules. `continue.md` and `restart.md` show what those two must also say: which part this is, or that an earlier volume exists and where its manuscripts are.

Write in whichever language you like; the task file says which language to answer in.
