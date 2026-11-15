# g191_044 — measured (issue #60)

> **Status: Gates A-E cleared, SHIP. Measured 2026-11-09 (Gate E, issue-solver run `is60-g191_044-25648565`).**

Decayed low-volume correlation rank + VWAP momentum rank: Guotai Junan's
(2017, "GTJA191", internal quant report, read via the HKUDS/Vibe-Trading
copy, MIT) alpha `#44`, per issue #60's own instruction. Module
`pandas_ta/statistics/g191_044.py`, column `G191_044_10_7_6_4_3_10_15`.
Tests: `tests/test_g191_044.py` (23, all passing). Numbers below:
`python docs/measure_g191_044.py`. Environment: this worktree's pinned
pandas/numpy. Measured 2026-11-09.

## Gate A: derivation from the published formula, not the prototype

Issue #60 states GTJA191 alpha `#44`:

    TSRANK(DECAYLINEAR(CORR(LOW,MEAN(V,10),7),6),4)
    + TSRANK(DECAYLINEAR(DELTA(VWAP,3),10),15)

with the issue's own parenthetical conversion: "VWAP -> (H+L+C)/3".

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own
named copy -- HKUDS/Vibe-Trading (MIT) -- was never read. Everything below
is derived from the issue's own stated formula string plus its own
parenthetical instruction, per the issue's own rule ("Gate A starts from
the source formula, not the prototype"), then cross-checked against the
issue's own prototype (`docs/issues/screen/ind_screen.py:362-366`):

    def _(o, h, l, c, v):
        return (tsrank(decaylinear(corr(l, mean(v, 10), 7), 6), 4)
                + tsrank(decaylinear(delta(tp(h, l, c), 3), 10), 15))

No disclosed interpretation choice was needed -- the issue's own string and
the prototype agree exactly, including every window length. Operators,
each read directly off the prototype's own module source
(`ind_screen.py:46,47,52,53,79-81,109`): `MEAN`/`DELTA`/`TSRANK`/`CORR`
match the convention every other `g191_*` port in this fork already
relies on; `DECAYLINEAR(X,d)` is a trailing `d`-bar weighted average with
weights `1..d` (current bar weighted highest), normalised to sum to 1;
`TP = (H+L+C)/3` is the VWAP proxy, matching the issue's own parenthetical.

### Warm-up: a disclosed necessary condition

