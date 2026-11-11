# Lag-1 autocorrelation of return changes — measured (`diff2_acf1`)

Issue #153 (KATS-DIFF2-ACF1-100), from the owner's library catalog screen, round 5, of
2026-10-25.

**Source:** Kats tsfeatures (Meta, MIT), `get_acfpacf_features` → `diff2y_acf1`
(`kats/tsfeatures/tsfeatures.py` at commit `a6b7e88`), after Hyndman's tsfeatures
`diff2_acf1`:

```python
nlag = min(acfpacf_lag, len(x) - 2)                                     # L1098, acfpacf_lag = 6
diff1x = [x[i] - x[i - 1] for i in range(1, len(x))]                    # L1100
diff2x = [diff1x[i] - diff1x[i - 1] for i in range(1, len(diff1x))]     # L1101
diff2y_acf_list = acf(diff2x, fft=True, nlags=nlag)[1:]                 # L1105
diff2y_acf1 = diff2y_acf_list[0]                                        # L975
```

- `acf` is `statsmodels.tsa.stattools.acf` (0.15.0, `tsa/stattools.py` L847–1060). It
  returns `acovf[:nlags + 1] / acovf[0]`.
- `acovf` (L488–623) demeans the series once by its full mean and divides every lag by
  n.
- So the value is `sum(x[t] * x[t-1]) / sum(x²)` on the demeaned twice-differenced
  series.

**Only these lines are ported.** The same Kats function has four outcomes for
`diff2y_acf1`, measured with `measure_diff2_acf1.py` (`kats_minimum`):
- **NaN** when the input has fewer than 10 points or is constant (L1090);
- **a raised ValueError** on 10 to 13 points. The function also computes partial
  autocorrelations (`pacf(x, nlags=7)` at L1107, and `pacf` of the two differences at
  L1118–1119). statsmodels' `pacf` refuses lags of half the sample or more;
- **NaN** when the variance of `diff1x` or of `diff2x` is exactly 0 (L1109–1116; with one
  lag, `_yule_walker_determinant`, L1156–1167, is that variance);
- **the value**, from 14 points on.

**Status:**
- Gates A, B and D are cleared, and this repo's suite is green, which is the half of
  Gate F that runs here.
- Gate C has synthetic counts only, and Gate E is owed. Both need the BIST frames and the
  private Backtesting repo, which the contributor's machine does not have.
- One finding is the owner's to weigh: on synthetic paths the column is close to a
  function of the window's lag-1 and lag-2 return autocorrelations (see "Family").

**Review round 1** (2026-11-10, verdict REVISE: 1 MAJOR, 4 MINOR, 3 NIT) is fixed here:
- "Kats' own minimum of 10" and "Kats' own lines and its own NaN guards" were false: Kats
  raises on 10 to 13 points, and the Gate A oracle left out the lines that raise. The
  minimum length is now 14, the oracle runs those lines, and the wording says which lines
  are ported.
- The guard tests did not bound the floor. A near-floor real series is now a test, and
  the measured headroom is in Decision 4.
- A subnormal close (1e-310) produced a confident value. It is now masked like 0.
- The docstring's Spearman figures were unqualified. They now say synthetic, pooled and
  per path.
