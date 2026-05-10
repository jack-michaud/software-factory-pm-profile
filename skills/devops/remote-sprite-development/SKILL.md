---
name: remote-sprite-development
description: Use when Software Factory production PM, builder, or reviewer tasks need to mutate or verify an existing remote Fly.io Sprite via explicit remote commands while preserving locality, checkpoint, evidence, rollback, and review guarantees.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [software-factory, sprite, remote-development, kanban, checkpoints, evidence]
    related_skills: [software-factory, kanban-worker, sprite-exec, sprite-development, software-factory-builder]
---

# Remote Sprite Development for Software Factory Profiles

## Overview

This skill is the production Software Factory contract for developing on an existing remote Sprite. It turns a PM intent into bounded builder/reviewer work that happens on the named target Sprite, not in the Kanban scratch workspace.

The central rule is locality: `$HERMES_KANBAN_WORKSPACE` is orchestration scratch. It is not the authoritative application source unless a task explicitly says it is an analysis-only checkout. All app inspection, edits, installs, builds, tests, runtime checks, checkpointing, and rollback validation must be performed on the target Sprite by explicit remote commands.

## Interim Decision: sprite exec Is Allowed Before pi-sprite

`pi-sprite` is not required for the next Software Factory dogfood if explicit `sprite exec` commands can satisfy the same checkpoint, evidence, rollback, and verification requirements in this skill.

Accepted interim remote execution boundary:

```bash
sprite -s <target-sprite> exec -- <read-only-command>
sprite -s <target-sprite> exec -- bash -c '<shell command with pipes, redirects, cd, or chaining>'
```

`pi-sprite` becomes required only if implementation testing proves that `sprite exec` cannot provide one of:

- reliable remote file mutation,
- readable command transcripts,
- checkpoint/rollback hooks,
- remote runtime verification.

Until that happens, do not block dogfood solely because `pi-sprite` is not in the loop.

## Role Boundaries

| Role | Owns | Must not do |
| --- | --- | --- |
| Meta PM | Experiment goal, tenant, acceptance criteria, risk framing, failure taxonomy, evaluation rubric | Run sprite mutation workflows or imply local scratch state is remote app state |
| Production PM | Tenant delivery graph, downstream builder/reviewer tasks, task bodies with target sprite and this contract | Mutate the Sprite unless separately assigned as a builder/reviewer task |
| Builder | Remote Sprite inspection/mutation, pre/post checkpoints, command transcripts, remote diffs, verification, rollback handle | Mutate locally and claim remote success; continue after checkpoint failure |
| Reviewer | Independent evidence review and safe remote verification; pass/fail/failure classification | Rubber-stamp local-only evidence; mutate without explicit review scope |

PM/meta profiles route and specify. Builder/reviewer profiles own remote commands and evidence.

## When to Use

Use this skill when:

- a Kanban task targets an existing Sprite such as `hermes-blog`, `hermes-pst`, `hermes-mooreu-base`, or another production tenant Sprite;
- the task asks for a remote app change, deployment, service tweak, runtime validation, rollback check, or review of such work;
- the task body mentions Software Factory production profiles, dogfood, remote Sprite development, checkpoint discipline, or remote evidence packages.

Do not use this skill for:

- purely local prototype work that intentionally never touches a Sprite;
- creating/destroying Sprites as a lifecycle task, unless paired with `sprite-lifecycle` and explicit approval;
- exposing public endpoints or data dumps without explicit user request and security review.

## Required Task Context

Every production task that mutates or verifies a Sprite must include the following in the body or loaded skill context:

- tenant name,
- target Sprite name,
- remote app path on the Sprite if known,
- expected service name/port/URL if known,
- acceptance criteria and quality gates,
- required skills: `kanban-worker`, `software-factory`, `remote-sprite-development`, plus app-specific skills when available,
- whether mutation is allowed or the task is review/read-only,
- protected data/routes and anything explicitly out of scope.

If target Sprite, mutation authority, or checkpoint availability is ambiguous, block before mutation.

## Target Locality Contract

