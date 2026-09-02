---
name: dispatching-native-agents
description: Use when a Codex session has at least two substantial, bounded, independent analysis, review, research, or investigation branches whose parallel execution materially improves coverage or latency, or when the user explicitly asks to fan out, 派工, 多路, 并行查, or spawn native subagents. Do not use for a single trivial question, JavaScript workflow files, `codex exec` children, or an explicit 4/6/8 Agent Fleet request.
---

# Dispatching Native Agents

Root decomposes and adopts. Luna covers. Sol judges, rarely. Children are UI-visible native `spawn_agent` calls, never `codex exec`.

If native `spawn_agent` is unavailable in the current session, report the exact capability error and stop. Suggest enabling `[features] multi_agent = true` and restarting Codex only when the current host documents that remedy and the effective configuration shows it disabled. Do not change configuration without explicit authorization or fall back to CLI, `python -m workflow`, or a JavaScript host.

Read [references/patterns.md](references/patterns.md) when using a pipeline or more than one fan-out wave.

## Four questions

Answer before every wave:

1. **How many distinct lenses?** Default one Luna per distinct evidence objective and method. Send **that branch** as Sol when the question itself is judgment, safety, hard-to-reverse, or a previous Luna on it already failed. Merge only assignments with materially the same scope, question, and method; static analysis and runtime reproduction are different methods.
2. **Fact, judgment, or choice?** A factual result Root can substantiate from primary evidence → 0 Sol. A judgment-bearing conclusion after a Luna wave → 1 Sol gate on a merge packet. A branch that *is* the judgment can start as Sol, with no Luna wave. A genuine choice among designs → Sol panel of 2–3, never Luna judges.
3. **Barrier?** Independent items must not wait for the slowest sibling. `wait_agent` is an event wake, not a join-all. Join only to dedupe before spending Sol.
4. **Is this segment done?** The next segment may change technique (search → judge → write → review). Do not keep the same crew through every segment.

## Dispatch shape

Pick **1–2** per segment. These are Claude-style shapes, not exclusive product modes. Do not run the whole list. Do not revive 4/6/8 Fleet.

| Shape | Claude analogue | Use when | On Codex |
|---|---|---|---|
| Solo | root only | one useful branch, or coordination costs more than it saves | no spawn |
| Fan-out | `parallel()` | independent lenses; next expensive step needs the set | spawn together; join **only** to dedupe before Sol |
| Pipeline | `pipeline()` (no barrier) | same items pass stages; siblings need not wait | when one item returns, spawn *its* next non-Sol stage |
| Loop | loop-until-dry | unknown how many findings | new lens each wave; 2 consecutive dry waves finish |
| Segments | sequential workflows | understand → design → write → review | new children each segment; writer idle before review |
| Panel | judge panel | choose among designs | 2–3 Sol, never Luna judges |
| Write | no native Codex worktree/isolation equivalent | user asked to implement | **one** writer (default Sol). This skill cannot bind a child to another directory. If the user wants parallel writers, stop and state that a separately selected worktree workflow is required |

There is no nested `workflow()`. Children must not spawn. Root simulates control flow; `wait_agent` is an event wake, not a join-all.

### Pipeline wait

`wait_agent` has no child-ID target list. When Root is idle, wait once for an agent event, process whichever item updated, and dispatch that item's next non-Sol stage immediately when needed. Do not delay an independent completed item merely to wait for its siblings. Use a full barrier only when the results must be merged and deduplicated before spending Sol.

See [references/patterns.md](references/patterns.md) for the detailed recipe.

## Roles

| Route | `agent_type` | Default use | Not a lock |
|---|---|---|---|
| Luna | `luna` | Coverage: facts, current state, evidence, refute a *given* claim | Skip Luna when **this branch** is already a judgment, safety, or hard-to-reverse question |
| Sol | `sol` | Gate, design choice, default writing, hard-to-reverse work; also any upgraded branch | Not cheap labor; do not rescan; do not majority-vote Luna |
| Spark | `spark` | Optional: short, mechanical, read-only, easily verified | Never a writer or a judge |
| Custom | `default` | User-named model/effort that is not a complete Luna/Sol/Spark preset | Do not relabel Custom as Luna or Sol |
| Root | parent | Split, spawn, merge, adopt | Dump the whole request on one child |

Default coverage is still Luna, and Sol is still scarce. The lock is gone: pick the route **per branch**. The user's explicit route, model, and effort win when mutually compatible. If the user names a fixed Luna/Sol/Spark route with incompatible model/effort, stop and ask which selection to preserve; never silently change the route or discard an override.

Spawn with `fork_turns=none`. With no user override, use the selected route's `agent_type` and do not also pass model/effort — the role file is the contract. A Root-decided route upgrade changes only `agent_type`; it is not a model/effort override. When the user names model or effort without a fixed route, use Custom (`agent_type=default`) and pass the named values. When both values exactly match a fixed role's configured model and reasoning effort, use that `agent_type` and omit model/effort. Do not pass model/effort alongside a fixed Luna, Sol, or Spark role. Resolve declared model and reasoning effort from the current `spawn_agent` contract; report any role-file tier as configured, not runtime-proven. These declarations are not runtime receipts. Put every needed fact in the child prompt.

