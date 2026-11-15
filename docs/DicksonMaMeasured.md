# Dickson Moving Average distance — measured and reverted (`dickson_ma`)

The close's percent distance from Nathan Dickson's moving average (DMA), the mean of
Ehlers & Way's error-correcting EMA (EC) and Alan Hull's moving average (HMA):
`DMA = (EC(30) + HMA(7)) / 2`. Issue #147 (BT-DMA-DIST), found by the 2026-10-24 library
catalog screen, round 4 (backtrader `DicksonMovingAverage`, GPL-3.0). backtrader shows only
that the indicator exists; the module was written from the definitions below as recalled,
and no backtrader code was read.

**Status: REVERTED on Gate E — STRUCK.** issue-solver's Gate E run on the port (code at
0156f88): `DICKSON_DIST_30_7` max |ρ| **0.8927** vs `Dist_to_PP_pct` (manifest), n = 374,196;
that comparator's per-frame median |ρ| is **0.9023** over 89 frames, with 52.8% of frames
≥ 0.90. Schema `r3-perframe-0.90` → **STRUCK**; pooled-only would have been DISCLOSE_GAP.
The module, its export, its `Category` entry, its accessor, its tests and its measurement
script are gone, and `README.md`, `docs/IndicatorDictionary.md`,
`docs/MLCompanionContract.md` and `tests/test_altport2_ports.py` are back at base `b0422ad`
(*Closed* below). Gates A and C were **not completed**; a revert does not owe them. This file
is the receipt; #147 closes as a measured revert.

Built and measured at 0156f88, now deleted: `pandas_ta/overlap/dickson_ma.py`, one column
`DICKSON_DIST_<length>_<hull_length>` (default `DICKSON_DIST_30_7`), in percent; tests
`tests/test_dickson_ma.py` (39, from pytest); `docs/measure_dickson_ma.py`. Read any of them
with `git show 0156f88:<path>`. Where the numbers come from: the Gate E numbers are read from
the launcher's output files (*Gate E* below); the pre-revert measured values were printed by
`docs/measure_dickson_ma.py` at 0156f88; the exceptions are the suite counts in Gate F and the
test count (pytest), the prototype figures quoted from the issue (marked *quoted*), the
dictionary / contract / README counts (`git diff b0422ad 0156f88`), the Gate E timing
(`run.log`, `journal.json`, `git log`), and quantities obtained by arithmetic from printed
ones (marked *derived*). Environment: numpy 1.26.4, pandas 2.3.3, Python 3.11.9. Measured
and Gate E 2026-10-25; the revert 2026-10-26.

## Sources, and how far each was checked

| source | used for | how it is known |
|---|---|---|
| backtrader `dma.py` (GPL-3.0) | that the indicator exists; the formula line `(EC(30) + HMA(7)) / 2` and the defaults 30 / 7, both as quoted in the issue | the issue text; the file was not opened |
| J. F. Ehlers and R. Way, "Zero Lag (Well, Almost)", *Technical Analysis of Stocks & Commodities*, Nov 2010 | EC, from its EasyLanguage listing | **recalled, not fetched**: the porting session had no web access and no copy of the paper. The listing below is the transcription the test oracle implemented |
| N. Dickson, "Dickson Moving Average", r/algotrading (2016) | the combination `(EC + HMA) / 2` | recalled as the post backtrader's docstring links (that docstring was not opened either); not fetched |
| A. Hull, alanhull.com | HMA | the fork's own upstream `hma`, checked against an independent loop written from Hull's formula |

The module and the test oracle came from the same recall. The oracle therefore proves that
the module computed the listing below; it cannot catch a misremembered constant (GainLimit
50, the 0.1 gain step, the strict `<`, the defaults 30 / 7). That is why Gate A is recorded
as not completed, and why step 0 of *If this is ever un-reverted* exists.

