# Wayfinder checkpoint — peekaboo milestone map

Working notes for the live charting session. Not a decision record. Confirmed decisions land only as wayfinder tickets. Existing ADRs, `docs/early-cuts.md`, and `docs/reference/harness-landscape.md` stay reference until a ticket says otherwise.

Status: map charted. Charting session stopped. Do not resolve a grilling ticket from a bot session.

## Issues

- Map: [First three milestones: chat loop, peek, agent loop](https://github.com/themayukhbasu/peekaboo/issues/9)
- Closed: [Does the agent loop send a fixed system message?](https://github.com/themayukhbasu/peekaboo/issues/10)
- Closed research: [What is Ollama's chat tool-call JSON?](https://github.com/themayukhbasu/peekaboo/issues/11)
- Frontier, owner live: [What does the agent loop do with several tool calls in one response?](https://github.com/themayukhbasu/peekaboo/issues/12)

## What this session is

Chart a `wayfinder:map` on GitHub (`themayukhbasu/peekaboo`). Decisions only. A later session runs `/to-spec`, then `/to-tickets`. This session does not implement the harness.

Grill rules: one question at a time, normal prose, pros and cons, push back, checkpoint after each settled answer. "Yes" accepts the recommendation.

## Settled

**Map cut (Q1, accepted).** Three milestones, in order, specified tightly enough for a later `/to-spec`:

1. **Chat loop.** One-shot. One user message, one model reply, no tools. Python, raw HTTP to Ollama, non-streaming. Each model call is one JSONL turn event inside that run's file. A terminal print of the harness fields may exist here as a debugging aid. That print is not the peek.
2. **Peek.** A tiny local web page. Python stdlib serves one HTML file. First screen is a directory listing of run files. A link opens that run's events and shows the harness fields. The raw provider body is a collapsed block. No npm, no frontend framework, no build step. Tool calls and the tool schema, once they exist, are sections on the event page, not a new design.
3. **Agent loop.** One-shot, same event stream. One tool, `read_file`, via Ollama's native `tools` field. Stops as in Q5. The schema, the tool call, and the tool result appear on the event and on the peek.

Stack for these three: Python, raw HTTP, Ollama only, non-streaming. A second provider is outside this map. A run is one process: one message in, one new file written, process exits. Ctrl-C kills a stuck run.

**Turn event (Q2, accepted).** Harness-shaped JSONL, one object per model call. Core: `model`, `messages_sent` (role and content), `assistant` (role and content), `stop_reason`, `error` (null on success), `raw_response`. Readers use the harness fields, not Ollama's JSON. No token, cost, cache, or segment fields in this map. Exact key names may move in `/to-spec`. The split (harness fields plus raw body) may not. The agent loop extends `messages_sent` with tool calls and tool results.

**Tool schema on the event (Q7, accepted).** The agent loop adds a `tools` field: the schema sent to the model (`name`, `description`, `parameters`). The chat loop sends no tools and omits the field. The peek renders `tools` as its own block. Ollama's native tool-call protocol is the wire. A text protocol such as "reply with `READ path`" is out.

**Peek surface (Q3, accepted).** Milestone 2 above.

**Tool (Q4, accepted).** The only tool is `read_file`. One argument, `path`. The path must stay inside the workspace. The result is file text, or a short error string if the file is missing or the path is outside the workspace. Large files are truncated and marked truncated. A tool failure is a tool result, not a crashed process. Line ranges, grep, bash, and an edit tool stay in the fog.

**Loop stop (Q5, accepted).** For one user message, stop when any of these happens:

1. The model replies with no tool call. `stop_reason` is `stop`.
2. Model calls for that user message hit 8. `stop_reason` is `max_turns`. The last event is written. The model is not called again.
3. The provider call fails. `error` is set, `stop_reason` is `error`, no retry.

The cap counts model calls, not tool calls. No token budget. No duplicate-call detector. 8 is a constant.

**Session commands (Q6, accepted).** `/exit` is a REPL command. It stays out of this map with the REPL. It is not a stop condition of these three milestones.

**Thin caller (Q11b, accepted).** `peekaboo chat`, `peekaboo agent`, and `peekaboo peek` are one-shot callers. They exit. There is no bare `peekaboo "message"`. `chat` calls `run(messages, tools=[])`. `agent` calls `run(messages, tools=[read_file])`. `run` does not read argv and does not know about a prompt. A later session is another caller of `run`, with a longer message list. One file per command may become one file per session later. That revises the layout. It does not replace `run`, the adapter, the turn event, `read_file`, or the peek.

**Run log (Q8, user override; Q9, accepted).** One JSONL file per run at `.peekaboo/runs/<utc-timestamp>.jsonl`, gitignored. The peek's first screen is that directory: one link per filename. No sidecar index, no prompt preview, no status column. Deleting a run is deleting the file. The CLI prints the path when the run finishes. Tests write into a temporary directory. A single append-only `turns.jsonl` is out. A metadata index is a later change.

**Verification (Q10, accepted).** Fixture tests gate a milestone. The fake is the HTTP transport (bytes in, bytes out). The adapter still parses a captured Ollama body, including a tool-call body and an error body. No daemon in the bot gate. A live smoke command calls localhost Ollama and skips with a clear message when nothing is listening. That smoke is manual. It is not required for a bot PR. No recording proxy in this map.

**Provider seam, implied by Q2 (say if this is wrong).** One Ollama adapter. Its output is the harness fields plus the raw body. The loop and the peek do not translate Ollama JSON themselves.

**System message (ticket closed).** Agent loop only: `run` prepends one fixed system message that the model may call `read_file`. It is part of `messages_sent`. Chat still sends only the user message. Exact wording is for `/to-spec`.

**Glossary.** `Run` and `Session` are in `GLOSSARY.md`. A run is one execution of the chat loop or the agent loop for a single user message. A session is a process that stays open for another message.

**Out of this map (fog, not tickets).** Tool registry, edit format, per-segment tokens, cost, cache, AGENTS.md, skills, MCP, hooks, permissions, sandbox, compaction, memory, subagents, evals, streaming, REPL (including `/exit`), paid APIs, a homemade text tool protocol, a single append-only turns log, a run-index sidecar, a live-Ollama test gate, a recording proxy. A content series stays out. Bash as a tool stays out.

## Repo facts

- No harness code yet.
- Glossary drafts: inner harness, outer harness, chat loop, agent loop, peek, turn event, provider seam.
- Bot rules stand: about 250 significant lines per PR, at most 3 open bot PRs, at most one new scheduled PR a day, bots never merge. HITL wayfinder tickets need the owner live.
- GitHub issue list has not been checked yet. Check `gh repo view` is `themayukhbasu/peekaboo` before the first `gh issue create`.

## Frontier

Next owner live: [What does the agent loop do with several tool calls in one response?](https://github.com/themayukhbasu/peekaboo/issues/12). Research on Ollama tool-call JSON is closed, so this grilling is unblocked.
