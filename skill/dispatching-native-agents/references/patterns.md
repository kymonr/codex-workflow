# Patterns

Pick 1–2 patterns per segment. Do not run this whole list. Dispatch **shape** (solo / fan-out / pipeline / loop / segments / panel / write) is chosen in SKILL.md; this file is the technique detail.

## Scout then fan-out

Root names scope and independent questions, then fans out. An optional Luna scout may propose questions; Root alone dispatches every child. Never blind-spawn a crowd.

## Distinct lenses

Count search *methods*, not a desired headcount. Useful splits: by module, by recent diff, by error string, by permission / data / API. Merge only assignments with materially the same evidence objective, scope, question, and method; static analysis and runtime reproduction are distinct. Usually run 2–8 useful coverage branches across Spark/Luna search and the optional completeness critic; adversarial refuters do not count toward that range. Split larger coverage sets into waves. A later wave identified before the current wave closes remains planned until it runs or Root accounts for it as dropped or `UNKNOWN` with a reason. A legacy Fleet number is a depth request, not a quota.

## Scoped candidate identity

Before the first evidence wave, Root records one snapshot identifier and:

- repository identity and `HEAD` for a Git target;
- the exact in-scope path set and per-path state;
- a content fingerprint for every dirty or untracked in-scope file.

`as-of` refers to that snapshot, not merely a timestamp. Bind every item-local chain to the snapshot it examined. When a completed writer changes the candidate, record a new snapshot and start a new review segment.

Recheck the bound snapshot before each item-local adversarial refute. After coverage reaches its stop rule and all in-flight refuters finish, recheck before dedupe and stable-ID assignment, including a pure-factual or `completed-empty` path. Recheck again before every Sol gate and immediately before the final answer. In-scope drift makes only affected claims and their old votes stale or `UNKNOWN`; out-of-scope drift does not invalidate the packet. Do not reinterpret old evidence or votes as proof about new bytes. Non-Git work skips Git fields but still names the source and in-scope identity that can be observed.

## Pipeline without a join

Each item owns its chain: find (default Luna, or Sol if the question is already judgment) → Root citation check → triggered item-local adversarial refute. Finder siblings keep running. After coverage reaches its stop rule and all in-flight refuters finish, Root rechecks candidate identity, deduplicates, assigns stable `C-###` IDs, and sends each distinct surviving judgment claim to one Sol gate. Independent Sol gates may run in parallel. Refuters ask distinct questions over bounded evidence, not a replay of the finder.

`wait_agent` has no child-ID target list. It wakes on an update from any live agent or on new user input.

1. Spawn independent stage-1 children.
2. While Root still has local work, do not wait.
3. When idle, call `wait_agent` once with a 5–10 minute timeout.
4. Process whichever item updated. Root checks each claim against its citation. When the adversarial trigger applies, pass that claim's bounded packet, temporary anchor, and bound snapshot to its refuters immediately while siblings continue independently.
5. After coverage reaches its stop rule, wait for all in-flight refuters. Then recheck scoped candidate identity, dedupe, assign stable `C-###` IDs, and dispatch one Sol gate per distinct surviving judgment claim; independent gates may run in parallel. Only a terminal segment that never found a claim becomes `completed-empty`.

Use `list_agents` after a timeout, ambiguous wake, suspected silent completion, or capacity failure; do not call it mechanically after every ordinary result. Do not poll mechanically or treat silence alone as proof that a child is stuck.

## Worked example

Three-module bug hunt (scout → Luna fan-out → first-back adversarial → optional Sol):

1. Root (or one Luna scout) names three independent modules and one question per module.
2. Spawn three Luna finders with `fork_turns=none`; each prompt includes the child return shape from SKILL.md. Do not wait for all three.
3. First finder returns: Root checks each numbered claim against cited evidence while the other two finders keep running. For every triggering claim, immediately start its 3 distinct refuters; use 2 only when live capacity allows no more, otherwise queue.
4. Process each independent return without waiting for its siblings.
5. When all finders are terminal, wait for in-flight refuters. A segment that never found a claim → `completed-empty`, 0 refuters, and 0 Sol. Claims rejected by vote are listed as `REJECT`, not empty. Root rechecks candidate identity, dedupes the survivors, and dispatches independent surviving judgment claims to parallel Sol gates. Pure facts Root substantiated use 0 refuters and 0 Sol.
6. Run the completeness critic below only if risk warrants it. Then account for every branch.

## Item-local adversarial refute

Trigger after Root checks a surviving material claim against its citation when either the segment is deep, adversarial, comprehensive, multi-agent, repository-wide, or legacy Agent Fleet review; or the claim needs Sol or involves safety, hard-to-reverse, or externally trusted judgment. A pure fact Root substantiates from primary evidence gets 0 refuters and 0 Sol.

