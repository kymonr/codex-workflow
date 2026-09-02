# Patterns

Pick 1–2 patterns per segment. Do not run this whole list. Dispatch **shape** (solo / fan-out / pipeline / loop / segments / panel / write) is chosen in SKILL.md; this file is the technique detail.

## Scout then fan-out

Root names scope and independent questions, then fans out. An optional Luna scout may propose questions; Root alone dispatches every child. Never blind-spawn a crowd.

## Distinct lenses

Count search *methods*, not a desired headcount. Useful splits: by module, by recent diff, by error string, by permission / data / API. Merge only assignments with materially the same evidence objective, scope, question, and method; static analysis and runtime reproduction are distinct.

## Pipeline without a join

Each item owns its chain: find (default Luna, or Sol if that question is already a judgment) → optional packet-only refute → Sol gate only if a surviving claim still needs judgment. The refuter is a distinct verification question over bounded evidence, not a replay of the finder.

`wait_agent` has no child-ID target list. It wakes on an update from any live agent or on new user input.

1. Spawn independent stage-1 children.
2. While Root still has local work, do not wait.
3. When idle, call `wait_agent` once with a 5–10 minute timeout.
4. Process whichever item updated. If that item's next stage is non-Sol, dispatch it immediately; siblings continue independently.
5. Wait for all relevant items only when their results must be merged and deduplicated before one serial Sol gate. Genuinely independent conclusions and design panels are exceptions.

Use `list_agents` after a timeout, ambiguous wake, suspected silent completion, or capacity failure; do not call it mechanically after every ordinary result. Do not poll mechanically or treat silence alone as proof that a child is stuck.

## Worked example

Three-module bug hunt (scout → Luna fan-out → first-back first-check → optional Sol):

1. Root (or one Luna scout) names three independent modules and one question per module.
2. Spawn three Luna finders with `fork_turns=none`. Do not wait for all three.
3. First finder returns: Root checks its claims against cited files. If the next stage is a packet-only refute, spawn that refute now. The other two finders keep running.
4. Process each independent return without waiting for its siblings.
5. When all finders are terminal, Root dedupes. Pure facts Root substantiated → 0 Sol. Judgment remaining → one Sol on one merge packet.
6. Run the completeness critic below only if risk warrants it. Then account for every branch.

## Completeness critic

Optional last step, not a fourth search wave. Ask “what class of risk or which owned files did nobody cover?” Missing risk class → Sol on the merge packet. Unread files → Luna. Skip when the job was a bounded factual list Root already substantiated.

## Loop until dry

1. Wave of lens Lunas
2. Root dedupes by file + claim text
3. Next wave only with a **different** lens
4. After 3 search waves in one segment, change lens or segment; only 2 consecutive dry waves finish the search

Do not restart the same assignment on the same files. Log anything truncated.

## Verify menu

| Need | Who |
|---|---|
| Fact Root can substantiate | Root verifies sufficient primary evidence, 0 Sol |
| Claim will be used to decide | Optional packet-only refute Luna when risk warrants |
| Several failure modes | One lens per mode; default Luna, Sol if that lens is itself a judgment |
| Judgment-bearing trusted conclusion | One Sol gate on the merge packet |
| Pick a design | Sol panel 2–3 |

## Segment switch

When those segments exist: Understand (lenses) → Design (Sol) → Implement (one writer, default Sol) → Review (fresh Lunas, optional Sol gate). New children each segment. Do not reuse a finder as the writer or as the reviewer of its own work. Review starts only after the writer is idle. If the user wants parallel writers, stop and require a separately selected worktree workflow; this pattern does not create worktrees.

## Escalate forward only

Default search Luna (Spark if mechanical) → optional packet-only refuter → Sol gate. A branch may **start** as Sol when the question itself requires it. Never replay the same failed assignment to the same route; upgrade Luna → Sol → Root. Within one unresolved chain, once Sol has judged, never down-route. A later review of completed implementation is a new segment, not a down-route. If Root cannot form a bounded Sol packet, Root handles the branch or marks it `UNKNOWN`. Nested spawn is forbidden in every pattern.

## Final accounting

Before answering, classify every planned material branch as completed, failed, interrupted, dropped with a reason, or `UNKNOWN`. A pipeline may avoid an intermediate barrier, but it may not silently omit unfinished coverage.
