# OBV Deviation from its SMA, over Average Volume — measured (`rd_obv_dev5`)

PandasTa issue #177. Source: Reddit, tier 4 (ResearchIntel kb/reddit.db): r/algotrading
`rd:algotrading:14rriwv` (2023-07-05), https://www.reddit.com/r/algotrading/comments/14rriwv/ —
"OBV vs SMA(OBV, 5)". Poster's words (tier 4, untested by the poster): "ADX >40 and OBV is over its
OBV_SMA. OBV SMA is a simple moving average of OBV on a 5 day count." Claimed use: SPY put-selling
trigger claimed 100% success over 10 years.

**Status: Gates A–F measured. SHIP (DISCLOSE band).**
`rd_obv_dev5` is wired into `Category["volume"]`.

Shipped: `pandas_ta/volume/rd_obv_dev5.py`, one column `RD_OBV_DEV5_{length}_{vol_length}` (default
`RD_OBV_DEV5_5_20`). Tests: `tests/test_rd_obv_dev5.py` (17). Numbers:
`python docs/measure_rd_obv_dev5.py` and `python docs/measure_rd_obv_dev5_cpu.py`. Environment:
Python 3.11.2, pandas 2.3.3, numpy 1.26.4. Measured 2026-11-26.

## This port ships only the OBV-vs-its-SMA half of the poster's condition

The poster's own trigger is two-part: "ADX >40 AND OBV is over its OBV_SMA". The ADX>40 half is not a
new feature — it is this fork's existing, already-ported `pandas_ta.trend.adx`. Combining the two
into a single boolean trigger (and backtesting the claimed 100% SPY put-selling success) is a
strategy decision for the parent repo, not a feature column; this port ships the second half as a
continuous, scale-free distance rather than the poster's own boolean read, matching the issue's own
"What" line ("OBV minus its 5-bar SMA, over average volume") and its scale-free prototype form.

## Gate A — the formula, read bar-by-bar

    OBV             = pandas_ta.volume.obv(close, volume)
    OBV_SMA5        = SMA(OBV, 5)
    AVG_VOLUME_20   = SMA(volume, 20)
    RD_OBV_DEV5     = (OBV - OBV_SMA5) / AVG_VOLUME_20