The EC listing as transcribed (line numbers are this document's, used by Gate A):

```
L1   Inputs: Length(20), GainLimit(50);
L2   Vars: alpha(0), Gain(0), BestGain(0), EC(0), Error(0), LeastError(0), EMA(0);
L3   alpha = 2 / (Length + 1);
L4   EMA = alpha*Close + (1 - alpha)*EMA[1];
L5   LeastError = 1000000;
L6   For Value1 = -GainLimit to GainLimit Begin
L7       Gain = Value1 / 10;
L8       EC = alpha*(EMA + Gain*(Close - EC[1])) + (1 - alpha)*EC[1];
L9       Error = Close - EC;
L10      If AbsValue(Error) < LeastError Then Begin
L11          LeastError = AbsValue(Error);
L12          BestGain = Gain;
L13      End;
L14  End;
L15  EC = alpha*(EMA + BestGain*(Close - EC[1])) + (1 - alpha)*EC[1];
```

## Gate A — line by line, against the recalled listing (not completed)

Module line numbers are `pandas_ta/overlap/dickson_ma.py` at 0156f88
(`git show 0156f88:pandas_ta/overlap/dickson_ma.py`; re-read 2026-10-26).

| listing | `pandas_ta/overlap/dickson_ma.py` | note |
|---|---|---|
| L1 `GainLimit(50)` | :7 `GAIN_LIMIT = 50` | fixed, not a parameter |
| L1 `Length(20)` | :38 `length ... else 30` | default 30 is backtrader's, per the issue; the paper's 20 is not used |
| L3 | :14 | |
| L4 | :23 | |
| L5 `LeastError = 1000000` | :25 `argmin` over all candidates | **departure**: the search starts from +inf. 1000000 is a price-unit constant; once \|Close − EC\| ≥ 1e6 for every gain, the listing keeps the previous bar's BestGain (EasyLanguage variables persist across bars), so the output would depend on price scale |
| L6–L7 | :15 `arange(-GAIN_LIMIT, GAIN_LIMIT + 1) / 10` | the same doubles as `Value1 / 10`: both are a correctly rounded integer / 10 |
| L8 | :24 | the same expression in the same operation order, vectorised over the 101 gains |
| L9–L13 | :25 `argmin(npabs(x[t] - cand))` | `argmin` returns the first minimum, i.e. the lowest gain on a tie, which is what the strict `<` scanning upward from −GainLimit keeps |
| L15 | :25 `cand[...]` | L15 recomputes L8 at BestGain, the same double as the stored candidate |
| `EMA[1]`, `EC[1]` start at 0 (L2) | :20–22 | **departure**: both are seeded on the first valid close. From 0 the EMA would start at alpha × Close, about 6% of price at length 30 (*derived*: 2/31); the head is masked instead (see *Warm-up*) |
| HMA (Hull) | :50 `hma(x, length=hull_length)` | `WMA(2 × WMA(int(n/2)) − WMA(n), int(sqrt n))`: at n = 7 that is WMA(2 × WMA(3) − WMA(7), 2) |
| DMA | :50 | `(EC + HMA) / 2` |
| distance | :51 | `100 × (close / DMA − 1)`; a non-positive DMA emits NaN |

Measured against the oracle at 0156f88 (`tests/test_dickson_ma.py::literal_ec`, a scalar loop
that follows L3–L15, and `literal_hma`, two nested WMA loops from Hull's formula; the
oracle's warm-up mask is a literal table, not the module's `_warmup`):

| check | measured |
|---|---|
| EC, bit-identical bars, lengths 10 / 30 / 50 (3 walks × 899 valid bars, *derived*: 900 bars minus one NaN bar each) | 2,697 / 2,697 at each length |
| distance vs oracle at (30, 7) / (10, 4) / (50, 16), 1,200-bar walk with one NaN bar | max \|diff\| 0 / 0 / 4.4e-14; NaN masks equal; n 915 / 1,103 / 720 |
| hand check, closes (10, 11), length 30: the best gain wants 1/alpha − alpha = 15.4 > 5 (*derived*), so it clamps at +5 and EC[1] = 10 + alpha² + 5·alpha | module 10.326742976066598, formula 10.326742976066598 |
| constant close 37.5, 600 bars | max \|distance\| 2.2e-14 |
| a one-bar drop held flat for 20 bars after 400 closes at 100: which drops make DMA ≤ 0 (grids 0.500–0.998 step 0.001, 499 points; 0.99800–0.99999 step 1e-5, 200 points) | none on the coarse grid; on the fine grid the first hit is 0.99806 (0.99805 misses) and every point above it hits; the test's 99.999% drop gives DMA ≤ 0 on 1 bar |
| the round-4 prototype `bt_dma_dist` × 100, past the warm-up (σ 0.005 / 0.02 / 0.05) | max \|diff\| 4.4e-14 over 2,723 bars each |

The last row is a cross-check, not Gate A: the prototype lives in the gitignored
`docs/issues/screen/`, so the script ran that block only where the folder exists. On these
NaN-free, all-positive walks the port computed what the screen measured, apart from the head
mask.

The oracle comparison is not vacuous: the test also asserted that its walks land the gain
search both on the clamp and strictly inside it.

### What the gain search actually does

Oracle BestGain over 3,000-bar walks (seed 1, length 30, 2,999 searched bars each):

| σ per bar | +5.0 | −5.0 | interior |
|---|---|---|---|
| 0.005 | 97.4% | 1.4% | 1.2% |
| 0.02 | 97.3% | 1.2% | 1.4% |
| 0.05 | 97.1% | 1.3% | 1.5% |

On a clamped bar, EC = alpha·EMA + 5·alpha·Close + (1 − 6·alpha)·EC[1] (algebra from L8 at
g = 5). That is a fixed two-pole filter of the close at length 30 (*derived*): pole
1 − 12/31 = 0.613 from EC's own recursion and 29/31 = 0.935 from the EMA it is fed, which
carries 1/6 of the DC gain (alpha / 6·alpha). So the "error-correcting" part mostly reduces
to a constant gain. On the proxy below the distance's closest comparator is `ROC_1`.

## Warm-up (the head, not only the tail)

The EMA's seed error decays as (1 − alpha) per valid close. The warm-up was
`ceil(ln 1e-8 / ln(1 − alpha))` **valid closes** (finite and > 0; a missing bar does not
shrink the seed error), computed from `length` alone. It is 277 at length 30, 92 at 10 and
461 at 50 (all three pinned as literals in the tests at 0156f88). HMA(7) needs 8 bars and is
covered by it.

Head check: started at bar s ∈ {100, 500, 900} vs bar 0, worst |diff| from the FIRST
emitted bar on, 10 seeds × σ ∈ {0.005, 0.02, 0.05} (90 runs per row), test bound 1e-6:

| length | warm-up | head worst |
|---|---|---|
| 30 (default) | 277 | 5.5e-8 |
| 10 | 92 | 5.1e-8 |
| 50 | 461 | 4.1e-7 |

At length 30, on the same 90 runs with the mask removed (compared from bar 7, the first bar
where HMA(7) exists):

| check | measured |
|---|---|
| worst \|diff\| at bar 7 | 1.980 |
| first bar from which it stays under 1e-3, vs `ceil(ln(1e-3 / 1.980) / ln(29/31))` | bar 7 + 135, vs 7 + 114 predicted |
| first bar from which it stays under 1e-6, vs the same prediction at 1e-6 | bar 7 + 226 = 233 (*derived* sum), vs 7 + 218 predicted |
| emitting from W // 2 = 138 (*derived*) instead (seed 3, s = 500), \|diff\| at the first emitted bar | 4.7e-5 |

Decay runs a little slower than (1 − alpha) predicts, as it did for `kalman_trend`. The
277-bar mask leaves 44 bars of margin (*derived*) over the 233 derived from the printed 226. The last row is
the Hilbert lesson in CLAUDE.md: half the warm-up passes a tail-only check and still emits a
start-dependent value 47 times the head test's bound (*derived*: 4.7e-5 / 1e-6).

## Gates

| gate | status |
|---|---|
| A Correctness | **not completed; port reverted on Gate E (STRUCK).** What was done: the module equalled the listing *as recalled* (numbers in *Gate A* above). That listing was never checked against the published one, so this is not a pass. Before any un-revert: step 0 of *If this is ever un-reverted* |
| B Causality | cleared on 0156f88 (module since deleted): future-perturbation over 32 offsets (290 to 1,189, step 29), all past the warm-up, bars < j compared bit-for-bit with NaN masks first. Two perturbations of bars ≥ j: another walk's closes, and each missing-bar value (NaN, 0, −1). Real module: 0 leaks under all four. Six mutants (`importlib` source read, `exec`'d in memory), each proved live: EC write back-dated, distance back-dated (`shift(-1)`), HMA fed tomorrow's close, EMA fed tomorrow's close — each caught at 32 of 32 under the walk perturbation; the gain search scored against tomorrow's close — caught at 19 of 32 (it reads tomorrow's close only inside the `argmin`, so it can leak only at offsets where the new close changes bar j−1's best gain; read in the code; which 19 offsets flip that gain was not measured); the missing-bar mask reading tomorrow's validity — caught at 32 of 32 under each missing-bar value, and at 0 under the walk perturbation, which is why the second perturbation exists. All counts were pinned in `tests/test_dickson_ma.py` |
| C Reachability | **not completed; port reverted on Gate E (STRUCK).** Real data, from Gate E's own counts for the column in `overlap_max.csv`: 374,196 non-NaN (`non_nan`) and 374,196 non-zero (`non_zero`) of 398,849 pooled bars over 89 frames. The 24,653 NaN bars (*derived*: 398,849 − 374,196) equal 89 × 277 (*derived*), consistent with the 277-bar head mask on every frame and no other NaN; not checked frame by frame. The positive / negative split on real data was not measured, so the real-data `0 < positive < finite` was not checked. Synthetic, at 0156f88: 1,200-bar walk, seed 11, tick 0.05: 923 finite, 923 non-zero, 484 positive / 439 negative, 923 distinct values |
| D Scale-free | cleared on 0156f88, synthetic: ×8 and ×64: max \|diff\| 0, `Series.equals` true, NaN masks equal. ×10 and ×3.7: max \|diff\| 6.7e-14 / 4.4e-14 (test bound 1e-9), NaN masks equal. 0 < 484 positive < 923 finite, with 923 distinct values |
| E Attribution | **STRUCK** (*Gate E* below): max \|ρ\| 0.8927 vs `Dist_to_PP_pct` (manifest), n 374,196; per-frame median 0.9023 over 89 frames, 52.8% of frames ≥ 0.90; compute_all max 0.8617 vs `log_return`; pooled-only verdict DISCLOSE_GAP |
| F Suites | **After the revert** (5a7b463), this repo, `python -m pytest -q` in one run: 2 failed / 3,162 passed / 83 skipped (1,050.57 s). The two failures are `test_altrepo_talib_csv::test_regenerating_reproduces_the_committed_rows` (`pandas-ta-classic not found at D:\AwakenAnalytics\PandasTaWork\AlternativeRepos\pandas-ta-classic`, a directory outside this repo) and `test_pine_coverage_csv::test_audited_rows_carry_their_evidence` (`supertrend` cites `RA2vGpkA-ta.pine`, the CLAUDE.md known break). Those counts equal the launcher's base `b0422ad` run in `gate-1/tests.md` (3,162 passed / 2 failed / 83 skipped), and the same two tests are that base run's two failures (`tests/pandasta-base.xml` in the launcher's run folder: `failures="2"`, those two testcases). **With the port, at 0156f88**, from `gate-1/tests.md` (clean worktrees): PandasTa 3,201 passed / 2 failed / 83 skipped, 0 regressions, 39 new tests passing; Backtesting 1,584 passed / 16 failed / 4 errors / 14 skipped at both base and 0156f88, 0 regressions. Neither repo is fully green at base either. The parent repo was not re-run after the revert; the launcher runs it. After 5a7b463 no file under `pandas_ta/` differs from base (`git diff --name-status b0422ad`), so that run is against base fork code |

## Gate E — measured on the port (issue-solver, 2026-10-25)

Run `is147-dickson_ma-0663a68d`: `gate_e_overlap.py run --module pandas_ta.overlap.dickson_ma`,
function `dickson_ma` at its defaults (`kwargs {}`), on the code at 0156f88 (the review gate's
`acceptance.md` names that HEAD; the launcher's gate-e stage started 2026-10-25 22:59:08,
after that commit at 22:42:50, and ran 304 s). Every number below is read from the
launcher's copy of the outputs, `C:/Users/Tolga/.issue-solver/runs/20261025-210235-147/gatee/is147-dickson_ma-0663a68d/`
(`overlap_max.csv`, `top25.csv`, `perframe.csv`, `degenerate.csv`, `meta.json`). That folder
and the harness-side `backtest_results/gatee/is147-dickson_ma-0663a68d/` exist only on the
owner's machine, so the rows that decide the verdict are copied here.

Pooled (`overlap_max.csv`):

| | measured |
|---|---|
| max \|ρ\| | **0.8927** (ρ = +0.8927) vs `Dist_to_PP_pct`, manifest set |
| n | 374,196 |
| max \|ρ\| within compute_all | 0.8617 vs `log_return`, n 374,196 |
| max \|ρ\| within the manifest | 0.8927 vs `Dist_to_PP_pct`, n 374,196 |
| comparators | 687, 1 of them degenerate (`squeeze_SQZ_NO`, constant; `degenerate.csv`) |
| verdict, schema `r3-perframe-0.90` | **STRUCK** |
| verdict, pooled only | DISCLOSE_GAP |

Per frame (`perframe.csv`: the five largest pooled comparators of `top25.csv`, 89 frames
each):

| comparator | set | pooled \|ρ\| | per-frame median | mean | min | max | frames ≥ 0.90 | frames ≥ 0.80 |
|---|---|---|---|---|---|---|---|---|
| `Dist_to_PP_pct` | manifest | 0.8927 | **0.9023** | 0.8979 | 0.7591 | 0.9379 | **52.8%** (47 of 89, *derived*) | 98.9% (88 of 89, *derived*) |
| `log_return` | compute_all | 0.8617 | 0.8647 | 0.8641 | 0.8287 | 0.8930 | 0% | 100% |
| `percent_return` | compute_all | 0.8617 | 0.8647 | 0.8641 | 0.8287 | 0.8930 | 0% | 100% |
| `VELOCITY` | compute_all | 0.8617 | 0.8647 | 0.8641 | 0.8287 | 0.8930 | 0% | 100% |
| `Ret_1d_pct` | manifest | 0.8617 | 0.8647 | 0.8641 | 0.8287 | 0.8930 | 0% | 100% |

Why STRUCK: the pooled maximum is 0.0073 under the 0.90 line (*derived*), but
`Dist_to_PP_pct`, a top-5 comparator, has a per-frame median 0.0023 over it (*derived*:
0.9023 − 0.90). The other four sit at 0.8647, in the DISCLOSE_GAP band.

Run stamp (`meta.json`): engine_code `f58eb5daf98fac30ae14bbd4b883d2a493019e65`, ladders
`a1575177ee31e5ee7cee9cf0d5c576671c7d9254`, cache_code
`d583ded2f94301e5d559dc7d3ba103f77b9b79e0`, data `1be6495ef7095ff67ad8f59a2fc0311d74f02652`,
universe `fa3060e68acef410cbc04573ac39450bd210d81d`, pandas 2.3.3 / numpy 1.26.4; canary
"AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS bit-equal"; 89 frames, 398,849 pooled bars, 329
compute_all + 358 manifest comparators; candidate_source_sha1
`97277791c91795071f1c6fcd76151e47caeb1885`, pandas_ta_src_sha1
`810e896647c82341d585bde6f672511b2faa07f7`.

**Against the prototype prior** (*quoted* from the issue, next section): pooled max 0.8889
(n 398,226) on the prototype → 0.8927 (n 374,196) on the port, +0.0038 (*derived*); top-5
per-frame max median 0.8979 → 0.9023, +0.0044 (*derived*); the same top comparator,
`Dist_to_PP_pct`; the next comparators 0.8599 → 0.8617. The per-frame median that sat
0.0021 under the STRUCK line on the prototype sits 0.0023 over it on the port. The two n
differ by 24,030 (*derived*: 398,226 − 374,196), which equals 89 × 270 (*derived*), the head
bars per frame that the port masks and the prototype emitted; consistent with the head mask,
not checked frame by frame. Which of the port's differences from the prototype (the head
mask, the NaN-gap handling, the DMA ≤ 0 mask) moved ρ up was not measured.

