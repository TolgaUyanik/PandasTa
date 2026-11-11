# First zero crossing of the return autocorrelation — measured (`firstzero_ac`)

Issue #152 (KATS-FIRSTZERO-AC-100), from the owner's library catalog screen, round 5, of
2026-10-25.

**Source:** Kats tsfeatures (Meta, MIT), `get_special_ac` → `firstzero_ac`
(`kats/tsfeatures/tsfeatures.py` at commit `a6b7e88`, L1293–1340):

```python
AC = acf(x, fft=True, nlags=len(x))[1:]                                  # L1316
...
j = 0                                                                    # L1332
while j < len(AC) - 1:
    if AC[j] > 0 and AC[j + 1] < 0:
        break
    else:
        j += 1
special_ac_features["firstzero_ac"] = j + 2                              # L1338
```

- `acf` is `statsmodels.tsa.stattools.acf` (0.15.0, `tsa/stattools/_stattools.py` L847):
  `avf[: nlags + 1] / avf[0]` (L1013). `nlags = len(x)` asks for one lag more than
  `acovf` returns, and the slice truncates, so `AC` holds lags 1 .. n − 1.
- `acovf` (L488) demeans once by the full mean, divides every lag by n, and with
  `fft=True` pads to `_next_regular(2n + 1)` (L609–613; `_next_regular` is
  `statsmodels/compat/scipy.py` L17).
- `AC[j]` is lag j + 1, so the value is the lag of the first negative autocorrelation
  that directly follows a positive one. With no such pair the loop runs out at
  `j = len(AC) − 1` and returns n, the window length.
- L1317 is a debug `print("AC", AC)` left in Kats; it has no effect on the value and is
  not ported.

**Not Hyndman's `firstzero_ac`.** Hyndman's is the first lag whose autocorrelation is
negative at all. Kats needs a positive lag directly in front of it: a window whose lag-1
autocorrelation is already negative reads a later lag (alternating returns read 3, not 1).

**Minimum length 5.** Kats' `transform` raises on fewer than 5 points (L502). That is the
only guard in front of `get_special_ac`. With every default feature group on, other groups
may raise first: #153 measured that `get_acfpacf_features` raises on 10 to 13 points, so a
default all-features Kats call returns nothing there. Those groups are not part of this
port. From 3 points on, `length` (no crossing) cannot be confused with a crossing lag
(2 .. length − 1), so 5 is also safe for the sentinel.

**Status:**
- Gates A, B and D are cleared, and this repo's suite is green, which is the half of
  Gate F that runs here.
- Gate C has synthetic counts only, and Gate E is owed. Both need the BIST frames and the
  private Backtesting repo, which the contributor's machine does not have.