1. Name the target Sprite explicitly in the task and handoff.
2. Treat `$HERMES_KANBAN_WORKSPACE` as local scratch only.
3. Use remote commands for all authoritative app inspection and mutation.
4. Label any local-only preparation as local-only evidence.
5. Never claim a local build/test proves remote Sprite state.
6. Store durable evidence in Kanban handoffs or non-secret workspace artifacts; never require private notes, local memories, sessions, logs, credentials, or hidden profile state to understand the result.

## Checkpoint Contract

Before any mutating command:

```bash
sprite -s <target-sprite> exec -- bash -c 'sprite-env checkpoints create --comment "pre-change: <task-id> <short-purpose>"'
```

Record the checkpoint handle/id/name, timestamp if available, and exact command. If checkpoint creation fails or is unavailable, block before mutation unless the human/PM explicitly accepts the risk in the task thread.

After successful verification:

```bash
sprite -s <target-sprite> exec -- bash -c 'sprite-env checkpoints create --comment "post-change: <task-id> verified <short-result>"'
```

Record both pre-change and post-change handles in completion metadata. If post-change checkpointing is unavailable, record the deployed/verified state handle and explain the gap.

## Allowed Remote Command Pattern

Read-only inspection:

```bash
sprite -s <target-sprite> exec -- bash -c 'cd <remote-app-path> && git status --short && pwd'
sprite -s <target-sprite> exec -- bash -c 'sprite-env services list'
sprite -s <target-sprite> exec -- bash -c 'curl -sS -o /tmp/check.out -w "%{http_code}\n" http://localhost:<port>/<route>'
```

Mutation after pre-checkpoint:

```bash
sprite -s <target-sprite> exec -- bash -c 'cd <remote-app-path> && <bounded edit/install/build/test command>'
```

File transfer only when required:

```bash
base64 /local/file | sprite -s <target-sprite> exec -- bash -c 'base64 -d > <remote-path>'
sprite -s <target-sprite> exec -- bash -c 'sha256sum <remote-path> && sed -n "1,80p" <remote-path>'
```

Prefer base64 piping/readback over relying on `--file` for critical writes because some Sprite CLI versions upload to `/tmp` or behave unexpectedly. If `--file` is used, record the exact local source, intended remote destination, observed upload destination, and readback verification.

Commands in handoffs must be copy-pastable, but must not contain secrets, tokens, API keys, OAuth material, private database content, or raw PII.

## Builder Evidence Package

Builder completion metadata must include:

```json
{
  "target_sprite": "hermes-blog",
  "tenant": "blog",
  "remote_workdir": "/home/sprite/app",
  "mutation_allowed": true,
  "pre_checkpoint": {"handle": "v12", "command": "sprite -s hermes-blog exec -- bash -c 'sprite-env checkpoints create --comment ...'"},
  "post_checkpoint": {"handle": "v13", "command": "sprite -s hermes-blog exec -- bash -c 'sprite-env checkpoints create --comment ...'"},
  "remote_commands": {
    "inspect": ["..."],
    "checkpoint": ["..."],
    "mutate": ["..."],
    "verify": ["..."]
  },
  "changed_files_remote": ["/home/sprite/app/path/file.ext"],
  "diff_summary": "Remote git diff/readback summary, no secrets",
  "verification": [{"command": "...", "result": "pass", "evidence": "HTTP 200 / tests passed"}],
  "runtime_routes_checked": ["https://<sprite-url>/<route>"],
  "rollback": {"available": true, "procedure": "sprite -s hermes-blog exec -- bash -c 'sprite-env checkpoints restore v12'"},
  "open_risks": [],
  "failure_class": null
}
```

Builder summaries should name concrete remote artifacts and verification, not just say "done".

## Reviewer Evidence Package

Reviewer completion metadata must include:

```json
{
  "target_sprite": "hermes-blog",
  "tenant": "blog",
  "evidence_reviewed": ["builder metadata", "remote diff summary", "verification output"],
  "independent_remote_commands": ["sprite -s hermes-blog exec -- bash -c 'cd /home/sprite/app && git status --short'"],
  "remote_state_matches_builder_claims": true,
  "verification_passed": true,
  "decision": "pass",
  "failure_class": null,
  "required_followups": []
}
```

