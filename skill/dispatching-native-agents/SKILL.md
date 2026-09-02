---
name: dispatching-native-agents
description: Use when a Codex session has at least two substantial, bounded, independent analysis, review, research, investigation, or implementation branches whose parallel execution materially improves coverage or latency; when the user asks to fan out, 派工, 多路, 并行查, or spawn native subagents; or for a deep, comprehensive, adversarial, multi-agent, repository-wide, or legacy Agent Fleet review. Legacy 4/6/8 labels request adaptive depth, not a fixed headcount. Do not use for a single trivial question, JavaScript workflow files, or `codex exec` children.
---

# Dispatching Native Agents

Root decomposes and adopts. Luna covers. Sol judges, rarely. Children are UI-visible native `spawn_agent` calls, never `codex exec`.

If native `spawn_agent` is unavailable in the current session, report the exact capability error and stop. Suggest enabling `[features] multi_agent = true` and restarting Codex only when the current host documents that remedy and the effective configuration shows it disabled. Do not change configuration without explicit authorization or fall back to CLI, `python -m workflow`, or a JavaScript host.

Read [references/patterns.md](references/patterns.md) for a pipeline, deep review, candidate-identity gate, or more than one fan-out wave.

## Four questions

Answer before every wave:

1. **How many distinct lenses?** Default one coverage agent per distinct evidence objective and method. Use Spark for a short, mechanical, read-only, easily checked branch; otherwise use Luna. Send **that branch** as Sol when the question itself is judgment, safety, hard-to-reverse, or a previous Luna on it already failed. Merge only assignments with materially the same scope, question, and method; static analysis and runtime reproduction are different methods. Usually run 2–8 useful coverage branches and split larger sets into waves. Ignore a legacy Fleet number rather than inventing lenses to match it.
2. **Fact, judgment, or choice?** A factual result Root can substantiate from primary evidence → 0 Sol. A coverage segment that reaches its applicable stop rule with 0 surviving claims → `completed-empty`, 0 refute Lunas, and 0 Sol; a branch that *is* a judgment and returns empty or off-scope still follows failure-packet escalation. A judgment-bearing conclusion after a Luna wave → 1 Sol gate on a merge packet. A branch that *is* the judgment can start as Sol, with no Luna wave. A genuine choice among designs → Sol panel of 2–3, never Luna judges.
3. **Barrier?** Independent items must not wait for the slowest sibling. `wait_agent` is an event wake, not a join-all. Join only to dedupe before spending Sol.
4. **Is this segment done?** The next segment may change technique (search → judge → write → review). Do not keep the same crew through every segment.

## Dispatch shape

Pick **1–2** per segment. These are Claude-style shapes, not exclusive product modes. Do not run the whole list. Do not revive 4/6/8 Fleet.

| Shape | Claude analogue | Use when | On Codex |
|---|---|---|---|
| Solo | root only | one useful branch, or coordination costs more than it saves | no spawn |
| Fan-out | `parallel()` | independent lenses; next expensive step needs the set | spawn together; join **only** to dedupe before Sol |
| Pipeline | `pipeline()` (no barrier) | same items pass stages; siblings need not wait | when one item returns, spawn *its* next item-local non-Sol stage; packet stages wait for merge |
| Loop | loop-until-dry | unknown how many findings | new lens each wave; 2 consecutive dry waves finish |
| Segments | sequential workflows | understand → design → write → review | new children each segment; writer idle before review |
| Panel | judge panel | choose among designs | 2–3 Sol independently propose from named angles; after all are idle, Root grafts, then an optional serial Sol reviews the synthesis |
| Write | writer segment | user asked to implement | one writer by default; when 2+ independent writers must run together and the workspace has an applicable worktree contract, route each through an isolated worktree |

There is no nested `workflow()`. Children must not spawn. Root simulates control flow; `wait_agent` is an event wake, not a join-all.

### Pipeline wait

`wait_agent` has no child-ID target list. When Root is idle, wait once for an agent event, process whichever item updated, and dispatch that item's next item-local non-Sol stage immediately when needed. A packet refute panel is merge-wide, not item-local: start it only after the coverage segment is terminal and Root has a non-empty, deduplicated merge packet. Do not delay an independent completed item merely to wait for its siblings.

See [references/patterns.md](references/patterns.md) for the detailed recipe.

## Roles

