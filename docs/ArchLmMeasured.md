# ARCH LM statistic — measured (`arch_lm`)

Issue #154 (KATS-ARCH-LM-100), from the owner's library catalog screen, round 5, of
2026-10-25.

**Source:** Engle's ARCH Lagrange-multiplier test (Engle 1982, *Econometrica* 50(4)), as
Kats tsfeatures (Meta, MIT) computes its "heterogeneity" feature in `get_het_arch`
(`kats/tsfeatures/tsfeatures.py` L1255–1269 at commit `a6b7e88`):

```python
return het_arch(x, nlags=min(10, len(x) // 5))[0]
```

The call goes to statsmodels 0.15.0, `statsmodels/stats/diagnostic.py`:
- `het_arch` (L936–999) returns `acorr_lm(resid**2, nlags)`.
- `acorr_lm` (L784–933) builds the lag matrix at L892 (`lagmat(..., trim="both")`), sets
  `nobs` at L893 to the number of regression rows, fits OLS on `[1, lags]` at L899, and
  computes `LM = (nobs - ddof) * R²` at L905, with `ddof = 0`.
- The residuals are not demeaned before squaring.

**Status:**
- Gates A, B and D are cleared, and this repo's suite is green, which is the half of
  Gate F that runs here.
- Gate C has synthetic counts only, and Gate E is owed. Both need the BIST frames and the
  private Backtesting repo, which the contributor's machine does not have.
- One choice is the owner's: simple or log returns (see "Open question").

