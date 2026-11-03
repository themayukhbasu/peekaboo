# Domain docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

This repo is **single-context**: one `GLOSSARY.md` and `docs/adr/` at the repo root. There is no `GLOSSARY-MAP.md`.

## Before exploring, read these

- **`GLOSSARY.md`** at the repo root, or
- **`GLOSSARY-MAP.md`** at the repo root if it exists: it points at one `GLOSSARY.md` per context. Read each one relevant to the topic.
- **`docs/adr/`**: read ADRs that touch the area you're about to work in. In multi-context repos, also check `src/<context>/docs/adr/` for context-scoped decisions.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill (reached via `/grill-with-docs` and `/improve-codebase-architecture`) creates them lazily when terms or decisions actually get resolved.

## File structure

Single-context (this repo):

```
/
├── GLOSSARY.md
└── docs/adr/
    ├── 0001-python-raw-http-ollama-first.md
    └── 0002-cli-and-early-peek.md
```

Multi-context would add a root `GLOSSARY-MAP.md` and per-context `GLOSSARY.md` plus `docs/adr/` directories. This repo has no per-context tree.

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `GLOSSARY.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal: either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0001 (Python, raw HTTP, and Ollama first), but worth reopening because…_

Prefer [docs/adr/](../adr/) and [docs/early-cuts.md](../early-cuts.md) when they disagree with [docs/reference/harness-landscape.md](../reference/harness-landscape.md). That survey is reference only.
