---
name: dispatching-native-agents
description: Use when a Codex session has at least two substantial, bounded, independent analysis, review, research, or investigation branches whose parallel execution materially improves coverage or latency; when the user asks to fan out, 派工, 多路, 并行查, spawn native subagents, or parallelize implementation; or for a deep, comprehensive, adversarial, multi-agent, repository-wide, or legacy Agent Fleet review. Legacy 4/6/8 labels request adaptive depth, not a fixed headcount. Do not use for a single trivial question, JavaScript workflow files, or `codex exec` children.
---

# Dispatching Native Agents

Root decomposes and adopts. Luna covers. Sol judges selectively. Children are UI-visible native `spawn_agent` calls, never `codex exec`.

If native `spawn_agent` is unavailable in the current session, report the exact capability error and stop. Suggest enabling `[features] multi_agent = true` and restarting Codex only when the current host documents that remedy and the effective configuration shows it disabled. Do not change configuration without explicit authorization or fall back to CLI, `python -m workflow`, or a JavaScript host.

Read [references/patterns.md](references/patterns.md) for a pipeline, deep review, candidate-identity gate, or more than one fan-out wave.

## Four questions

Answer before every wave:

1. **How many distinct lenses?** Default one coverage agent per distinct evidence objective and method. Use Spark for a short, mechanical, read-only, easily checked branch; otherwise use Luna. Send **that branch** as Sol when the question itself is judgment, safety, hard-to-reverse, or a previous Luna on it already failed. Merge only assignments with materially the same scope, question, and method; static analysis and runtime reproduction are different methods. Usually run 2–8 useful coverage branches and split larger sets into waves. Ignore a legacy Fleet number rather than inventing lenses to match it.
2. **Fact, judgment, or choice?** A factual result Root can substantiate from primary evidence → 0 refuters and 0 Sol. A coverage segment that reaches its stop rule without ever finding a claim → `completed-empty`, 0 refuters, and 0 Sol; claims rejected by adversarial vote are not `completed-empty`. After Root checks a material claim against its cited evidence, trigger item-local adversarial refute when this is a deep/adversarial/comprehensive/multi-agent/repository-wide/legacy Fleet review or the claim needs Sol, safety, hard-to-reverse, or externally trusted judgment. An evidence-backed refute majority may reject it; `uncertain` is not a vote. After coverage stops and every assigned refuter reaches a terminal accounting state, distinct surviving judgment claims may enter independent Sol gates in parallel. A branch that *is* the judgment can start as Sol from a bounded proposition packet, with no search wave. A genuine design choice uses Sol proposals and scoring, never design votes.
3. **Barrier?** Independent items must not wait for the slowest sibling. `wait_agent` is an event wake, not a join-all. Item-local refute starts as soon as Root checks that claim; wait for coverage to reach its stop rule and every assigned refuter, including queued refuters, to reach a terminal accounting state only before candidate recheck, dedupe, stable IDs, and Sol gates.
4. **Is this segment done?** The next segment may change technique (search → judge → write → review). Do not keep the same crew through every segment.

## Dispatch shape

Pick **1–2** per segment. These are Claude-style shapes, not exclusive product modes. Do not run the whole list. Do not revive 4/6/8 Fleet.

| Shape | Claude analogue | Use when | On Codex |
|---|---|---|---|
| Solo | root only | one useful branch, or coordination costs more than it saves | no spawn |
| Fan-out | `parallel()` | independent lenses; next expensive step needs the set | spawn together; join **only** to dedupe before Sol |
| Pipeline | `pipeline()` (no barrier) | same items pass stages; siblings need not wait | after Root checks a returned claim, start its triggered item-local refute immediately; after coverage stops and refuters finish, dedupe and run independent Sol gates in parallel |
| Loop | loop-until-dry | unknown how many findings | new lens each wave; 2 consecutive dry waves finish |
| Segments | sequential workflows | understand → design → write → review | new children each segment; writer idle before review |
| Panel | judge panel | choose among designs | 2–3 Sol propose from named angles; 2–3 new Sol score every proposal; Root takes the highest score as the base and grafts named parts; one new Sol breaks a tie |
| Write | writer segment | user asked to implement | one writer by default; only when the user explicitly requests parallel implementation and 2+ independent writers must run together, use the applicable worktree contract to isolate each writer |

There is no nested `workflow()`. Children must not spawn. Root simulates control flow; `wait_agent` is an event wake, not a join-all.

### Pipeline wait