## The prior from the prototype (*quoted* from issue #147, NOT measured here)

The 2026-10-24 screen ran Gate E on the prototype: max |ρ| **0.8889** vs `Dist_to_PP_pct`
(n = 398,226), top-5 per-frame max median 0.8979 → DISCLOSE_GAP; next comparators
`log_return` 0.8599 and `Ret_1d_pct` 0.8599. Fork overlap (stage 2): 0.8844 vs
`priorday_fib:PDFIB_MID`.

Written before Gate E ran on the port, and kept as written: on NaN-free, all-positive data
the port matches the prototype to 4.4e-14 past the warm-up (Gate A cross-check), so there
the only difference Gate E can see is the head mask: 270 bars per frame (*derived*: 277 −
the 7 the prototype also lost to HMA) that the prototype emitted and the port does not. On
real frames they can also differ outside the head, which was not measured: the prototype's
EMA is `ewm(adjust=False)` (`ind_screen_r4.py:86`), which treats a NaN gap differently from
the port's skip; it treats zero and negative closes as valid; and it has no DMA ≤ 0 mask.
The per-frame median sat 0.0021 (*derived*) under the 0.90 STRUCK line, so the verdict could
land on either side. That is a guess; Gate E decides. **Gate E decided: STRUCK** (previous
section).

