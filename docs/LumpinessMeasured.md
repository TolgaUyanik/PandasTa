# Lumpiness of returns — measured (`lumpiness`)

Issue #156 (KATS-LUMPINESS-100), from the owner's library catalog screen, round 5, of
2026-10-25.

**Source:** Kats tsfeatures (Meta, MIT), `get_lumpiness` (`kats/tsfeatures/tsfeatures.py`
L658–673 at commit `a6b7e88`), after Hyndman's tsfeatures `lumpiness`:

```python
v = [np.var(x_w) for x_w in np.array_split(x, len(x) // window_size + 1)]   # window_size = 20
return np.var(v)
```

**Status:**
- Gates A, B and D are cleared, and this repo's suite is green, which is the half of
  Gate F that runs here.
- Gate C has synthetic counts only, and Gate E is owed. Both need the BIST frames and the
  private Backtesting repo, which the contributor's machine does not have.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/lumpiness.py` | statistics | `LUMPINESS_100` | `[0, +inf)` or NaN |

Tests: `tests/test_lumpiness.py` (25 tests, passing on pandas 2.3.3 and 3.0.0).

Numbers: `python docs/measure_lumpiness.py`, run from the repo root. Environment:
Python 3.13.14, pandas 2.3.3, numpy 2.5.4 (`.venv-pd2`). Measured 2026-11-10.

## Decisions

