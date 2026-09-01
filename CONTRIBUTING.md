# Contributing

## Development environment

Use Python 3.12 and install the project in editable mode:

```text
py -3.12 -m pip install -e .
py -3.12 -m unittest discover -s tests -t . -v
```

Tests must not require a real Codex request. Use `--mock`, temporary directories
and temporary Git repositories. Never use the project repository itself as a
worktree test fixture.

## Change discipline

Keep a pull request focused on one coherent capability or hardening change.
State the permission boundary it affects, add a red regression test first, and
show the final full-suite result.

Changes must not:

- add `danger-full-access`, `--full-auto` or approval-policy flags;
- allow JavaScript to supply argv, sandbox or worktree paths;
- add arbitrary `-c` or `--config` forwarding;
- auto-apply, commit, merge, push, reset or delete user work;
- introduce Node as a second workflow runtime;
- enable QuickJS `set_time_limit` while Python callables are installed.

## Required verification

Before opening a pull request, run:

```text
python -m unittest discover -s tests -t . -v
python -m compileall -q workflow tests
python -m pip check
python -m workflow run examples/hello.js --mock --timeout-seconds 30
python -m workflow run examples/parallel-hello.js --mock --timeout-seconds 30
python -m workflow run examples/nested-parent.js --mock --args-file examples/nested-args.json --timeout-seconds 30
```

Also inspect a fresh `journal.jsonl` and confirm:

- ordinary agents use `-s read-only`;
- only host-authorized worktrees use `-s workspace-write`;
- exactly one allowed `model_reasoning_effort` `-c` is present;
- no forbidden approval or full-access token appears;
- cache hits contain no live argv and are marked `cache: true`.

## Style

Prefer small pure validators around security-sensitive values. Keep QuickJS
operations on the pump thread. Worker threads may execute agents, but must return
through queues rather than touching the QuickJS context.

Document user-visible changes in `CHANGELOG.md`. Do not commit generated `runs/`,
worktrees, caches, credentials or local editor settings.
