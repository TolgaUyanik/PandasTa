# Brutally Honest Review — maxvol_adv, rounds 3-4 (PR #197 rounds 1-2)

Rounds 1-2 are `2026-10-28-maxvol-adv-review.md` and `-r2.md` (the author's, before the PR).

**Date:** 2026-10-29
**Target:** branch `B2-MAXVOL14-ADV50` vs `origin/dev` — round 3 at `2f05b20`, round 4 at `5dfa8ea`
**Final verdict:** PASS (round 4)
**Type:** code (+ text for the docs)

## Round 3 (PR round 1) — `2f05b20` — **Verdict: REVISE** (2 MAJOR, 5 MINOR, 3 NIT)

### MAJOR
- **docs/MaxvolAdvMeasured.md:3-6, :58, :72 (Gate F)** — Gate F not met by the PR's own banner; the Backtesting suite was not run.
  - Fix: run both suites at HEAD, record counts and failing-id diff, flip the banner.
  - **Applied (5dfa8ea):** this repo 2 failed / 3258 passed / 83 skipped (only the two CI deselects); Backtesting 16 failed / 1584 passed / 4 errors with this branch and with dev, identical 20 failing node ids.
- **docs/MLCompanionContract.md:27; tests/test_altport2_ports.py:162-163** — "Gate E pending" contradicts the ledger in the same diff.
  - Fix: quote the ledger rows.
  - **Applied:** RCR_100 0.4827 / MAXVOLADV_14_50 0.7003 SHIP; PFE_10_5 0.9285 STRUCK (#23); KFT_DIST 0.8791 DISCLOSE_GAP, KFT_VEL 0.9938 STRUCK (#22).

### MINOR
- **Gate F table (MaxvolAdvMeasured.md:60-72)** — described pre-merge base d7fd91d, listed the since-fixed wilder_rma failure. **Applied:** replaced with the 2026-10-29 measurement; the old pandas-3 row is kept, labelled as the author's earlier run.
- **Prototype "not on this machine / was not read"** (doc :18-22, module docstring :47-50, Gate A row) — it exists at `docs/issues/screen/ind_screen_r8.py:116-118`. **Applied:** cited, read; one divergence stated (negative ADV finite there, NaN here).
- **NaN-blanking off by one / wrong for short > long** (module :56-57, doc :53, test docstring :20-21). **Applied:** "itself and the next max(short, long) − 1 bars"; `short=80` case asserted in `test_edge_cases`.
- **docs/EquivalentStrategies.md** — out of scope, numbers unqualified. **Applied the "if it stays" fix:** kvo 0.8986 labelled stage-2 per-frame max median, 12 frames, not Gate E; #193 frames labelled synthetic. Not moved to its own PR (author's file; owner's call).
- **guard workflow did not run on #197** (outside the diff; CLAUDE.md:42-46). **Not applied in this PR** — outside its scope. `pull_request_target` takes the workflow from the default branch (`main`), which has no workflows. Needs its own change (land the guard on `main`, or correct CLAUDE.md): tracked as #207.

### NIT
- **Gate E run not locatable** — **Applied:** run dir, Backtesting `91ab7ae2`, engine_code `f58eb5da`, pandas_ta_src_sha1 `8a2d3e46`, exact `--name`.
- **"pool was not inspected" reads open; 22 zeros unexplained** — **Applied:** settled by Gate E (top two 0.7003 / 0.5828); zeros explained from the formula.
- **PR body empty, #191 not named** — **Applied in the doc header and commit;** PR body edited on push.

Gate E was re-run after the docstring edit changed the module sha1 (`gatecheck-20261029-maxvol_adv-r2`): identical numbers; ledger row re-recorded.

### Summary (round 3, verbatim)

The code is right. It is a correct four-line ratio, and its zero/negative-ADV handling holds: pandas returns exactly 0.0 for an all-zero window, measured even after fractional volumes. It is causal: real module 0/31, both look-ahead mutants 31/31, with the ×1000 future closing the max-hiding hole. It is scale-free: I reproduced 2.2167e-16 / 3.9249e-16 and the 1.129–7.358 range. All five wiring touch points are present, and 174 targeted tests pass locally. The Gate E ledger row matches overlap_max.csv and meta.json field for field (0.7002603748771254, pvo_PVOs_12_26_9, n 394,488, per-frame 0.74506, 394,488 / 394,466, 687, canary bit-equal), and Gate C's 4,361 = 89 × 49 checks out. The paperwork is where it fails. Gate F, a hard requirement, is unmet by the PR's own banner. The commit whose only job was to record Gate E left two sentences this PR wrote still saying "Gate E pending", against the ledger it just edited. The Gate F table describes a pre-merge tree and lists a failure that is now fixed. The doc says the prototype "is not on this machine" while it sits in the owner's docs/issues/screen/, hiding one real divergence. The NaN-blanking claim is off by one and wrong for short > long. An out-of-scope EquivalentStrategies.md rides along with unqualified numbers. Fix the two MAJORs and the MINORs, run Gate F, then merge.

## Round 4 (PR round 2) — `5dfa8ea` — **Verdict: PASS** (0 CRITICAL, 0 MAJOR, 2 MINOR, 6 NIT)

All round-3 fixes verified: ledger `module_sha1` 2c694d96 recomputed at HEAD, every value field matches the r2 run, r1/r2 Gate E outputs byte-identical, prototype citation accurate, local and Backtesting counts match the evidence files. Remaining findings, all applied in the next commit unless noted:

- **MINOR — EquivalentStrategies.md kvo row** says "same formula; only adds a scale fix", which the code contradicts: kvo signs a zero hlc3 change 0 and the candidate +V, and kvo's `ema` is SMA-seeded while the candidate's `ewm(adjust=False)` is not. `MFI_Pctl 0.7989` was unlabelled. **Applied:** differences listed (non-exhaustive), MFI figure labelled prototype Gate E `screen_r8_20261026`.
- **MINOR — Gate F provenance:** the evidence files did not record which pandas_ta each Backtesting run imported. **Applied:** each run printed its import path (captured in the run's output); tree sha1s `efca0690` (dev) and `8a2d3e46` (branch) now cited.
- **NIT — "one case only"** omitted the short-frame API difference (`None` vs all-NaN). **Applied in the doc;** the module docstring ("the one difference is a negative ADV") speaks of the ratio and was left alone, since editing it would force another Gate E run.
- **NIT — short=80 gap count unpinned.** **Applied:** `assert int(gap80.isna().sum()) == 79 + 80`.
- **NIT — environment line** scoped to Gates A/B/D; Gates C/E/F environment added. **Applied.**
- **NIT — review record not in the PR / numbering.** **Applied:** this file, committed as `docs/reviews/2026-10-29-maxvol-adv-review-r3.md`.
- **NIT — PR body empty.** **Applied on push** (body with `Refs #191`, gates, Gate F basis).
- **NIT — guard deferral untracked.** **Applied:** #207.

### Summary (round 4, verbatim, abridged to the verdict)

Every round-1 fix I checked is real. [...] The code is still a correct, causal, scale-free four-line ratio. What is left is paperwork. [...] Gate F is honestly stated as "no regressions" rather than "green", and the merge is rightly left to the owner. None of the findings is CRITICAL or MAJOR, so it passes. Fix the two MINORs before pushing.
