# Threat Model

## Scope

Codex Workflow is an experimental local orchestration host. It executes a
workflow script in QuickJS, delegates `agent()` work to Codex subprocesses, and
records an auditable run directory. This document describes the intended
boundaries; it is not a claim that arbitrary hostile JavaScript is safe.

## Protected assets

- the user's main repository and uncommitted work;
- Codex credentials, environment variables, and local files;
- approval and sandbox policy;
- integrity of agent argv, results, journal identity, and resume decisions;
- availability of the CLI and cleanup of child process trees;
- confidentiality of prompts, schemas, model output, and logs.

## Trust assumptions

The user controls the selected script, `--cd` directory, arguments, and CLI
configuration. Workflow scripts should be reviewed or generated in a trusted
context. Codex itself and the local `codex` executable are outside this
project's implementation boundary.

A script is treated as capable of attempting denial of service and of mutating
ordinary JavaScript objects, prototypes, and globals. It must not be able to
select operating-system capabilities or call Python directly.
## Trust boundaries

### JavaScript to Python host

The QuickJS API exposes only `agent`, `parallel`, `pipeline`, `phase`, `log`,
`args`, `budget`, and one-level `workflow`. Host bridges are captured in a
private closure and removed from `globalThis`. Runtime completion state and
pending Promise registries are not directly addressable by user code.

Prompts and options cross the boundary as JSON text and are validated before
worker execution. JavaScript cannot provide raw argv, sandbox values, approval
flags, or worktree paths. Dynamic code constructors, time, randomness, Node,
QuickJS `std`/`os`, `require`, and `process` are unavailable.

### Python host to Codex process

The host constructs a closed argv list and never invokes a shell string. Normal
agents use `-s read-only`. `workspace-write` is accepted only for a host-created
Git worktree outside the main repository. Forbidden flags and arbitrary `-c`
configuration remain rejected in both builder and validator paths.

### Supervisor to runtime

The public CLI launches the QuickJS runtime in a separate process. A wall-clock
timeout or Ctrl+C terminates that runtime process tree. Agent executors also
track active subprocesses and cancel them on workflow failure.
## Security invariants

A valid change must preserve all of the following:

1. No execution path may request `danger-full-access`.
2. No script may select approval policy, `--full-auto`, or arbitrary config.
3. Ordinary agents remain read-only.
4. `workspace-write` appears only as the `-s` value for a host-authorized
   worktree, and that worktree is outside the complete Git repository root.
5. Worker threads never touch the QuickJS context.
6. Nested workflow paths remain inside `--cd` after resolution.
7. Cache hits follow a strict successful prefix and never consume live-agent
   capacity.
8. No implementation automatically applies, commits, merges, pushes, resets,
   checks out, or deletes user work.
9. Tests never make a real Codex request unless explicitly authorized.

## Availability controls

The QuickJS heap is limited to 32 MiB, JavaScript job counts are bounded, agent
and workflow payloads have size limits, live agents are capped, and agent
concurrency is bounded. The supervisor handles synchronous infinite loops that
cannot be interrupted from inside QuickJS while Python callables are enabled.

On supported platforms, cancellation attempts to terminate the complete runtime
or Codex child process tree. Forced termination can still leave partial run
artifacts, which are evidence rather than a successful completion record.
## Residual risks

- The project has not undergone an independent security audit or systematic
  intrinsic-by-intrinsic QuickJS hardening review.
- A hostile script may still find denial-of-service patterns not covered by the
  current heap, job, payload, agent, and wall-clock limits.
- Force-killing a process can leave an incomplete journal or external resources
  created before termination.
- Worktrees and run directories are retained and may contain sensitive source,
  prompts, generated output, or credentials copied by external tools.
- The local Codex installation, its shim scripts, and any processes it launches
  are trusted dependencies. Platform-specific process-tree semantics can vary.
- Resume assumes deterministic agent registration order. Concurrent workflows
  may lose cache hits when their actual call order changes; a mismatch disables
  the rest of the old prefix rather than searching later records.
- Token usage is not available, so `budget` is advisory except for live-agent
  and runtime limits.
- A repository may change concurrently while a run or detached worktree is
  being created; callers remain responsible for reviewing resulting state.

## Out of scope

This project does not protect against a malicious Python environment, a replaced
`quickjs` package, a compromised Codex executable, an administrator on the same
machine, or secrets deliberately included in prompts. It is not a multi-tenant
service boundary.

Report suspected boundary violations through the private process described in
[`SECURITY.md`](../SECURITY.md).
