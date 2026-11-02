# CLI agent with an early, separate peek

The product is a **CLI coding agent** plus a **separate peek surface**. Peek starts early and stays simple: first a **JSONL turn-event log**, then a **tiny local web viewer** over the same stream. The agent CLI and the peek are not one TUI from day one.

## Early sequence

See [docs/early-cuts.md](../early-cuts.md). In short: one-shot chat + JSONL → web peek → one-tool agent loop → REPL/streaming. Later stages are decided later; [harness-landscape.md](../reference/harness-landscape.md) is reference only.

## Considered options

- **CLI-only peek via pager/files forever** — too weak for the peek-a-boo thesis; deferred only as the first slice.
- **Full TUI (chat + peek) from day one** — rejected; UI chrome would compete with learning the harness under small PRs.
- **Tools or streaming inside the first slice** — deferred so the wire and event shape stay clear.

## Consequences

Milestone demos will look thinner than Claude Code–class tools at first. That is deliberate: each milestone should change what the peek shows.
