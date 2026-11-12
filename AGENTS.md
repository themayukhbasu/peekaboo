# Agent notes

peekaboo is a learning project: a mini coding agent / inner harness with a transparent per-turn context view. It is built in public, and it is not for production.

Read [README.md](README.md) for the vision, [docs/early-cuts.md](docs/early-cuts.md) for the first milestones, [GLOSSARY.md](GLOSSARY.md) for terms, and [docs/adr/](docs/adr/) for decisions. [docs/reference/harness-landscape.md](docs/reference/harness-landscape.md) is an agent-authored research survey only — not the living plan; prefer ADRs and early-cuts when they disagree.

Stack for early milestones: **Python**, **raw HTTP** to **Ollama**, thin provider seam for paid APIs later. Product: **CLI** plus a **separate peek** (JSONL first, then a tiny web viewer). Do not add a package that hides the inner harness or the provider seam — provider SDKs, agent frameworks, and similar — unless an ADR says so ([ADR 0001](docs/adr/0001-python-raw-http-ollama-first.md)). A popular library for an ordinary Python concern, such as reading a dotenv file or logging, is fine; decide each addition on that distinction. Do not introduce a full TUI unless an ADR says so.

## Package conventions

These match the merged config loader ([#24](https://github.com/themayukhbasu/peekaboo/pull/24)).

- Spec defaults and environment-variable names are the frozen dataclass instances `default` and `env_name` in `peekaboo.config`. Add a setting as a field and read it as `default.model` or `env_name.model`. That shape is for these two namespaces. It is not a rule that every group of constants is a dataclass.
- `load_config` reads dotenv with `python-dotenv` (`dotenv_values`). The process environment wins, including a blank value, and a missing or blank value keeps the spec default. An injected `environ` with no `dotenv_path` reads that mapping alone. A missing file adds nothing. Leave file syntax in the python-dotenv docs linked from the module docstring. Who may read the environment stays in [CODING_STANDARDS.md](CODING_STANDARDS.md).
- Write a Python docstring as a short summary for the caller. Link upstream syntax instead of copying it.
- Python docstrings in this package use reStructuredText inline literals (double backticks), as in `src/peekaboo/__init__.py` and `src/peekaboo/config.py`. Docutils treats single backticks as interpreted text and double backticks as inline literals ([PEP 287](https://peps.python.org/pep-0287/), [inline literals](https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#inline-literals)). On #24 the owner asked why the doubles were there and, after that explanation, left them ([question](https://github.com/themayukhbasu/peekaboo/pull/24#discussion_r4500212220), [okay fine](https://github.com/themayukhbasu/peekaboo/pull/24#discussion_r4500381283)).

## Working rules

- Keep changes small and scoped to the ask.
- Keep documentation and diagram changes lean. Do not install packages, or render Mermaid or Markdown, to validate documentation. GitHub renders Mermaid. Verify only what the change actually needs. Once the edit is done, commit and push rather than running extra checks. Do not spend tokens on work nobody asked for.
- Never commit secrets, API keys or `.env` files.
- Write documentation in British English.

## Bot team

- Four bots work here. Peekaboo: PM leads and assigns tickets. Peekaboo: Builder opens code PRs via cloud agents. Peekaboo: Researcher takes research tickets only. Peekaboo: Reviewer reviews builder PRs. The owner, Mayukh, reviews and merges every PR. Bots never merge, approve, close PRs, or push to main.
- Tutoring sits outside this repo, with Mayukh's Learn: Tutor bot and the socratic stack in `themayukhbasu/skills/socratic`. Learn: Scout keeps the Notion "To Learn" list. Tutoring notes stay with Learn: Tutor. Leave `docs/learning/` unused.
- Work is tracked as GitHub Issues. Wayfinder maps and decision tickets use `wayfinder:*` labels. The builder claims `ready-for-agent`. The researcher claims `ready-for-researcher` (a `wayfinder:research` ticket carries that too; other research the owner hands out carries it alone). Bots never resolve HITL tickets (grilling, prototype, HITL task); those need the owner live.
- Runs can stop mid-way (for example at a usage limit) and nothing replays them, so GitHub is the only state. Before starting new work, each bot resumes its own unfinished work first: an existing branch or PR for the issue, unresolved review comments, or an existing `research/<slug>` branch. The PM re-sends stalled tickets (assigned, open, no PR or findings after a day, or a draft PR without a description) as "resume #N" before assigning anything new, and never double-assigns.
- When the Reviewer catches a real flaw in a builder PR, it opens a drill seed in this repo: a GitHub issue labelled `drill-seed`, with the snippet, the flaw, and its category from the socratic drill taxonomy. Drill seeds live in peekaboo.
- The Reviewer sends Learn: Scout the names of concepts in a PR that look new to Mayukh, plus the PR link, so Scout can add or update To Learn entries (the PR is the source, priority P1). Scout dedupes.
- When a bot finds a gap in a skill it runs (the socratic stack, or a grok-bot project skill), it opens a small pull request on `themayukhbasu/skills` that describes the gap and the fix, for Mayukh's review. Bots never merge.

## Pull requests

- Target about 250 significant lines per PR. Up to about 300 is allowed only when splitting would cut through a seam; the PR states the reason. Count everything except generated and lock files. Tests, fixtures, and docs count.
- Bigger work ships as a stack. Each slice stays within the size rule, is cut along a real seam, and builds and tests on its own. Only the top PR closes the issue. A stack of up to 4 slices needs no permission. More than 4 needs Mayukh's OK first (the PM asks him, or re-slices the ticket). Open every slice of a stack together.
- Scheduled work starts at most one ticket a day. A whole stack counts as one ticket. An on-demand ask from Mayukh skips the daily limit.
- At most 3 tickets in review at once. Group open bot PRs by ticket; a stack counts as one. Docs PRs count. A new ticket also waits while total open bot-PR lines, counted the same way, are about 1000 or more. Slices of a ticket already started still finish. At either cap, ask Mayukh to merge or close before a new ticket, including when he asks for more on demand.
- Every PR description is written with the `/pr` skill and backs each claim with evidence (real command output, sample data, test results). No "should work".
- Before opening a PR, run the project's `verify-*` skill if one exists, otherwise the tests and linters that exist.
- Review comments are fixed on the same branch, with a reply under each comment saying what changed.
- Research findings go on throwaway `research/<slug>` branches with no PR.
- PR descriptions are concise. Use diagrams (Mermaid in Markdown) wherever they make the change easier to follow, e.g. data flow, sequence or state.
- When a PR implements a tricky concept (often one the researcher looked into), cite the sources: link the primary sources and any research branch or ticket it builds on.

Review flow:

1. The Builder finishes a PR, or a whole stack, verifies it, and hands it to Peekaboo: Reviewer.
2. The Reviewer reviews each slice and the stack as a whole. It checks description quality, including Read this first; the size rule; every acceptance criterion in the issue or spec, one by one; `AGENTS.md` and `CODING_STANDARDS.md` through the `code-review` skill; naming; that the tests and evidence are real; and CI. It picks the riskiest function itself and checks that function is on the must-read list. It runs the pstack skills `interrogate` (an adversarial pass), `blast-radius`, `no-comments`, `unslop` (on the description), `principle-prove-it-works`, `principle-test-behavior-not-implementation`, and `principle-subtract-before-you-add`. It names at least one concrete risk, or writes "none found, checked X, Y, Z".
3. The Reviewer posts one GitHub review per round with event `COMMENT` and a verdict line: "Reviewer: pass" or "Reviewer: changes needed". Bots never approve, merge, or close. On "changes needed", the Builder fixes the same branch and hands it back. At most 2 rounds. After that the PM flags the PR to Mayukh as needs-Mayukh.
4. Mayukh hears about a PR only after "Reviewer: pass". The PM sends the review alert or the daily summary. Mayukh reviews and merges.
5. Approve gate: when a PR lists must-read functions, Mayukh runs the socratic approve gate on it with Learn: Tutor before merging (what the change does, how it could fail, how he would verify it). The PM alert says so.

## Build and test

uv is the only package manager. From a checkout:

- `uv sync` installs the package, the `peekaboo` console script, and the Ruff dev dependency.
- `uv run python -m unittest discover -s tests` runs the tests.
- `uv run ruff check` lints Python.
- `uv run ruff format --check` checks Python formatting. `uv run ruff format` applies it.
- `uv run peekaboo --help` runs the placeholder command.

Ruff is the lint and format gate for those two commands. It is a dev dependency, not a provider SDK or an agent framework.

Before opening a PR, run the sync, test, lint, and format commands above. When a `verify-*` skill exists, run that too.

Builders changing the package use these skills:

- `codebase-design` for deep modules and where a seam goes.
- `tdd` for tests at the public interface.

Peekaboo: Reviewer uses `code-review` for standards in `AGENTS.md` and `CODING_STANDARDS.md`, and for the originating issue. The review flow names the other skills it runs.