`wait_agent` has no child-ID target list. When Root is idle, wait once for an agent event, process whichever item updated, check each claim against its citation, and dispatch any triggered item-local adversarial refute immediately while sibling finders continue. Sol gates wait until coverage reaches its stop rule and every assigned refuter, including queued refuters, reaches a terminal accounting state; Root then rechecks candidate identity, deduplicates, and assigns stable IDs. Do not delay an independent completed item merely to wait for its siblings.

See [references/patterns.md](references/patterns.md) for the detailed recipe.

## Roles

| Route | `agent_type` | Default use | Not a lock |
|---|---|---|---|
| Luna | `luna` | Coverage: facts, current state, evidence, refute a *given* claim | Skip Luna when **this branch** is already a judgment, safety, or hard-to-reverse question |
| Sol | `sol` | Judgment, design, scoring, deep-review gates, default writing, and hard-to-reverse work | May run in parallel for independent conclusions or panel seats; do not rescan or serve as search coverage; majority refute may drop a claim only before its Sol gate, and a Sol-adopted claim is not later outvoted |
| Spark | `spark` | Short, mechanical, read-only, easily verified | Never a writer or a judge; when Root selected Spark by default and it is unavailable or insufficient, transfer only the unfinished work once to Luna in a bounded remainder packet; a user-fixed Spark route never falls back automatically |
| Custom | `default` | User-named model/effort that is not a complete Luna/Sol/Spark preset | Do not relabel Custom as Luna or Sol |
| Root | parent | Split, spawn, merge, adopt | Dump the whole request on one child |

Default coverage is still Luna, and Sol remains reserved for judgment rather than search. The lock is gone: pick the route **per branch**. The user's explicit route, model, and effort win when mutually compatible, but route capability constraints still apply. A user-fixed Spark route is incompatible with writing: stop and ask the user to choose a writer-capable route; never silently reroute it. If the user names a fixed Luna/Sol/Spark route with incompatible model/effort, stop and ask which selection to preserve; never silently change the route or discard an override.

Spawn with `fork_turns=none`. With no user override, use the selected route's `agent_type` and do not also pass model/effort — the role file is the contract. A Root-decided route upgrade changes only `agent_type`; it is not a model/effort override. When the user names model or effort without a fixed route, use Custom (`agent_type=default`) and pass the named values. When both values exactly match a fixed role's configured model and reasoning effort, use that `agent_type` and omit model/effort, except that a Spark-matched writing assignment remains Custom so the named values are preserved without assigning the non-writer Spark role. Do not pass model/effort alongside a fixed Luna, Sol, or Spark role. Resolve declared model and reasoning effort from the current `spawn_agent` contract. Put every needed fact in the child prompt.

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

An adversarial refuter appends these lines to that same Markdown return; never switch to JSON:

```text
TARGET: C-###
VERDICT: stands | unsupported | uncertain
evidence: <packet pointer>
```

Before stable IDs exist, `TARGET` uses the temporary claim anchor and snapshot ID supplied by Root. Before dispatching refuters, Root registers that anchor by normalized claim meaning, scope, and snapshot. An equivalent later claim appends its evidence to the same anchor and reuses the existing refute chain instead of starting another one. Material evidence arriving after refute dispatch does not change the packet those refuters saw: carry the combined claim forward as `contested`, assign one stable ID at dedupe, and apply the evidence-revision Sol rule below; never create an independent conflicting disposition for the equivalent claim. `CLAIMS: none` means the refuter found no new search claim; it is not an `unsupported` vote.

A pointer without a bounded payload is `UNVERIFIED`. Root builds merge packets, refute packets, and Sol packets only from numbered `CLAIMS`; do not infer claims from prose. Child numbers are local to that return. After merge and dedupe, Root assigns stable `C-001`, `C-002`, ... IDs from one monotonic namespace for the entire Root task; waves and segments never reset it, while a new Root task starts at `C-001`. Root freezes each stable claim's meaning, scope, and existing evidence provenance. Non-material evidence may append without reopening it. Material evidence that could change the disposition increments that ID's evidence revision, sets it to `contested`, and permits at most one new Sol gate for that revision; do not rerun refuters for the same claim and snapshot. A semantic rewrite, merge, or split creates a new ID. The child status `supported | inferred | UNVERIFIED` describes evidence support only; Root separately records `ADOPT | REJECT | UNKNOWN | contested` in the transcript-local `seen` set so a later wave does not silently revive the claim. Every stable ID must end as `ADOPT`, evidence-backed `REJECT`, or `UNKNOWN`; resolve remaining `contested` or `UNVERIFIED` material claims to `UNKNOWN` when evidence cannot settle them. Every route may return `CLAIMS: none` only after completing the assigned in-scope work and finding no claim; keep `UNCOVERED` and `NOT_IN_SCOPE`. Material in-scope `UNCOVERED` keeps the branch and overall coverage incomplete: preserve any numbered claims, then either dispatch only the bounded remainder as a planned branch or finish that remainder as `UNKNOWN`; it never supports `completed-empty`. Sol may add `ADOPT | REJECT | UNKNOWN` and reasons to the same shape. A missing, malformed, empty, or off-scope return is a failure result, never `completed-empty`. Use at most one `followup_task` only to supply concrete input or the return shape Root omitted, never to request another search; otherwise follow the failure-packet path.

