---
name: software-factory-evidence-report
description: Generate Software Factory PM evidence HTML/JSON reports from public Kanban task surfaces.
version: 0.1.0
---
# Software Factory Evidence Report

Use this skill when a PM/root-orchestrator task completes, when Jack asks for a visibility report, or when reviewing an interim Software Factory task graph. The report generator is deterministic: it extracts and normalizes Kanban task-tree metadata, emits JSON plus HTML, and flags minimum deadlock/quality signals. PM/LLM work remains responsible for nuanced interpretation, narrative synthesis, deciding follow-up routing, and final completion wording.

## Privacy and source boundary

Use only public Kanban API/CLI/tool JSON or an explicitly public-safe exported task context. Do not read raw `kanban.db`, `.env`, `auth.json`, `state.db`, sessions, memories, logs, local profile state, sprite credentials, API keys, OAuth tokens, SSH keys, or private Obsidian notes. Do not paste secrets or raw private state into an input JSON file.

Links are allowed by default for internal operator reports, including local worktree paths, task ids, public GitHub URLs, runtime URLs, checkpoint ids, and artifact paths, as long as they do not reveal secrets or private raw state. There is no separate public/redacted mode in Phase 1.

## On-demand generation

From an installed PM profile that includes this distribution-owned script:

```bash
python scripts/software_factory_evidence_report.py <root_task_id> --board software-factory --out-dir ./sf-evidence-reports
```

Outputs:

- `<root_task_id>-software-factory-evidence-report.html`
- `<root_task_id>-software-factory-evidence-report.json`

The command prints a small JSON summary with output paths, task count, report status, and quality-signal count.

If live Kanban CLI access is not available, provide a public-safe export made from `hermes kanban show --json <task_id>` objects:

```bash
python scripts/software_factory_evidence_report.py <root_task_id> --input-json public-task-export.json --out-dir ./sf-evidence-reports
```

## Automatic PM behavior

When completing a root PM/orchestrator objective or a major PM-created implementation graph:

1. Generate the evidence report before final completion when the graph is sufficiently closed, or generate an interim report if downstream work remains open.
2. Inspect the HTML/JSON for minimum signals: `blocked_without_followup`, `reviewer_without_remediation`, `missing_evidence`, `source_map_missing`, `stale_ready`, `stale_running`, `child_under_blocked_parent_deadlock`, and `hallucinated_created_card` when exposed by task events/metadata.
3. Use the JSON as deterministic extraction evidence; use PM judgment to summarize done claim, unresolved risks, and recommended follow-up tasks.
4. Include the generated artifact paths and any critical/warning signal summary in the PM handoff metadata.
5. If the report surfaces actionable follow-up work, create/link durable Kanban tasks with role-appropriate assignees instead of leaving advisory-only prose.

## Expected report sections

The HTML/JSON report includes:

- Header with root task id/title, generated timestamp, final/interim status, and done claim.
- Objective, scope, out-of-scope boundaries, and acceptance criteria extracted from the root task.
- Assumptions and PM decisions from metadata/comments.
- Task graph nodes and dependency/follow-up/remediation edges.
- Timeline of task events and runs.
- Evidence by role: PM, builder, reviewer, publisher, docs, installer.
- Review outcomes and remediation loops.
- Launch/deploy proof section, with an explicit not-assumed note when runtime deployment is out of scope.
- Deadlock/quality signals and unresolved risks.
- Audit appendix naming the no-secret/public-surface boundary.

## PM synthesis guidance

Use this deterministic report as a fact base, not as the whole final answer. In the final PM narrative:

- State exactly what “done” means and whether it is succeeded, succeeded-with-risks, blocked, failed, superseded, or inconclusive.
- Cite concrete task ids, output paths, commits, URLs, review verdicts, and validation results from the report.
- Separate verified evidence from claimed/unverified evidence.
- Name skipped validation and non-goals explicitly.
- Route remediation for warnings/critical signals through Kanban tasks when action is required.

## Reviewer expectation

A reviewer should be able to run the script against the current implementation/review root task and find the review task id in the generated task graph/timeline. If the review task is not present, inspect dependency edges and created-card metadata before approving.