## Proxy overlap (NOT Gate E)

Spearman ρ of `DICKSON_DIST_30_7` on one synthetic walk (σ = 0.02, seed 1), n = 2,723,
measured at 0156f88:

| comparator | ρ |
|---|---|
| `ROC_1` | **0.8956** |
| 100·(close / EMA₅ − 1) | 0.8543 |
| 100·(close / EC₃₀ − 1), EC alone | 0.8457 |
| 100·(close / HMA₁₀ − 1) | 0.7846 |
| 100·(close / EMA₁₀ − 1) | 0.7542 |
| 100·(close / EMA₂₀ − 1) | 0.6709 |
| `CMO_14` / `RSI_14` | 0.6321 |
| 100·(close / HMA₂₀ − 1) | 0.6216 |
| 100·(close / EMA₃₀ − 1) | 0.6210 |
| 100·(close / HMA₇ − 1) | 0.6120 |
| `KFT_DIST_0.01_0.0001` | 0.6014 |
| `BIAS_SMA_26` | 0.5940 |
| `ROC_5` | 0.5539 |
| `ROC_10` | 0.5116 |
| `PFE_10_5` | 0.3404 |
| `PPO_12_26_9` | 0.2816 |

The maximum is `ROC_1` at every σ tried and moves by at most 0.0014 (*derived*): 0.8956 /
0.8957 / 0.8956 / 0.8943 for σ = 0.005 / 0.01 / 0.02 / 0.05. This agrees in direction with
the screen, whose next comparators on real data were the one-day returns (0.8599, *quoted*),
and with Gate E on the port, where the one-day returns (`log_return`, `percent_return`,
`VELOCITY`, `Ret_1d_pct`) are the next four at 0.8617. The comparator that struck it,
`Dist_to_PP_pct`, has no counterpart on the proxy.

