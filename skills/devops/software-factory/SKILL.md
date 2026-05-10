---
name: software-factory
description: Public Software Factory profile workflow context.
version: 0.1.0
---
# Software Factory

The Software Factory uses Hermes Kanban as the durable control plane for PM, builder, orchestrator, reviewer, and publisher roles.

Public profile distributions include reusable workflow guidance only. They intentionally exclude runtime credentials, private notes, memories, logs, sessions, and local machine state.

## Remote Sprite Development

When Software Factory work targets an existing remote Sprite, load `remote-sprite-development` and preserve role locality: PM profiles route and specify, builder profiles execute approved remote mutations with pre/post checkpoints and rollback evidence, and reviewer profiles perform independent read-only remote verification by default. Public profile distributions must include this reusable skill so production and meta PM/builder/reviewer installs can load the same contract without relying on private local profile state.
