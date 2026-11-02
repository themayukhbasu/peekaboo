# peekaboo

Terms for the learning-grade coding-agent harness and its transparent context view.

## Language

**Inner harness**:
The runtime around the model that assembles context, calls the model, runs tools, and repeats until the turn ends.
_Avoid_: agent framework, orchestration layer

**Outer harness**:
Configuration the inner harness loads, such as AGENTS.md, skills folders, hooks, and MCP server lists.
_Avoid_: project config (too vague), rules dump

**Chat loop**:
A single user message in and a model reply out, with no tools.
_Avoid_: minimal agent, agent loop

**Agent loop**:
Repeated model calls that may include tool calls until the model replies without tools (or a guard stops it).
_Avoid_: chat loop, workflow (reserve workflow for later multi-step patterns)

**Peek**:
The transparent per-turn view of what entered the context window (contents, later tokens, cost, cache).
_Avoid_: debug log, transcript (a transcript may feed the peek; it is not the product idea)

**Turn event**:
One recorded harness turn written to the peek event stream (for example a JSONL line), including the assembled request and model result.
_Avoid_: log line, trace span (until tracing is a deliberate feature)

**Provider seam**:
A thin boundary between the harness loop and a concrete model HTTP API, so Ollama can be swapped for paid APIs later.
_Avoid_: SDK, client (those are implementations behind the seam)