| Route | `agent_type` | Default use | Not a lock |
|---|---|---|---|
| Luna | `luna` | Coverage: facts, current state, evidence, refute a *given* claim | Skip Luna when **this branch** is already a judgment, safety, or hard-to-reverse question |
| Sol | `sol` | Gate, design choice, default writing, hard-to-reverse work; also any upgraded branch | Not cheap labor; do not rescan; do not majority-vote Luna |
| Spark | `spark` | Short, mechanical, read-only, easily verified | Never a writer or a judge; when Root selected Spark by default and it is unavailable or insufficient, transfer only the unfinished work once to Luna in a bounded remainder packet; a user-fixed Spark route never falls back automatically |
| Custom | `default` | User-named model/effort that is not a complete Luna/Sol/Spark preset | Do not relabel Custom as Luna or Sol |
| Root | parent | Split, spawn, merge, adopt | Dump the whole request on one child |

Default coverage is still Luna, and Sol is still scarce. The lock is gone: pick the route **per branch**. The user's explicit route, model, and effort win when mutually compatible. If the user names a fixed Luna/Sol/Spark route with incompatible model/effort, stop and ask which selection to preserve; never silently change the route or discard an override.

Spawn with `fork_turns=none`. With no user override, use the selected route's `agent_type` and do not also pass model/effort — the role file is the contract. A Root-decided route upgrade changes only `agent_type`; it is not a model/effort override. When the user names model or effort without a fixed route, use Custom (`agent_type=default`) and pass the named values. When both values exactly match a fixed role's configured model and reasoning effort, use that `agent_type` and omit model/effort. Do not pass model/effort alongside a fixed Luna, Sol, or Spark role. Resolve declared model and reasoning effort from the current `spawn_agent` contract; report any role-file tier as configured, not runtime-proven. These declarations are not runtime receipts. Put every needed fact in the child prompt.

### Child return shape

Every child prompt must require this Markdown return shape; do not require JSON:

```text
CLAIMS:
1. <one-sentence claim>
   evidence: <path / quote / command / snapshot-id>
   status: supported | inferred | UNVERIFIED
UNCOVERED: <in-scope work not examined>
NOT_IN_SCOPE: <work explicitly not done>
```

A pointer without a bounded payload is `UNVERIFIED`. Root builds merge packets, refute packets, and Sol packets only from numbered `CLAIMS`; do not infer claims from prose. Child numbers are local to that return. After merge and dedupe, Root assigns stable `C-001`, `C-002`, ... IDs and freezes each claim's meaning, scope, and existing evidence provenance. New evidence may append to the same ID; a semantic rewrite, merge, or split creates a new ID. The child status `supported | inferred | UNVERIFIED` describes evidence support only; Root separately records `ADOPT | REJECT | UNKNOWN | contested` in the transcript-local `seen` set so a later wave does not silently revive the claim. Every stable ID must end as `ADOPT`, evidence-backed `REJECT`, or `UNKNOWN`; resolve remaining `contested` or `UNVERIFIED` material claims to `UNKNOWN` when evidence cannot settle them. Every route may return `CLAIMS: none` only after completing the assigned in-scope work and finding no claim; keep `UNCOVERED` and `NOT_IN_SCOPE`. Material in-scope `UNCOVERED` keeps the branch and overall coverage incomplete: preserve any numbered claims, then either dispatch only the bounded remainder as a planned branch or finish that remainder as `UNKNOWN`; it never supports `completed-empty`. Sol may add `ADOPT | REJECT | UNKNOWN` and reasons to the same shape. A missing, malformed, empty, or off-scope return is a failure result, never `completed-empty`. Use at most one `followup_task` only to supply concrete input or the return shape Root omitted, never to request another search; otherwise follow the failure-packet path.

Before every `spawn_agent`:

```text
Subagent: <branch> -> <route> (agent_type=<luna|sol|spark|default>, model=<declared>, effort=<declared>, tier=<value|UNKNOWN> [configured], override=<none|user>, runtime=UNKNOWN, fork=none)
```

## Caps

Guidance, not a lookup table. Typically use 2–8 live coverage agents across Spark and Luna. When more useful lenses exist, batch the next wave rather than refuse or exceed current capacity. Normally one live Sol; the sole exception is a 2–3 Sol panel for a genuine design choice.

A bounded one-wave coverage segment reaches its stop rule when every planned branch has a final accounting status. Closing one wave does not complete the whole coverage workflow: a later wave already identified remains planned until it runs or Root accounts for it as dropped or `UNKNOWN` with a reason. Any failed, interrupted, `UNKNOWN`, or materially dropped coverage branch prevents `completed-empty` and makes coverage incomplete. A material claim survives until Root rejects it with evidence; adopted, `UNVERIFIED`, `contested`, and `UNKNOWN` claims therefore prevent `completed-empty`. For repeated search — a loop or a user target `N` — require `N` to be a positive integer when present, and stop at the first of: adopted, deduplicated claims reach `N`; 2 consecutive waves produce no new unique claims; or the third search wave completes. Without a user-supplied `N`, do not invent one. A zero-claim wave counts as dry; it does not by itself mean `completed-empty`. The third wave closes the current search segment; changing lens does not reset the count, and a new segment must not exist merely to reset the cap. When `N` is present and a stop rule fires below it, report found/target/dropped and incomplete coverage; 0 surviving claims becomes `completed-empty` only when the eligibility rule above holds, while some surviving claims become completed with coverage explicitly incomplete. `N` does not change Luna/Sol caps or authorize more Sol. If work is capped while still productive, say what was dropped.