Runtime for 5,000 bars, `timeit.repeat` with 5 runs: min 0.76 s, median 0.88 s (one
Python-level loop over bars, 101 gains vectorised per bar). Two earlier single-call timings,
from the first two runs of the script, read 0.28 s and 1.58 s; the cause of that spread
was not measured.

## Docs touched by the wiring

At 0156f88 `docs/IndicatorDictionary.md` had been regenerated in full (pandas 2.3.3): the
`dickson_ma` row, the counts, the `overlap (51)` header, the feed-ready entry, the probe date,
and the removal of the hand-patch notes for `pfe` and `kalman_trend`, whose rows came out
identical; `docs/MLCompanionContract.md` moved 568 → 569 tagged columns and 215 → 216 `SF`
and said the dictionary was regenerated in full.

The revert restored both files to base `b0422ad` whole, not hunk by hunk. With the port gone,
the regeneration's other hunks describe a generator run whose output included the port, and
the contract's "regenerated in full" wording would be false against the base dictionary. So
the base text is back: the two hand-patch notes, 568 / 215, and 235 / 243 in the dictionary
and the README.

## Closed: measured revert (2026-10-26)

What the revert did, each path restored with `git restore --source=b0422ad`:

- deleted `pandas_ta/overlap/dickson_ma.py`, `tests/test_dickson_ma.py`,
  `docs/measure_dickson_ma.py`;
