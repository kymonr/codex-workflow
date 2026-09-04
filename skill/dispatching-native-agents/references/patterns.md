# Patterns

Pick 1–2 patterns per segment. Do not run this whole list. Dispatch **shape** (solo / fan-out / pipeline / loop / segments / panel / write) is chosen in SKILL.md; this file is the technique detail.

## Scout then fan-out

Root names scope and independent questions, then fans out. An optional Luna scout may propose questions; Root alone dispatches every child. Never blind-spawn a crowd.

Before the first Find spawn, Root freezes one read-only Map brief from the optional Luna scout or from Root's own map: facts, risks, key paths, named refs, and the candidate `as-of` identity. Inject the same frozen brief into every Find prompt. Map→Find is a justified barrier because Find needs cross-item Map context. The scout still does not dispatch. Do not inject the brief into refuter or Sol packets. Independent Finders do not wait for sibling Finders; item-local refute starts as soon as Root checks that claim. Do not thaw, rewrite, or customize the brief per Finder after freeze.

## Distinct lenses

Count search *methods*, not a desired headcount. Useful splits: by module, by recent diff, by error string, by permission / data / API. Merge only assignments with materially the same evidence objective, scope, question, and method; static analysis and runtime reproduction are distinct. Usually run 2–8 useful coverage branches across Spark/Luna search and the optional completeness critic; adversarial refuters do not count toward that range. Split larger coverage sets into waves. A later wave identified before the current wave closes remains planned until it runs or Root accounts for it as dropped or `UNKNOWN` with a reason. A legacy Fleet number is a depth request, not a quota.

Repository-wide deep audit is a worked illustration, not a quota. Useful Map lenses: governance/control-truth, implementation, hygiene/CI. Useful Find lenses: security, correctness, governance-drift, CI/protection, frontend/UI, data-boundary. Root still counts distinct evidence methods in the live scope and may merge, split, or drop those names. Do not invent a lens to match three Map, six Find, a Fleet number, or any other headcount.

Example: Root records the scoped candidate snapshot, keeps only Map and Find methods the live scope presents, merges duplicate methods, and splits a name that hides two methods. Fan-out follows that count, not three plus six. If remaining distinct methods exceed live capacity, batch the next wave; nine names are not a headcount target.

## Scoped candidate identity

Before the first evidence wave, Root records one snapshot identifier and:

- repository identity and `HEAD` for a Git target;
- the exact in-scope path set and per-path state;
- a content fingerprint for every dirty or untracked in-scope file.

For a Git target, the same snapshot also names the audited ref (working-tree `HEAD`, `origin/main`, or another named ref) and the required read method: working-tree files for a checkout candidate, or `git show <ref>:path` for a named-ref candidate. When the candidate is a named ref, list named untracked exceptions children may read from the working tree; an unlisted untracked file is not that named-ref candidate. When remote or GitHub state is in scope, record a remote as-of: published SHA, and issue or CI identity when those are examined. Put those published-ref fields in every child prompt that reads the candidate. Children must not treat a stale checkout as the candidate. Keep working-tree `HEAD` and dirty or untracked fingerprints; published-ref is an added dimension. A mismatch of the bound audited ref, required read method, named untracked exceptions, or in-scope remote as-of is in-scope drift for affected claims.

`as-of` refers to that snapshot, not merely a timestamp. Bind every item-local chain to the snapshot it examined. When a completed writer changes the candidate, record a new snapshot and start a new review segment.

Recheck the bound snapshot before each item-local adversarial refute. After coverage reaches its stop rule and every assigned refuter, including queued refuters, reaches a terminal accounting state, recheck before dedupe and stable-ID assignment, including a pure-factual or `completed-empty` path. Recheck again before every Sol gate and immediately before the final answer. In-scope drift makes only affected claims and their old votes stale or `UNKNOWN`; out-of-scope drift does not invalidate the packet. Do not reinterpret old evidence or votes as proof about new bytes. Non-Git work skips Git fields but still names the source and in-scope identity that can be observed.

## Pipeline without a join

