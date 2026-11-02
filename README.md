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

## Roadmap

1. Minimal agent loop
2. Tools and an edit format
3. Context assembly and the context/token/cost view
4. Loading AGENTS.md, skills and MCP
5. Hooks and permissions
6. Sandboxing
7. Compaction and memory
8. Subagents
9. Evals

## Status

Early days. This is a learning project, and it is not for production use.