Before every `spawn_agent`:

```text
Subagent: <branch> -> <route> (agent_type=<luna|sol|spark|default>, model=<declared>, effort=<declared>, tier=<value|UNKNOWN> [configured], override=<none|user>, runtime=UNKNOWN, fork=none)
```

## Caps

Guidance, not a lookup table. Typically 2–6 live Luna; around 8, **batch the next wave** rather than refuse. Normally one live Sol; the sole exception is a 2–3 Sol panel for a genuine design choice. After 3 search waves in one segment, checkpoint and change lens or segment; only 2 consecutive waves with no new unique claims establish dry completion. If work is capped while still productive, mark coverage incomplete and say what was dropped.

## Sol gate

Do not spawn Sol without a Root-written packet visible in the parent transcript immediately before dispatch: scope, exclusions, decision context, numbered claims, bounded evidence payloads with provenance pointers and snapshot / as-of identity, and the questions Sol must answer (unsupported, missing class, severity wrong). A pointer without a bounded payload is `UNVERIFIED`.

Before spending Sol, merge the surviving claims from the same decision segment into one packet and use one serial Sol. Split only genuinely independent conclusions or a genuine design panel.

Root opening evidence does not waive the gate. Skip Sol only when the remaining result is purely factual, Root directly verified the primary evidence sufficient for every material factual conclusion, and no judgment, completeness, severity, or design question remains.

A refuter Luna is optional when risk warrants it. It receives the packet and may inspect only its cited evidence; it does not rescan the repository. A pointer-only claim remains `UNVERIFIED`.

Root must adopt, reject-with-evidence, or mark `UNKNOWN` every material Sol issue. One reproduced hard finding is not outvoted.

## Escalation and lifecycle

Never replay the same failed Luna assignment to another Luna. A packet-only refuter is allowed because it asks a different verification question over bounded evidence.

For an empty or off-scope Luna, use at most one `followup_task`, only to supply a concrete input Root forgot. If it still fails, Root writes a failure packet from attempted scope, evidence or commands, gaps, and questions. Escalate to one Sol only when Sol can judge that packet without rescanning the repository; otherwise Root handles the branch or marks it `UNKNOWN`. "Try harder" is a forbidden replay.

Nested spawn is forbidden. Children do not message peers. Within one unresolved chain, never down-route after Sol. A later segment may use a new route; implementation review may start fresh Lunas only after the writer is idle. Never `codex exec`. Never 4/6/8 tables, fixed Luna/Sol ratios, or mandatory discovery→challenge→reproduction.

User cancellation stops new dispatch, follow-up, and downstream segments immediately. Request interruption of live children only when still needed for cancellation; an unconfirmed final state remains `UNKNOWN`.

Optional last step only when risk warrants: one completeness critic; see [references/patterns.md](references/patterns.md). Do not turn it into a mandatory fourth search wave.

Before the final answer, account for every planned material branch as completed, failed, interrupted, dropped with a stated reason, or `UNKNOWN`. Non-barrier scheduling never permits silent omission.

A slow or silent child is not automatically stuck. If a live child is duplicate, clearly off-scope, or no longer needed, use `interrupt_agent` when available to stop its current turn; interruption does not close the agent or guarantee capacity. On a spawn-capacity failure, call `list_agents` once, then batch after existing agents reach a terminal state or drop the branch and disclose it. Never retry-loop.

## Writes

Read-only unless the user clearly asked to implement. Then at most one active writer, including Root; the default writer is Sol. Luna writes only when the user named Luna. Root gives the writer a decided plan, file scope, acceptance tests, and applicable workspace rules. Review starts only after the writer is idle. Do not parallel-write the same files.

If the user explicitly wants **parallel file writes**, stop. Do not spawn two writers. State that this skill cannot provide the required isolation; continue only if the user separately selects an available worktree workflow. This skill never creates worktrees.

This skill grants no extra authority to commit, push, merge, checkout, create a worktree, change sandbox or approval policy, or ignore applicable `AGENTS.md` instructions.

## Collision with Dynamic Workflow

If both this skill and the old `dynamic-workflow` skill are loaded: this skill owns intelligent native dispatch (lenses, pipeline, loop-until-dry, scarce Sol). Use the old skill only when the user names Agent Fleet, 4/6/8, or `$dynamic-workflow`. Do not steal a named Fleet request, and do not apply 4/6/8 tables to ordinary fan-out.

## Common mistakes

- CLI or JS-host fallback when native spawn is unavailable
- Delaying an independent completed item by treating a pipeline as join-all
- Sol without a transcript-visible packet
- Skipping Sol merely because Root opened the evidence
- Replaying the same Luna search assignment
- Finalizing with an unaccounted material branch
- Treating headcount as confidence
- Sol panel on fact-finding
- Parallel writers or review before the writer is idle
- Sending a judgment/safety branch to Luna only because it looks like search
- Relabeling a Custom override as Luna or Sol
- Treating dispatch shapes as exclusive product modes (old Fleet)
- Spawning two writers after this skill has stopped for missing worktree isolation
- Applying 4/6/8 Fleet tables when this skill owns the job
- Claiming complete coverage after skipping a warranted completeness critic
