# run summary — auto-2026-11-13-ts-cid-ce-20

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| ts-cid-ce-20 (issue #95) | **ESCALATED at the round cap** — all round-4 fixes applied, no reviewer has seen the post-round-4 prose | 4 (REVISE / REVISE / REVISE / REVISE, every finding applied or explicitly declined with a reason) | `pandas_ta/statistics/ts_cid_ce_20.py` (new), `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `tests/test_ts_cid_ce_20.py` (new), `tests/test_altport2_ports.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `docs/TsCidCe20Measured.md` (new), `docs/measure_ts_cid_ce_20.py` (new), this folder | 1. **Gate E is owed** — the launcher runs it; a receipt session records the ledger row and answers the three open items in `docs/TsCidCe20Measured.md`. 2. **Re-read the four paragraphs rewritten in round 4** (`01-ts-cid-ce-20.md`, "Fixes applied, and why there is no round 5"). 3. **`pandas_ta/core.py:453`/`:692` mutate the live `Category` list** — pre-existing, order-dependent, owner's call. |

## What shipped

`TS_CID_CE_20` — tsfresh's `cid_ce(x, normalize=True)` on 20 simple returns,
`sqrt(sum (r[i]-r[i-1])**2 / var(r))`, registered in `Category["statistics"]`
with the five wiring touch points and 132 tests. Dimensionless, affine-
invariant in the returns, bounded in [0.701759, 8.916700], bit-identical under
a ×8/×64 price rescale, causal at 0/35 offsets of a perturbation sweep.

## What the rounds changed, in one line each

| round | verdict | what it cost |
|---|---|---|
| 1 | REVISE (2 MAJOR) | the 1e+8 accumulator failure was measured but undocumented and untested; the manifest cited a review log that did not exist. Four more numbers tightened; the unjustified `gap >= 0` guard deleted. |
| 2 | REVISE (1 CRITICAL, 1 MAJOR) | round 1's own fix overclaimed ("NaN to the end of the series" at a magnitude where 156 bars fire); the prototype accuracy figure had been measured against a different oracle. |
| 3 | REVISE (1 MAJOR) | the Cost section was a receipt for the pre-deletion spelling (32.4 MB against the shipped 29.2 MB); two mutant-cell counts and the Jensen sentence were still wrong. |
| 4 | REVISE (1 CRITICAL, 1 MAJOR) | the test module's header still carried round 2's retracted sentence, a renamed test and the demoted sibling control; the mutant counts were wrong again. All prose; all applied. |

The pattern, named rather than buried: the magnitude story lives in four
files and nothing enforces their agreement. Every CRITICAL in this run was a
copy that a previous round's fix did not reach — not an arithmetic error.
The mathematics passed every round from the first.

## Assumptions logged

Eight, in `00-manifest.md` (Phase 2), each taking the smaller-scope reading
because `AskUserQuestion` is unavailable in a headless run. The two that
matter most: Gate E is **not** run here, and the per-return magnitude bound
was **not** tightened to make the accumulator failure local (the crossover is
a function of the window's own scale, the local spelling costs 35.7 s against
55–59 ms, and every neighbouring port that divides by a rolling variance
behaves the same way).