## Candidate identity gate

Before the first evidence wave, Root records a scoped candidate snapshot: repository identity, `HEAD`, in-scope paths, and per-path state. Add a content fingerprint for every dirty or untracked in-scope file. `as-of` names this snapshot; a clock alone is not candidate identity. Bind each item-local chain to its snapshot.

Always recheck the same scoped identity immediately after Root merges coverage, including a pure-factual or `completed-empty` path; when a packet refute panel or Sol gate follows, complete the recheck before dispatch. Recheck it once more immediately before the final answer. In-scope drift at either recheck makes the affected claim stale or `UNKNOWN`; never validate an old claim against a new candidate. Out-of-scope drift does not invalidate the packet. After each writer becomes idle, take its post-write snapshot; start the new review segment only after all writers are idle. Skip Git-specific fields for a non-Git target, but retain an equivalent scoped source identity when available. Detailed examples are in [references/patterns.md](references/patterns.md).

## Sol gate

Do not spawn Sol without a Root-written packet visible in the parent transcript immediately before dispatch: scope, exclusions, decision context, numbered claims, bounded evidence payloads with provenance pointers and snapshot / as-of identity, and the questions Sol must answer (unsupported, missing class, severity wrong). For a direct Sol judgment or design branch with no prior coverage claims, Root supplies at least one numbered decision proposition plus bounded primary evidence or user constraints; an empty proposition is not a packet. A pointer without a bounded payload is `UNVERIFIED`.

Before spending Sol, merge the surviving claims from the same decision segment into one packet and use one serial Sol. A coverage segment becomes `completed-empty` only after reaching its applicable stop rule with 0 surviving claims; spawn neither refute Lunas nor a Sol gate. A completeness critic may ask which class was missed without reviewing the empty packet. Give it only the coverage packet, the named in-scope source inventory, and `UNCOVERED`; it checks missing modality, a material claim that remains unverified, and unread in-scope source without rescanning the repository. If it returns an evidence-backed numbered claim, Root replaces the empty conclusion with a non-empty merge packet and applies the normal refute/Sol gate. If it instead identifies material unread in-scope evidence, Root withdraws `completed-empty`, marks coverage incomplete, and accounts for the unread branch as `UNKNOWN`. Otherwise `completed-empty` stands. The critic does not start another search wave or reset a search cap.

Split only genuinely independent conclusions or a genuine design panel. A design panel is only for an actual choice and is skipped when the user already selected a design. Give 2–3 Sol distinct proposal angles; they do not see, review, or vote on each other's proposals. After every panelist is idle, Root writes a synthesis packet naming the base proposal, grafted parts, exclusions, and unresolved questions; if judgment remains, one new serial Sol reviews that synthesis.

Root opening evidence does not waive the gate. Skip Sol only when the remaining result is purely factual, Root directly verified the primary evidence sufficient for every material factual conclusion, and no judgment, completeness, severity, or design question remains.

For a non-empty merge packet involving externally trusted judgment, safety, or hard-to-reverse work, Root may send the same numbered packet in one wave to 2–3 Luna refuters. Give each a distinct question: citation support, payload freshness/snapshot completeness, or severity/category. They use `fork_turns=none`, inspect only packet payloads, do not rescan, and count toward Luna caps. Drop a claim only when a refuter shows that the cited packet evidence does not support it; vague doubt or unsupported disagreement marks it `contested` for Sol. Never use a Luna majority vote. See [references/patterns.md](references/patterns.md).

Root must adopt, reject-with-evidence, or mark `UNKNOWN` every material Sol issue. One reproduced hard finding is not outvoted.

## Escalation and lifecycle

Never replay the same failed Luna assignment to another Luna. A packet refute panel is allowed because each member asks a distinct verification question over the same bounded evidence.

A missing, malformed, empty, or off-scope child return follows the return-shape failure rule above. After a Luna failure, Root writes a failure packet from attempted scope, evidence or commands, gaps, and questions; escalate to one Sol only when Sol can judge that packet without rescanning the repository, otherwise Root handles the branch or marks it `UNKNOWN`. If a direct Sol still fails after any permitted input/shape follow-up, Root owns the failure packet and either decides from its existing evidence or marks the branch `UNKNOWN`; do not replay, down-route, or ask Sol to rescan. "Try harder" is a forbidden replay.

