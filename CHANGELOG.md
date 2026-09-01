# Changelog

All notable changes to this project are documented here. The project is still
pre-alpha and has not published a compatibility-stable release.

## Unreleased

### Added

- `phase(title)` journal grouping with registration-time agent snapshots.
- JSON `args`, advisory `budget`, and configurable hard `--max-agents`.
- Strict `--resume-from` successful-prefix caching.
- Host-created detached Git worktrees for explicit `isolation: "worktree"`.
- One-level nested `workflow({scriptPath}, args)` execution.
- External runtime supervisor with wall-clock timeout and Ctrl+C handling.
- Cooperative workflow cancellation and tracked Codex process-tree termination.
- Windows and Linux GitHub Actions tests.
- API, journal, threat-model, security, contribution, and release documentation.
- Installed `codex-workflow` console entry point.

### Changed

- Real agent stdout and stderr now stream directly to per-agent log files.
- Agent indices are allocated at JavaScript registration time.
- CLI execution is supervised by default.
- Package metadata now includes the README, project URLs, and pre-alpha
  classifiers.
### Security

- Runtime state and host callables are hidden from workflow scripts.
- Direct and indirect JavaScript function constructors are disabled.
- Host runtime logic uses captured intrinsics rather than mutable user globals.
- Schema keyword types, bounds, recursion depth, and finite numbers are checked
  before an agent starts.
- `workspace-write` remains forbidden except at the authorized `-s` value for a
  host-created worktree outside the repository root.
- Nested workflow paths are resolved and constrained to `--cd`.

### Fixed

- Preflight failures and live-agent limit rejections are written to the journal.
- Direct argv validation now enforces the prompt length limit.
- Empty model and effort options fail closed instead of falling back silently.
- Existing journals are no longer truncated merely by constructing a reader.
- Run directory allocation is atomic under concurrent starts.
- Top-level workflow failure cancels other in-flight agents.

## Initial implementation

The initial commits established the capability-restricted QuickJS runtime,
read-only `agent()`, asynchronous job pump, `parallel()`, `pipeline()`, locked
Codex argv, JSON Schema subset, mock execution, and versioned run artifacts.
