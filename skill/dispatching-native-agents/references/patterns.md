# Patterns

Pick 1–2 patterns per segment. Do not run this whole list. Dispatch **shape** (solo / fan-out / pipeline / loop / segments / panel / write) is chosen in SKILL.md; this file is the technique detail.

## Scout then fan-out

Root names scope and independent questions, then fans out. An optional Luna scout may propose questions; Root alone dispatches every child. Never blind-spawn a crowd.

## Distinct lenses

Count search *methods*, not a desired headcount. Useful splits: by module, by recent diff, by error string, by permission / data / API. Merge only assignments with materially the same evidence objective, scope, question, and method; static analysis and runtime reproduction are distinct.

## Pipeline without a join

Each item owns its item-local chain: find (default Luna, or Sol if that question is already a judgment) → optional item-local non-Sol verification. After the coverage segment reaches its stop rule, Root merges and deduplicates before an optional packet refute panel and a Sol gate only if a surviving claim still needs judgment. Refuters ask distinct verification questions over bounded evidence, not a replay of the finder.

`wait_agent` has no child-ID target list. It wakes on an update from any live agent or on new user input.

1. Spawn independent stage-1 children.
2. While Root still has local work, do not wait.
3. When idle, call `wait_agent` once with a 5–10 minute timeout.
4. Process whichever item updated. If that item's next stage is item-local and non-Sol, dispatch it immediately; siblings continue independently.
5. After the coverage segment reaches its stop rule, wait for every relevant branch needed by the merge, then merge and dedupe. Only then can 0 surviving claims become `completed-empty`. A non-empty judgment-bearing packet may enter an optional refute panel and one serial Sol gate. Genuinely independent conclusions and design panels are exceptions.

Use `list_agents` after a timeout, ambiguous wake, suspected silent completion, or capacity failure; do not call it mechanically after every ordinary result. Do not poll mechanically or treat silence alone as proof that a child is stuck.

## Worked example

Three-module bug hunt (scout → Luna fan-out → first-back first-check → optional Sol):

1. Root (or one Luna scout) names three independent modules and one question per module.
2. Spawn three Luna finders with `fork_turns=none`; each prompt includes the child return shape from SKILL.md. Do not wait for all three.
3. First finder returns: Root checks its numbered claims against cited evidence while the other two finders keep running. Do not start the packet refute panel until the coverage wave is terminal and Root has a non-empty merge packet.
4. Process each independent return without waiting for its siblings.
5. When all finders are terminal, Root applies the `completed-empty` eligibility rule in SKILL.md and dedupes. An eligible 0 surviving claims → `completed-empty`, 0 refute Lunas, and 0 Sol. Pure facts Root substantiated → 0 Sol. Judgment remaining → optional refute panel, then one Sol on one merge packet.
6. Run the completeness critic below only if risk warrants it. Then account for every branch.

## Packet refute panel

For a non-empty merge packet involving externally trusted judgment, safety, or hard-to-reverse work, Root may spawn 2–3 Luna in one wave with the same numbered packet and distinct questions: citation support; freshness, snapshot, or missing payload; severity or category. Use `fork_turns=none`, packet payloads only, and no repository rescan. Drop a claim only when cited packet evidence does not support it; unsupported doubt becomes `contested` for Sol. Never vote. These refuters count toward Luna caps.

## Completeness critic

Optional last step, not a fourth search wave. Ask “what class of risk or which owned files did nobody cover?” Return an evidence-backed numbered claim or `CLAIMS: none`. A supported missing-class claim lets Root replace the empty conclusion with a non-empty merge packet and apply the normal gate. Material unread in-scope evidence withdraws `completed-empty`, marks coverage incomplete, and makes the unread branch `UNKNOWN`; otherwise `CLAIMS: none` leaves `completed-empty` standing. The critic does not start another search wave. Skip when the job was a bounded factual list Root already substantiated.

## Loop until dry

1. Run a wave of lens Lunas.
2. Root dedupes by file + claim text.
3. Continue only with a **different** lens.
4. Stop at the first of: a user-supplied positive integer `N` is reached by adopted, deduplicated claims; 2 consecutive waves produce no new unique claims; or the third search wave completes.
5. A zero-claim wave counts as dry, not `completed-empty` by itself. The third wave closes the segment; changing lens does not reset the count, and a new segment must not exist merely to reset the cap.
6. When `N` is present and a stop rule fires below it, report found/target/dropped and incomplete coverage. Without a user-supplied `N`, do not invent one.

Do not restart the same assignment on the same files. Log anything truncated.

## Verify menu

| Need | Who |
|---|---|
| Fact Root can substantiate | Root verifies sufficient primary evidence, 0 Sol |
| Non-empty packet will support a trusted judgment | Optional 2–3 Luna packet refute panel in one wave, each with a distinct question |
| Several failure modes | One lens per mode; default Luna, Sol if that lens is itself a judgment |
| Judgment-bearing trusted conclusion | One Sol gate on the merge packet |
| Pick a design | Sol panel 2–3 |

## Design panel then graft

Use only for a genuine choice when the user has not already selected a design. Spawn 2–3 Sol with distinct named angles, such as fastest viable delivery, risk and rollback, or usability. They propose independently, do not see or judge each other, and never vote. After every panelist is idle, Root writes a synthesis packet naming the base proposal, grafted parts, exclusions, and unresolved questions. If judgment remains, start one new serial Sol only after the panel is idle.

## Segment switch

When those segments exist: Understand (lenses) → Design (Sol) → Implement (one writer, default Sol) → Review (fresh Lunas, optional Sol gate). New children each segment. Do not reuse a finder as the writer or as the reviewer of its own work. Review starts only after the writer is idle. If the user wants parallel writers, stop and require a separately selected worktree workflow; this pattern does not create worktrees.

## Escalate forward only

Default search Luna (Spark if mechanical) → optional packet refute panel → Sol gate. A branch may **start** as Sol when the question itself requires it. Never replay the same failed assignment to the same route; upgrade Luna → Sol → Root. If a direct Sol still fails after the permitted input/shape follow-up, Root decides from the existing failure packet or marks the branch `UNKNOWN`; never replay, down-route, or rescan. A later review of completed implementation is a new segment, not a down-route. If Root cannot form a bounded Sol packet, Root handles the branch or marks it `UNKNOWN`. Nested spawn is forbidden in every pattern.

## Final accounting

Before answering, classify every planned material branch as completed, `completed-empty`, failed, interrupted, dropped with a reason, or `UNKNOWN`. A pipeline may avoid an intermediate barrier, but it may not silently omit unfinished coverage.
