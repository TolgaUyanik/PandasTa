# 02 — ALTPORT-0: triage the 20 measured AlternativeRepos gaps

**Status: DONE — 7 BUILD / 13 SKIP.** Three review rounds; round 3's fixes were
applied on the main thread after the executing agent hit a session rate limit
mid-edit (its script changes had landed, the document's had not).

Deliverables: `docs/AltportTriage.md`, `docs/gen_altport0_triage.py`,
`docs/scalecheck_altport0.py`.

## Verdicts

**BUILD (7):** `cvi` · `hvol` · `MarketFacilitationIndex` · `ProjectionBands` ·
`ProjectionOscillator` · `WilliamsAccumulationDistribution` · `smc_sweep`
**SKIP (13):** `fosc` `dx` `adxr` `avolume` `VolatilityChaikins` `Envelopes`
`RelativeMomentumIndex` `ce` `SwingIndex` `RangeIndicator` `msw` `vosc` `mavp`

BUILD means *enters ALTPORT-1 screening*. It authorises no code.

## The defect that dominated the review, and its lesson

Round 1 reported three exact identities — `fosc` diff 0.0, `dx` 7.1e-14,
`VolatilityChaikins` diff 0.0. All three were **tautologies**: each candidate
was transcribed using FORK helpers (`ta.linreg`, `ta.rma`, `ta.ema`) and then
compared against a FORK column. That comparison has no failure mode. Call the
upstream packages and all three collapse:

| row | claimed | measured upstream |
|---|---|---|
| `fosc` vs `CFO_14` | 0.0 | max abs **9.8601**, ρ 0.967784 |
| `dx` vs shipped-derived | 7.1e-14 | max abs **24.931**, 3,860/51,854 bars (7.44%), ρ 0.998721 |
| `VolatilityChaikins` vs `cvi` | 0.0 | AEFES **6.3675**, pooled **8073.93**, ρ 0.999955 |

> **Transcribing an upstream indicator with the fork's own helpers and comparing
> it to a fork column cannot return "different".**

The tell needed no measurement at all: `VolatilityChaikins` **`.round(4)`s its
own output**, so "max abs diff exactly 0.0" was impossible on its face.

## Two mechanisms worth more than the verdicts

**`fosc = cfo − 100·slope/close`.** The fork's `linreg` runs x = 1..n; classic's
runs x = 0..n−1. So `pandas_ta.linreg(tsf=True)` IS
`pandas_ta_classic.linreg(tsf=False)` (max diff 1.5e-14), and classic's TSF
projects one slope-step further. Residual 3.53e-13 over 51,866 bars. This is why
the scan's 0.950818 was right and the "identical" claim was not. (The
coordinator first proposed `+`; the sign is `−`.)

**`dx` is a correlation trap — the best finding in the file.** ρ(dx, `ADX_14`) is
only **0.576974**, comfortably ship-band, yet `dx` is algebraically
`100·|DMP−DMN|/(DMP+DMN)` from two shipped columns. A correlation-only Gate E
would have shipped it. **Algebra decides where correlation cannot.** Upstream
agreement is a separate, Gate A question and is NOT established here — classic's
`ma("rma")` SMA-seeds Wilder smoothing and the fork's `ta.rma` does not.

## A Gate D subtlety

Five BUILD forms appeared to fail ×8 invariance against upstream tti output.
All five are artifacts of **tti's own rounding** — `.round(4)`, and `.round(10)`
on `MarketFacilitationIndex` whose values are ~1e-7. Recomputed unrounded: all 0.
The transcriptions used for that recomputation were diffed against upstream at
×1 and agree to **4.99e-05 to 5.00e-05**, exactly the `.round(4)` half-ulp floor.

`SwingIndex` is genuinely different: at ×8 the `K/3` term is 8× larger so the
±100 clamp bites — **0 clamped bars at ×1, 101 at ×8** — and dividing `K/3` back
out cannot recover it. `RangeIndicator` genuinely fails unrounded at BOTH
parameterisations (83.2727 at tti's 5/3, 68.9421 at 14/3).

> Scale-invariance measured THROUGH a rounded upstream output produces false
> failures. Recompute unrounded, then prove the recomputation faithful.

## A verdict that reversed itself

`smc_sweep` was SKIPped on the argument that the fork's `liquidity_sweep` covers
it. Asked to run the ±1-bar event-coincidence rate it had itself named as the
right metric, it measured **133/895 (14.9%) and 132/881 (15.0%)** — far below the
~0.7 bar — which refuted its own stated reason. Flipped to BUILD, labelled the
weakest of the seven, since the concept is still shared and no statistic on two
~1.7%-density flags will settle it.

## Two claims that were decorative until challenged

- **"The engine ships no donchian-derived column."** Written from a grep for
  `DCU`/`DCL`. `indicator_engine.py:1278-1329` emits a twelve-member Donchian
  distance grid, and the comment at `:1367-1369` says so in words. Searching for
  a NAME instead of the thing — the same defect the altrepo scanners kept
  producing. The real adversary for rows 6 and 7 is
  `dist_low_*`/`dist_from_high_*` at **0.832368**, and `:1373-1396` records the
  engine already DELETING `dist_to_bb_*_pct` at r 0.9429/0.9379 against exactly
  those columns. BUILD survives; the reason was fabricated.
- **The ticker guard.** Reported as "caught by an in-script glob resolver". It
  caught nothing — a bogus list printed a warning, loaded 3 frames and exited 0.
  Now a real `sys.exit`, verified by negative control: bogus list → **exit 1**
  naming the drift.

## Open, carried into ALTPORT-1

- `hvol` sits at **0.821076** vs `NATR_14` BEFORE the full sweep, and its nearest
  shipped column by construction is **unmeasured**: `indicator_engine.py:436`
  computes `rel_vol_20` as `hvol_20`'s own numerator over a per-date constant.
  Measure that first.
- `pb_lo_dist_pct` is proposed but in no script's FORMS; its ×8 invariance is
  inferred from identical construction, not run.
- `mavp` is the one verdict resting on no measurement from this run.
