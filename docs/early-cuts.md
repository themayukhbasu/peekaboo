# Early cuts

How the first milestones are sliced for learning. Later stages stay fog until more grill / wayfinder sessions; [reference/harness-landscape.md](reference/harness-landscape.md) is a research survey only. Decisions: [ADR 0001](adr/0001-python-raw-http-ollama-first.md), [ADR 0002](adr/0002-cli-and-early-peek.md). Terms: [GLOSSARY.md](../GLOSSARY.md).

## Sequence

1. **One-shot chat loop** — Python, raw HTTP to Ollama, non-streaming; emit JSONL turn events.
2. **Tiny local web peek** — read-only viewer over that event stream.
3. **Agent loop with one tool** — e.g. `read_file` or `bash`, with a max-turns guard.
4. **REPL**, then **streaming**.

After that, decide the next ladder deliberately — do not treat the landscape survey as the plan.

## Why this order

Peek is the product thesis, so it starts early and stays simple (log first, then a small web pane). Tools and streaming wait until the wire and turn-event shape are clear. Local Ollama keeps the early cuts free; a thin provider seam leaves room for paid APIs later.