- NITs: a test band's headroom is stated, the merge-tree provenance is corrected, and
  six trend-versus-reversal neighbours are measured.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/diff2_acf1.py` | statistics | `DIFF2ACF1_100` | `(-1, 1)` or NaN; about −0.5 for returns with no memory |

Tests: `tests/test_diff2_acf1.py` (37 tests). The three statsmodels tests skip where
statsmodels is absent: in CI, and in `.venv`, where 34 pass and 3 are skipped.

Numbers: `python docs/measure_diff2_acf1.py`, run from the repo root. It needs
statsmodels for its first two sections. Environment: Python 3.13.14, pandas 2.3.3,
numpy 2.5.4 (`.venv-pd2`). Measured 2026-11-10.

## Decisions

1. **Input: log close**, as the issue states ("scale-free form: on log close").
   - `diff(log close)` is the log return, and `diff(diff(log close))` is the change of
     the log return from one bar to the next.
   - The module takes `log(c / c1)` where Kats takes `log c − log c1`. The two agree to
     rounding (Gate A), and the ratio form is exact under a ×2^k rescale.
2. **Window = `length` closes.** Bar T reads closes T − length + 1 .. T, as `kpss` (#157)
   does. Its input is log close too, from the same screen.
   - At the default that is 99 log returns and 98 return changes; the first value is at
     bar 99.
   - **The prototype's window is not visible here** (`ind_screen_r5.py` is on the owner's
     machine only). If it meant 100 return changes, the window would be 102 closes.
   - Measured over 100 iid paths at the same bars, 100 closes against 102 closes: Spearman
     0.9873, median absolute difference 0.0048, maximum 0.140.
3. **`length` has a floor of 14**, the shortest input on which Kats' own call returns a
   value (see "Source").
   - A smaller or missing value falls back to 100, the repo's convention (`kpss`,
     `arch_lm`). The docstring says so, and `length=13` is tested.
   - Kats' lag cap (`nlag`) does not matter: only lag 1 is read.
4. **A rounding guard, where Kats tests exact zero.**
   - The rule: a window is NaN when the std of its return changes is at most **64 machine
     epsilons × (1 + its largest |log return|)**, about 1.4e-14 for ordinary returns.
   - Why the floor is absolute: the rounding error of `log(c / c1)` is about
     eps × (1 + |r|), whatever the size of the return.
   - Why it is needed: Kats returns NaN only when the variance is exactly 0. On a series
     whose return changes are pure rounding noise, it reports the autocorrelation of that
     noise.
   - Measured, shipped against unguarded (`measure_diff2_acf1.py`). "Units" are the
     window's std in multiples of eps × (1 + max |log return|), the largest over the
     series:

     | series (300 bars) | shipped fires | unguarded fires, median (min .. max) | units |
     |---|---|---|---|
     | `100 * (1 + 1e-2)^t` | 0 | 201, −0.671 (−0.760 .. −0.605) | 1.06 |
     | `100 * (1 + 1e-4)^t` | 0 | 201, −0.579 (−0.648 .. −0.432) | 0.98 |
     | `100 * (1 + 1e-7)^t` | 0 | 201, −0.667 (−0.722 .. −0.584) | 1.01 |
     | `100 * (1 + 1e-8)^t` | 0 | 201, −0.691 (−0.763 .. −0.500) | 1.10 |
     | `100 * (1 + 1e-10)^t` | 0 | 140, −0.500 (−0.500 .. −0.000) | 0.14 |
     | `exp(linspace(0, 30, 300))`, 10% a bar | 0 | 201, −0.508 (−0.599 .. −0.466) | 7.85 |
     | log close = 1e-5 t² (constant return change) | 0 | 201, −0.626 (−0.703 .. −0.544) | 0.96 |
     | 10.0 with one-ulp jitter | 0 | 201, −0.673 (−0.733 .. −0.577) | 1.41 |

   - The unguarded values are **plausible**: medians −0.50 to −0.69 and single values
     −0.76 to −0.00, inside the column's ordinary range. A reader could not tell them
     from real readings.
   - **Headroom of 64.** Rounding-only series reach at most 7.85 units, so the floor has
     about 8× margin below it. The smallest real series measured, iid log returns of
     standard deviation 1e-12, sits at 5.8e3 units, about 90× above it. Ordinary frames
     sit at 7e12 units or more, and the tick series at 1.5e6 or more.
   - All eight rounding-only cases are tests, and the unguarded module fails all eight.
     The 1e-12 series is a test too.
   - **The tests bound the floor from both sides** (checked by swapping the constant): a
     floor of 2 units fails the steep-exponential test, and a floor of 1e4 units fails
     the 1e-12 test. A floor of 1e3 passes everything.
   - Where it changes nothing: on the five Gate A frames and on a 10%-a-bar series on a
     0.01 tick, at lengths 14, 100 and 252, the guarded and unguarded columns are
     identical on every bar (17 frame × length cases).
5. **Bad inputs.**
   - A close that is NaN, infinite, zero, negative or subnormal (below 2.2e-308) is
     missing data. Its windows are NaN: bars 150..249 for a bad close at bar 150.
   - Subnormal closes are included because one of them, 1e-310, used to pass as a valid
     price. Bar 150 then read −6.5e-5 where the clean value was −0.39, driven by a single
     log return of −718.
   - A price ratio that overflows is treated as missing, not as inf. Closes of 1e-300
     then 1e300 are both normal floats, but their ratio is inf: bars 151..249 are NaN, and
     bars 150 and 250 still fire on the finite returns into and out of the pair.
   - Each window is computed on its own, in chunks, so a bad tick moves exactly the bars
     whose window holds it: bars 300..399 for a tick at bar 300.

## Gate A — correctness

**The oracle** is `kats_diff2y_acf1` in `measure_diff2_acf1.py`. It follows the control
flow of Kats' function as far as `diff2y_acf1` depends on it, in Kats' order:
- the guard at L1090;
- L1098–1105;
- `pacf(x)` at L1107;
- the zero-variance guard at L1109–1116;
- the two `pacf` calls at L1118–1119;
- the value at L975.

The `pacf` results feed other features and are discarded. The calls are kept because
they raise on short inputs. Not reproduced: the `acf(x)` and `acf(diff1x)` values
(L1103–1104) and the feature switches, which do not affect `diff2y_acf1`.

It is run on the log close of every window, for lengths 14 / 63 / 100 / 252, against the
**unguarded** module, so the rounding guard does not enter Gate A:

| frame | zero returns | NaN masks equal | max abs difference |
|---|---|---|---|
| AR(1) φ = 0.2, 1500 bars | 0% | 4 / 4 | 3.7e-14 |
| iid normal, 1500 bars | 0% | 4 / 4 | 3.8e-14 |
| GARCH(0.20, 0.75), 1500 bars | 0% | 4 / 4 | 7.3e-14 |
| tick-rounded near 5 on a 0.01 tick | 20% | 4 / 4 | 4.3e-14 |
| iid with 150 flat bars, 800 bars | 19% | 4 / 4 | 3.1e-14 |

- The NaN masks are equal in all 20 cases, and Kats' call raises in none of them. In the
  flat case, Kats' constant-input guard and the port's zero-variance rule blank the same
  bars.
- The differences are rounding: Kats differences logs, and the port takes the log of the
  ratio. The largest in each row is at length 14.

In the tests:
- the Kats value lines are pinned at 1e-11, with the `pacf` calls run alongside
  (skipped without statsmodels);
- the `pacf` raise on 10 to 13 points, and its absence at 14, is pinned (skipped
  without statsmodels; it pins statsmodels' behaviour, not the module's);
- an independent loop with no statsmodels is pinned at 1e-12 and runs in CI;
- a closed form: 13 alternating log returns ±a give 12 alternating return changes, so
  DIFF2ACF1_14 = −11/12.

## Gate B — causality

- **Future perturbation:** 16 offsets, every close from `j` on replaced by another path
  rescaled to join it. Bars before `j` are bit-identical.
- **Mutant:** the chunk write offset `lo = length - 1 + start` is moved to
  `length - 2 + start`, one bar earlier. The mutant is live, and it is caught at 16 of 16
  offsets.

## Gate C — reachability

- **Synthetic:** 501 of 600 bars fire (the first at bar 99), all 501 values are distinct,
  and all lie in (−1, 1).
- **Real data: owed.** The counts come with the Gate E run on BIST.
- What blanks a bar:
  - a bad close, or a price ratio that overflows, blanks the `length` bars whose window
    holds it;
  - a window whose return changes vary only at rounding level is NaN (Decision 4). On
    real data that means a suspended stretch of `length` or more unchanged closes.

## Gate D — scale-free

- ×8 and ×64: bit-identical, with matching NaN masks.
- ×10 and ×3.7: within 1e-9.
- `0 < fires < n`.

## Semantics — what DIFF2ACF1_100 reads

**Population value.** For log returns with autocorrelations ρ1 and ρ2, the lag-1
autocorrelation of their changes is `(2ρ1 − 1 − ρ2) / (2(1 − ρ1))`. For AR(1) returns
with coefficient φ this is `−(1 − φ) / 2`. Returns with no memory give **−0.5, not 0**:
consecutive changes `r_t − r_{t−1}` and `r_{t−1} − r_{t−2}` share `r_{t−1}` with opposite
signs.

**Measured**, 200 paths × 600 bars per row, 501 values per path, log returns of standard
deviation 2%:

| log returns | population | pooled median | pooled mean | p10 | p90 |
|---|---|---|---|---|---|
| AR(1) φ = −0.3 | −0.65 | −0.6393 | −0.6359 | −0.7108 | −0.5553 |
| AR(1) φ = −0.1 | −0.55 | −0.5413 | −0.5381 | −0.6219 | −0.4485 |
| iid normal | −0.50 | −0.4924 | −0.4893 | −0.5775 | −0.3959 |
| AR(1) φ = +0.1 | −0.45 | −0.4432 | −0.4405 | −0.5329 | −0.3434 |
| AR(1) φ = +0.3 | −0.35 | −0.3449 | −0.3429 | −0.4433 | −0.2382 |
| iid Student-t(3) | −0.50 | −0.4941 | −0.4904 | −0.5754 | −0.4013 |
| GARCH(0.10, 0.85) | −0.50 | −0.4906 | −0.4875 | −0.5853 | −0.3861 |
| GARCH(0.20, 0.75) | −0.50 | −0.4886 | −0.4848 | −0.5923 | −0.3726 |

- **It orders return autocorrelation.** The medians follow the population values, 0.005
  to 0.011 closer to 0 at 98 points. Trending returns read above −0.5, and reversing
  returns (for example bid-ask bounce) read below.
- **A single bar is noisy.** For iid returns the p10–p90 band is −0.58 to −0.40, which
  is 0.18 wide.
  - The φ = −0.1 and φ = +0.1 medians are only 0.10 apart, and their bands overlap.
  - The φ = −0.3 and φ = +0.3 bands do not overlap (−0.71 .. −0.56 against
    −0.44 .. −0.24).
- **Its centre does not move with volatility clustering or fat tails.** GARCH and t(3)
  medians are −0.49, the same as iid normal. GARCH(0.20, 0.75) widens the band slightly,
  to −0.59 .. −0.37.
- **What the tests pin, on 10 paths:**
  - the ordering φ = −0.3 < 0 < +0.3;
  - each median within 0.03 of its population value. The 10-path medians are −0.632 /
    −0.483 / −0.333, which is 0.017 to 0.018 off, so the band has about 0.012 of
    headroom;
  - the GARCH median within 0.03 of the iid one.

  These are bands and orderings, not exact medians, because the medians depend on numpy's
  RNG stream (NEP 19).

## Family — what it restates

All of this section is synthetic. Gate E on real data is owed.

**The window's own return autocorrelations** (100 paths × 600 bars). Let
`g = (2ρ̂1 − 1 − ρ̂2) / (2(1 − ρ̂1))`, the population identity evaluated on the sample
lag-1 and lag-2 autocorrelations of the same window's 99 log returns.

| log returns | Spearman vs g, pooled (per-path min) | Spearman vs ρ̂1 alone, pooled (per-path p10 / p50 / p90) | \|column − g\| median / max |
|---|---|---|---|
| iid normal | 0.9923 (0.966) | 0.7135 (0.376 / 0.723 / 0.887) | 0.0044 / 0.091 |
| AR(1) φ = +0.3 | 0.9906 (0.961) | 0.6086 (0.277 / 0.614 / 0.823) | 0.0055 / 0.098 |
| GARCH(0.20, 0.75) | 0.9902 (0.941) | 0.7014 (0.378 / 0.751 / 0.884) | 0.0042 / 0.172 |

- **On these paths the column is close to a function of ρ̂1 and ρ̂2 of the window's
  returns** (Spearman 0.99). It carries the information of those two numbers and little
  else. None of these paths has zero returns, so tick-rounded data is not covered.
- Against the lag-1 autocorrelation alone it is 0.61–0.71 pooled, and it varies a lot by
  path (0.28 to 0.89, p10 to p90).
- **Two open issues would add a plain return-autocorrelation column:** #94 (TS-AC1-60,
  lag-1) and #96 (TS-AGGAC-60, mean of lags 1–10).
  - If #94 ships, it and this column will overlap. By the numbers above, the Spearman is
    0.61–0.71 at equal windows. That is below the 0.76 ship line, but it is synthetic and
    the windows differ (60 against 100), so it needs its own measurement.
  - Whether the engine's 687 Gate E comparators already hold a return-autocorrelation
    column is not visible from here.

**Columns in `Category` that use serial correlation.** A grep of `pandas_ta` for
`autocorr`, `.corr(...shift(` and `.cov(...shift(` finds two modules besides this one:
`roll_spread` and `a101_048`. Measured over 100 iid paths × 600 bars, on the bars where
both columns fire:

| column | what it is | Spearman | bars |
|---|---|---|---|
| ROLL_20 (default) | Roll spread from the 20-bar serial covariance of price changes | −0.2591 | 29,351 |
| ROLL_100 | the same at 100 bars | −0.5454 | 25,774 |
| A101_048 (default) | 250-bar autocorrelation of price changes, times the day's change | −0.0010 | 34,900 |

- The ROLL sign is as expected: a more negative serial covariance means a larger Roll
  spread and a lower DIFF2ACF1.
- ROLL is NaN on 41.4% (ROLL_20) and 48.6% (ROLL_100) of the bars where this column
  fires, because Roll has no reading when the covariance is not negative.
- A101_048 flips sign with each day's change, so it does not rank bars the way this
  column does.

**Trend-versus-reversal columns in `Category`.** The docstring says the column reads
trending against reversing returns, so these are its obvious neighbours. Measured over 100
paths × 600 bars each, at their defaults unless stated; `chop` is given
high = low = close, because these frames are close-only:

| column | Spearman, iid normal | Spearman, AR(1) φ = +0.3 |
|---|---|---|
| ER_10 (default) | −0.0041 | −0.0222 |
| ER_100 | −0.0259 | −0.0440 |
| `g191_165` (default) | −0.0390 | −0.0488 |
| CHOP (default) | −0.0370 | −0.0025 |
| VHF (default) | +0.0351 | −0.0118 |
| KPSS_100 (default) | −0.0037 | −0.0159 |

All twelve are within ±0.05. Within one regime, where every window has the same true
autocorrelation, the column's bar-to-bar variation is estimation noise that these columns
do not share.

None of the columns measured in this section is near the 0.76 line.

## Cost

These are machine-dependent (Intel64 Family 6 Model 140). Timings are the range over 5
runs with tracemalloc off, across two invocations of the script; peak memory comes from a
separate run with tracemalloc on:

| n | length | time | peak memory |
|---|---|---|---|
| 5,000 | 100 | 0.003–0.005 s | 6 MiB |
| 5,000 | 252 | 0.006–0.008 s | 6 MiB |
| 20,000 | 100 | 0.010–0.012 s | 7 MiB |
| 20,000 | 252 | 0.024–0.030 s | 7 MiB |
| 200,000 | 100 | 0.099–0.167 s | 14 MiB |
| 200,000 | 252 | 0.247–0.394 s | 14 MiB |

Machine load moves these, so they are an order of magnitude.

## Gate E — owed

From `../Backtesting/Backtesting` on the owner's machine:

```sh
python scripts/analysis/gate_e_overlap.py run --module pandas_ta.statistics.diff2_acf1 --name diff2_acf1
python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD   # from this repo
```

The prototype's numbers in the issue (max |ρ| 0.1321 vs `Swing_Range_pct`, SHIP) are not
a measurement of this port.

## Gate F — suites

Full suite on this branch (`.venv-pd2`, CI's two deselects, `GATE_E_PENDING_OK=1`):
5302 passed, 84 skipped, 0 failed (after merging `dev` at `5859c0f`).

Without the variable, `test_every_indicator_that_needs_a_row_has_one` fails on the owed
rows `diff2_acf1` and `mtd_ret`; `mtd_ret` is already owed on `dev`. The Backtesting suite
cannot be run here.

## Counters touched

- `CATEGORY_TOTAL` 315 → 316. Statistics is not in `CATEGORY_BUCKETS`.
- README: 316 registered, 324 callable, statistics (29).
- `docs/MLCompanionContract.md`: 660 → 661 tagged and 303 → 304 `SF`, with a revert note
  (newest first).
- `docs/IndicatorDictionary.md`, regenerated with `.venv-pd2`. Its diff is the
  `diff2_acf1` row (`DIFF2ACF1_100` SF, 99 warm-up), the four counts and the shortlist
  entry, and nothing else.
- `Category`: `diff2_acf1` is placed alphabetically, before `entlz`.

All counts are as of `dev` at `5859c0f`, which this branch has merged.

## Interaction with #292 (`arch_lm`) and #294 (`lumpiness`)

**This PR conflicts with both.** Measured with `git merge-tree` of this branch at
`b38b54e` (on `dev` at `19fca14`) against `origin/issue-154-arch-lm` at `2f81c01` and
`origin/issue-156-lumpiness` at `2190116`, which are both still based on `dev` at
`4dca6d3`:
- against #292, six files: `README.md`, `docs/IndicatorDictionary.md`,
  `docs/MLCompanionContract.md`, `pandas_ta/__init__.py`,
  `pandas_ta/statistics/__init__.py` and `tests/test_altport2_ports.py`;
- against #294, five files: the same list without `pandas_ta/statistics/__init__.py`.

Each of the three PRs adds +1 to the same counters. Each PR that lands after the first
has to:
1. merge `dev`;
2. take the counter files from `dev`;
3. re-apply its +1;
4. regenerate the dictionary.

Counted from `dev` at `5859c0f` (315 / 323 / statistics (28) / 660 / 303 `SF`), with no
other port landing in between:

| order | `CATEGORY_TOTAL` | README registered / callable / statistics | MLCompanionContract tagged / `SF` |
|---|---|---|---|
| first | 316 | 316 / 324 / (29) | 661 / 304 |
| second | 317 | 317 / 325 / (30) | 662 / 305 |
| third | 318 | 318 / 326 / (31) | 663 / 306 |