Nested spawn is forbidden. Children do not message peers. Within one unresolved chain, never down-route after Sol. A later segment may use a new route; implementation review may start fresh Lunas only after the writer is idle. Never `codex exec`. Never 4/6/8 tables, fixed Luna/Sol ratios, or mandatory discovery→challenge→reproduction.

User cancellation stops new dispatch, follow-up, and downstream segments immediately. Request interruption of live children only when still needed for cancellation; an unconfirmed final state remains `UNKNOWN`.

Optional last step only when risk warrants: one completeness critic; see [references/patterns.md](references/patterns.md). Do not turn it into a mandatory fourth search wave.

Before the final answer, account for every planned material branch as completed, `completed-empty`, failed, interrupted, dropped with a stated reason, or `UNKNOWN`. Non-barrier scheduling never permits silent omission.

A slow or silent child is not automatically stuck. After that child's first timeout, Root may send at most one non-interrupting progress question. Keep waiting for a healthy child; silence alone never authorizes replay, reroute, or interruption. While a child is active, Root may do other work but must not repeat that child's scope, question, and method. If a live child is duplicate, clearly off-scope, or no longer needed, use `interrupt_agent` when available to stop its current turn; interruption does not close the agent or guarantee capacity. On a spawn-capacity failure, call `list_agents` once, then batch after existing agents reach a terminal state or drop the branch and disclose it. Never retry-loop.

## Writes

Read-only unless the user clearly asked to implement. Use one active writer, including Root, when the work is serial or has one write set; the default child writer is Sol. Luna writes only when the user named Luna. Root gives every writer a decided plan, closed file scope, acceptance checks, and applicable workspace rules. Review starts only after all writers are idle. Never parallel-write the same files.

An implementation request may route directly to parallel worktrees without another permission question when all of these are true: the target is one Git repository; 2+ writers must run concurrently; their `owned_targets` are mutually exclusive; and applicable workspace instructions already define worktree creation, dispatch, integration, and cleanup boundaries. For work under `D:\codex`, read and follow `D:\codex\docs\agent-workflows\worktree-parallel-dispatch.md` as the single source of truth. Outside that workspace, use an equivalent applicable contract or fall back to one writer.

Native spawn does not hard-bind a child to a directory. Root creates each worktree, names its absolute path and closed `owned_targets` in the prompt, and treats the result as a candidate patch. Each writer reports status and untracked files; Root rejects out-of-scope writes, verifies the diff, and applies accepted changes as patches to the target worktree rather than merging the writer branch. A writer does not run Git write commands. If the target worktree is dirty, disclose that a new worktree starts from `HEAD` without those changes; do not parallelize a branch that silently depends on them. Non-Git targets, overlapping write sets, or an ambiguous baseline use one writer. Never run `git init` to unlock parallelism. Worktree cleanup remains a separate scoped action.

This skill grants no extra authority to commit, push, merge, checkout, create or remove a worktree, change sandbox or approval policy, or ignore applicable `AGENTS.md` instructions. The current user request supplies authority; workspace rules constrain the safe route, and this skill chooses within both.

## Legacy request mapping

Treat `Agent Fleet`, `Agent Fleet 4/6/8`, and equivalent old review language as a request for this skill's adaptive deep review. Ignore the legacy number; distinct evidence lenses and current capacity determine the wave. Never create duplicate work to fill a preset. `$dynamic-workflow` is not an alias: it targets that separate skill only while installed. After retirement, direct requests for `$dynamic-workflow`, Managed Workflow, or Worktree Writer v2 are unavailable; report the retired capability and do not silently downgrade it to this skill's generic dispatch or worktree route.

## Common mistakes

- CLI or JS-host fallback when native spawn is unavailable
- Delaying an independent completed item by treating a pipeline as join-all
- Sol without a transcript-visible packet
- Skipping Sol merely because Root opened the evidence
- Replaying the same Luna search assignment
- Finalizing with an unaccounted material branch
- Treating headcount as confidence
- Sol panel on fact-finding
- Parallel writers without disjoint `owned_targets` and an applicable worktree contract
- Treating a worktree as a hard child cwd sandbox instead of verifying its candidate patch
- Sending a judgment/safety branch to Luna only because it looks like search
- Relabeling a Custom override as Luna or Sol
- Treating dispatch shapes as exclusive product modes (old Fleet)
- Inventing a worktree protocol when the workspace has none
- Applying 4/6/8 Fleet tables when this skill owns the job
- Claiming complete coverage after skipping a warranted completeness critic