Each item owns its chain: find (default Luna, or Sol if the question is already judgment) → Root citation check → triggered item-local adversarial refute. Finder siblings keep running. After coverage reaches its stop rule and every assigned refuter, including queued refuters, reaches a terminal accounting state, Root rechecks candidate identity, deduplicates, assigns stable `C-###` IDs, and sends each distinct surviving judgment claim to one Sol gate per evidence revision. Independent Sol gates may run in parallel. Refuters ask distinct questions over bounded evidence, not a replay of the finder.

Exception: when Root must rank a verify-queue cap because refute slots are fewer than surviving material claims, wait for coverage to reach its stop rule, rank, drop the tail with reason `verify-cap`, then start item-local refute only for the prefix. After that prefix is selected, each selected claim's refute starts without waiting for its selected siblings. This join exists solely to spend expensive refute slots; it is not a generic Find barrier. Rank a Sol-slot shortage only at the existing post-refute barrier; do not delay item-local refute for Sol capacity. If no such cap applied, do not invent one.

`wait_agent` has no child-ID target list. It wakes on an update from any live agent or on new user input.

1. Spawn independent stage-1 children.
2. While Root still has local work, do not wait.
3. When idle, call `wait_agent` once with a 5–10 minute timeout.
4. Process whichever item updated. Root checks each claim against its citation. Before refute, register normalized meaning, scope, and snapshot under one temporary anchor. An equivalent later claim appends evidence to that anchor and reuses its refute chain. Material evidence arriving after dispatch makes the combined claim `contested` for one stable ID and a later evidence-revision Sol gate; it does not start another refute chain. When the adversarial trigger applies, pass that claim's bounded packet, temporary anchor, and bound snapshot to its refuters immediately while siblings continue independently.
5. After coverage reaches its stop rule, start queued assigned refuters as capacity opens and wait until every assigned refuter has a terminal accounting state. Then recheck scoped candidate identity, dedupe, assign stable `C-###` IDs, and dispatch one Sol gate per distinct surviving judgment claim and evidence revision; independent gates may run in parallel. Only a terminal segment that never found a claim becomes `completed-empty`.

Use `list_agents` after a timeout, ambiguous wake, suspected silent completion, or capacity failure; do not call it mechanically after every ordinary result. Do not poll mechanically or treat silence alone as proof that a child is stuck.

## Worked example

Three-module bug hunt (scout → Luna fan-out → first-back adversarial → optional Sol):

1. Root (or one Luna scout) names three independent modules and one question per module.
2. Spawn three Luna finders with `fork_turns=none`; each prompt includes the child return shape from SKILL.md. Do not wait for all three.
3. First finder returns: Root checks each numbered claim against cited evidence while the other two finders keep running. For every triggering claim, immediately start its 3 distinct refuters; use 2 only when live capacity allows no more, otherwise queue.
4. Process each independent return without waiting for its siblings.
5. When all finders are terminal, start queued assigned refuters as capacity opens and wait for every assigned refuter to reach a terminal accounting state. A segment that never found a claim → `completed-empty`, 0 refuters, and 0 Sol. Claims rejected by vote are listed as `REJECT`, not empty. Root rechecks candidate identity, dedupes the survivors, and dispatches independent surviving judgment claims to parallel Sol gates. Pure facts Root substantiated use 0 refuters and 0 Sol.
6. Run the completeness critic below only if risk warrants it. Then account for every branch.

## Item-local adversarial refute

Trigger after Root checks a surviving material claim against its citation when either the segment is deep, adversarial, comprehensive, multi-agent, repository-wide, or legacy Agent Fleet review; or the claim needs Sol or involves safety, hard-to-reverse, or externally trusted judgment. A pure fact Root substantiates from primary evidence gets 0 refuters and 0 Sol.

Use 3 mutually blind refuters by default, 2 when only two live slots are available, otherwise queue. A queued refuter remains assigned: start it when capacity opens and include it in the pre-dedupe barrier. If workflow closure arrives before capacity opens, account for it as a missing vote, mark the claim `contested`, and disclose the gap. Use Luna by default; use Sol when the claim itself is judgment, safety, or hard-to-reverse, or when the segment is deep or adversarial. Each uses `fork_turns=none`, sees only the bounded claim packet, and takes one distinct question: citation support; freshness, snapshot, or missing payload; severity/category. Refuters do not rescan, do not count toward the 2–8 coverage range, and do not mint stable IDs for extra findings. Put extra material only in `UNCOVERED` for a possible later lens.

