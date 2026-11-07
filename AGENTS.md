# Agent notes

peekaboo is a learning project: a mini coding agent / inner harness with a transparent per-turn context view. It is built in public, and it is not for production.

Read [README.md](README.md) for the vision, [docs/early-cuts.md](docs/early-cuts.md) for the first milestones, [GLOSSARY.md](GLOSSARY.md) for terms, and [docs/adr/](docs/adr/) for decisions. [docs/reference/harness-landscape.md](docs/reference/harness-landscape.md) is an agent-authored research survey only — not the living plan; prefer ADRs and early-cuts when they disagree.

Stack for early milestones: **Python**, **raw HTTP** to **Ollama**, thin provider seam for paid APIs later. Product: **CLI** plus a **separate peek** (JSONL first, then a tiny web viewer). Do not introduce provider SDKs, agent frameworks, or a full TUI unless an ADR says so. A small utility library is allowed when no ADR rules it out; add it with uv and say why in the PR. `python-dotenv` is allowed on that basis: [ADR 0001](docs/adr/0001-python-raw-http-ollama-first.md) bans provider SDKs and agent frameworks, not every third-party package.

## Package conventions

These match the merged config loader ([#24](https://github.com/themayukhbasu/peekaboo/pull/24)).

- Spec defaults and environment-variable names are the frozen dataclass instances `default` and `env_name` in `peekaboo.config`. Add a setting as a field and read it as `default.model` or `env_name.model`. That shape is for these two namespaces. It is not a rule that every group of constants is a dataclass.
- `load_config` reads dotenv with `python-dotenv` (`dotenv_values`). The process environment wins, including a blank value, and a missing or blank value keeps the spec default. An injected `environ` with no `dotenv_path` reads that mapping alone. A missing file adds nothing. Leave file syntax in the python-dotenv docs linked from the module docstring. Who may read the environment stays in [CODING_STANDARDS.md](CODING_STANDARDS.md).
- Write a Python docstring as a short summary for the caller. Link upstream syntax instead of copying it.
- Python docstrings in this package use reStructuredText inline literals (double backticks), as in `src/peekaboo/__init__.py` and `src/peekaboo/config.py`. Docutils treats single backticks as interpreted text and double backticks as inline literals ([PEP 287](https://peps.python.org/pep-0287/), [inline literals](https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#inline-literals)). Markdown files in this repo stay Markdown. On #24 the owner asked why the doubles were there and, after that explanation, left them ([question](https://github.com/themayukhbasu/peekaboo/pull/24#discussion_r4500212220), [okay fine](https://github.com/themayukhbasu/peekaboo/pull/24#discussion_r4500381283)).

## Working rules

- Keep changes small and scoped to the ask.
- Keep documentation and diagram changes lean. Do not install packages, or render Mermaid or Markdown, to validate documentation. GitHub renders Mermaid. Verify only what the change actually needs. Once the edit is done, commit and push rather than running extra checks. Do not spend tokens on work nobody asked for.
- Never commit secrets, API keys or `.env` files.
- Write documentation in British English.

## Bot team

- Three bots work here: a PM (lead; assigns tickets), a builder (code PRs via cloud agents) and a researcher (research tickets and tutoring). The owner, Mayukh, reviews and merges every PR. Bots never merge, approve, close PRs or push to main.
- Work is tracked as GitHub Issues. Wayfinder maps and decision tickets use `wayfinder:*` labels. The builder claims `ready-for-agent`. The researcher claims `ready-for-researcher` (a `wayfinder:research` ticket carries that too; other research the owner hands out carries it alone). Bots never resolve HITL tickets (grilling, prototype, HITL task); those need the owner live.
- Runs can stop mid-way (for example at a usage limit) and nothing replays them, so GitHub is the only state. Before starting new work, each bot resumes its own unfinished work first: an existing branch or PR for the issue, unresolved review comments, or an existing `research/<slug>` branch. The PM re-sends stalled tickets (assigned, open, no PR or findings after a day, or a draft PR without a description) as "resume #N" before assigning anything new, and never double-assigns.

## Pull requests

- About 250 significant lines of diff per PR.
- Hard cap: at most 3 open bot PRs at any time, code and docs together. At the cap, open nothing new; ask the owner to merge or close first. This applies even when the owner asks for more.
- Scheduled work opens at most one new PR per day. When the owner asks directly (on demand), the one-per-day limit does not apply, but the 3-open cap still does.
- Every PR description is written with the `/pr` skill and backs each claim with evidence (real command output, sample data, test results). No "should work".
- Before opening a PR, run the project's `verify-*` skill if one exists, otherwise the tests and linters that exist.
- Review comments are fixed on the same branch, with a reply under each comment saying what changed.
- Research findings go on throwaway `research/<slug>` branches with no PR. Tutoring notes go in `docs/learning/` by PR and count toward the limits above.
- PR descriptions are concise. Use diagrams (Mermaid in Markdown) wherever they make the change easier to follow, e.g. data flow, sequence or state.
- When a PR implements a tricky concept (often one the researcher looked into), cite the sources: link the primary sources and any research branch or ticket it builds on.

## Build and test

uv is the only package manager. From a checkout:

- `uv sync` installs the package and the `peekaboo` console script.
- `uv run python -m unittest discover -s tests` runs the tests.
- `uv run peekaboo --help` runs the placeholder command.

Before opening a PR, run the sync and the test command above. When a `verify-*` skill exists, run that too.

Builders changing the package use these skills:

- `codebase-design` for deep modules and where a seam goes.
- `tdd` for tests at the public interface.
- `code-review` for standards in `CODING_STANDARDS.md` and the originating issue.
