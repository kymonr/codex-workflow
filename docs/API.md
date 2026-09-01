# API Reference

Codex Workflow executes one JavaScript file inside embedded QuickJS. The script
may use top-level `await`; line-leading `export const` is rewritten to `const`.
Other JavaScript module export forms are rejected.

The public JavaScript surface is intentionally small. Scripts cannot construct
Codex argv, select approval policy, choose arbitrary sandbox modes, or provide a
worktree path.

## `agent(prompt, opts?)`

Starts one Codex agent and immediately returns a Promise.

- `prompt`: non-empty string, at most 24,000 characters, not beginning with `-`.
- `opts.label`: optional `[A-Za-z0-9._-]{1,80}` string.
- `opts.schema`: optional supported JSON Schema object.
- `opts.model`: optional non-empty model name accepted by the host validator.
- `opts.effort`: optional `low`, `medium`, `high`, or `xhigh`.
- `opts.isolation`: optional literal string `"worktree"`.

Without a schema, the Promise resolves to the final text. With a schema, the
final message is parsed as JSON and validated before the Promise resolves.
Failures reject the Promise and are also recorded in `journal.jsonl`.
## `parallel(thunks)`

Accepts an array of at most 4,096 functions and starts them concurrently. The
result Promise resolves to an equally sized array in input order. A thunk that
throws or returns a rejected Promise contributes `null`; sibling thunks continue.
Invalid input rejects the workflow rather than truncating the array.

## `pipeline(items, ...stages)`

Accepts at most 4,096 input items. Each stage is called as
`stage(previous, originalItem, index)`. Every item owns an independent stage
chain, so one item may enter a later stage while another remains in an earlier
stage. There is no cross-item stage barrier. If a stage fails, that item becomes
`null` and skips its remaining stages.

## `phase(title)`

Sets the current journal phase. `title` must be a non-empty string of at most 80
characters. The phase is captured when `agent()` is registered, not when its
worker begins. Calling `phase()` does not wait for agents or change scheduling.

## `log(message)`

Converts `message` to a string and appends a `log` event. It does not write to
the target repository.
## `args`

Contains the parsed JSON supplied by `--args` or `--args-file`; the default is
`{}`. Any JSON object, array, scalar, or `null` is accepted. Nested child scripts
receive their own second argument and do not inherit the parent's lexical value.

## `budget`

`budget.total` is the positive integer passed through `--budget-tokens`, or
`null` when no target was configured. Until reliable Codex usage data exists,
`budget.spent()` returns `0`; `budget.remaining()` returns `Infinity` without a
target and otherwise returns the configured total. This is not a hard token
ceiling. `--max-agents` and the runtime timeout are the available hard stops.

## `workflow({scriptPath}, childArgs?)`

Runs one child script in the same QuickJS job pump. `scriptPath` is resolved
relative to the parent script and must remain inside `--cd`. The child receives
`childArgs`, defaulting to `{}`, and shares the parent journal, agent index,
concurrency limit, live-agent limit, phase state, and resume cursor.

Only one nesting level is allowed. A child calling `workflow()` fails with an
error containing `nested workflow`. A successful child resolves to `null`.
## CLI

```text
codex-workflow run <script>
  [--mock]
  [--runs-root <path>]
  [--cd <workdir>]
  [-m <model>]
  [--effort low|medium|high|xhigh]
  [--args <json> | --args-file <path>]
  [--budget-tokens <positive-int>]
  [--max-agents <1..1000>]
  [--resume-from <old-run-dir>]
  [--timeout-seconds <positive-finite-number>]
```

`python -m workflow` exposes the same CLI. The normal entry point supervises a
separate runtime process. `--mock` avoids real Codex requests while preserving
validation, scheduling, artifacts, argv construction, schema handling, resume,
and worktree creation where requested.

## Fixed limits

- QuickJS heap: 32 MiB.
- Script source: 256,000 characters.
- Agent payload: 128,000 characters.
- Live agent calls: configurable from 1 to 1,000.
- `parallel()` and `pipeline()` arrays: 4,096 entries.
- Child workflow calls: 4,096 registrations, with nesting depth limited to one.