Before every `spawn_agent`:

```text
Subagent: <branch> -> <route> (<model>/<effort>, <configured|user>)
```

## Caps

Guidance, not a lookup table. Typically use 2–8 live coverage agents across Spark/Luna search and the optional completeness critic. Adversarial refuters do not count toward that range. When more useful coverage lenses exist, batch the next wave rather than refuse or exceed current capacity. Multiple Sol may be live only as independent design proposers, design scorers, judgment gates for distinct deduplicated claims, or Sol refuters required by the adversarial rule. Sol never fills search coverage or a headcount target. When total live slots are insufficient, queue refuters or Sol instead of refusing the branch, exceeding host capacity, or changing sandbox policy. A queued refuter remains assigned: start it when capacity opens and include it in the pre-dedupe barrier. If workflow closure arrives before capacity ever opens, account for that refuter as a missing vote, mark the claim `contested`, and disclose the capacity gap.

A bounded one-wave coverage segment reaches its stop rule when every planned branch has a final accounting status. Closing one wave does not complete the whole coverage workflow: a later wave already identified remains planned until it runs or Root accounts for it as dropped or `UNKNOWN` with a reason. Any failed, interrupted, `UNKNOWN`, or materially dropped coverage branch prevents `completed-empty` and makes coverage incomplete. `completed-empty` requires reaching the stop rule without ever finding a claim; finding claims that adversarial vote later rejects produces listed `REJECT` dispositions, not `completed-empty`. For repeated search — a loop or a user target `N` — require `N` to be a positive integer when present, and stop at the first of: post-adversarial adopted, deduplicated claims reach `N`; 2 consecutive waves produce no new unique claims; or the third search wave completes. Without a user-supplied `N`, do not invent one. A zero-claim wave counts as dry; it does not by itself mean `completed-empty`. The third wave closes the current search segment; changing lens does not reset the count, and a new segment must not exist merely to reset the cap. When `N` is present and a stop rule fires below it, report found/target/dropped and incomplete coverage. `N` does not authorize more coverage or Sol. If work is capped while still productive, say what was dropped.

## Candidate identity gate

Before the first evidence wave, Root records a scoped candidate snapshot: repository identity, `HEAD`, in-scope paths, and per-path state. Add a content fingerprint for every dirty or untracked in-scope file. `as-of` names this snapshot; a clock alone is not candidate identity. Bind each item-local chain to its snapshot.

Recheck the bound scoped identity before each item-local adversarial refute. After coverage reaches its stop rule and every assigned refuter, including queued refuters, reaches a terminal accounting state, recheck before dedupe and stable-ID assignment, including a pure-factual or `completed-empty` path; recheck again before every Sol gate and immediately before the final answer. In-scope drift makes only affected claims and their old votes stale or `UNKNOWN`; never validate old evidence or votes against new bytes. Out-of-scope drift does not invalidate the packet. After each writer becomes idle, take its post-write snapshot; start the new review segment only after all writers are idle. Skip Git-specific fields for a non-Git target, but retain an equivalent scoped source identity when available. Detailed examples are in [references/patterns.md](references/patterns.md).

## Sol gate

Do not spawn Sol without a Root-written packet visible in the parent transcript immediately before dispatch: scope, exclusions, decision context, numbered claims, bounded evidence payloads with provenance pointers and snapshot / as-of identity, and the questions Sol must answer (unsupported, missing class, severity wrong). For a direct Sol judgment or design branch with no prior coverage claims, Root supplies at least one numbered decision proposition plus bounded primary evidence or user constraints; an empty proposition is not a packet. A pointer without a bounded payload is `UNVERIFIED`.