1. **Input and window.** The input is one-bar simple returns,
   `close / close.shift(1) - 1`, and the window is `length` returns, so bar T reads closes
   T − length .. T. This is the same convention as `arch_lm` (#154).
   - Kats applies the function to a whole series. The issue says the 100-bar window,
     returns as the input, and z-scoring the window are the prototype's choices. The
     prototype's code (`ind_screen_r5.py`) is on the owner's machine only, so its return
     definition is unknown.
   - Measured over 200 GARCH(0.10, 0.85) paths: log returns would move LUMPINESS_100 by
     at most 0.059. The median move is 0.0026, about 1.6% of the median value 0.169, and
     the Spearman ρ between the two columns is 0.9992. That is small, but it is not zero.
2. **The z-score** is `(r − mean) / std` over the window, with population std
   (`ddof = 0`), the same as Kats' `np.var`. With `ddof = 1` every value would scale by
   the constant `((n − 1) / n)²`.
3. **The tiles are Kats' `array_split`, not fixed blocks of 20.**
   - 100 returns make **6 tiles of 17, 17, 17, 17, 16, 16**, and 252 make 13 (5 of 20,
     8 of 19). These are pinned in `test_tiles_are_kats_array_split`.
   - The tile size (Kats' `window_size` = 20) is fixed rather than a parameter.
   - `length` has a floor of 20 (2 tiles). Below that there is one tile, whose variance
     of variances is the constant 0. A smaller or missing value falls back to 100.
4. **A rounding guard that Kats does not need.**
   - The guard: a window is NaN when the std of its returns is at most 1e-9 × their RMS.
   - Why: z-scoring a window whose returns differ only by floating-point rounding blows
     that noise up to unit variance. On `100 * 1.01^t`, a steady 1% a bar, the returns
     differ by sd/rms 1.0e-14. Unguarded, the column read a median of 0.156 and a maximum
     of 0.593, out of pure rounding.
   - Effect: with the guard, all 200 bars of that series are NaN. On the GARCH frame and
     on the tick-rounded frame, the guarded and unguarded columns are identical on every
     bar. Real tick-level variation (sd/rms 4.6e-4) is kept
     (`test_the_guard_keeps_real_tick_variation`).
   - Kats works on the raw series, so this case does not arise there. The guard exists
     because of the prototype's z-score.
5. **Bad inputs.**
   - A window with a NaN, zero or negative close is NaN.
   - So is a window holding a return whose square overflows, such as one extreme close of
     1e-300 or 1e160. This is the same masking as `arch_lm`.
   - Each window is computed on its own, in chunks, so a bad tick moves exactly the bars
     whose window holds one of its two returns: bars 300..400 for a tick at bar 300.

## Gate A — correctness

Kats' two lines, verbatim, on the z-scored window, at every bar (`measure_lumpiness.py`),
for lengths 20 / 63 / 100 / 252:

| frame | zero returns | NaN masks equal | max abs difference |
|---|---|---|---|
| GARCH(0.10, 0.85), 1500 bars | 0% | 4 / 4 | 4.1e-15 |
| iid normal, 1500 bars | 0% | 4 / 4 | 3.2e-15 |
| iid t(3), 1500 bars | 0% | 4 / 4 | 6.7e-15 |
| tick-rounded near 5 on a 0.01 tick | 23% | 4 / 4 | 1.9e-14 |
| iid with 150 flat bars, 800 bars | 19% | 4 / 4 | 7.1e-15 |

- The script computes returns as `diff / c`, a different rounding from the module's
  `c1 / c0 − 1`, so it is close but not exact.
- The test's oracle uses the module's form and agrees to 1e-12 relative (pinned).
- A closed form is pinned too. 10 returns of ±1% followed by 10 of ±3% z-score to tile
  variances 0.2 and 1.8, so LUMPINESS_20 = 0.64.

## Gate B — causality

- **Future perturbation:** 16 offsets, every close from `j` on replaced by another path
  rescaled to join it. Bars before `j` are bit-identical.
- **Mutant:** the chunk write offset `lo = length + start` is moved to
  `length - 1 + start`, one bar earlier. The mutant is live, and it is caught at 16 of 16
  offsets.

## Gate C — reachability

- **Synthetic:** 500 of 600 bars fire (100 warm-up), and all 500 values are distinct.
- **Real data: owed.** The counts come with the Gate E run on BIST.
- What blanks a bar:
  - a bad or overflowing close blanks the `length` bars whose window holds its returns;
  - a window of all-equal returns, or of returns equal up to rounding, is NaN.

  Unlike `arch_lm`, a window with only some zero returns still fires.

## Gate D — scale-free

- ×8 and ×64: bit-identical, with matching NaN masks.
- ×10 and ×3.7: within 1e-9.
- `0 < fires < n`.

## Semantics — what LUMPINESS_100 reads

200 paths × 600 bars per row, 500 values per path, with returns of standard deviation 2%:

| returns | pooled median | pooled mean | p90 |
|---|---|---|---|
| iid normal | 0.0813 | 0.0937 | 0.1715 |
| iid Student-t(3) | 0.2622 | 0.4398 | 0.9534 |
| GARCH(0.05, 0.90) | 0.1180 | 0.1407 | 0.2624 |
| GARCH(0.10, 0.85) | 0.1692 | 0.2099 | 0.4031 |
| GARCH(0.20, 0.75) | 0.2804 | 0.3693 | 0.7464 |

- **It rises with volatility clustering:** 0.081 for iid, then 0.118 / 0.169 / 0.280 as
  the GARCH α grows.
- **Fat tails read like strong clustering.**
  - iid t(3) returns have no dependence at all, yet they read a median of 0.262, close to
    GARCH(0.20)'s 0.280, with a far heavier upper tail (p90 0.95).
  - One huge squared return makes its own tile's variance dominate the window.
  - So a high LUMPINESS reading does not separate "a volatility burst" from "one outlier
    day".
  - This is the opposite of `arch_lm` (#154), where fat tails read low. The two columns
    may be informative together.
- **What the tests pin, on 10 paths:**
  - the ordering iid < GARCH(0.10) < GARCH(0.20), with medians 0.0822 / 0.1810 / 0.3024;
  - the t(3) median, 0.2827, above twice the normal one.

## Cost

These are machine-dependent (Intel64 Family 6 Model 140). Times are the best of 3 with
tracemalloc off; peak memory comes from a separate run with tracemalloc on:

| n | length | time | peak memory |
|---|---|---|---|
| 5,000 | 100 | 0.023 s | 6 MiB |
| 5,000 | 252 | 0.054 s | 6 MiB |
| 20,000 | 100 | 0.086 s | 7 MiB |
| 20,000 | 252 | 0.168 s | 7 MiB |
| 200,000 | 100 | 0.569 s | 11 MiB |
| 200,000 | 252 | 1.794 s | 11 MiB |

## Gate E — owed

From `../Backtesting/Backtesting` on the owner's machine:

```sh
python scripts/analysis/gate_e_overlap.py run --module pandas_ta.statistics.lumpiness --name lumpiness
python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD   # from this repo
```

The prototype's numbers in the issue (max |ρ| 0.2122 vs `ZIGZAG`, SHIP) are not a
measurement of this port.

## Gate F — suites

Full suite on this branch (`.venv-pd2`, CI's two deselects, `GATE_E_PENDING_OK=1`):
5130 passed, 84 skipped, 0 failed.

Without the variable, `test_every_indicator_that_needs_a_row_has_one` fails on the owed
rows `lumpiness` and `mtd_ret`; `mtd_ret` is already owed on `dev`. The Backtesting suite
cannot be run here.

## Counters touched

- `CATEGORY_TOTAL` 310 → 311. Statistics is not in `CATEGORY_BUCKETS`.
- README: 311 registered, 319 callable, statistics (29).
- `docs/MLCompanionContract.md`: 655 → 656 tagged and 298 → 299 `SF`, with a revert note
  (newest first).
- `docs/IndicatorDictionary.md`, regenerated with `.venv-pd2`. Its diff is the
  `lumpiness` row (`LUMPINESS_100` SF, 100 warm-up), the four counts and the shortlist
  entry, and nothing else.
- `Category`: `lumpiness` is appended to the second statistics line rather than placed
  alphabetically. That keeps it off the line #154 edits, so the two PRs do not conflict.

All counts are as of `dev` at `4dca6d3`.