If failing, set `decision` to `fail` or `block`, include the most specific `failure_class`, and explain whether the problem is process/tooling/context/app implementation.

## Rollback Contract

A production builder task is not complete until it states the concrete rollback procedure from the pre-change checkpoint.

Example:

```bash
sprite -s <target-sprite> exec -- bash -c 'sprite-env checkpoints restore <pre-checkpoint-handle>'
```

Also note any service recreation, dependency reinstall, or runtime restart needed after checkpoint restore. Checkpoints are primarily filesystem state; service definitions and running process state may need separate restoration steps.

If rollback is unavailable and risk has not been accepted in the Kanban thread, block before mutation.

## Observability Contract

Minimum durable observability:

- Kanban task graph shows PM -> builder -> reviewer dependencies.
- Builder/reviewer completions include structured metadata for target Sprite, checkpoints, commands, verification, rollback, and failure class.
- Non-fatal anomalies are preserved as Kanban comments.
- Command transcript artifacts may be stored in the task workspace if they contain no secrets.
- Reviewers explicitly state whether evidence was sufficient.

Desired future improvements:

- automatic command transcript capture,
- dashboard badges for missing checkpoint, missing rollback, local-only verification, and missing reviewer evidence,
- secret redaction before transcript persistence.

## Failure Classification

Use exactly one primary class when possible:

1. `contract_missing` - task did not include required remote-development guidance.
2. `locality_violation` - agent acted locally while claiming remote verification.
3. `checkpoint_failure` - checkpoint unavailable, failed, missing, or not recorded.
4. `rollback_gap` - no viable restore path captured.
5. `evidence_gap` - commands/diffs/tests insufficient or non-reproducible.
6. `tooling_failure` - Sprite CLI/pi-sprite/session mechanics failed despite correct behavior.
7. `skill_context_failure` - required skill/app context missing.
8. `implementation_failure` - remote change fails acceptance despite correct process.
9. `review_failure` - reviewer passed insufficient or contradictory evidence.
10. `human_decision_blocker` - approval required for risk, scope, credentials, or destructive action.

## Task Body Templates

### Production PM Seed Task Template

```text
Title: Plan tenant=<tenant> remote Sprite change for <app/change>
Assignee: <production-pm-profile>
Tenant: <tenant>

Goal:
- Create a delivery graph for <requested change> on target Sprite <target-sprite>.
- Do not mutate the Sprite in this PM task.

Required context:
- Load skills: kanban-worker, software-factory, remote-sprite-development.
- Target Sprite: <target-sprite>
- Remote app path: <remote-app-path or unknown; builder must discover remotely>
- Service/URL: <service name, port, URL if known>
- App-specific context: <repo path, test/build commands, routes, protected areas>
- Quality gates: <tests, build, runtime checks, reviewer checks>

PM acceptance criteria:
1. Create builder task with mutation authority, target Sprite, checkpoint requirement, remote command/evidence contract, and app acceptance criteria.
2. Create reviewer task depending on the builder task with read-only remote verification scope.
3. Ensure PM/meta profiles do not run sprite mutation workflows.
4. Complete with child task IDs and the failure classes reviewers must use.
```

### Builder Task Template

```text
Title: Implement <change> on remote Sprite <target-sprite>
Assignee: <builder-profile>
Tenant: <tenant>
Skills: kanban-worker, software-factory, software-factory-builder, remote-sprite-development, sprite-exec, <app-skill>

Mutation authority: allowed only on target Sprite <target-sprite>.
Locality: $HERMES_KANBAN_WORKSPACE is orchestration scratch only. All authoritative app work must be remote.
Remote app path: <path or discover read-only first>

Acceptance criteria:
1. Create and record pre-change checkpoint before mutation; block if unavailable.
2. Inspect remote state and record relevant commands.
3. Apply bounded remote changes only on <target-sprite>.
4. Read back remote diff/changed files.
5. Run remote tests/build/runtime verification.
6. Create and record post-change checkpoint after successful verification.
7. Complete with builder evidence metadata schema from remote-sprite-development.
8. Include rollback procedure from pre-change checkpoint.

Safety:
- Do not include secrets in command transcripts or metadata.
- Block on credentials, destructive ambiguity, target mismatch, or rollback/checkpoint gaps.
```

