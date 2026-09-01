# Security Policy

## Status

Codex Workflow is experimental software. The CLI runs QuickJS in a supervised
child process and constrains every Codex invocation, but it is not yet presented
as a hardened service for arbitrary hostile JavaScript.

## Supported versions

Only the current `master` branch is supported during pre-alpha development.
There are no security-maintenance guarantees for older commits or copied run
directories.

## Reporting a vulnerability

Do not publish working sandbox escapes, credential material, private prompts or
repository contents in a public issue.

Use GitHub private vulnerability reporting from the repository Security tab when
it is available. Otherwise, open a minimal issue asking the maintainer to
establish a private channel; omit exploit details until that channel exists.

A useful report contains:

- affected commit SHA and operating system;
- whether `--mock` or a real Codex process was involved;
- the smallest safe reproducer;
- expected and observed permission boundaries;
- any child processes or files left behind;
- suggested mitigation, when known.

## Security invariants

Reports are especially relevant when they show that JavaScript can:

- select arbitrary process argv, sandbox or approval policy;
- obtain `danger-full-access`;
- obtain `workspace-write` outside a host-created worktree;
- access Node, QuickJS `std`/`os`, Python objects or host files directly;
- forge runtime completion, journal identity or resume results;
- escape `--cd` through a nested workflow path;
- leave a process tree running after supervisor cancellation.

Resource-exhaustion reports are also relevant, although some denial-of-service
risk remains documented in `docs/THREAT_MODEL.md`.

## Operational precautions

Run unfamiliar scripts with `--mock`, use a disposable repository, inspect the
journal and generated argv, and avoid placing secrets in prompts. Worktrees and
run directories are intentionally retained for inspection and may contain
sensitive data.

No bug bounty or response-time commitment is currently offered.
