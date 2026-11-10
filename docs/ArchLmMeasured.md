# ARCH LM statistic — measured (`arch_lm`)

Issue #154 (KATS-ARCH-LM-100), from the owner's library catalog screen, round 5, of
2026-10-25.

**Source:** Engle's ARCH Lagrange-multiplier test (Engle 1982, *Econometrica* 50(4)), as
Kats tsfeatures (Meta, MIT) computes its "heterogeneity" feature in `get_het_arch`
(`kats/tsfeatures/tsfeatures.py` L1255–1269 at commit `a6b7e88`):

```python
return het_arch(x, nlags=min(10, len(x) // 5))[0]
```

Here `het_arch` is `statsmodels.stats.diagnostic.het_arch`, which calls
`acorr_lm(resid**2, nlags)`. Its body is checked against statsmodels 0.15.0 in
`.venv-pd2`:
- regress `e = x**2` on a constant and its `nlags` lags (`lagmat`, `trim="both"`), by
  OLS;
- return `LM = (nobs - ddof) * R²`, where `nobs` is the number of regression rows, and
  `ddof = 0`.

**Status:**
- Gates A, B and D are cleared, and this repo's suite is green, which is the half of
  Gate F that runs here.
- Gate C has synthetic counts only, and Gate E is owed. Both need the BIST frames and the
  private Backtesting repo, which the contributor's machine does not have.
- No owner decision is needed beyond Gate E.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/arch_lm.py` | statistics | `ARCHLM_100` | `[0, length - lags]` = `[0, 90]` at the default, or NaN |

Tests: `tests/test_arch_lm.py` (22 tests). The two statsmodels tests skip where
statsmodels is absent: in CI, and in `.venv`, where 20 pass and 2 are skipped.

Numbers: `python docs/measure_arch_lm.py`, run from the repo root. It needs statsmodels
for its Gate A section.

Environment: Python 3.13.14, pandas 2.3.3, numpy 2.5.4 (`.venv-pd2`). Measured
2026-11-10.

## Decisions

1. **The input is one-bar simple returns, `close / close.shift(1) - 1`.** This is the
   repo's convention (`osap_retskew_21`, `lot_zeroret_60`, and `ret()` in the screen
   prototype). The window is `length` returns, so bar T reads closes T − length .. T. Kats
   applies the test to a whole series; the issue says the window and the input are the
   prototype's choices, and the prototype's code is not in this repo. R² does not change
   when the returns are scaled; log returns would differ from simple ones only at second
   order.
2. **Lags = `min(10, length // 5)`**, Kats' rule, so 10 at any `length` ≥ 50. It is not a
   separate parameter, so the column name carries only `length`.
3. **The LM statistic itself, not its p-value**, as Kats returns it.
4. **Computed one window at a time, by SVD on the centred design.**
   - Centring y and every regressor removes the constant.
   - The projection keeps singular values above `1e-15` × the largest, which is
     statsmodels' pinv cutoff.
   - Windows are evaluated in chunks of `2^18` cells. A bad tick moves exactly the bars
     whose window holds one of its two returns: bars 300..400 for a tick at bar 300.
5. **NaN windows.** A window with a NaN, zero or negative close is NaN. So is a window
   whose squared returns are all equal, such as no price change at all: its R² is
   undefined.

## Gate A — correctness

`het_arch(window, nlags=min(10, length // 5))[0]` was computed at every window, for
lengths 20 and 100 (`measure_arch_lm.py`):

| frame | zero returns | NaN, port / statsmodels | max abs difference |
|---|---|---|---|
| GARCH(0.10, 0.85), 1500 bars | 0% | 20 / 20 and 100 / 100 | 1.8e-14 / 8.5e-14 |
| iid normal, 1500 bars | 0% | 20 / 20 and 100 / 100 | 1.2e-14 / 6.1e-14 |
| tick-rounded near 5 on a 0.01 tick | 15% | 20 / 20 and 100 / 100 | 1.4e-14 / 6.8e-14 |
| iid with 150 flat bars, 800 bars | 19% | 154 / 154 and 160 / 160 | 1.8e-14 / 4.0e-13 |

- The NaN masks are equal in all eight cases.
- The flat case includes rank-deficient windows. There, a single nonzero squared return
  is fitted exactly, and both the port and statsmodels read the maximum, 90.

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
- Two inputs kill a window: a bad close, or a window with no price change at all.

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
- **Not a calibrated test at 90 rows.** On iid normal returns, 2.35% of bars exceed the
  χ²₁₀ 5% critical value, not 5%. Overlapping windows also make it vary a lot by path:
  the per-path share runs from 0% to 7.6% (p10–p90). The column should be read as a
  ranking, not as a p-value.
- **Fat tails read low.** iid t(3) returns have a median of 5.18, below iid normal's
  8.37. A window's few huge squared returns dominate its variance but do not predict one
  another. A low reading therefore does not mean calm.
- In the tests, the ordering of iid < GARCH(0.10) < GARCH(0.20) and the t(3) result are
  pinned on 10 paths. The exceedance share is not pinned: at 10 paths it read 4.2%,
  which is noise.

## Cost

Measured with tracemalloc on:

| n | length | time | peak memory |
|---|---|---|---|
| 20,000 | 100 | 0.76 s | 47 MiB |
| 20,000 | 252 | 1.38 s | 48 MiB |
| 200,000 | 100 | 7.69 s | 51 MiB |
| 200,000 | 252 | 14.18 s | 52 MiB |

Most of the time goes to one SVD per window. A daily frame of about 5,000 bars takes
well under a second.

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
5101 passed, 84 skipped, 0 failed. Without the variable, `test_every_indicator_that_needs_a_row_has_one`
fails on the owed rows `arch_lm` and `mtd_ret` (the latter already owed on `dev`). The
Backtesting suite cannot be run here.

## Counters touched

- `CATEGORY_TOTAL` 309 → 310. Statistics is not in `CATEGORY_BUCKETS`.
- README: 310 registered, 318 callable, statistics (29).
- `docs/MLCompanionContract.md`: 654 → 655 tagged and 297 → 298 `SF`, with a revert note
  (newest first).
- `docs/IndicatorDictionary.md`, regenerated with `.venv-pd2`. Its diff is the `arch_lm`
  row (`ARCHLM_100` SF, 100 warm-up), the four counts and the shortlist entry, and nothing
  else.

All counts are as of `dev` at `4f9a32e`.