Append the `TARGET`, `VERDICT`, and packet `evidence` lines defined in SKILL.md to the ordinary Markdown return. Before stable IDs exist, Root supplies a temporary claim anchor plus snapshot ID. `CLAIMS: none` is not an opposition vote.

| `VERDICT` | Counts? | Effect |
|---|---|---|
| `unsupported` with packet evidence | yes | vote to reject |
| `stands` with packet evidence | yes | vote to retain |
| `uncertain`, empty, off-scope, failed, or evidence-free | no | no vote |

Apply outcomes in this order. Any assigned refuter that failed or did not return makes the claim `contested`. Otherwise, fewer than 2 valid votes or a tie makes it `contested`. Otherwise, more `unsupported` than `stands` makes the claim `REJECT` in transcript-local `seen` and keeps it out of Sol, while more `stands` than `unsupported` retains it for dedupe. Send a `contested` claim to Sol only when judgment remains necessary. Run one round per claim and snapshot. Do not replace or upgrade failed refuters. Snapshot drift voids only affected old votes. Majority rejection happens only before a Sol gate; a Sol-adopted claim is never sent back to refuters.

On a repository-wide or deep audit, write refute prompts so these packet-backed findings return evidence-backed `unsupported`, not `uncertain`: cited evidence exists only on a stale working tree and not on the named audited ref; the defect is already absent on the named audited ref; the claim is only a process smell with no concrete file or command evidence in the packet. Uncertainty remains `uncertain` and does not vote; do not recode it as `unsupported`. These criteria do not replace the three distinct refute questions. When only two live slots are available on such an audit, those two questions may specialize as existence on the named audited ref versus impact given declared project flags.

## Completeness critic

Optional last step, not a fourth search wave. Give the critic only the coverage packet, named in-scope source inventory, `UNCOVERED`, and any `verify-cap` dropped list. Ask: “what class of risk or which owned files did nobody cover; which important modality is absent; which material claim remains unverified; and which in-scope source remains unread?” It may compare those inputs but does not rescan the repository, and returns `CLAIMS: none` only after checking every question. A named promotion from the dropped list re-enters the existing verify or Sol path; it is not a new search wave and does not authorize a repository rescan. A supported missing-class claim lets Root replace the empty conclusion with a non-empty claim and apply the same item-local adversarial trigger before any Sol gate. Material unread in-scope evidence withdraws `completed-empty`, marks coverage incomplete, and makes the unread branch `UNKNOWN`; otherwise `CLAIMS: none` leaves `completed-empty` standing. The critic does not start another search wave. Skip when the job was a bounded factual list Root already substantiated.

## Stable claims and `seen`

Child numbering is local. After Root merges and deduplicates, assign `C-001`, `C-002`, ... from one monotonic namespace for the entire Root task; never reset it between waves or segments, and start a new Root task at `C-001`. Keep each ID bound to one meaning, scope, and evidence provenance. Non-material evidence may append without reopening the claim. Material evidence that could change its disposition increments that ID's evidence revision, sets it to `contested`, and permits at most one new Sol gate for that revision; never rerun refuters for the same claim and snapshot. A semantic rewrite, merge, or split creates a new ID. Evidence status and Root disposition are separate fields; every stable ID ends as adopted, rejected with evidence, or `UNKNOWN`.

Maintain a transcript-local `seen` set containing adopted, rejected (including majority-rejected), `UNKNOWN`, and `contested` claims. Compare the next wave against all four outcomes. A repeated claim with no materially new evidence is not new coverage and does not reset a dry-wave count.

## Loop until dry

1. Run a wave of lens coverage agents (Spark or Luna).
2. Root dedupes against stable claim meaning and the transcript-local `seen` set.
3. Continue only with a **different** lens.
4. Stop at the first of: a user-supplied positive integer `N` is reached by post-adversarial adopted, deduplicated claims; 2 consecutive waves produce no new unique claims; or the third search wave completes.
5. A zero-claim wave counts as dry, not `completed-empty` by itself. The third wave closes the segment; changing lens does not reset the count, and a new segment must not exist merely to reset the cap.
6. When `N` is present and a stop rule fires below it, report found/target/dropped and incomplete coverage. Without a user-supplied `N`, do not invent one.

