# Release Checklist

This project is pre-alpha. Complete every blocking item before creating a tag or
publishing a package.

## Ownership and legal

- [ ] Choose and add an explicit open-source license.
- [ ] Confirm the repository owner and package publisher identity.
- [ ] Review third-party dependency and action licenses.
- [ ] Confirm that no private prompts, run directories, worktrees, credentials,
      or local configuration are tracked.

The missing project license is currently a release blocker. Public repository
visibility alone does not grant reuse rights.

## Version and change record

- [ ] Choose the release version and update `pyproject.toml` and
      `workflow/__init__.py` together.
- [ ] Move relevant entries from `Unreleased` into a dated changelog section.
- [ ] Confirm README status and compatibility claims match the release.
- [ ] Review all user-visible CLI and journal changes.

## Code verification

- [ ] Run the full unit-test suite on Python 3.12.
- [ ] Run `python -m compileall -q workflow tests`.
- [ ] Run `python -m pip check`.
- [ ] Build a wheel and source distribution in a clean environment.
- [ ] Install the wheel and verify `codex-workflow --help`.
## Functional acceptance

- [ ] Run `examples/hello.js` with `--mock` under the supervisor.
- [ ] Run `examples/parallel-hello.js` with `--mock`.
- [ ] Run `examples/nested-parent.js` with representative JSON args.
- [ ] Verify phase snapshots, max-agent rejection, resume prefix hits, worktree
      isolation, nested-depth rejection, timeout, and cancellation tests.
- [ ] Do not run a real Codex request unless that validation is explicitly
      authorized and its cost and repository scope are understood.

## Security review

- [ ] Re-read `docs/THREAT_MODEL.md` and `SECURITY.md`.
- [ ] Inspect every built argv and confirm exactly one allowed reasoning `-c`.
- [ ] Confirm ordinary agents use `-s read-only`.
- [ ] Confirm only host-created out-of-repository worktrees use
      `-s workspace-write`.
- [ ] Search for forbidden access, approval, full-auto, shell, and config flags.
- [ ] Test process-tree cleanup on Windows and Linux.
- [ ] Review QuickJS global, prototype, and constructor hardening.
- [ ] Confirm nested paths cannot escape `--cd`.
- [ ] Confirm cache hits have no live argv and revalidate schemas.

## CI and repository

- [ ] Require the Windows and Linux GitHub Actions matrix to pass.
- [ ] Review pinned third-party action commit SHAs.
- [ ] Enable private vulnerability reporting where available.
- [ ] Configure branch protection or repository rules for the release branch.
- [ ] Confirm generated artifacts and caches remain ignored.
## Documentation and privacy

- [ ] Verify every README and API example with `--mock`.
- [ ] Confirm journal event documentation matches the implemented version.
- [ ] Document any migration required by a journal-version change.
- [ ] State that run directories and worktrees may contain sensitive material.
- [ ] State the retained-worktree cleanup procedure without automating apply,
      commit, merge, or deletion.
- [ ] Confirm the trusted-script limitation remains prominent.

## Publication

- [ ] Create a signed or otherwise attributable release commit.
- [ ] Push the reviewed commit and wait for CI.
- [ ] Create the tag only after CI succeeds.
- [ ] Publish release notes derived from `CHANGELOG.md`.
- [ ] Publish a package only from a clean, reproducible build.
- [ ] Reinstall the published artifact and repeat the smoke tests.

## Post-release

- [ ] Verify repository links, release assets, and package metadata.
- [ ] Monitor security reports and CI failures.
- [ ] Record regressions and breaking changes in the changelog.
- [ ] Preserve old journal readers or document incompatibility explicitly.