Use 3 mutually blind refuters by default, 2 when only two live slots are available, otherwise queue. Use Luna by default; use Sol when the claim itself is judgment, safety, or hard-to-reverse, or when the segment is deep or adversarial. Each uses `fork_turns=none`, sees only the bounded claim packet, and takes one distinct question: citation support; freshness, snapshot, or missing payload; severity/category. Refuters do not rescan, do not count toward the 2–8 coverage range, and do not mint stable IDs for extra findings. Put extra material only in `UNCOVERED` for a possible later lens.

Append the `TARGET`, `VERDICT`, and packet `evidence` lines defined in SKILL.md to the ordinary Markdown return. Before stable IDs exist, Root supplies a temporary claim anchor plus snapshot ID. `CLAIMS: none` is not an opposition vote.

| `VERDICT` | Counts? | Effect |
|---|---|---|
| `unsupported` with packet evidence | yes | vote to reject |
| `stands` with packet evidence | yes | vote to retain |
| `uncertain`, empty, off-scope, failed, or evidence-free | no | no vote |

Apply outcomes in this order. Any assigned refuter that failed or did not return makes the claim `contested`. Otherwise, fewer than 2 valid votes or a tie makes it `contested`. Otherwise, more `unsupported` than `stands` makes the claim `REJECT` in transcript-local `seen` and keeps it out of Sol, while more `stands` than `unsupported` retains it for dedupe. Send a `contested` claim to Sol only when judgment remains necessary. Run one round per claim and snapshot. Do not replace or upgrade failed refuters. Snapshot drift voids only affected old votes. Majority rejection happens only before a Sol gate; a Sol-adopted claim is never sent back to refuters.

## Completeness critic

Optional last step, not a fourth search wave. Give the critic only the coverage packet, named in-scope source inventory, and `UNCOVERED`. Ask: “what class of risk or which owned files did nobody cover; which important modality is absent; which material claim remains unverified; and which in-scope source remains unread?” It may compare those inputs but does not rescan the repository, and returns `CLAIMS: none` only after checking every question. A supported missing-class claim lets Root replace the empty conclusion with a non-empty claim and apply the same item-local adversarial trigger before any Sol gate. Material unread in-scope evidence withdraws `completed-empty`, marks coverage incomplete, and makes the unread branch `UNKNOWN`; otherwise `CLAIMS: none` leaves `completed-empty` standing. The critic does not start another search wave. Skip when the job was a bounded factual list Root already substantiated.

## Stable claims and `seen`

Child numbering is local. After Root merges and deduplicates a segment, assign `C-001`, `C-002`, ... and keep each ID bound to one meaning, scope, and evidence provenance. Additional evidence may append to that claim. A semantic rewrite, merge, or split creates a new ID. Evidence status and Root disposition are separate fields; every stable ID ends as adopted, rejected with evidence, or `UNKNOWN`.

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

Default search Luna (Spark if the branch is short, mechanical, read-only, and easily checked) → triggered item-local adversarial refute → Sol gate for each distinct surviving judgment claim. When Root selected Spark by default and it is unavailable or proves insufficient, transfer only the unfinished scope once to Luna in a remainder packet containing the original scope, completed claims and evidence, `UNCOVERED`, and the failure or capability limit; do not replay completed work. When the user fixed the Spark route, report the failure or capability limit and keep the route unchanged unless the user chooses another route. A branch may **start** as Sol when the question itself requires judgment, safety, or hard-to-reverse choices. Never replay the same failed assignment to the same route; upgrade Luna → Sol → Root. A failed adversarial refuter is a missing vote, never an upgrade or replay. If a direct Sol still fails after the permitted input/shape follow-up, Root decides from the existing failure packet or marks the branch `UNKNOWN`; never replay, down-route, or rescan. A later review of completed implementation is a new segment, not a down-route. If Root cannot form a bounded Sol packet, Root handles the branch or marks it `UNKNOWN`. Nested spawn is forbidden in every pattern.

## Waiting without replay

After a child's first timeout, Root may send that child at most one non-interrupting progress question. A healthy child remains awaited. Silence does not authorize replay, reroute, or interruption. Root may advance unrelated work while waiting, but does not repeat the active child's scope, question, and method.

## Final accounting

Before answering, classify every planned material branch as completed, `completed-empty`, failed, interrupted, dropped with a reason, or `UNKNOWN`, and give every stable `C-###` an adopted, evidence-backed rejected (including adversarial majority rejection), or `UNKNOWN` disposition. A majority-rejected claim is never reported as empty. Material `UNVERIFIED` or `contested` claims remain surviving; if a contested claim still needs judgment, it must enter a Sol gate or finish as `UNKNOWN`, never implicit `ADOPT`. A pipeline may avoid an intermediate barrier, but it may not silently omit unfinished coverage.