- Two findings are the owner's to weigh: the `length` sentinel on sparse returns, and the
  column's tag, `ORD` rather than `SF` (see "For the owner").

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/firstzero_ac.py` | statistics | `FIRSTZEROAC_100` | whole numbers 2 .. 100, or NaN |

Tests: `tests/test_firstzero_ac.py` (39 tests). The four statsmodels tests skip where
statsmodels is absent (CI, and the pandas 3 venv: 35 passed, 4 skipped there).

Every number below is reproduced by `docs/measure_firstzero_ac.py`; the section name is
given with each block. Synthetic data only.

## Window

Bar T reads closes T − length .. T: `length` one-bar returns `c / c1 − 1`, the convention
of `arch_lm` (#154) and `lumpiness` (#156), the two other Kats return features. The first
value is at bar `length` (bar 100 at the default). Returns are price ratios, so a ×2^k
rescale is exact.

The module repeats statsmodels' FFT (same padding, transform and divisor) on each chunk of
windows at once, rather than calling `acf` per window. The signs Kats compares come out the
same (Gate A).

## Gate A — correctness (`gate_a`)

`_next_regular` equals statsmodels' for every target 1 .. 4999.

The oracle runs Kats' L1316 and L1331–1338 through statsmodels' own `acf` on the returns of
every window, on eight 600-bar frames, at lengths 5, 10, 63, 100 and 252. Cells are
"equal / compared (NaN by the guard)":

| frame | L=5 | L=10 | L=63 | L=100 | L=252 |
|---|---|---|---|---|---|
| AR(1) φ = −0.3 | 595/595 (0) | 590/590 (0) | 537/537 (0) | 500/500 (0) | 348/348 (0) |
| AR(1) φ = 0 | 595/595 (0) | 590/590 (0) | 537/537 (0) | 500/500 (0) | 348/348 (0) |
| AR(1) φ = +0.3 | 595/595 (0) | 590/590 (0) | 537/537 (0) | 500/500 (0) | 348/348 (0) |
| AR(1) φ = +0.8 | 595/595 (0) | 590/590 (0) | 537/537 (0) | 500/500 (0) | 348/348 (0) |
| GARCH(0.20, 0.75) | 595/595 (0) | 590/590 (0) | 537/537 (0) | 500/500 (0) | 348/348 (0) |
| tick-rounded to 0.1, sd 0.4% | 595/595 (0) | 590/590 (0) | 537/537 (0) | 500/500 (0) | 348/348 (0) |
| sine returns, period 22 | 595/595 (0) | 590/590 (0) | 537/537 (0) | 500/500 (0) | 348/348 (0) |
| 150 flat bars, then iid 1% | 450/450 (145) | 450/450 (140) | 450/450 (87) | 450/450 (50) | 348/348 (0) |

- Of 20,560 windows, 20,138 equal Kats' value and 0 differ.
- The other 422 are NaN by the rounding guard. All 422 are windows of the flat stretch, where
  every return is 0; none has a return sd above 1e-12. Kats returns `length` there (every
  autocorrelation is NaN, so no lag passes its test).
- The autocorrelations themselves, module FFT against statsmodels, differ by at most
  2.2e-16 (every 7th window).

In the tests: the Kats lines at lengths 5, 10 and 100 and the `_next_regular` comparison
(skipped without statsmodels); an independent loop with no FFT, at lengths 5, 10 and 100,
in CI; and three closed forms:
- alternating returns read 3;
- sine returns of period 10 and 22 read 3 and 6 at every bar;
- one step in a flat price reads `length` on the 100 windows holding it (demeaned,
  AC(k) = −k / (n − 1) × a positive factor: all negative, so no crossing).

## The rounding guard (`guard`)

A window whose return standard deviation is at most 64 machine epsilons times its largest
|1 + r| is NaN. The rounding of `c / c1 − 1` is absolute, about eps × |1 + r|, whatever
the size of r, so the floor is too. This is the guard `lumpiness` (#156) uses.

"Units" is the return sd in eps × max |1 + r| units, the scale of the floor (64).
"Unguarded" turns the guard off:

| series (300 bars) | shipped fires | unguarded fires | unguarded values | max units |
|---|---|---|---|---|
| 100 × (1 + 0.01)^t | 0 | 200 | 3, 4, 5 | 0.62 |
| 100 × (1 + 1e-4)^t | 0 | 200 | 3, 4, 5, 6 | 0.58 |
| 100 × (1 + 1e-7)^t | 0 | 200 | 3, 4, 5, 8 | 0.61 |
| 100 × (1 + 1e-8)^t | 0 | 200 | 3 .. 7 | 0.63 |
| 100 × (1 + 1e-10)^t | 0 | 200 | 100 | 0.10 |
| exp(linspace(0, 30, 300)), 10% a bar | 0 | 200 | 4, 5, 8 | 5.69 |
| 1.1^t | 0 | 200 | 2 .. 9 | 0.38 |
| flat 10.0, one-ulp jitter | 0 | 200 | 3, 4, 5, 6 | 0.79 |

- Unguarded, rounding noise reads 2 to 9: the ordinary range of the column, so it cannot
  be told from a real reading.
- Real variation clears the floor by a wide margin: iid returns of sd 1e-13 sit at 393
  units or more and fire on 200 of 200 bars; sd 1e-12, at 3811 or more.
- The headroom is therefore 5.69 below the floor (the steepest noise measured) and 393
  above it (the smallest real series measured). Swapping the constant in the module shows
  the tests bound it from both sides:
  - with no guard, 7 of the 10 guard and flat-price tests fail;
  - with a floor of 2, `test_a_steep_exponential_is_nan` fails;
  - with a floor of 1000 or 1e4, `test_the_guard_keeps_very_small_real_returns` fails.

## What it reads (`semantics`)

40 paths × 1100 bars per row, every 25th bar from bar 100:

| returns | median | p10 .. p90 | mean | share reading 2 | share reading 100 |
|---|---|---|---|---|---|
| AR(1) φ = −0.3 | 3 | 3 .. 5 | 3.76 | 0.001 | 0 |
| AR(1) φ = −0.1 | 4 | 3 .. 6 | 4.22 | 0.083 | 0 |
| AR(1) φ = 0 (iid) | 3 | 2 .. 7 | 3.86 | 0.259 | 0 |
| AR(1) φ = +0.1 | 3 | 2 .. 6 | 3.42 | 0.403 | 0 |
| AR(1) φ = +0.3 | 3 | 2 .. 7 | 4.07 | 0.239 | 0 |
| AR(1) φ = +0.6 | 6 | 4 .. 13 | 7.19 | 0.003 | 0 |
| AR(1) φ = +0.9 | 14 | 8 .. 27 | 16.08 | 0 | 0 |
| GARCH(0.20, 0.75) | 3 | 2 .. 6 | 3.88 | 0.253 | 0 |
| Student-t(3) iid | 3 | 2 .. 6 | 3.85 | 0.270 | 0 |

- **It reads strong persistence, not autocorrelation in general.** φ = 0.9 reads later
  lags than 0.6, and 0.6 later than iid. Below that the medians are 3 or 4 whatever the
  sign of φ. Against the window's own lag-1 return autocorrelation the Spearman is 0.022
  (30 paths, φ = −0.3 / 0 / +0.3, every 10th bar).
- **It reads cycle length.** Returns `0.01 sin(2πk / P)` read about the first lag above P / 4: P = 10
  reads 3, P = 22 reads 6, P = 40 reads 10 or 11, P = 70 reads 17 to 20. P = 40 plus iid
  noise of the same sd still reads a median of 10 (p10 .. p90: 8 .. 11).
- **Volatility clustering and fat tails do not move it.** GARCH and Student-t(3) read as
  iid returns do.
- **It is sticky.** On 4900 iid bars the value changes on 11.7% of bars and takes 15
  distinct values. One extra return rarely changes the sign pattern of the window.

## The `length` sentinel (`sentinel`)

With no positive-to-negative pair the value is `length`. On ordinary returns this does not
happen: 0 of the bars above read 100. A window whose returns are zero except for one move
has every autocorrelation negative, so it always reads `length`. On sparse returns that is
common:

| returns of ±1% on … of bars, 0 otherwise (20 paths × 1100 bars) | share of fired bars reading 100 |
|---|---|
| 50% | 0 |
| 20% | 0 |
| 5% | 0.0314 |
| 2% | 0.3632 |

A thinly traded name (a BIST stock that prints the same close for days) is where this
lands. The column then jumps from small integers to 100. Kats returns exactly this, so it
is ported as is; see "For the owner".

## Gate B — causality (`causality`)

- The mutant moves the chunk write index one bar earlier (`lo = length + start` →
  `lo = length − 1 + start`).
- Future perturbation at 16 offsets (130 .. 580, every 30 bars), two ways:

| perturbation from the offset on | real module leaks | mutant caught |
|---|---|---|
| another path, rescaled to join | 0/16 | **0/16** |
| close × 1000 (one return of 999) | 0/16 | 16/16 |

- The path swap, which the other ports use, does not catch this mutant. The column is a
  whole number that changes on about 1 bar in 9, and the mutant's leaked bar differs from
  the real one by a single return, which rarely moves it. A ×1000 jump makes every
  autocorrelation of the windows holding it negative, which always moves it. The test uses
  the jump.
- A bad tick (close × 1000 at bar 300) changes the returns at bars 300 and 301. It moves
  exactly bars 300 .. 400 (101 bars), the windows holding either return; every other bar
  is bit-identical.

## Gate D — scale-free (`scale`)

On three 600-bar iid frames (seeds 4, 5, 6), ×8, ×64, ×10 and ×3.7 all give equal NaN
masks and 0 differing bars. ×8 and ×64 are exact by construction. ×10 and ×3.7 move returns
by rounding, which could flip the sign of an autocorrelation within rounding of 0; none
does on these frames, and the test allows at most 1% of bars to differ.

Seed 4: 500 of 600 bars fire (the first value at bar 100), with 7 distinct values from 2
to 14.

## Family (`family`)

Spearman of `FIRSTZEROAC_100` against every numeric column of every other `Category`
indicator at its defaults, on 8 synthetic OHLCV paths × 1100 bars (φ = 0, 0.3, 0.6, 0.9,
two seeds each).
- 474 columns are compared.
- 6 indicators raise at defaults on these frames (`avwap_z`, `ichimoku`, `nwog`, `pivot`,
  `priormonth_range`, `vwap`), most because the synthetic index is not a datetime index.
- The ten highest pooled values:

| column | pooled, 8 paths | the 2 iid paths | per-path median |
|---|---|---|---|
| `range_profile:RPO_VA_WIDTH_PCT_110_80` | 0.606 | 0.054 | 0.137 |
| `vhf:VHF_28` | 0.604 | 0.037 | 0.211 |
| `adxr:ADXR_14` | 0.568 | 0.122 | 0.172 |
| `sr_corridor:SRCOR_WIDTH_ATR_8_5_0.6` | 0.540 | 0.044 | 0.222 |
| `adx:ADX_14` | 0.538 | 0.113 | 0.158 |
| `g191_174:G191_174_20_20_1` | 0.531 | 0.049 | 0.235 |
| `ht_dcperiod:HT_DCPERIOD` | 0.514 | 0.154 | 0.229 |
| `volume_sr_zones:VOLSR_RES_DIST_10_20` | 0.499 | 0.131 | 0.087 |
| `chop:CHOP_14_1_100` | 0.436 | 0.027 | 0.133 |
| `er:ER_10` | 0.434 | 0.006 | 0.108 |

The pooled values are driven by the mix of paths: a φ = 0.9 path trends, so it reads late
lags and high trend strength at once. Within a path the largest median is 0.24, and on the
iid paths 0.15. Nothing approaches the 0.90 line on synthetic data. The prototype's Gate E
(max |ρ| 0.0540 vs `Swing_Range_pct` on BIST) is not a measurement of this port.

## Cost (`cost`)

One FFT per window, in chunks of 2^18 window cells. Timings are three runs, min .. max;
peak memory is measured in a separate run with tracemalloc on.

| n | length | time | peak |
|---|---|---|---|
| 2,000 | 100 | 41 .. 50 ms | 21.8 MiB |
| 2,000 | 252 | 89 .. 109 ms | 28.4 MiB |
| 20,000 | 100 | 284 .. 286 ms | 30.4 MiB |
| 20,000 | 252 | 694 .. 1681 ms | 28.8 MiB |
| 200,000 | 100 | 3.7 .. 3.9 s | 34.5 MiB |
| 200,000 | 252 | 10.5 .. 10.9 s | 33.0 MiB |

## For the owner

1. **The `length` sentinel.** Kats returns n when there is no crossing, and so does the
   port. It read 100 on none of the sampled bars of the semantics table. On returns that
   move on 2% of bars, 36% of fired bars read 100. The alternative is NaN for "no crossing", which departs from Kats
   and blanks those bars. Shipped: Kats' value.
2. **`ORD`, not `SF`.** `gen_indicator_dictionary.py` tags `FIRSTZEROAC_100` `ORD` (a small
   integer set). The contract count moves `ORD` 51 → 52 and leaves `SF` at 305. The column
   is still scale-free (Gate D).
3. **Window.** `length` returns (101 closes), as `arch_lm` and `lumpiness`. If the
   prototype meant 100 closes, that is `length=99`.
4. **Gate E and real-data Gate C** are owed. After that: merge, or measure and revert.

## Gate F — suites

Full suite on this branch (`.venv-pd2`, CI's two deselects, `GATE_E_PENDING_OK=1`):
5379 passed, 84 skipped, 0 failed.

The Backtesting suite cannot be run here.

## Counters touched

- `CATEGORY_TOTAL` 317 → 318 (note newest first). Statistics is not in
  `CATEGORY_BUCKETS`.
- README: 318 registered, 326 callable, statistics (29).
- `docs/MLCompanionContract.md`: 662 → 663 tagged and 51 → 52 `ORD`, `SF` unchanged at
  305, with a revert note (newest first).
- `docs/IndicatorDictionary.md`, regenerated with `.venv-pd2`. Its diff is the
  `firstzero_ac` row (`FIRSTZEROAC_100` ORD, warm-up 100), the four counts and the
  shortlist entry.
- `Category`: `firstzero_ac` is placed alphabetically, after `ffd`.

All counts are as of `dev` at `4a88858`.

## Not done here

- **Gate C on real data and Gate E.** They need the BIST frames and Backtesting:
  ```sh
  python scripts/analysis/gate_e_overlap.py run --module pandas_ta.statistics.firstzero_ac --name firstzero_ac
  python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD
  ```
- **The Backtesting suite.**
