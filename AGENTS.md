# Agent notes

peekaboo is a learning project: a mini coding agent / inner harness with a transparent per-turn context view. It is built in public, and it is not for production.

Read [README.md](README.md) for the vision, [docs/early-cuts.md](docs/early-cuts.md) for the first milestones, [GLOSSARY.md](GLOSSARY.md) for terms, and [docs/adr/](docs/adr/) for decisions. [docs/reference/harness-landscape.md](docs/reference/harness-landscape.md) is an agent-authored research survey only — not the living plan; prefer ADRs and early-cuts when they disagree.

Stack for early milestones: **Python**, **raw HTTP** to **Ollama**, thin provider seam for paid APIs later. Product: **CLI** plus a **separate peek** (JSONL first, then a tiny web viewer). Do not introduce SDKs, agent frameworks, or a full TUI unless an ADR says so.

## Working rules

- Keep changes small and scoped to the ask.
- Prefer at most one PR per day and about 250 lines of diff per PR, so each change is reviewable and learnable.
- Keep documentation and diagram changes lean. Do not install packages, or render Mermaid or Markdown, to validate documentation. GitHub renders Mermaid. Verify only what the change actually needs. Once the edit is done, commit and push rather than running extra checks. Do not spend tokens on work nobody asked for.
- Never commit secrets, API keys or `.env` files.
- Write documentation in British English.

## Build and test

Empty for now. Fill in when the first harness package exists.