`obv()` is this fork's own existing, already-ported, already-tested On Balance Volume
(`pandas_ta/volume/obv.py`). This port re-uses that function rather than re-deriving OBV from
scratch. The "5" is the poster's own stated window ("a simple moving average of OBV on a 5 day
count"); the "20" denominator comes from the issue's own parenthetical, which states the scale-free
form directly: `(OBV - SMA5(OBV)) / SMA20(volume)`. Both are offered as parameters with those
defaults, not hard constants, per this fork's fixed-suffix-port convention (`osap_retskew_21`,
`rd_vwio_10`).

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass | An independent recompute (calls this fork's own, already-tested `obv()`, then a plain NumPy loop for both SMAs and the division — never the module's own `sma()` helper) matches the shipped column on 681 of 681 compared bars of a 700-bar synthetic close/volume walk, max\|diff\| 6.162e-15. `length=1` reduces the numerator to identically 0.0 on all 681 fired bars, pinning that a 1-bar SMA of OBV is OBV itself. |
| B Causality | pass | 9-offset future-perturbation sweep (whole tail from bar j onward scaled x1000 on both close and volume): real module leaks at 0 of 9. A mutant (`importlib`-read source, OBV shifted one bar toward the future with `.shift(-1)` before the SMAs, `exec`'d in memory) is live (differs from the real module) and leaks at 9 of 9 — a plain cumulative-sum shift moves every downstream bar, unlike a median's single-outlier robustness, so the mutant is caught at every swept offset. |
| C Reachability | pass | Synthetic: 900-bar close/volume walk (seed 11, σ=0.02): 881 of 900 finite (19-bar warm-up: `max(length, vol_length) - 1` = 19), 881 distinct values, range [-3.438930, 2.896876]. Ten independent 900-bar seeds: 881 non-NaN of 900 on every seed, 881 distinct values each. Real data (launcher's Gate E run, 89 BIST frames, 398,849 pooled bars): 397,148 non-NaN, 396,356 non-zero, 0 degenerate columns. |
| D Scale-free | pass | Price-only rescale of `close` (x8/x64/x10/x3.7): bit-identical on all 881 fired bars, matching NaN masks — OBV reads only the SIGN of `close.diff()`, so the numerator is untouched by ANY positive rescale, and the denominator (`SMA(volume, 20)`) does not read `close` at all. Volume-only rescale: bit-identical at x8/x64 (881/881 cells, max\|diff\| 0.0), within 8.216e-15 / 6.606e-15 at x10/x3.7 (well under the 1e-9 test tolerance, matching house convention). `0 < 881 < 900` fires, 881 distinct values (non-constant). Re-run clean with `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` (`docs/measure_rd_obv_dev5_cpu.py`): same 17/17 tests pass — no exact bit-count or digit beyond a stated tolerance is pinned, so the CPU-variant kernels on a GitHub runner cannot break this suite. |
| E Attribution | pass (DISCLOSE) | Launcher's Gate E run `is177-rd_obv_dev5-33cccf3e` (2026-11-26), module sha1 `084688f6ee7b85ef8085afa939328246cc48610a`, `pandas_ta_src_sha1` `62fa548b6c3016bd7ca6ffed965576e1fa7c79a9`, 89 frames, 398,849 pooled bars, 687 comparators (329 compute_all + 358 manifest), canary bit-equal on AKBNK.IS/BIENY.IS/AGHOL.IS/SASA.IS, 0 degenerate columns. `RD_OBV_DEV5_5_20`: max \|ρ\| 0.7877381604286016 vs `Dist_to_FWMA_pct_Pctl` (manifest, n = 392,431); per-frame max median 0.7931577002282519 vs `Dist_to_FWMA_pct`. Verdict `DISCLOSE` (0.76 ≤ 0.7877 < 0.80), 0.0% of 89 frames at per-frame ρ ≥ 0.90. Agrees with the prototype's own screen measurement to every digit the issue publishes (0.7877, per-frame 0.7932, n = 392,431). Ledger row recorded: `docs/gate_e_ledger.csv` (`rd_obv_dev5,RD_OBV_DEV5_5_20,DISCLOSE,...,is177-rd_obv_dev5-33cccf3e,2026-11-26`). |
| F Suites | this repo only (per the porting rules, the launcher runs both whole suites) | `python -m pytest -q tests/test_rd_obv_dev5.py tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`: see "Final suite run" below. Whole suites: run by issue-solver in clean worktrees (see the PR body). |

## Wiring counts, read back

`Category` total 413 (was 412 on `dev`'s tip at this branch's base), `Category["volume"]` 48 (was
47). README headline ("413 indicators" / "421" callable) and the `volume (48)` row updated to match;
`docs/IndicatorDictionary.md` regenerated (`RD_OBV_DEV5_5_20` tagged `SF`, warm-up 19);
`docs/MLCompanionContract.md`'s running tally updated 757 → 758 tagged columns, 383 → 384 `SF`;
`CATEGORY_TOTAL` 413 and `CATEGORY_BUCKETS["volume"]` 48 in `tests/test_altport2_ports.py`.

## Final suite run

Round 1 (`docs/RdObvDev5Measured.md` port session), `python -m pytest -q tests/test_rd_obv_dev5.py
tests/test_readme_counts.py tests/test_altport2_ports.py tests/test_wiring_accessors.py
tests/test_ml_companions.py tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
tests/test_prose_counts_match_the_csvs.py` — 1,699 passed, 7 skipped, 1 failed, measured 2026-11-26.
The 1 failure was `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
expected: `rd_obv_dev5` had no ledger row until the launcher's Gate E run.

Round 2 (this receipt session), after recording the ledger row: see "Receipt session suite run"
below.

## Receipt session — Gate E recorded, SHIP

The launcher's Gate E run (`is177-rd_obv_dev5-33cccf3e`, 2026-11-26) landed at `DISCLOSE`
(0.7877, agreeing with the prototype's own screen measurement to every digit the issue
publishes), under the 0.80 `DISCLOSE_GAP` line and far under the 0.90 `STRUCK` line. Per the
issue's Gates owed and this fork's Gate E bands, `DISCLOSE` ships as-is — no column removed, no
revert. Ledger row recorded in `docs/gate_e_ledger.csv` (`python docs/gate_e_ledger.py record
{runs}/20261126-180108-177/gatee/is177-rd_obv_dev5-33cccf3e --measured
2026-11-26`).

`pandas_ta/volume/rd_obv_dev5.py`'s docstring still reads "This session's own Gate E run is
owed; see docs/RdObvDev5Measured.md" — left as written on purpose: any edit to that file moves
`module_sha1` off run `is177-rd_obv_dev5-33cccf3e`, so the docstring stays a stale pin and the
live result is this file, not the module.

Gate D's price-only bit-identity claim ("ANY positive factor") is exact in real arithmetic but
is a float-level guarantee only for a power-of-two factor; a non-power-of-two factor can round
two adjacent closes to the same scaled value, flipping a `+1` diff sign to `0` and moving every
later OBV bar. Measured bit-identical at x8/x64 (power-of-two) and within tolerance at x10/x3.7;
sub-ulp close ties are the only theoretical exception, and they do not occur on the measured
frames (real closes are far more than an ulp apart).

## Receipt session suite run

`python -m pytest -q tests/test_rd_obv_dev5.py tests/test_readme_counts.py
tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py`
— 1,707 passed, 7 skipped, 0 failed, measured 2026-11-26 (the ledger test now passes: the row is
recorded). Both repos' whole suites: run by issue-solver in clean worktrees (see the PR body).