### Reviewer Task Template

```text
Title: Review remote Sprite change on <target-sprite>
Assignee: <reviewer-profile>
Tenant: <tenant>
Parents: <builder-task-id>
Skills: kanban-worker, software-factory, remote-sprite-development, sprite-exec, <app-skill>

Scope: read-only remote verification unless explicitly approved otherwise.
Target Sprite: <target-sprite>

Acceptance criteria:
1. Review builder metadata for target locality, pre/post checkpoints, changed files, verification, and rollback.
2. Re-run safe remote verification commands on <target-sprite>.
3. Confirm remote state matches builder claims.
4. Decide pass/fail/block.
5. If failed, classify using remote-sprite-development failure classes.
6. Complete with reviewer evidence metadata schema.

Safety:
- Do not mutate unless a separate reviewer mutation scope is explicitly granted.
- Do not pass local-only verification as remote proof.
```

## Non-Destructive Dry Run: tenant=blog PM Seed Body

This is an example to copy into a future task body. Do not dispatch it from this skill.

```text
Title: Plan tenant=blog remote Sprite dogfood for homepage copy update
Assignee: metasoftwarefactorypm
Tenant: blog

Goal:
- Create the production delivery graph for a small homepage copy update on target Sprite hermes-blog.
- This PM task must not run sprite, sprite-env, fly, pi-sprite, or any mutation workflow.

Required skills/context:
- Load: kanban-worker, software-factory, remote-sprite-development.
- Target Sprite: hermes-blog
- Remote app path: unknown; builder must discover with read-only sprite exec.
- Required quality gates: pre-checkpoint, bounded remote mutation, readback diff, remote build/test if present, runtime route check, post-checkpoint, reviewer read-only verification.
- Interim tooling decision: pi-sprite is not required if sprite exec satisfies checkpoint/evidence/rollback/verification; reviewer must block and recommend pi-sprite only if sprite exec cannot satisfy those requirements.

PM acceptance criteria:
1. Create a builder child task assigned to the production builder with mutation authority limited to hermes-blog and the remote-sprite-development evidence schema.
2. Create a reviewer child task assigned to the production reviewer depending on the builder.
3. Include failure classes: contract_missing, locality_violation, checkpoint_failure, rollback_gap, evidence_gap, tooling_failure, skill_context_failure, implementation_failure, review_failure, human_decision_blocker.
4. Complete with child task IDs only; no Sprite commands run in this PM task.
```

## Common Pitfalls

1. Running local `npm`, `git`, `pytest`, `curl`, or `write_file` and claiming it proves the remote Sprite. It does not.
2. Forgetting `bash -c` for pipes, redirects, `cd`, heredocs, variable expansion, or chained commands.
3. Continuing after checkpoint creation fails.
4. Recording "checkpoint created" without the checkpoint handle or command.
5. Using `--file` without readback verification.
6. Storing secrets, `.env`, auth files, databases, sessions, or private logs in transcripts or metadata.
7. Letting PM/meta profiles mutate Sprites while also evaluating the factory process.
8. Reviewer passes evidence without independently checking remote state.

## Verification Checklist

For builders:

- [ ] Target Sprite named and used in every remote command.
- [ ] Pre-change checkpoint created and recorded before mutation.
- [ ] Mutations happened remotely, not in local scratch.
- [ ] Remote changed files/diff read back.
- [ ] Remote verification executed and recorded.
- [ ] Post-change checkpoint created or gap explained.
- [ ] Rollback procedure recorded.
- [ ] Metadata contains no secrets.

For reviewers:

- [ ] Builder evidence includes target locality, checkpoints, commands, changed files, verification, rollback.
- [ ] Independent safe remote verification was run or reviewer blocked with reason.
- [ ] Decision is pass/fail/block.
- [ ] Failure class is supplied for fail/block decisions.

For PM/meta profiles:

- [ ] PM task did not mutate the Sprite.
- [ ] Builder and reviewer tasks force-load this skill or inline this contract.
- [ ] Meta evaluation can reconstruct the run from Kanban handoffs alone.