After coverage reaches its stop rule and every assigned refuter, including queued refuters, reaches a terminal accounting state, Root rechecks candidate identity, deduplicates, and assigns stable `C-###` IDs. Each distinct surviving judgment claim may enter one Sol gate per evidence revision; the same `C-###` revision never enters two gates. Independent gates may run in parallel. Root opening evidence does not waive the gate. Skip Sol only when the remaining result is purely factual, Root directly verified sufficient primary evidence for every material factual conclusion, and no judgment, completeness, severity, or design question remains.

`completed-empty` applies only when the stop rule is reached and no claim was ever found; spawn no refuters or Sol for that path. If adversarial vote rejects every found claim, list each `C-###` as `REJECT`; that result is not `completed-empty` and defaults to 0 Sol unless a `contested` claim still needs judgment. A completeness critic may ask which class was missed without rescanning. Give it only the coverage packet, named in-scope source inventory, and `UNCOVERED`. An evidence-backed new claim from the critic follows the same adversarial trigger and Sol gate; material unread evidence withdraws `completed-empty`, makes coverage incomplete, and becomes `UNKNOWN`. Otherwise `completed-empty` stands. The critic does not start another search wave or reset a search cap.

### Item-local adversarial refute

After Root checks a surviving material claim against its cited evidence, start item-local adversarial refute when either the segment is deep, adversarial, comprehensive, multi-agent, repository-wide, or legacy Agent Fleet review; or the claim needs Sol or involves safety, hard-to-reverse, or externally trusted judgment. Ordinary factual fan-out stays unchanged: a pure fact Root substantiates from primary evidence gets 0 refuters and 0 Sol.

Default to 3 mutually blind refuters; use 2 when only two live slots are available, otherwise queue without exceeding host capacity. Queued refuters remain assigned and must start when capacity opens before the pre-dedupe barrier may pass. Use Luna by default. Use Sol when the claim itself is judgment, safety, or hard-to-reverse, or when the segment is a deep or adversarial review. Each refuter uses `fork_turns=none`, sees only that claim's bounded evidence packet, and asks one distinct question: citation support; freshness, snapshot, or missing payload; or severity/category. Refuters do not rescan the repository, do not count toward the 2–8 coverage range, and do not create stable IDs for extra findings. Extra material goes only to `UNCOVERED` for Root to consider as a later lens and never counts as a vote.

Run one refute round per claim and snapshot. A failed refuter is not upgraded or replaced; its vote is missing. Count only `stands` or `unsupported` with a pointer to packet evidence. `uncertain`, empty, off-scope, failed, or evidence-free returns do not vote; `CLAIMS: none` is not opposition. Apply outcomes in this order: any assigned refuter that failed or did not return makes the claim `contested`; otherwise, fewer than 2 valid votes or a tie makes it `contested`; otherwise, more `unsupported` than `stands` makes it `REJECT` in transcript-local `seen` and keeps it out of Sol, while more `stands` than `unsupported` leaves it for dedupe. Send a `contested` claim to a Sol gate only when judgment is still required. Candidate drift voids only affected old votes.

### Design scoring

Use design scoring only for a genuine choice the user has not already made. Spawn 2–3 mutually blind Sol proposers from named angles: fastest viable delivery, risk and rollback, and usability. After all proposers are idle, Root writes one scoring packet containing every proposal. Spawn 2–3 new Sol scorers; never reuse a proposer. Each scorer gives every proposal a 1–5 score for each named angle and one sentence of reason per score. Root totals scores, or averages them when scorer counts differ, takes the highest-scoring proposal as the base, and names grafted parts, exclusions, and unresolved questions. A tie gets one new Sol that sees only the scoring packet and breaks that tie. Never use majority vote for design, and never mix adversarial votes with design scores.

Root must adopt, reject-with-evidence, or mark `UNKNOWN` every material Sol issue. Adversarial majority rejection happens only before that claim's Sol gate. Once Sol adopts a claim, do not dispatch refuters to outvote it; Sol does not vote against refuters.

## Escalation and lifecycle

Never replay the same failed Luna assignment to another Luna. An adversarial refute set is allowed because each member asks a distinct question over the same bounded evidence. Run no second refute round for the same claim and snapshot, and do not upgrade a failed refuter to Sol. Material new evidence reopens the stable claim only through its next evidence revision and optional Sol gate; it does not authorize another refute round.

A missing, malformed, empty, or off-scope child return follows the return-shape failure rule above. After a Luna failure, Root writes a failure packet from attempted scope, evidence or commands, gaps, and questions; escalate to one Sol only when Sol can judge that packet without rescanning the repository, otherwise Root handles the branch or marks it `UNKNOWN`. If a direct Sol still fails after any permitted input/shape follow-up, Root owns the failure packet and either decides from its existing evidence or marks the branch `UNKNOWN`; do not replay, down-route, or ask Sol to rescan. "Try harder" is a forbidden replay.

