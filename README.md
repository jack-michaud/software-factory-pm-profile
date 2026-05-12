# softwarefactorypm profile

This is a local-installable role distribution root for current Hermes. It is generated/maintained from the Software Factory profiles monorepo prototype.

Install locally for testing:

```bash
hermes profile install /path/to/software-factory-profiles/profiles/pm --name softwarefactorypm-monorepo-test --yes
```

Role boundary: Frames Software Factory work, acceptance criteria, risks, and handoffs without mutating sprites or runtime systems.

## Generated public repository shape

This root is current-Hermes-compatible: `distribution.yaml` is at repository root.

Install after publication:

```bash
hermes profile install https://github.com/jack-michaud/software-factory-pm-profile.git --name softwarefactorypm
```

Update after publication:

```bash
hermes profile update softwarefactorypm --yes
```

Public/private boundary: credentials, runtime state, logs, memories, sessions, Kanban DB/workspaces, sprite credentials, SSH keys, OAuth tokens, API keys, and private Obsidian notes are not included.

## Runtime configuration

This distribution owns `config.yaml`. The file pins model execution to `gpt-5.5` via provider `openai-codex` using `chat_completions`, enables the public-safe `hermes-cli` toolset, and points `skills.external_dirs` at `../../skills` so controlled installs can reuse shared skill overlays without vendoring private/local skill trees.

Authority for this role is governed by `SOUL.md` plus the role-specific bootstrap skill. Publisher/docs profiles additionally include `role-capability-manifest.yaml`.

## Publication provenance

Version: v0.1.0
Source of truth: https://github.com/jack-michaud/software-factory
Source tag: profiles/v0.1.0
Source commit: 63035a90746ab304b7e8c5f231d9d89c2106e9d8
Generated manifest: GENERATED_METADATA.json
License: MPL-2.0

This repository is generated. File issues and feature requests on https://github.com/jack-michaud/software-factory rather than editing this generated repository directly.
## Optional docs deployment target

This distribution declares `SOFTWARE_FACTORY_DOCS_SPRITE_NAME` as an optional env var. Set it in the installed profile's user-owned `.env` only when PM-created docs publication/deployment tasks should target a dedicated docs sprite. For this environment the expected non-secret value is `hermes-sf-docs`. Distribution installs/updates must not overwrite `.env`; use `distribution.yaml` and this guidance as the contract.

## Remote Sprite Development

This distribution includes the `remote-sprite-development` skill. Install/update the same public distribution for both production and matching meta profiles (for example `softwarefactorybuilder` and `metasoftwarefactorybuilder`) so remote Sprite task routing, checkpoint, evidence, rollback, and review contracts are loadable without private local profile state.

## Evidence report generation

This distribution includes `scripts/software_factory_evidence_report.py` and the `software-factory-evidence-report` skill. PMs use them to generate Phase 1 Software Factory visibility reports from public Kanban CLI/API JSON surfaces:

```bash
python scripts/software_factory_evidence_report.py <root_task_id> --board software-factory --out-dir ./sf-evidence-reports
```

The command emits an HTML report and machine-readable JSON report with the task graph, timeline, role evidence, review/remediation loops, quality signals, unresolved risks, and audit boundary. It must not read raw Kanban databases, `.env`, `auth.json`, sessions, memories, logs, local profile state, private notes, or credentials.
