# STL seasonality strength of log price — measured (`stl_seasonal_strength`)

Issue #155 (KATS-STL-SEAS-100), from the owner's library catalog screen, round 5, of
2026-10-25.

**Source:** Kats tsfeatures (Meta, MIT), `get_stl_features`:
`1 - var(resid) / var(seasonal + resid)` (issue text). Kats' own `get_stl_features`
control flow — which STL parameters it passes, if any beyond `period` — is not
independently re-confirmed in this session (no network access to the Kats source). The
screen prototype (`docs/issues/screen/ind_screen_r5.py`, candidate `kats_stl_seas_100`,
local to the owner's machine) calls `statsmodels.tsa.seasonal.STL(window, period=5).fit()`
— i.e. every STL parameter at its statsmodels default (`robust=False`) — on a 100-bar
rolling window of log close.

STL itself is Cleveland, Cleveland, McRae & Terpenning (1990), *STL: A Seasonal-Trend
Decomposition Procedure Based on LOESS*, J. Official Statistics 6, 3-73. `statsmodels`
is a dev-only dependency (`setup.py`'s `extras_require["dev"]`) and is never imported by
shipped code, so this module reimplements STL from scratch in plain numpy — the same
approach `kpss.py` and `arch_lm.py` take for their own statsmodels originals — and is
checked against statsmodels' own STL as an oracle in
`tests/test_stl_seasonal_strength.py` / `docs/measure_stl_seasonal_strength.py`.

**Status:**
- Gates A, B and D are cleared, and this repo's test subset
  (`tests/test_stl_seasonal_strength.py` plus the wiring/count suites named below) is
  green, which is the half of Gate F that runs here.
- **Gate E: SHIP.** Max |ρ| 0.1696 vs `natr_Chg_5d`, per-frame max median 0.1688 — below the
  0.76 ship line. Port stays.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/stl_seasonal_strength.py` | statistics | `STLSEAS_100` | unbounded (Kats' own formula is not clipped; measured [-0.04, 0.69] across this session's synthetic frames) |

Tests: `tests/test_stl_seasonal_strength.py` (29 tests). Four cases (two functions, one
parametrised over lengths 50/100/101) call statsmodels as an oracle and are skipped where
it is absent (CI); the rest, including a CI-runnable cross-check of
`_build_ops`'s closed-form matrix-power shortcut against direct iteration (not an
independent check of the LOESS/cycle-subseries/low-pass math itself — see Gate A, check 2),
run everywhere.

Numbers: `python docs/measure_stl_seasonal_strength.py`, from the repo root; needs
statsmodels for the Gate A oracle. Environment: Python 3.11.2, pandas 2.3.3, numpy
1.26.4. CPU-variant check: `python docs/measure_stl_seasonal_strength_cpu.py`. Measured
2026-11-24.

## Decisions

1. **Input: `log(close / the window's own first close)`**, not `log(close)` directly.
   Mathematically identical (STL's degree-1 trend LOESS absorbs an added constant
   exactly, so the seasonal and residual components — and this ratio — are unchanged),
   but it is what makes Gate D bit-identical under a power-of-two price rescale: the
   same device `kpss.py` uses, and for the same reason (division of two operands each
   multiplied by an exactly-representable factor has an unchanged true quotient, hence
   an unchanged correctly-rounded result).
2. **Window = `length` closes, period fixed at 5.** Bar T reads closes T − length + 1
   .. T. Only `length` is a keyword; `period` is a module constant (`PERIOD = 5`), per
   the issue's own candidate naming (`kats_stl_seas_100` — the "100" is the window, the
   period is baked into the candidate's identity, not a separate suffix).
3. **Every other STL parameter is the statsmodels default for `period=5`**: seasonal
   smoother window 7, trend window 11 (smallest odd integer greater than
   `1.5*5/(1-1.5/7) = 9.545...`), low-pass window 7 (smallest odd integer greater than
   5), all three LOESS degrees 1, `inner_iter=5`, `outer_iter=0` (`robust=False`, the
   screen prototype's own call). These are fixed module constants (`SEASONAL`, `TREND`,
   `LOW_PASS`, `INNER_ITER`), not exposed as keywords, matching the prototype's single
   call shape.
4. **`length` has a floor of 50** (`MIN_LENGTH`): 10 full 5-bar cycles, so each of the 5
   weekday subseries has at least 10 points — comfortably above the 7-point seasonal
   smoother this port's own LOESS implementation needs (`_loess_weights` asserts its
   window never exceeds the data it is given; the floor keeps every LOESS call in that
   regime for every subseries, the low-pass series, and the trend series, so the
   boundary-expansion case the original Cleveland algorithm needs for an
   under-sized window is never exercised and does not need to be implemented). Kats' own
   minimum for `get_stl_features` is not independently confirmed (no network access).
5. **The linear-operator reduction.** With `robust=False`, STL's robustness weights
   never leave 1, so every step of the decomposition — detrending, cycle-subseries
   LOESS, low-pass filtering, deseasonalising, trend LOESS — is linear in the window's
   values, with weights that depend only on position within the window (length, period,
   and the fixed smoother windows), never on the data. The whole 5-iteration inner loop
   therefore collapses to two fixed `length x length` matrices (one for the seasonal
   component, one for the trend), built once per `length` and cached (`_build_ops`),
   then applied to every rolling window by a single matrix multiply. This is not a
   performance shortcut layered on top of "the real algorithm" — it IS the real
   algorithm, computed in closed form rather than by iterating. Checked two ways (Gate A
   below): statsmodels' own (iterative, Cython) STL, independent of this module
   entirely, matches to ~1e-13; and
   `tests/test_stl_seasonal_strength.py::test_matches_a_hand_run_fixed_point_recursion`
   / `docs/measure_stl_seasonal_strength.py`'s `fixed_point_cross_check` re-run the
   5-pass recursion by direct iteration (no closed-form matrix powers) and match the
   module's closed-form shortcut to ~1e-13 too — but that second check reuses the
   module's own `_seasonal_op`/`_loess_weights`, so it validates only the closed-form
   reduction, not the LOESS/cycle-subseries/low-pass math those operators implement
   (see Gate A's wording below for the precise boundary).
6. **The flat/jitter guard, not the diff1_pacf5/diff2_acf1 shape.** A window whose log
   closes do not vary beyond the rounding of `log(close)` (standard deviation at most 64
   machine epsilons times `1 + max|log close|`) is NaN — an exactly flat price, or
   one-ulp float jitter around one, where `var(seasonal + resid)` would be a rounding
   artifact (0/0 in the exact-flat case). Unlike diff1_pacf5/diff2_acf1, which guard
   RETURNS (where a smooth deterministic drift is exactly constant), this guard does
   **not** blank a drift of any steepness: STL reads log-close LEVELS directly, and a
   drift's values genuinely vary. Measured (`guard`, below): every drift case still
   fires with ordinary-looking values; only the exactly-flat and one-ulp-jitter cases
   are blanked.
7. **Bad inputs**, same rule as the other log-based ports: a close that is NaN, infinite,
   zero, negative or subnormal (below 2.2e-308) is missing data, and its windows are
   NaN — here via IEEE 754 NaN poisoning every output of the matrix multiply
   (`0 * NaN = NaN` regardless of the multiplying weight), not a separate check.
8. **Not clipped to [0, 1].** The issue's formula has no clip, and Kats' own call is not
   independently confirmed to clip either; this port reports the raw ratio. Measured: a
   near-flat drift (`g=1e-10`) reaches -0.04 on a 300-bar synthetic frame (see "the
   flat/jitter guard" numbers below) — still finite and well-behaved, not a guard
   failure, just the ratio going slightly negative the way Hyndman's unclipped
   seasonal-strength measure can.

## Gate A — correctness

**Two checks**, the first independent of the module's own matrix-building code, the
second not:

1. **statsmodels' `STL(window, period=5).fit()`** — the exact call the screen prototype
   made — run on **every window** of two 400-bar AR(1) frames (φ = 0.2 and φ = -0.4), at
   lengths 50, 100 and 101, plus a non-multiple-of-5 length (53, exercising the general
   unequal-subseries-length interleaving in `_cycle_subseries_op`) on a third frame:

   | frame | length | fits checked | max abs diff |
   |---|---|---|---|
   | AR(1) φ=0.2, 400 bars | 50 | 351 | 4.20e-14 |
   | AR(1) φ=0.2, 400 bars | 100 | 301 | 4.23e-14 |
   | AR(1) φ=0.2, 400 bars | 101 | 300 | 1.01e-13 |
   | AR(1) φ=-0.4, 400 bars | 50 | 351 | 4.41e-14 |
   | AR(1) φ=-0.4, 400 bars | 100 | 301 | 6.18e-14 |
   | AR(1) φ=-0.4, 400 bars | 101 | 300 | 1.03e-13 |
   | AR(1) φ=0.1, 200 bars | 53 (not a multiple of 5) | 148 | 4.23e-14 |

   Every difference is at the ~1e-13 scale or below — rounding, not a modelling gap.
   `test_matches_statsmodels_stl` (lengths 50/100/101) and
   `test_a_length_not_a_multiple_of_5_still_matches` (length 53) pin this; both skip
   where statsmodels is absent (CI).
2. **A hand-run fixed-point recursion** (`tests/test_stl_seasonal_strength.py::
   _fixed_point_stl`, used by `test_matches_a_hand_run_fixed_point_recursion` and this
   script's `fixed_point_cross_check`): the same 5-pass inner loop iterated directly
   (`S = seasonal_op @ (Y - T); T = trend_loess_op @ (Y - S)`, five times from `T=0`),
   not via `_build_ops`'s closed-form matrix powers. Matches the module to **6.64e-14**
   over 201 windows of a 300-bar AR(1) frame. **Not an independent check of the
   LOESS/cycle-subseries/low-pass math** — `_fixed_point_stl` calls `_seasonal_op` and
   `_loess_weights`, the same operator-construction code `_build_ops` itself uses to
   build its two matrices, so a bug there would be inherited by both sides of this
   comparison and would not be caught by it. What it DOES independently check is
   narrower but still real: that the closed-form matrix-power shortcut in `_build_ops`
   (`coefs[-1]`/`coefs[-2]`) actually equals direct iteration of the recursion it claims
   to shortcut — a bug in that algebra (an off-by-one pass count, the wrong
   `coefs` index for the final seasonal) would show up here even though it runs on the
   same underlying operators. Check 1 above (statsmodels, skipped in CI) is the only
   independent check of the LOESS/cycle-subseries/low-pass math itself.

## Gate B — causality

- **Future perturbation:** 16 offsets, every close from `j` on replaced by another path
  rescaled to join it. Real module leaks at **0 of 16** offsets.
- **Mutant:** the chunk write offset `lo = length - 1 + start` moved to `length - 2 +
  start`, one bar earlier. Live (differs from the real module on a 600-bar frame) and
  caught at **16 of 16** offsets.
- **A bad close moves exactly its windows:** a close set to NaN at bar 300 (window width
  100) nulls exactly bars 300..399; every other bar is bit-identical
  (`test_a_bad_close_nulls_exactly_its_windows`).

## Gate C — reachability

- **Synthetic** (`reachability`; also `test_fires_and_is_not_constant`): 501 of 600 bars
  fire (first at bar 99), all 501 values distinct, range [0.1858, 0.5291] on this frame.
- **Real data:** Gate E's run, 390,038 bars pooled, `STLSEAS_100` non-NaN and non-zero on
  all of them (see Gate E below).

## Gate D — scale-free

- ×8 and ×64: **bit-identical**, NaN masks matching (`test_price_scale_is_bit_identical`
  — see Decision 1 for why this port achieves exact bit-identity where a naive
  `log(close)` input would not).
- ×10 and ×3.7: within 1e-10, well inside tolerance (1.78e-15 / 2.00e-15 measured;
  `test_price_scale_within_tolerance`).
- `0 < fires < n`, and the column is not constant (`test_fires_and_is_not_constant`).
- Chunk-size independence: not bit-exact (BLAS's summation order can differ by a
  handful of ULPs across chunk sizes — measured max abs diff 1.33e-15, tested below
  1e-9), unlike the simpler elementwise ports' chunk tests
  (`test_chunk_boundaries_do_not_change_values`).

## The flat/jitter guard

(`guard`, above; see Decision 6.)

| series (300 bars) | fires | range |
|---|---|---|
| `100*(1+1e-2)^t` | 201 of 201 | [0.3043, 0.3973] |
| `100*(1+1e-4)^t` | 201 of 201 | [0.2348, 0.5974] |
| `100*(1+1e-7)^t` | 201 of 201 | [0.1667, 0.5662] |
| `100*(1+1e-8)^t` | 201 of 201 | [0.2172, 0.6112] |
| `100*(1+1e-10)^t` | 201 of 201 | [-0.0374, 0.6903] |
| 10.0 with one-ulp jitter | 0 | — |
| exactly flat (150 bars of 10.0) | 0 | — |
| iid log returns, sd 1e-12 | 201 of 201 | — |
| iid log returns, sd 1e-9 | 201 of 201 | — |

Every drift, however shallow, still fires with ordinary-looking values; only the
exactly-flat and one-ulp-jitter cases are blanked. Pinned by
`test_a_smooth_drift_still_fires`, `test_flat_prices_are_nan`,
`test_one_ulp_jitter_is_nan`.

## Cost

Machine-dependent (x86_64). Timings are the range over 5 runs with tracemalloc off;
peak memory from a separate run with tracemalloc on (`cost`, above):

| n | length | time | peak memory |
|---|---|---|---|
| 5,000 | 100 | 0.013–0.019 s | 3 MiB |
| 5,000 | 252 | 0.035–0.079 s | 3 MiB |
| 20,000 | 100 | 0.051–0.113 s | 3 MiB |
| 20,000 | 252 | 0.145–0.182 s | 3 MiB |
| 200,000 | 100 | 0.493–0.525 s | 6 MiB |
| 200,000 | 252 | 1.601–1.682 s | 6 MiB |

The two fixed `length x length` matrices are built once (cached per `length`) and
reused for every window via a single matrix multiply per chunk, so cost scales with `n`
and with `length^2` (building the matrices) plus `n * length` (applying them) rather
than with `n * length` STL fits the way the screen prototype's per-window
`statsmodels.STL(...).fit()` loop did.

## Gate E — overlap

Run `is155-stl_seasonal_strength-8a978073`, 2026-11-24, 89 ALTPORT-1 frames, 398,849
pooled bars (390,038 non-NaN/non-zero for `STLSEAS_100`), 687 comparators
(329 `compute_all` + 358 manifest), canary bit-equal (AKBNK.IS, BIENY.IS, AGHOL.IS,
SASA.IS).

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `STLSEAS_100` | 0.1696 | `natr_Chg_5d` (manifest) | 390,038 | 0.1688 | SHIP |

Next comparators: `natr_Chg_5d` 0.1696, consistent with the issue's own prototype
measurement (0.1696 vs the same comparator). Well inside the SHIP band (< 0.76).
Recorded in `docs/gate_e_ledger.csv`.

## Gate F — suites

Not the whole suite (the launcher runs it). This session's subset, from the repo root:

```
python -m pytest -q tests/test_stl_seasonal_strength.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

Result (this receipt session, after recording the ledger row above): all pass.

CPU-variant check (`python docs/measure_stl_seasonal_strength_cpu.py`,
`NPY_DISABLE_CPU_FEATURES` set to this machine's AVX-512/AVX2/FMA3 features, standing in
for a GitHub runner without AVX-512): all tests passed.

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 382 → 383 (`tests/test_altport2_ports.py`).
- README: 382 → 383 registered, 390 → 391 callable, statistics (71) → (72).
- `docs/IndicatorDictionary.md`, regenerated (`python docs/gen_indicator_dictionary.py`).
- `Category`: `stl_seasonal_strength` placed alphabetically, after `stdev`.
