---
name: kanban-profile-workflow
description: Public multi-profile Kanban workflow conventions.
version: 0.1.1
---
# Kanban Profile Workflow

Use Kanban for durable cross-profile work. Keep PM, builder, orchestrator, reviewer, and publisher responsibilities separate. Generated public artifacts must be independently validated before publication.

## Durable task creation and blockers

Do not leave draft-only artifacts when work is ready to track but blocked by gates. Create concrete Kanban tasks with stable `idempotency_key` values so retries do not duplicate work. If a dependency or gate is not green, create the task as triage/blocked rather than hiding it in a markdown draft, then add explicit comments that name the blocker task ids, missing evidence, and the condition that unblocks dispatch.

Builders and reviewers should not silently work around missing prerequisites. When implementation or verification is blocked, declare the blocker in the task thread and handoff metadata: required artifact, owning profile, suspected failure class, and the concrete evidence needed. PM then creates or links unblocking Kanban tasks instead of asking the same worker to guess.

## PM escalation loop

For PM-led Software Factory work, use this escalation sequence:

1. Inspect the board/task artifacts and any approved public source repos or generated profile distributions that are in scope. Do not read private profile state, secrets, local memories, sessions, or Kanban databases directly.
2. Create or link concrete unblocking tasks with `idempotency_key` values and explicit acceptance criteria. Use triage/blocked state when gates are not green.
3. Allow at most two PM <-> builder/reviewer resolution cycles for the same blocker family. Each cycle must leave comments and task handoff metadata with evidence reviewed, decision, blocker ids, and remaining question.
4. After two unsuccessful cycles, escalate to the orchestrator or human with evidence: task ids, source paths/commits inspected, blocker classification, attempted unblocking tasks, and a precise decision request.

Lesson from t_140783aa/t_21b2c8b6: meta PM correctly separated the experiment harness from the production tenant graph, but the next step was left as a draft-only seed. The corrected behavior is to create the durable production PM task with an idempotency key, hold it triaged/blocked until gates clear, and create/link the unblocking tasks that make those gates green.
