# Stability of returns — measured (`stability`)

Issue #158 (KATS-STABILITY-100), from the owner's library catalog screen, round 5, of
2026-10-25.

**Source:** Kats tsfeatures (Meta, MIT), `get_stability` (issue #158's text; the exact
line/commit in `kats/tsfeatures/tsfeatures.py` is not independently re-confirmed in this
session, no network access to the Kats source), after Hyndman's tsfeatures `stability`:

```python
v = [np.mean(x_w) for x_w in np.array_split(x, len(x) // window_size + 1)]   # window_size = 20
return np.var(v)
```

**Status:**
- Gates A, B and D are cleared below.
- Gate E: **pending, run by issue-solver after this session.**
- Gate F: this repo's own suite (the module's tests plus the wiring/ledger/dictionary
  guards) is green, including under the CI CPU-feature set (see "Gate F"). Whole suites:
  run by issue-solver in clean worktrees (see the PR body).

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/stability.py` | statistics | `STABILITY_100` | `[0, +inf)` or NaN |

Tests: `tests/test_stability.py` (29 tests).

Numbers: `python docs/measure_stability.py`, run from the repo root. Environment:
Python 3.11.2, pandas 2.3.3, numpy 1.26.4. Measured 2026-11-24.

## Decisions

1. **Input and window.** The input is one-bar simple returns,
   `close / close.shift(1) - 1`, and the window is `length` returns, so bar T reads closes
   T − length .. T. This is the same convention as `lumpiness` (#156) and `arch_lm` (#154).
   - Kats applies the function to a whole series. The issue says the 100-bar window and
     z-scoring the window ("scale-free form: returns z-scored in the window") are the
     prototype's choices; its code (`ind_screen_r5.py`) is local to the owner's machine.
2. **The z-score** is `(r − mean) / std` over the window, with population std
   (`ddof = 0`) — the same z-score `lumpiness` uses, since `stability` is `get_lumpiness`'s
   sibling in Kats/Hyndman's tsfeatures family and the issue gives it the identical
   "returns z-scored in the window" note.
3. **The tiles are Kats' `array_split`, not fixed blocks of 20, and are identical to
   `lumpiness`'s.**
   - 100 returns make 6 tiles of 17, 17, 17, 17, 16, 16, and 252 make 13 (5 of 20, 8 of
     19) — pinned by `test_tiles_are_kats_array_split`, reusing `lumpiness`'s own pinned
     numbers.
   - `stability` and `lumpiness` differ only in what each tile is reduced to before the
     outer `np.var` — mean here, variance there — so the module reuses `lumpiness`'s
     `_tiles` helper shape (copied, not imported, since each port stays a single file).
   - `length` has a floor of 20 (2 tiles). Below that there is one tile, whose variance of
     means is the constant 0. A smaller or missing value falls back to 100, the repo's
     convention (`kpss`, `arch_lm`, `lumpiness`). `length=10` and `19` are tested.
4. **A rounding guard that Kats does not need** — identical in form to `lumpiness`'s,
   because it guards the identical z-score.
   - The rule: a window is NaN when the std of its returns is at most **64 machine
     epsilons × the window's largest |1 + r|**, about 1.4e-14 for ordinary returns.
   - Why it is needed: a steady drift of any size, or a flat price jittering by one ulp,
     z-scores to exactly the kind of one-directional run `stability` is built to flag in
     real data — so an unguarded window reads a large, spurious value made of floating-
     point noise, not structure.
   - Measured, shipped against unguarded (`measure_stability.py`):

     | series (300 bars) | shipped fires | unguarded fires, median / max |
     |---|---|---|
     | `100 * (1 + 1e-2)^t` | 0 | 200, 0.014 / 0.047 |
     | `100 * (1 + 1e-4)^t` | 0 | 200, 0.014 / 0.046 |
     | `100 * (1 + 1e-7)^t` | 0 | 200, 0.020 / 0.059 |
     | `100 * (1 + 1e-8)^t` | 0 | 200, 0.016 / 0.056 |
     | `100 * (1 + 1e-10)^t` | 0 | 141, 0.049 / 0.055 |
     | 10.0 with one-ulp jitter | 0 | 200, 0.003 / 0.006 |

   - Where it changes nothing: on the five Gate A frames below, at lengths 20, 100 and
     252, the guarded and unguarded columns are identical on every bar.
   - Where it does act: on a 10%-a-bar series on a 0.01 tick, it blanks 37 bars at length
     20 and none at 100 or 252 — the same case, and the same count, `lumpiness` measures,
     since both guard the same return series at the same price level.
   - Kats works on the raw series, so this case does not arise there. The guard belongs
     to the prototype's z-scored form.
5. **Bad inputs.**
   - A window with a NaN, zero or negative close is NaN.
   - So is a window holding a return whose square overflows, such as one extreme close of
     1e-300 or 1e160. Same masking as `lumpiness`/`arch_lm`.
   - Each window is computed on its own, in chunks, so a bad tick moves exactly the bars
     whose window holds one of its two returns: bars 300..400 for a tick at bar 300.

## Gate A — correctness

Kats' two lines, verbatim (issue #158's text, `np.mean` per tile then `np.var` across
tiles), on the z-scored window, at every bar (`measure_stability.py`), for lengths
20 / 63 / 100 / 252. The returns use the module's form, `c1 / c0 − 1`. The comparison is
against the **unguarded** module, so the guard does not enter Gate A; it is measured in
Decision 4.

| frame | zero returns | NaN masks equal | max abs difference |
|---|---|---|---|
| GARCH(0.10, 0.85), 1500 bars | 0% | 4 / 4 | 0.0 |
| iid normal, 1500 bars | 0% | 4 / 4 | 0.0 |
| block-regime (±2% mean, 20-bar blocks), 1500 bars | 0% | 4 / 4 | 0.0 |
| tick-rounded near 5 on a 0.01 tick | 23% | 4 / 4 | 0.0 |
| iid with 150 flat bars, 800 bars | 19% | 4 / 4 | 0.0 |

- The port is bit-identical to Kats on all 20 frame × length cases.
- The test oracle (`tests/test_stability.py::test_matches_kats_on_the_z_scored_window`) is
  pinned at 1e-12 relative, on a GARCH frame, lengths 20 and 100.
- A closed form is pinned too: 10 returns of +1% then 10 of -1% (length 20, 2 tiles of 10)
  z-score to tile means exactly +1 and -1 (population std of the window equals the common
  |return|, so each return maps to ±1), so `STABILITY_20 = VAR([1, -1]) = 1.0` exactly.

## Gate B — causality

- **Future perturbation:** 16 offsets, every close from `j` on replaced by another path
  rescaled to join it. Bars before `j` are bit-identical (`test_real_module_never_reads_the_future`).
- **Mutant:** the chunk write offset `lo = length + start` is moved to
  `length - 1 + start`, one bar earlier. The mutant is live (produces a different column
  than the real module) and is caught at 16 of 16 offsets (`test_mutant_is_caught`).

## Gate C — reachability

- **Synthetic:** 500 of 600 bars fire (100 warm-up), and all 500 values are distinct
  (`test_fires_and_is_not_constant`).
- **Real data:** not measured in this session — Gate E's run (pending) is also where the
  real-data fire count will come from, the same as every other port in this repo.
- What blanks a bar:
  - a bad or overflowing close blanks the `length` bars whose window holds its returns;
  - a window whose returns vary only at rounding level is NaN (Decision 4).

  Like `lumpiness`, a window with only some zero returns still fires.

## Gate D — scale-free

- ×8 and ×64: bit-identical, with matching NaN masks (`test_price_scale_is_bit_identical`).
- ×10 and ×3.7: measured max abs diff 5.551e-16 / 5.274e-16 on a 600-bar GARCH frame — far
  inside the 1e-9 the test (`test_price_scale_within_tolerance`) requires.
- `0 < fires < n`: 500 of 600 fire (`test_fires_and_is_not_constant`).

## Semantics — what STABILITY_100 reads

10 paths × 600 bars per row, 500 values per path, returns of standard deviation 2% (iid,
GARCH) or 2%/1% step-mean block-regime paths (20-bar blocks, mean flipping sign each
block — the drift profile the column exists to flag):

| returns | pooled median | pooled mean | p90 |
|---|---|---|---|
| iid normal | 0.0452 | 0.0535 | 0.1012 |
| GARCH(0.10, 0.85) | 0.0446 | 0.0540 | 0.1043 |
| block-regime, drift ±1% | 0.1189 | 0.1254 | 0.1993 |
| block-regime, drift ±2% | 0.2379 | 0.2398 | 0.3175 |

- **It does not react to volatility clustering by itself:** iid normal (0.0452) and
  GARCH(0.10, 0.85) (0.0446) read about the same median — unlike `lumpiness`, which rises
  with GARCH's α, `stability` is built on tile *means*, which an unconditional-mean
  volatility process does not move.
- **It rises with a localised directional run:** a return path whose mean steps between
  +drift and -drift every 20 bars (close to the tile width) reads 2.6× the iid median at
  a 1% step and 5.3× at a 2% step — pinned at the >3× level by
  `test_a_block_regime_reads_higher_than_iid` (10 paths, same generators).
- Medians are RNG-stream dependent (NEP 19); the pytest assertion checks the ordering and
  a 3× margin rather than exact values, the same discipline `lumpiness`'s semantics tests
  use.

## Cost

Machine-dependent (x86_64). Timings come from 5 runs per invocation, tracemalloc off; peak
memory from a separate run with tracemalloc on:

| n | length | time | peak memory |
|---|---|---|---|
| 5,000 | 100 | 0.009–0.010 s | 8 MiB |
| 5,000 | 252 | 0.022–0.023 s | 8 MiB |
| 20,000 | 100 | 0.039–0.040 s | 9 MiB |
| 20,000 | 252 | 0.093–0.095 s | 8 MiB |
| 200,000 | 100 | 0.383–0.392 s | 13 MiB |
| 200,000 | 252 | 0.934–0.998 s | 13 MiB |

Machine load moves these numbers; they are an order of magnitude, not a guarantee.

## Gate E — pending, run by issue-solver after this session

Not run here (this session does not have access to `../Backtesting` and never runs
`gate_e_overlap.py`; see `CLAUDE.md`'s "Owed, not failed, on the way to `dev`"). The
launcher runs Gate E after this session and a later receipt session records the ledger
row and the measured numbers here.

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_stability.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

Result: 1 failed, 1479 passed, 7 skipped. The 1 failure is
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` on the owed
`stability` row — expected per the issue-solver rules until the launcher's Gate E run and
a receipt session record it, not a defect.

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for a GitHub
runner without AVX-512 — this machine's own dispatchable set per
`numpy.core._multiarray_umath.__cpu_features__`): `python docs/measure_stability_cpu.py`
— 29 passed (just `tests/test_stability.py`; the ledger/readme/wiring modules above are
not CPU-sensitive and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 383 → 384. Statistics is not in `CATEGORY_BUCKETS`.
- README: 383 → 384 registered, 391 → 392 callable, statistics (72) → (73).
- `docs/MLCompanionContract.md`: 728 → 729 tagged and 362 → 363 `SF` (newest first in the
  chain).
- `docs/IndicatorDictionary.md`, regenerated with this environment's package. Its diff is
  the `stability` row (`STABILITY_100` SF, 100 warm-up), the three header counts, the
  statistics section count, and the SF shortlist, and nothing else.
- `Category`: `stability` is placed alphabetically, after `skew` and before `stdev`.

All counts are as of this branch, based on `dev` at `3f8cc3d`.