**Review round 1** (2026-11-10, verdict REVISE: 2 MAJOR, 6 MINOR, 2 NIT) is fixed here:
- The exceedance shares were pinned while the docs said they were not; the pin is removed.
- The NaN rule was misstated; it is corrected and pinned.
- An extreme close crashed the whole series in the SVD; it is now masked.
- A statsmodels-0.15-only keyword is removed.
- The pinv equivalence was overstated; it is corrected and measured.
- The fat-tail semantics were half-told; they are completed.
- The log-vs-simple claim was never measured; it is now measured, and it was wrong.
- The timings were taken under tracemalloc; they are re-measured without it.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/arch_lm.py` | statistics | `ARCHLM_100` | `[0, length - lags]` = `[0, 90]` at the default, or NaN |

Tests: `tests/test_arch_lm.py` (25 tests). The two statsmodels tests skip where
statsmodels is absent: in CI, and in `.venv`, where 23 pass and 2 are skipped.

Numbers: `python docs/measure_arch_lm.py`, run from the repo root. It needs statsmodels
for its Gate A section. Environment: Python 3.13.14, pandas 2.3.3, numpy 2.5.4
(`.venv-pd2`). Measured 2026-11-10.

## Decisions

1. **Input: one-bar simple returns, `close / close.shift(1) - 1`.**
   - The window is `length` returns: bar T reads closes T − length .. T.
   - Simple returns follow this repo's convention: `osap_retskew_21` and
     `lot_zeroret_60` use `pct_change`, and the round-1 screen's `ret()` is
     `ind_screen.py:108`, quoted in `docs/G191190Measured.md`.
   - **The round-5 prototype's return definition and window length are unknown.**
     Its code, `ind_screen_r5.py`, is only on the owner's machine.
   - **The choice matters** (`measure_arch_lm.py`, 200 GARCH(0.10, 0.85) paths): log
     returns move ARCHLM_100 by up to 5.57, with a median of 0.33. The Spearman ρ between
     the two columns is 0.9955, so the ranking barely changes but the values do. See
     "Open question".
2. **Lags = `min(10, length // 5)`**, Kats' rule, so 10 at any `length` ≥ 50.
   - It is not a separate parameter.
   - `length` has a floor of 10 (2 lags, 8 regression rows). A smaller or missing value
     falls back to 100, which is the repo's convention, and the docstring says so.
3. **The LM statistic itself, not its p-value**, as Kats returns it.
4. **Computed one window at a time, by SVD on the centred design.**
   - Centring y and the lags removes the constant.
   - The cutoff keeps singular values above `1e-15` × the largest. That is the same
     relative cutoff statsmodels' pinv uses, but statsmodels applies it to the uncentred
     `[1, lags]`, a different matrix. On a near-singular window the two can decide rank
     differently: Gate A measures up to 4.4e-10.
   - Windows are evaluated in chunks of `2^18` cells. A bad tick moves exactly the bars
     whose window holds one of its two returns: bars 300..400 for a tick at bar 300.
5. **NaN windows:**
   - **Bad input:** a window with a NaN, zero or negative close is NaN. So is a window
     with a return whose square overflows: one extreme close, such as 1e-300 or 1e160,
     used to crash the whole series in the SVD.
   - **A regressand with no variance:** the regressand is the window's **last
     `length − lags` squared returns**. When those are all equal, R² is undefined and the
     window is NaN. A run of R zero returns therefore blanks R − (length − lags) + 1 bars,
     starting `lags` bars before any window is entirely flat.
   - Measured: 150 equal closes, i.e. 149 zero returns, blank 60 bars (390..449) at
     length 100 (`test_a_run_of_unchanged_closes_blanks_before_the_window_is_flat`).
     statsmodels blanks the same bars (Gate A, flat case).

## Gate A — correctness

`het_arch(window, nlags=min(10, length // 5))[0]` at every window, lengths 20 and 100
(`measure_arch_lm.py`):

| frame | zero returns | NaN, port / statsmodels | max abs difference |
|---|---|---|---|
| GARCH(0.10, 0.85), 1500 bars | 0% | 20 / 20 and 100 / 100 | 1.8e-14 / 8.5e-14 |
| iid normal, 1500 bars | 0% | 20 / 20 and 100 / 100 | 1.2e-14 / 6.1e-14 |
| tick-rounded near 5 on a 0.01 tick | 15% | 20 / 20 and 100 / 100 | 1.4e-14 / 6.8e-14 |
| iid with 150 flat bars, 800 bars | 19% | 154 / 154 and 160 / 160 | 1.8e-14 / 4.0e-13 |
| near-singular: squared returns periodic (period 3) with 1e-10 relative noise | 0% | 20 / 20 and 100 / 100 | **2.7e-10 / 4.4e-10** |

- The NaN masks are equal in all ten cases.
- The last row is where the two rank cutoffs part (Decision 4). On ordinary data the
  difference stays at 1e-13 or below.
- In the flat case, a window with a single nonzero squared return is fitted exactly, and
  both the port and statsmodels read the maximum, 90.

In the tests:
- the statsmodels call is pinned at 1e-11 on a GARCH frame (skipped without
  statsmodels);
- an independent `lstsq` loop with an explicit intercept is pinned at rtol 1e-9 and
  runs in CI;
- a closed form: squared returns following `e_t = 0.5 e_{t-1} + 1e-4` exactly are
  fitted with R² = 1, so the statistic is the row count, 16 at length 20.

## Gate B — causality

- **Future perturbation:** 16 offsets, every close from `j` on replaced by another path
  rescaled to join it. Bars before `j` are bit-identical.
- **Mutant:** the chunk write offset `lo = length + start` is moved to
  `length - 1 + start`, one bar earlier. The mutant is live, and it is caught at 16 of 16
  offsets.

## Gate C — reachability

- **Synthetic:** 500 of 600 bars fire (100 warm-up), and all 500 values are distinct.
- **Real data: owed.** The counts come with the Gate E run on BIST.
- What blanks a bar is in Decision 5:
  - a bad or overflowing close blanks the `length` bars whose window holds its returns;
  - a run of R ≥ length − lags zero returns blanks R − (length − lags) + 1 bars.

  BIST has suspended and illiquid stretches, so the second case will occur on real data.
  How often is part of Gate C.

## Gate D — scale-free

- ×8 and ×64: bit-identical, with matching NaN masks. Returns are price ratios, which are
  exact under ×2^k.
- ×10 and ×3.7: within 1e-9.
- `0 < fires < n`.

## Semantics — what ARCHLM_100 reads

200 paths × 600 bars per row, 500 values per path (`measure_arch_lm.py`), with returns
of standard deviation 2%:

| returns | pooled median | pooled mean | share > 18.307 (χ²₁₀ 5%) | per-path share p10 / p50 / p90 |
|---|---|---|---|---|
| iid normal | 8.365 | 8.934 | 0.0235 | 0.000 / 0.004 / 0.076 |
| iid Student-t(3) | 5.182 | 6.554 | 0.0419 | 0.000 / 0.024 / 0.112 |
| GARCH(0.05, 0.90) | 9.339 | 10.271 | 0.0725 | 0.000 / 0.046 / 0.188 |
| GARCH(0.10, 0.85) | 11.150 | 12.706 | 0.1779 | 0.032 / 0.163 / 0.334 |
| GARCH(0.20, 0.75) | 15.522 | 17.919 | 0.3946 | 0.188 / 0.398 / 0.618 |

- **The value rises with volatility clustering.** The median goes from 8.4 (iid) to 9.3 /
  11.2 / 15.5 as the GARCH α grows.
- **Not a calibrated test at 90 rows.**
  - On iid normal returns the mean is 8.93, below the asymptotic 10, and 2.35% of bars
    exceed the χ²₁₀ 5% critical value, not 5%.
  - Overlapping windows make the share vary a lot by path: 0% to 7.6% (p10–p90).
  - The column should be read as a ranking, not as a p-value.
- **Fat tails distort both ends.** iid t(3) returns have a lower median (5.18 against
  8.37) but a heavier upper tail: 4.19% of bars exceed 18.307, against 2.35% for normal,
  with a per-path p90 of 0.112 against 0.076. A few huge squared returns dominate a
  window's variance without predicting one another. So a low reading does not mean calm,
  and a high reading on fat-tailed returns does not by itself prove clustering.
- **What the tests pin, on 10 paths:**
  - the ordering iid < GARCH(0.10) < GARCH(0.20), with its medians;
  - the t(3) median being below the normal one.

  The exceedance shares are not pinned. On 10 paths, overlapping windows make them too
  noisy: the iid normal share read 4.2% there, against 2.35% over 200 paths.

## Cost

These are machine-dependent (Intel64 Family 6 Model 140). Times are the best of 3 with
tracemalloc off; peak memory comes from a separate run with tracemalloc on:

| n | length | time | peak memory |
|---|---|---|---|
| 5,000 | 100 | 0.29 s | 46 MiB |
| 5,000 | 252 | 0.67 s | 47 MiB |
| 20,000 | 100 | 1.50 s | 47 MiB |
| 20,000 | 252 | 2.90 s | 48 MiB |
| 200,000 | 100 | 31.3 s | 51 MiB |
| 200,000 | 252 | 54.5 s | 52 MiB |

- Most of the time goes to one SVD per window.
- The same script on this machine has given about half these times in an earlier run,
  and a reviewer's machine measured about 2× slower: treat them as an order of
  magnitude.
- A daily frame of about 5,000 bars takes well under a second. An intraday frame of 200k
  bars takes tens of seconds.

## Open question for the owner

**Simple returns (shipped) or log returns?**
- The prototype's choice is unknown (Decision 1).
- The two columns rank almost identically (ρ 0.9955), but their values differ, by up to
  5.57 with a median of 0.33. A Gate E run on the wrong form would measure a slightly
  different column.
- Switching is a one-line change to `r`, and every test except the semantics pins would
  carry over.

## Gate E — owed

From `../Backtesting/Backtesting` on the owner's machine:

```sh
python scripts/analysis/gate_e_overlap.py run --module pandas_ta.statistics.arch_lm --name arch_lm
python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD   # from this repo
```

The prototype's numbers in the issue (max |ρ| 0.1347 vs `natr`, SHIP) are not a
measurement of this port.

## Gate F — suites

Full suite on this branch (`.venv-pd2`, CI's two deselects, `GATE_E_PENDING_OK=1`):
5104 passed, 84 skipped, 0 failed before the dev merge; 5130 passed, 84 skipped, 0 failed after merging `dev` at `4dca6d3`.

Without the variable, `test_every_indicator_that_needs_a_row_has_one` fails on the owed
rows `arch_lm` and `mtd_ret`; `mtd_ret` is already owed on `dev`. The Backtesting suite
cannot be run here.

## Counters touched

- `CATEGORY_TOTAL` 310 → 311. Statistics is not in `CATEGORY_BUCKETS`.
- README: 311 registered, 319 callable, statistics (29).
- `docs/MLCompanionContract.md`: 655 → 656 tagged and 298 → 299 `SF`, with a revert note
  (newest first).
- `docs/IndicatorDictionary.md`, regenerated with `.venv-pd2`. Its diff is the `arch_lm`
  row (`ARCHLM_100` SF, 100 warm-up), the four counts and the shortlist entry, and nothing
  else.

All counts are as of the merge with `dev` at `4dca6d3`.