Nested spawn is forbidden. Children do not message peers. Within one unresolved chain, never down-route after Sol. A later segment may use a new route; implementation review may start fresh Lunas only after the writer is idle. Never `codex exec`. Never 4/6/8 tables, fixed Luna/Sol ratios, or mandatory discovery→challenge→reproduction.

User cancellation stops new dispatch, follow-up, and downstream segments immediately. Request interruption of live children only when still needed for cancellation; an unconfirmed final state remains `UNKNOWN`.

Optional last step only when risk warrants: one completeness critic; see [references/patterns.md](references/patterns.md). Do not turn it into a mandatory fourth search wave.

Before the final answer, account for every planned material branch as completed, `completed-empty`, failed, interrupted, dropped with a stated reason, or `UNKNOWN`. Non-barrier scheduling never permits silent omission.

A slow or silent child is not automatically stuck. After that child's first timeout, Root may send at most one non-interrupting progress question. If a later wait timeout shows no progress or state change since that question, request interruption once, mark the branch `UNKNOWN`, and continue final accounting without replay or reroute. Observed progress resets only this unchanged-timeout observation, not the one-question budget. While a child is active, Root may do other work but must not repeat that child's scope, question, and method. If a live child is duplicate, clearly off-scope, or no longer needed, use `interrupt_agent` when available to stop its current turn; interruption does not close the agent or guarantee capacity. On a spawn-capacity failure, call `list_agents` once, then batch after existing agents reach a terminal state or drop the branch and disclose it. Never retry-loop.

## Writes

Read-only unless the user clearly asked to implement. Implicit invocation may parallelize read-only coverage, not writers. Use one active writer, including Root, unless the user explicitly requests parallel implementation; the default child writer is Sol. Luna writes only when the user named Luna. Spark never writes: a user-fixed Spark writing route requires a user choice, while a route-free model/effort match uses Custom as defined above. Root gives every writer a decided plan, closed file scope, acceptance checks, and applicable workspace rules. Review starts only after all writers are idle. Never parallel-write the same files.

When the current request both authorizes implementation and explicitly requests parallel writing, Root may create the required worktrees without a second permission question when all of these are true: the target is one Git repository; 2+ writers must run concurrently; their `owned_targets` are mutually exclusive; and applicable workspace instructions already define worktree creation, dispatch, integration, and cleanup boundaries. For work under `D:\codex`, read and follow `D:\codex\docs\agent-workflows\worktree-parallel-dispatch.md` as the single source of truth. Outside that workspace, use an equivalent applicable contract or fall back to one writer. A stricter applicable rule still wins; this skill does not create a second worktree protocol.

Native spawn does not hard-bind a child to a directory. Root creates each worktree, names its absolute path and closed `owned_targets` in the prompt, and treats the result as a candidate patch. Each writer reports status and untracked files; Root rejects out-of-scope writes, verifies the diff, and applies accepted changes as patches to the target worktree rather than merging the writer branch. A writer does not run Git write commands. If the target worktree is dirty, disclose that a new worktree starts from `HEAD` without those changes and let the user choose a serial route, a usable baseline, or an adjusted scope before creating worktrees. Non-Git targets, overlapping write sets, or an ambiguous baseline use one writer. Never run `git init` to unlock parallelism. Worktree cleanup remains a separate scoped action.

This skill grants no authority beyond the current request. The explicit parallel-implementation request above covers only worktree creation required by the applicable contract; it does not authorize commit, push, merge, unrelated checkout or branch changes, worktree removal, sandbox or approval-policy changes, or ignoring applicable `AGENTS.md` instructions.

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
- Counting adversarial refuters toward the 2–8 coverage range
- Treating `uncertain`, `CLAIMS: none`, or an evidence-free return as an `unsupported` vote
- Running a second refute round for the same claim and snapshot
- Using design votes instead of independent proposal scoring
- Parallel writers without an explicit user request, disjoint `owned_targets`, and an applicable worktree contract
- Treating a worktree as a hard child cwd sandbox instead of verifying its candidate patch
- Sending a judgment/safety branch to Luna only because it looks like search
- Relabeling a Custom override as Luna or Sol
- Treating dispatch shapes as exclusive product modes (old Fleet)
- Inventing a worktree protocol when the workspace has none
- Applying 4/6/8 Fleet tables when this skill owns the job
- Claiming complete coverage after skipping a warranted completeness critic
