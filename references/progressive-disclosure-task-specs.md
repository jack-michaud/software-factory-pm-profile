# Progressive-disclosure Kanban task specs

Use this reference when a Software Factory role creates, decomposes, reviews, publishes, installs, validates, or documents Kanban task specs. Root `SOUL.md` and root profile instructions should stay concise: keep role identity, authority boundaries, public/private rules, and a short context map there, then route detailed task-writing guidance to references or focused skills with explicit `When X, read Y` triggers.

## Required task shape

Software Factory PM/Kanban task specs should contain:

1. **Title** — imperative and specific enough to identify the intended outcome.
2. **Goal** — one or two sentences explaining the outcome and why it matters.
3. **Context index** — an always-read line plus trigger-routed optional context, using explicit `When X, read Y` wording. Include parent task ids, source maps, skills, reference files, and validation artifacts only when relevant.
4. **Scope** — separate `In` and `Out` boundaries so the assignee knows what authority is granted and what must be left to a follow-up task.
5. **Acceptance criteria** — independent, objectively verifiable criteria that define done.
6. **Evidence expectations** — for each non-trivial criterion, name the proof expected in the handoff: command output, artifact path, source path, diff hunk/snippet, screenshot, public URL, reviewer verdict, Kanban task id, or generated manifest.

## Acceptance-criteria quality bar

Acceptance criteria must be:

- **Clear and concise** — plain language with no ambiguous adjectives unless paired with a threshold.
- **Testable / objectively verifiable** — a reviewer or automated check can decide pass/fail from evidence.
- **Outcome-focused** — describe user/system behavior or delivered artifacts, not internal implementation steps unless the implementation choice is itself required.
- **Measurable where possible** — use paths, counts, target profile lists, command names, URLs, status codes, or other thresholds instead of words like "better" or "complete".
- **Independent** — each criterion should stand alone enough that failures are diagnosable.
- **Stakeholder-readable** — PM, builder, reviewer, publisher, docs, and installer roles should interpret the criterion the same way.
- **Evidence-linked** — every non-trivial criterion should include `Evidence:` or otherwise state the expected proof.

If a criterion cannot be proven with public-safe evidence, rewrite it before dispatch or mark the task blocked with the smallest decision needed.

## Progressive context rules

- Keep non-negotiables in the always-read layer: safety boundaries, task contract, authority limits, escalation/blocking rules, and acceptance criteria.
- Put deeper doctrine, examples, prior research, source maps, and validation checklists in linked references or focused skills.
- Use compact pyramid summaries for large backlog/research inputs: short root summary first, then grouped details with links or artifact paths.
- Require handoffs to state which context was used so routing misses are debuggable.
- Do not copy private runtime state, raw Kanban databases/workspaces, logs, sessions, memories, credentials, or local profile state into task specs or evidence.

## Task-level forced-skill rule

PM-created Kanban tasks should leave task-level forced skills unset by default. Workers already receive their assigned profile SOUL/context and built-in Kanban worker guidance; forcing those same role, project, or built-in skills at task startup can crash dispatch when the target profile does not expose the exact skill name. Do not force role/project/built-in skills such as `software-factory`, `software-factory-pm`, or `kanban-worker` merely because they are generally relevant.

Only specify task-level `skills=[...]` when every condition is true:

1. The skill is narrowly scoped and non-role-specific, or it supplies an external tool/workflow contract required before the worker can safely start.
2. The PM has public-safe evidence that the exact skill name is loadable in the target profile context.
3. The task acceptance criteria genuinely require that contract at startup rather than allowing the worker to load optional context after orienting.
4. The task body records why the skill is required, the evidence for target-profile loadability, and what the assignee should do if the skill is unavailable, including a block/remediation path rather than blind dispatch.

For remote Sprite work, preserve the existing routing doctrine: if `remote-sprite-development` is required, either make its target-profile availability explicit with public-safe evidence or inline the remote mutation/review contract in the task body. If the skill is unavailable in the target profile, classify the issue as `skill_context_failure` and create source/install remediation before dispatching tenant or Sprite mutation work.

## Role routing

- PM: use this reference whenever drafting, decomposing, or linking Kanban tasks.
- Orchestrator: use this reference when turning goals into durable task graphs or checking dependency shapes.
- Reviewer: use this reference when verifying task-spec quality, evidence coverage, and root-file compactness.
- Builder: use this reference when creating scoped follow-up tasks from implementation findings or when reporting evidence against acceptance criteria.
- Publisher: use this reference when release/publication tasks need gated dependencies, proof of approval, or source/push evidence.
- Docs: use this reference when transforming release packets into docs tasks or documenting public-safe workflow expectations.
