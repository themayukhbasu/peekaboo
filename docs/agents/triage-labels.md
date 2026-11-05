# Triage labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the label strings used in this repo's issue tracker.

The team vocabulary is `wayfinder:*` for wayfinder maps and decision tickets (see `issue-tracker.md`), `ready-for-agent` for the builder queue, and `ready-for-researcher` for the researcher queue. Apply a label only when this file names it. An empty middle column means leave labels unchanged and record the role in the triage comment.

| Label in mattpocock/skills | Label in our tracker | Meaning |
| -------------------------- | -------------------- | ------- |
| `needs-triage` | | Maintainer needs to evaluate this issue. Record that in a comment. |
| `needs-info` | | Waiting on the reporter. The triage comment holds the questions. |
| `ready-for-agent` | `ready-for-agent` | Builder queue: a fully specified build ticket. Not for the researcher. |
| `ready-for-human` | | Owner-only HITL work on a wayfinder ticket: `wayfinder:grilling`, `wayfinder:prototype`, or a HITL `wayfinder:task`. |
| `wontfix` | | Will not be actioned. Close the issue with a comment. |

When a skill mentions a role (for example "apply the AFK-ready triage label"), use the corresponding label string from this table.

Wayfinder maps and their child tickets carry `wayfinder:*` labels. They never carry `ready-for-agent`.

## Bot queues

Two labels, two bots. The PM assigns within a queue and does not put one bot's work on the other label.

| Label | Bot | What belongs on it |
| ----- | --- | ------------------ |
| `ready-for-agent` | Builder | A sliced build ticket from `/to-tickets`. Code PR. |
| `ready-for-researcher` | Researcher | AFK research the owner wants done. A `wayfinder:research` ticket carries this as well as its wayfinder label. Any other research issue the owner hands out carries this label and no wayfinder label. Findings go on a throwaway `research/<slug>` branch with no PR. |

`wayfinder:grilling`, `wayfinder:prototype`, and a HITL `wayfinder:task` never get either queue label. Tutoring notes are a docs PR when the owner asks for them. They are not implied by `ready-for-researcher`.
