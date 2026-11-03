# Triage labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the label strings used in this repo's issue tracker.

The team vocabulary is `wayfinder:*` for wayfinder maps and decision tickets (see `issue-tracker.md`) and `ready-for-agent` for build tickets. Apply a label only when the middle column names one. An empty middle column means leave labels unchanged and record the role in the triage comment.

| Label in mattpocock/skills | Label in our tracker | Meaning |
| -------------------------- | -------------------- | ------- |
| `needs-triage` | | Maintainer needs to evaluate this issue. Record that in a comment. |
| `needs-info` | | Waiting on the reporter. The triage comment holds the questions. |
| `ready-for-agent` | `ready-for-agent` | Build ticket: fully specified, ready for an AFK agent. |
| `ready-for-human` | | Owner-only HITL work on a wayfinder ticket: `wayfinder:grilling`, `wayfinder:prototype`, or a HITL `wayfinder:task`. |
| `wontfix` | | Will not be actioned. Close the issue with a comment. |

When a skill mentions a role (for example "apply the AFK-ready triage label"), use the corresponding label string from this table.

Wayfinder maps and their child tickets carry only `wayfinder:*` labels.
