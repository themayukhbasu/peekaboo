---
name: slow-wayfinder
description: >-
  Personal overlay on stock /wayfinder: one question at a time, repo checkpoints,
  and map-only charting. Requires the project's /wayfinder, /to-spec, and
  /to-tickets skills. Use with /wayfinder, when charting a map, working a
  wayfinder:grilling ticket, or when the human says how they want wayfinding run.
  Where this conflicts with stock wayfinder or grilling (including multi-question
  rounds), these win.
---

# Slow wayfinder

## Requires

This overlay assumes the Matt Pocock skills stack is installed in the project:

- `/wayfinder` — map and decision tickets
- `/grilling` — pulled in by wayfinder for HITL decisions (this skill overrides its multi-question rounds)
- `/to-spec` — next step when the frontier is empty
- `/to-tickets` — slice the spec into build tickets after `/to-spec`

If any are missing, say so and stop; do not invent a substitute workflow.

Read the project's `/wayfinder` skill and issue-tracker docs first. Then apply these overlays. Where they conflict with stock wayfinder or grilling (including multi-question rounds), these win.

## Question style

- Ask **one question at a time**. Wait for the answer before the next.
- Normal prose. No multi-Q frontier dump in one message.
- Keep each question short. State the options with **pros and cons**. When a concept is advanced (REPL vs agent loop, provider seam, fixture vs live smoke), explain it in plain language before asking.
- Recommend one option. **"Yes" accepts the recommendation.** Push back when the preference fights the destination, session size budgets, PR reviewability, or a settled cut.
- Grill the product hard: what is delivered at each stage, and the complexity-versus-learning trade-off. Prefer thinner milestones one agent session can finish over landscape stages that bundle three lessons. Shape cuts so the eventual PRs stay reviewable (see **PR size**).

## Authority

- Existing ADRs, early-cuts, glossary drafts, and survey docs are **reference only** until a closed wayfinder ticket records the decision.
- Confirmed decisions live on tickets and in the map's Decisions-so-far. The chat and a checkpoint file are not the authority.

## Checkpoint

After each settled answer, update a repo file (default `docs/wayfinder/session-checkpoint.md`):

- Settled cut, open frontier, fog, out of scope, and issue links by **title**.
- Mark it as working notes, not a decision record.
- Keep it lean. Crash, outage, and usage limits must not wipe the route.

## Charting

- Charting creates the map and the decision tickets, then **stops**. Do not resolve research or grilling in the charting session unless user explicitly asks.
- Never put implementation or triage labels on a wayfinder decision ticket. Those tickets are decisions, not build work.
- Leave `wayfinder:grilling` and other HITL tickets for a live human exchange. Do not answer both sides of a grilling.
- Do not run `/to-spec` or `/to-tickets` until the map's open grilling tickets that block the cut are closed, unless the human explicitly asks to draft the unblocked milestones only.
- Size every ticket for one agent session. Prefer one decision or one research fact per ticket.

## PR size

Shorter PRs are preferred so a human can review them. Guideline: about **~250 significant lines of code** per PR, with a modest buffer. Significant lines means real logic and tests, not generated noise, lockfile churn, or pure formatting.

When charting, grilling milestones, or later when `/to-tickets` will slice the work: prefer cuts that fit that budget. If a ticket or milestone looks like it needs a much larger PR, say so and get the human's explicit agreement before locking it in.

## After the map

When the frontier is empty: tell the human the next step is `/to-spec`, then `/to-tickets`. Do not invent build tickets during wayfinding. When those skills run, keep the **PR size** guideline in mind.