- restored to base: `pandas_ta/overlap/__init__.py` (export), `pandas_ta/__init__.py`
  (`Category` entry), `pandas_ta/core.py` (accessor), `tests/test_altport2_ports.py`
  (`CATEGORY_TOTAL` 235), `README.md` (235 / 243 and the `overlap (50)` list),
  `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md` (568 / 215).

Checked after the revert: `git diff --name-status b0422ad` lists four added files and
nothing else, this file and the three of `docs/reviews/auto-2026-10-25-bt-dma-dist/` (the
review folder of this revert, `docs/reviews/auto-2026-10-26-bt-dma-dist-revert/`, was not
yet tracked). No file under `pandas_ta/`, `tests/` or the other docs differs from base.

## If this is ever un-reverted

Before any un-revert, in order:

0. **Check Gate A against the source.** Get the published listing (S&C Nov 2010, or Ehlers'
   `ZeroLag.pdf`) and backtrader's `DicksonMovingAverage` docstring for the defaults (period
   30, hperiod 7, gainlimit 50; the docstring, not the code), and diff them against L1–L15 and
   the defaults above. If anything differs, fix the module and the oracle together, then re-run
   the measurement script and the tests and update every number here.
1. Gate C on real data, from the port's own output over the same 89 frames: the positive and
   negative bar counts of `DICKSON_DIST_30_7` and the real-data `0 < positive < finite`.
2. A new Gate E run on the changed column whose verdict is not STRUCK. The column measured
   here is STRUCK.