The two branches are PARALLEL, not chained. Branch 1 (`mean_v_length=10,
corr_length=7, decay1_length=6, tsrank1_length=4`) needs `mean_v_length +
corr_length + decay1_length + tsrank1_length - 3 = 24` bars. Branch 2
(`delta_length=3, decay2_length=10, tsrank2_length=15`) needs
`delta_length + decay2_length + tsrank2_length - 1 = 27` bars. The true
warm-up is the max of the two: `min_length = 27` at the shipped defaults,
enforced by `verify_series`; `tests/test_g191_044.py::
test_term1_branch_dominates_the_warmup_when_larger` proves the max-of-two
logic directly, by pushing branch 1's own window lengths far above
branch 2's.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula plus its own parenthetical conversion, matching the issue's own prototype line-for-line | Spot-checked against an independent per-bar computation (plain numpy `np.corrcoef`/`np.dot` over explicit slices, not the module's own vectorised `.rolling()` calls), both at small lengths (`mean_v_length=3, corr_length=3, decay1_length=2, tsrank1_length=2, delta_length=1, decay2_length=2, tsrank2_length=2`, 3 bars on a 60-bar frame) and at the shipped defaults (3 bars on a 900-bar frame): every one of the 6 spot-checked bars matches the module's float64 output exactly, e.g. `t=300 module=1.0166666666666666 independent=1.0166666666666666`, `t=899 module=0.9166666666666666 independent=0.9166666666666666` (`python docs/measure_g191_044.py`) |
| B Causality | pass | Future-perturbation sweep (OHLCV series rewritten from `j` onward, another synthetic frame), 34 offsets past the 27-bar warm-up: real module **0 of 34** leaks (`python docs/measure_g191_044.py`). Two independent mutants (`importlib` source read, `exec`'d in memory, each shown live-different from the real module): shifting the final write index `tsrank2_length=15` bars into the future -- caught at **34 of 34**; flipping the backward `DELTA` (`tp.shift(delta_length)`) into a FORWARD shift (`tp.shift(-delta_length)`) -- caught at **30 of 34**. The 4 misses were isolated and CONFIRMED, not hand-waved: at those 4 offsets the leaked future segment is an unrelated random walk, so the corrupted `delta_tp` differs by TENS of units (e.g. `j=270`: base `[-0.71, 0.40, 1.87, 3.12]` vs perturbed `[-0.71, 33.11, 34.64, 34.21]`) -- but `term2` ITSELF (isolated by subtracting the independently-computed `term1`, identical in both runs at these specific bars because `term1`'s own lookback window -- `mean_v_length+corr_length+decay1_length+tsrank1_length-3 = 24` bars -- never reaches the perturbation boundary `j` for `t < j`, from the mutant's full output) is measured at **exactly `1.0` in BOTH the base and the perturbed run, at all 12 bars** (3 bars x 4 offsets, `python docs/measure_g191_044.py`): `TSRANK` is a `[0,1]`-bounded order statistic, so once the TRUE value already sits at its own 15-bar window's rank ceiling, an even larger outlier still ranks `1.0` -- the corruption is provably invisible to a rank-only comparison at exactly those bars, not merely plausible |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic OHLCV series (seed 11, see `docs/measure_g191_044.py:_ohlcv`), shipped default: **1,474 of 1,500** bars non-NaN (98.27%), first valid at bar 26 (exactly the structural warm-up boundary, `min_length - 1`). **60 distinct values** observed -- an INHERENT ceiling, not a bug: `TSRANK(x,n)` with no ties is a plain integer rank out of `n`, so `term1` (`tsrank1_length=4`) has at most 4 distinct values and `term2` (`tsrank2_length=15`) has at most 15; their sum has at most `4*15=60` combinations, matching exactly what is measured. Range `[0.316667, 2.000000]`, median `1.183333` |
| D Scale-free | pass | `CORR` is exactly invariant to a positive rescale of either input, `DECAYLINEAR` is a fixed-weight linear combination of an already-invariant (or linearly-scaling) series, and `TSRANK` is an order statistic invariant to ANY positive rescale of its own input -- so both branches are scale-free BY CONSTRUCTION, for price (`high`/`low`/`close`) and volume rescaled INDEPENDENTLY. Measured on the 1,500-bar series: PRICE x8/x64/x10/x3.7 **all bit-identical, 0.0 max\|diff\|**, and VOLUME x8/x64/x10/x3.7 **all bit-identical, 0.0 max\|diff\|** -- not merely the power-of-two cases, since `CORR`'s invariance and `TSRANK`'s rank-ordering are exact for ANY positive `k`, leaving no floating-point rounding residual at all (unlike a ratio- or correlation-only column, which still carries scalar-multiply rounding). `0 < 1,474 fires < 1,500` and `60 > 1` distinct values rule out a constant column |
| E Attribution | **SHIP** | `G191_044_10_7_6_4_3_10_15`: max \|rho\| **0.6081050199445434** vs `smi_SMIo_5_20_5` (manifest comparator set), n = 376,794; per-frame max median \|rho\| **0.6059791400351803** (same comparator, `smi_SMIo_5_20_5`), 89 frames, 0.0% of frames >= 0.90. Both the pooled max (0.6081 < 0.76) and the per-frame max median (0.6060 < 0.90) clear the `r3-perframe-0.90` SHIP band in CLAUDE.md. Run `is60-g191_044-25648565`, 687 comparators (329 `compute_all` + 358 `manifest`), 89 ALTPORT-1 frames, canary bit-equal (`AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS`). Ledger row recorded in `docs/gate_e_ledger.csv`. |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **294 -> 295** (`statistics` **26 -> 27**); `df.ta.<name>()`
accessor count **302 -> 303**. Touch points:
`pandas_ta/statistics/g191_044.py` (module),
`pandas_ta/statistics/__init__.py` (export), `pandas_ta/__init__.py` ->
`Category["statistics"]` (discovery), `pandas_ta/core.py` ->
`AnalysisIndicators.g191_044` (accessor), `tests/test_g191_044.py`
(tests). `README.md`'s headline and `statistics (27)` row, and
`docs/IndicatorDictionary.md` (regenerated), both updated and checked by
`tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s running tag
count updated **639 -> 640 / 282 -> 283 `SF`** (`G191_044_10_7_6_4_3_10_15`
probes cleanly at the dictionary's 600-bar synthetic frame and takes many
distinct values, so the generator tags it `SF`). `tests/test_altport2_ports.py`'s
`CATEGORY_TOTAL` updated to match (294 -> 295); no `CATEGORY_BUCKETS` entry
needed (that dict only tracks `trend`/`volatility`/`volume`, not
`statistics`).

Gate E ran via the launcher (`gate_e_overlap.py`, Backtesting #107) and the
ledger row is recorded (`docs/gate_e_ledger.csv`, `python docs/gate_e_ledger.py
record ... --measured 2026-11-09`). `mtd_ret` is still owed in the same
assertion, pre-existing and unrelated to this port (carried over from
issue #206, per `docs/G191026Measured.md`'s identical note).

## Suite run (this repo, this session)

`python -m pytest -q`, full suite, default collection order: **3 failed,
4719 passed, 83 skipped**. `g191_044`'s own tests (`tests/test_g191_044.py`):
**23 passed**. Pre-existing / expected failures, all unrelated to this
port's correctness (CLAUDE.md "Known breaks" plus this port's own owed
Gate E row):
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
(owed for `['g191_044', 'mtd_ret']` -- `g191_044`'s row is owed by design
per this session's override rules; `mtd_ret` pre-dates this session),
`tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this
worktree) and `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
(untracked `docs/pine/` corpus). No other test regresses.
