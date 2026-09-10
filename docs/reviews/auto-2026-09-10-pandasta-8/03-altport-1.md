# 03 — ALTPORT-1: Gate E screen of the seven BUILDs

**Status: DONE at the 3-round cap.** 1 STRUCK · 4 disclosure · 4 ship by the band;
the SURVIVOR SET going to ALTPORT-2 is a separate question, unresolved — see below.

Deliverables: `docs/AltportScreen.md`,
`../Backtesting/scripts/analysis/measure_altport1_overlap_full.py`, 11 CSVs in
`backtest_results/altport1/`, `../Backtesting/tests/test_comparators.py` (14 passed).

## The measurement

89 BIST_100 daily frames, 408,253 pooled bars, **492 engine comparators**
(485 numeric + 1 bool + 6 ordered), `n_unmapped` and `n_unmapped_values` both 0
on all 89 rows.

| column | pooled max ρ | against | per-frame median | ≥0.90 on | verdict |
|---|---|---|---|---|---|
| `C_POSC_14` | 0.894742 | `cfo` | **0.910212** | **62.9%** | **STRUCK** |
| `C_WAD_BAR_SF` | 0.889416 | `percent_return` | 0.889192 | 12.4% | disclosure |
| `C_PB_WIDTH_PCT` | 0.874411 | `natr` | 0.864806 | 1.1% | disclosure |
| `C_HVOL_20` | 0.834724 | `natr` | 0.831216 | 4.5% | disclosure |
| `C_PB_UP_DIST_PCT` | 0.773573 | `dist_from_high_5` | — | — | disclosure (written rung) |
| `C_PB_LO_DIST_PCT` | 0.727354 | `cfo` | — | — | ship |
| `C_MFI_BW_SF_20` | 0.536816 | `vol_at_low_ratio` | — | — | ship |
| `C_CVI_10` | 0.501290 | `CHOP` | — | — | ship |
| `C_SMC_SWEEP` | 0.161383 | `CCI` | — | — | ship |

## What three review rounds actually corrected

**Round 1 — the band gap was manufactured.** `CLAUDE.md:98` writes "ρ ~ 0.9",
approximate on purpose; 0.894742 is that. The gap appeared only after rewriting
it as ">= 0.90 exactly" and routing the orphan into the most permissive rung. The
proof the decision preceded the prose: `_verdict` defined `DISCLOSE = 0.80` and
never called it.

**Round 1 — one estimator where the repo's law uses two.** The harness pooled
first and correlated once; no per-frame ρ existed anywhere. `FINDINGS.md`'s
SEMANTIC-DUPLICATE LAW killed a column at pooled 0.879 with 29.2% of frames >0.9.
POSC is worse on both legs. **Pooling DEPRESSES ρ here** (0.9102 → 0.8947), so
pooled-only was the permissive reading.

**Round 2 — the headline CSV was never regenerated.** Every other artifact was
rerun; the one file the verdict was quoted against still read `DISCLOSE` for POSC
and lacked the `verdict_permissive_ge090` column the document claimed made the
choice auditable. Now stamped `verdict_schema` with stages 6/7 exiting on a
mismatch — the failure mode is an error rather than a silence.

**Round 3 — the threshold was fitted and is now gone.** `REVERT_APPROX = 0.89`
sat 0.0006 above WAD and 0.0053 below POSC — the one value striking exactly one
column, which the document advertised. **Deleted.** The gap now resolves on the
per-frame leg at the same 0.90 the band already names. No new constant.

## THE OPEN RULING — what ALTPORT-2 receives

The two halves of this chain applied different laws. ALTPORT-0 SKIPped `vosc` at
ρ **0.753468** for restating `pvo`, noting explicitly that a correlation-only
gate would have passed it. ALTPORT-1 then shipped `PB_WIDTH_PCT` at **0.874**
while calling it *"a range-width restating a range-width"*.

Applying ALTPORT-0's question test to all eight non-struck columns:

- **Clear on both standards — 3:** `CVI_10`, `MFI_BW_SF_20`, `SMC_SWEEP`
- **Skipped on question-redundancy — 3:** `HVOL_20` and `PB_WIDTH_PCT` (both
  vs `natr`), `WAD_BAR_SF` (vs the signed daily return)
- **Conditional on one ruling — 2:** `PB_UP_DIST_PCT`, `PB_LO_DIST_PCT`

⚠ **The coordinator proposed 4 and was wrong.** That set keeps `PB_LO` (0.727)
and drops `PB_UP` (0.774) — separated by 0.046 of ρ either side of the `vosc`
number — but they are the SAME construction mirrored, both slope-corrected,
both against the same Donchian grid. **Splitting them on a correlation threshold
IS a correlation gate**, which is the thing the question standard exists to
override. Coherent answers are **5 or 3, never 4.**

**The ruling, in one sentence: is slope-correcting a Donchian band a new
economic question, or a better estimator of one already shipped?**
Yes → 5. No → 3.

**ASSUMPTION (logged, Phase 2 closed): taken as NO → 3 survivors.** The
conservative reading, smallest blast radius, and consistent with ALTPORT-0's own
`msw` reasoning — *"low ρ says the estimator disagrees, not that the question is
new"*. The owner can overturn this to 5; it is a judgement about economic
questions, not a measurement.

## Findings that outlive the task

- **Pooling can depress ρ.** POSC pools to 0.8947 from a per-frame median of
  0.9102. Any Gate E taken on the pooled figure alone is the permissive reading
  and should say so.
- **A threshold chosen after seeing the numbers is not a reading of the
  contract.** 0.89 struck exactly one column and the document said so admiringly.
- **`smc_sweep`'s null:** 200 per-frame circular shifts give 11.10% ± 0.38
  against an observed 20.96% — **1.89× enrichment, not "79% disjoint"**. Stated
  as an upper bound on bar-level alignment, since a circular shift also destroys
  shared time-varying density.
- **Gate D on every tti-derived column fails bit-identity at ×8** (PB_LO 0.0336,
  POSC 0.481) — tti's `.round(4)`, not a real defect, but Gate D must be re-run
  on the ported fork implementations rather than inherited.
- **De-rounding is not always conservative.** It moved `MFI_BW_SF_20` by
  **−0.0366**, the anti-conservative direction the original argument assumed
  impossible.
- **TVPTA-9 remains open.** One of 15 harnesses was converted to the 492-column
  comparator surface. The repo-wide blind spot is not closed.
