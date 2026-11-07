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

After the early cuts, later capability is still fog; a research survey of possible stages lives in [docs/reference/harness-landscape.md](docs/reference/harness-landscape.md) (not the living plan):

1. Tools and an edit format
2. Richer context assembly (tokens, cost, cache) in the peek
3. Loading AGENTS.md, skills and MCP
4. Hooks and permissions
5. Sandboxing
6. Compaction and memory
7. Subagents
8. Evals

## Status

Early days. Learning project, not for production. `peekaboo chat MESSAGE` sends one user message to local Ollama, writes one JSONL run under `.peekaboo/runs/`, and prints that path. The peek and the agent loop come in later milestones.

## Development

uv is the package manager. See [AGENTS.md](AGENTS.md) for the builder commands.

Runtime settings load through `peekaboo.config.load_config`, the only reader of the process environment and of a `.env` file in the working directory. The process environment overrides `.env` when both set the same name, including a blank process value. The file is parsed with [python-dotenv](https://github.com/theskumar/python-dotenv#file-format) (`dotenv_values`): `${NAME}` expands from an earlier binding in the file, then the process environment, and a bare `$NAME` does not. The default model is `llama3.2` (the tag in Ollama's `/api/chat` examples). The other defaults are an Ollama base URL of `http://127.0.0.1:11434`, an HTTP timeout of 120 seconds, runs under `.peekaboo/runs`, a peek bind of `127.0.0.1:8765`, and a `read_file` truncation limit of 32 KiB (32768 characters) of decoded text. Environment variable names are documented on that module.

```bash
uv sync
uv run python -m unittest discover -s tests
uv run peekaboo --help
uv run peekaboo chat "why is the sky blue?"
```

### Live Ollama smoke

Opt-in. `tests/live_smoke.py` is not named `test*.py`, so `unittest discover` does not load it, read `.env`, or call Ollama. If nothing is listening, the module skips. It is not a merge gate. A live reply is only data: harness fields, not the model's words.

```bash
uv run python -m unittest tests.live_smoke
```
