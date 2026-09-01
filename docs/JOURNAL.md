# Journal and Run Directory

Each invocation creates a new run directory. Existing runs are never overwritten
by resume.

```text
<runs-root>/<YYYYMMDD-HHMMSS>-<script-stem>[-N]/
  script.js
  journal.jsonl
  agents/
    000-<label>/
      argv.json
      schema.json      # only when requested
      last.txt
      stdout.log
      stderr.log
```

`journal.jsonl` is UTF-8 JSON Lines. Every non-empty line must contain one JSON
object. Writers append one complete line under a process-local lock and flush it
immediately. `JOURNAL_VERSION` is currently `1` and is recorded on
`run.started`.

A force-killed runtime can leave a valid prefix without `run.finished`. Such a
run is incomplete and must not be treated as successful merely because earlier
agent events exist.

## Event order

The first event is `run.started`. `phase`, `workflow`, `agent`, and `log` events
follow as the dynamic script runs. The final event is `run.finished` when the
runtime exits normally or reports a handled workflow error.
## `run.started`

```json
{
  "event": "run.started",
  "journal_version": 1,
  "script": "C:/absolute/workflow.js",
  "workdir": "C:/absolute/repository",
  "mock": true,
  "args": {"q": 7},
  "budget_tokens": null,
  "max_agents": 1000,
  "resume_from": null
}
```

`args` is part of resume compatibility. `budget_tokens` is an advisory target;
`max_agents` is the hard live-execution limit. `resume_from` names the source run
when prefix caching is enabled.

## `phase`, `workflow`, and `log`

```json
{"event":"phase","title":"Scan"}
{"event":"workflow","script":"C:/absolute/child.js","args":{"q":7}}
{"event":"log","message":"started"}
```

A workflow event records a child registration, not a separate run directory.
## Live agent success

```json
{
  "event": "agent",
  "index": 0,
  "label": "scan",
  "prompt": "inspect repository",
  "phase": "Scan",
  "identity": "{...canonical JSON...}",
  "cache": false,
  "requested_opts": {"label": "scan"},
  "opts": {
    "label": "scan",
    "schema": null,
    "model": null,
    "effort": "medium",
    "isolation": null
  },
  "argv": ["codex", "exec", "-s", "read-only", "..."],
  "ok": true,
  "return": "result text",
  "exit_code": 0
}
```

A worktree agent also records `worktree` after successful creation. The `argv`
field is the exact validated argument list sent to the executor.
## Cache hit and failure

A cache hit has `"cache": true`, returns the old value, and contains no live
argv or agent artifact slot. Its schema is revalidated before reuse.

A failed registration or execution has `"ok": false`, an `error`, and a `stage`.
Current stages include `options`, `limit`, `slot`, `schema`, `argv`, `artifacts`,
`cache`, `worktree`, and `executor`. Fields accumulated before the failure remain
in the record for diagnosis.

Agent indices are assigned at JavaScript registration time. Events may be
appended in completion order, so readers that need logical call order must sort
agent events by `index`.

## `run.finished`

```json
{"event":"run.finished","ok":true,"agents":3}
```

On handled failure, `ok` is false and `error` is present. `agents` counts all
registered calls, including cache hits and preflight failures; it is not the
number of live Codex processes.

## Resume and privacy

Resume consumes only the consecutive successful agent prefix beginning at index
zero. The first missing, failed, or mismatched record ends caching for the rest
of the new run. Journal files contain full prompts, options, argv, results, and
errors. Treat the entire run directory as sensitive and apply an explicit local
retention policy.
