# Python, raw HTTP, and Ollama first

peekaboo is a learning project, so the first stack optimises for understanding the wire over shipping speed. The harness is **Python** (familiarity), talks to the model with **raw HTTP** (no provider SDK or agent framework in the early milestones), and uses **Ollama only** until the chat loop and JSONL peek events work. A thin **provider seam** keeps paid APIs (Anthropic, OpenAI, and others) as a later swap, not a rewrite.

## Considered options

- **TypeScript or Go** for the harness — rejected for now so language learning does not compete with harness learning.
- **Official provider SDKs or an agent framework** — rejected for early milestones; they hide the protocol. SDKs may return once the raw loop is understood.
- **Paid APIs from day one** — rejected until the free local path proves the loop and peek.

## Consequences

Early tool-calling quality will be limited by local models; that is acceptable for learning the harness, not for judging agent IQ. Streaming, REPL, and multi-provider adapters come after the non-streaming one-shot chat path is solid.
