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

**Review round 1** (2026-11-10, verdict REVISE: 2 MAJOR, 4 MINOR, 2 NIT) is fixed here:
- The rounding guard was scaled to the size of the returns, so small drifts and one-ulp
  jitter got through, up to a median of 4.34. It is now scaled to machine epsilon.
- The claim that this PR does not conflict with #292 was false. It is withdrawn, and the
  interaction is spelled out below.
- The cost table did not reproduce; it is re-measured.
- The arch_lm comparison was half-told; it is completed.
- The claim that the guard changes nothing was over-general; it is now measured on six
  frames.
- The semantics medians were exact pins on RNG draws; they are now a 5% band.
- NITs: `length=10` is tested, and the Gate A oracle now uses the module's own return
  form.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/lumpiness.py` | statistics | `LUMPINESS_100` | `[0, +inf)` or NaN |

Tests: `tests/test_lumpiness.py` (30 tests, passing on pandas 2.3.3 and 3.0.0).

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
     the Spearman ρ between the two columns is 0.9992.
2. **The z-score** is `(r − mean) / std` over the window, with population std
   (`ddof = 0`), the same as Kats' `np.var`.
3. **The tiles are Kats' `array_split`, not fixed blocks of 20.**
   - 100 returns make 6 tiles of 17, 17, 17, 17, 16, 16, and 252 make 13 (5 of 20, 8 of
     19). These are pinned.
   - The tile size (Kats' `window_size` = 20) is fixed rather than a parameter.
   - `length` has a floor of 20 (2 tiles). Below that there is one tile, whose variance of
     variances is the constant 0. A smaller or missing value falls back to 100, which is
     the repo's convention (as in `kpss` and `arch_lm`). The docstring says so, and
     `length=10` and `19` are tested.
4. **A rounding guard that Kats does not need.**
   - The rule: a window is NaN when the std of its returns is at most **64 machine
     epsilons × the window's largest |1 + r|**, about 1.4e-14 for ordinary returns.
   - Why the floor is absolute: the rounding error of `c / c1 − 1` is about eps × |1 + r|
     whatever the size of r. So a steady drift of any size is pure rounding, and so is a
     flat price jittering by one ulp.
   - Why it is needed: z-scoring such a window blows the noise up to unit variance.
   - Measured, shipped against unguarded (`measure_lumpiness.py`):

     | series (300 bars) | shipped fires | unguarded fires, median / max |
     |---|---|---|
     | `100 * (1 + 1e-2)^t` | 0 | 200, 0.156 / 0.593 |
     | `100 * (1 + 1e-4)^t` | 0 | 200, 0.148 / 0.375 |
     | `100 * (1 + 1e-7)^t` | 0 | 200, 0.123 / 0.421 |
     | `100 * (1 + 1e-8)^t` | 0 | 200, 0.101 / 0.296 |
     | `100 * (1 + 1e-10)^t` | 0 | 141, **4.344** / 4.865 |
     | 10.0 with one-ulp jitter | 0 | 200, 0.036 / 0.086 |

   - The first version of this guard was relative to the RMS of the returns
     (1e-9 × RMS), and it let every drift of 1e-7 or smaller through. All six cases are
     tests now. Both the unguarded module and the old relative guard fail them: 6 of 6
     and 4 of 6.
   - Where it changes nothing: on the five Gate A frames below, at lengths 20, 100 and
     252, the guarded and unguarded columns are identical on every bar.
   - Where it does act: on a 10%-a-bar series on a 0.01 tick, it blanks 37 bars at length
     20 and none at 100 or 252. Those are the windows where the price has grown to about
     1e11, so a 0.01 tick is itself at rounding level.
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
for lengths 20 / 63 / 100 / 252. The returns use the module's form, `c1 / c0 − 1`. The
comparison is against the **unguarded** module, so the guard does not enter Gate A; it is
measured in Decision 4.

| frame | zero returns | NaN masks equal | max abs difference |
|---|---|---|---|
| GARCH(0.10, 0.85), 1500 bars | 0% | 4 / 4 | 0.0 |
| iid normal, 1500 bars | 0% | 4 / 4 | 0.0 |
| iid t(3), 1500 bars | 0% | 4 / 4 | 0.0 |
| tick-rounded near 5 on a 0.01 tick | 23% | 4 / 4 | 0.0 |
| iid with 150 flat bars, 800 bars | 19% | 4 / 4 | 0.0 |

- The port is bit-identical to Kats on all 20 frame × length cases.
- The test oracle is pinned at 1e-12 relative.
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
  - a window whose returns vary only at rounding level is NaN (Decision 4).

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
- **Compared with `arch_lm` (#154, `ArchLmMeasured.md`):** there, t(3) reads a *lower*
  median than normal (5.18 vs 8.37) but a *heavier* upper tail (4.19% vs 2.35% above the
  5% critical value). Here t(3) reads high at the median and in the tail. Fat tails
  distort both columns, in different ways.
- **What the tests pin, on 10 paths:**
  - the ordering iid < GARCH(0.10) < GARCH(0.20);
  - the t(3) median being above twice the normal one.

  The medians themselves (0.0822 / 0.1810 / 0.3024 and t(3) 0.2827) are pinned only
  within 5%, because they depend on numpy's RNG stream (NEP 19).

## Cost

These are machine-dependent (Intel64 Family 6 Model 140). Timings come from 5 runs per
invocation, with tracemalloc off, and the range covers two invocations. Peak memory comes
from a separate run with tracemalloc on:

| n | length | time | peak memory |
|---|---|---|---|
| 5,000 | 100 | 0.005–0.008 s | 8 MiB |
| 5,000 | 252 | 0.012–0.019 s | 8 MiB |
| 20,000 | 100 | 0.021–0.033 s | 9 MiB |
| 20,000 | 252 | 0.048–0.064 s | 8 MiB |
| 200,000 | 100 | 0.213–0.227 s | 13 MiB |
| 200,000 | 252 | 0.491–0.523 s | 13 MiB |

An earlier run on the same machine measured 3–5× slower times. Machine load moves these
numbers, so they are an order of magnitude.

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
5135 passed, 84 skipped, 0 failed.

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
- `Category`: `lumpiness` is placed alphabetically, after `lot_zeroret_60`.

All counts are as of `dev` at `4dca6d3`.

## Interaction with #292 (`arch_lm`)

**The two PRs conflict.** `git merge-tree` shows conflicts in `pandas_ta/__init__.py` (the
same statistics `Category` line), `tests/test_altport2_ports.py`, `README.md`,
`docs/IndicatorDictionary.md` and `docs/MLCompanionContract.md`. Both PRs also add
"+1 on 310".

Whichever lands second has to:
1. merge `dev`;
2. take the counter files from `dev`;
3. re-apply its +1, giving `CATEGORY_TOTAL` 312, README 312 / 320 / statistics (30), and
   MLCompanionContract 657 / 300 `SF`;
4. regenerate the dictionary.

That is the same procedure every port PR here needs once another port lands first.
