Version Control
==

Agents will not make commits without explicit permission.

Configuration
==

When using configuration loading helpers, do not supply fallback defaults for missing config roots or files; failures should be explicit if configuration is absent.

Codex Sandbox
==

Codex runs with workspace-only write permissions, so it cannot modify files outside `/home/gideon/tmp/super_powers` (e.g., `~/.pyenv`). Operations that require writing there must be performed by the user or with an escalated command request.
