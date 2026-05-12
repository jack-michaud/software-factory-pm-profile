# software-factory-pm-profile v0.1.0

Generated Hermes profile distribution for Software Factory role: pm.

- Source repo: https://github.com/jack-michaud/software-factory
- Source tag: profiles/v0.1.0
- Source commit: 63035a90746ab304b7e8c5f231d9d89c2106e9d8
- Generated manifest: GENERATED_METADATA.json
- Generated tree hash: d4ba705d36c2b627cab340e8e5155de1ef8fad63eface0f1e8eaebe837b8d018
- Validation: validate_monorepo.py exit 0; scan_generated_output.py exit 0; pytest tests exit 0
- Public-safety scan: 0 findings in publisher preflight
- Publication gates: human approval, dry-run validation, and publisher execution completed.

Branch protection is intentionally deferred for v0 by human decision.

## Unreleased

- Added Phase 1 Software Factory evidence report generation for PM/root-orchestrator task graphs. The PM profile now ships a deterministic HTML/JSON report script plus a `software-factory-evidence-report` skill and SOUL trigger for automatic final/interim report generation using public Kanban task surfaces only.
- Fixed evidence report role classification so reviewer/builder/publisher/installer/docs/PM roles are inferred from assignee or run profile before fallback title/body prose, preventing reviewer tasks about PM reports from being shown as PM tasks.
- Added progressive-disclosure Kanban task-spec guidance so root profile instructions remain concise maps while detailed PM/task-writing doctrine lives in linked references with explicit `When X, read Y` triggers. The guidance defines required task fields, evidence-linked acceptance criteria, and role-specific routing for future maintainers.
