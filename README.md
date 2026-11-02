# peekaboo

Peek inside an agent's context window.

## Vision

peekaboo is Mayukh's personal learning project: a mini coding agent built from scratch, in the spirit of Claude Code, Codex CLI and Cursor's agent. He is building the inner harness, the runtime just outside the model, and it loads outer-harness config in open formats such as AGENTS.md, skills folders and MCP servers.

It exists to learn how agents really work by building one, and to make the invisible context visible.

## What makes it different

You can peek at everything that enters the context window each turn: the contents, the token count, the cost and any cache hits. That transparent view is the signature idea, and where the name comes from.

## Feasibility

A solo learning project can reach this. A minimal agent loop is small, capability grows in stages, and local models via Ollama keep the early stages free. Paid APIs (Anthropic, OpenAI and others) can come later.

## Inspiration

A few existing agents:

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview)
- [OpenAI Codex CLI](https://github.com/openai/codex)
- [Aider](https://github.com/Aider-AI/aider)
- [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent)
- [opencode](https://github.com/anomalyco/opencode)

## Early cuts

Staged so peek lands before tool complexity. See [docs/early-cuts.md](docs/early-cuts.md). Stack and product decisions: [ADR 0001](docs/adr/0001-python-raw-http-ollama-first.md), [ADR 0002](docs/adr/0002-cli-and-early-peek.md). Terms: [GLOSSARY.md](GLOSSARY.md).

1. One-shot chat loop (Python, raw HTTP → Ollama) + JSONL turn events
2. Tiny local web peek over that event stream
3. Agent loop with one tool
4. REPL, then streaming

## Roadmap

After the early cuts, capability grows in the longer plan in [docs/gameplan.md](docs/gameplan.md) (unchanged reference plan):

1. Tools and an edit format
2. Richer context assembly (tokens, cost, cache) in the peek
3. Loading AGENTS.md, skills and MCP
4. Hooks and permissions
5. Sandboxing
6. Compaction and memory
7. Subagents
8. Evals

## Status

Early days. Learning project, not for production. Language and early shape are decided; most harness code is not started yet.