Do not restart the same assignment on the same files. Log anything truncated.

## Verify menu

| Need | Who |
|---|---|
| Fact Root can substantiate | Root verifies sufficient primary evidence, 0 Sol |
| Material claim meets the adversarial trigger | 2–3 item-local refuters with distinct questions; evidence-backed majority may reject; default Luna, use Sol for judgment/safety/hard-to-reverse or deep/adversarial review |
| Several failure modes | One lens per mode; default Luna, Sol if that lens is itself a judgment |
| Judgment-bearing trusted conclusion | After dedupe, one Sol gate per distinct survivor; independent gates may run in parallel |
| Pick a design | 2–3 Sol proposers, then 2–3 new Sol scorers; Root selects and grafts; one Sol breaks a tie |

## Design panel then graft

Use only for a genuine choice when the user has not already selected a design. Spawn 2–3 mutually blind Sol proposers with named angles: fastest viable delivery, risk and rollback, and usability. After all proposers are idle, Root writes one scoring packet containing every proposal. Spawn 2–3 new Sol scorers; never reuse proposers. Each scorer gives every proposal a 1–5 score for each named angle and one sentence of reason per score. Root totals scores, or averages them when scorer counts differ, selects the highest-scoring proposal as the base, and names grafted parts, exclusions, and unresolved questions. A tie gets one new Sol that sees only the scoring packet. Never vote on design; never mix adversarial votes with design scores.

## Segment switch

When those segments exist: Understand (lenses) → Design (Sol) → Implement (one writer by default) → Review (fresh coverage agents, optional Sol gate). New children each segment. Do not reuse a finder as the writer or as the reviewer of its own work. Review starts only after all writers are idle. Only when the current request explicitly asks for parallel writing and 2+ independent writers must run concurrently, use the applicable workspace worktree contract; under `D:\codex`, the single source of truth is `D:\codex\docs\agent-workflows\worktree-parallel-dispatch.md`. If no applicable contract exists, use one writer.

## Escalate forward only

Default search Luna (Spark if the branch is short, mechanical, read-only, and easily checked) → triggered item-local adversarial refute → Sol gate for each distinct surviving judgment claim. When Root selected Spark by default and it is unavailable or proves insufficient, transfer only the unfinished scope once to Luna in a remainder packet containing the original scope, completed claims and evidence, `UNCOVERED`, and the failure or capability limit; do not replay completed work. When the user fixed the Spark route, report the failure or capability limit and keep the route unchanged unless the user chooses another route. Spark never writes: a user-fixed Spark writing assignment stops for a user choice, while a route-free model/effort match uses Custom. A branch may **start** as Sol when the question itself requires judgment, safety, or hard-to-reverse choices. Never replay the same failed assignment to the same route; upgrade Luna → Sol → Root. A failed adversarial refuter is a missing vote, never an upgrade or replay. If a direct Sol still fails after the permitted input/shape follow-up, Root decides from the existing failure packet or marks the branch `UNKNOWN`; never replay, down-route, or rescan. Material new evidence reopens the same stable claim only as a new evidence revision and optional Sol gate; it does not authorize another refute round. A later review of completed implementation is a new segment, not a down-route. If Root cannot form a bounded Sol packet, Root handles the branch or marks it `UNKNOWN`. Nested spawn is forbidden in every pattern.

## Waiting without replay

After a child's first timeout, Root may send that child at most one non-interrupting progress question. If a later wait timeout shows no progress or state change since that question, request interruption once, mark the branch `UNKNOWN`, and continue accounting without replay or reroute. Observed progress resets only this unchanged-timeout observation, not the one-question budget. Root may advance unrelated work while waiting, but does not repeat the active child's scope, question, and method.

## Final accounting

Before answering, classify every planned material branch as completed, `completed-empty`, failed, interrupted, dropped with a reason, or `UNKNOWN`, and give every stable `C-###` an adopted, evidence-backed rejected (including adversarial majority rejection), or `UNKNOWN` disposition. A majority-rejected claim is never reported as empty. Material `UNVERIFIED` or `contested` claims remain surviving; if a contested claim still needs judgment, it must enter a Sol gate or finish as `UNKNOWN`, never implicit `ADOPT`. A pipeline may avoid an intermediate barrier, but it may not silently omit unfinished coverage.
