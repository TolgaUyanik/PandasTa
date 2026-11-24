# STL trend strength of log price — measured (`stl_trend_strength`)

Issue #160 (KATS-STL-TREND-100), from the owner's library catalog screen, round 5, of
2026-10-25.

**Source:** Kats tsfeatures (Meta, MIT), `get_stl_features`:
`1 - var(resid) / var(trend + resid)` (issue text). Kats' own `get_stl_features`
control flow — which STL parameters it passes, if any beyond `period` — is not
independently re-confirmed in this session (no network access to the Kats source). The
screen prototype (`docs/issues/screen/ind_screen_r5.py`, candidate `kats_stl_trend_100`,
local to the owner's machine) calls `statsmodels.tsa.seasonal.STL(window, period=5).fit()`
— i.e. every STL parameter at its statsmodels default (`robust=False`) — on a 100-bar
rolling window of log close.

STL itself is Cleveland, Cleveland, McRae & Terpenning (1990), *STL: A Seasonal-Trend
Decomposition Procedure Based on LOESS*, J. Official Statistics 6, 3-73. `statsmodels`
is a dev-only dependency (`setup.py`'s `extras_require["dev"]`) and is never imported by
shipped code. This module does **not** re-derive the STL decomposition from scratch:
`pandas_ta.statistics.stl_seasonal_strength` (issue #155) already reimplements it in
plain numpy — `_build_ops`, the two fixed `length x length` operators the 5-iteration
inner loop collapses to under `robust=False` — and checks that reimplementation against
statsmodels' own STL as an oracle. This module imports `_build_ops` and three constants
(`NOISE_ULPS`, `MIN_LENGTH`, `CHUNK_CELLS`) from that module rather than duplicating the
LOESS/cycle-subseries/low-pass math; only the final ratio differs (`var(trend + resid)`
here, `var(seasonal + resid)` there). This is the same pattern the fork already uses
elsewhere (`pandas_ta/momentum/sk_fcb_pos.py` imports private helpers from
`pandas_ta/volatility/sk_fcb_width.py`) — not a new convention.

**Status:**
- Gates A, B and D are cleared, and this repo's test subset
  (`tests/test_stl_trend_strength.py` plus the wiring/count suites named below) is
  green, which is the half of Gate F that runs here.
- **Gate E: SHIP.** `STLTREND_100` max |ρ| 0.4498 vs `Cloud_Thickness_pct` (manifest,
  n = 390,038); per-frame max median 0.4530 (89 frames, 0% of frames ≥ 0.90). Both well
  under the 0.76 ship line. See the Gate E section below for the full run record.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/stl_trend_strength.py` | statistics | `STLTREND_100` | unbounded (Kats' own formula is not clipped; measured [0.9093, 0.9958] on this session's AR(1) synthetic frame, and exactly 1.0 for a noiseless drift — see Gate C and the drift guard table) |

Tests: `tests/test_stl_trend_strength.py` (29 tests). Two test functions (four
parametrized cases) call statsmodels as an oracle and skip where it is absent (CI); the
rest, including a hand-run fixed-point cross-check that does not depend on statsmodels,
run everywhere.

Numbers: `python docs/measure_stl_trend_strength.py`, from the repo root; needs
statsmodels for the Gate A oracle. Environment: Python 3.11.2, pandas 2.3.3, numpy
1.26.4. CPU-variant check: `python docs/measure_stl_trend_strength_cpu.py`. Measured
2026-11-24.

## Decisions

1. **Reuse `stl_seasonal_strength`'s `_build_ops`, not a re-derivation.** The two
   indicators are literally the same STL decomposition (`period=5`, same `seasonal`
   / `trend` / `low_pass` windows, same `robust=False` linearisation into two fixed
   `length x length` matrices) with a different final ratio. A second, independently
   written copy of the LOESS/cycle-subseries/low-pass math would be a correctness risk
   of its own — the two copies drifting apart on a future fix to one — not a benefit, so
   `stl_trend_strength.py` imports `_build_ops` (plus `NOISE_ULPS`, `MIN_LENGTH`,
   `CHUNK_CELLS`) from `pandas_ta.statistics.stl_seasonal_strength` directly. The shared
   `_OP_CACHE` (keyed by window `length` alone) is the same dict object in both modules —
   verified in `test_build_ops_is_shared_with_stl_seasonal_strength`. This module's own
   test suite therefore does not re-validate the LOESS math against statsmodels from
   scratch; it validates that THIS module combines the shared operators into the right
   ratio (Gate A below compares against statsmodels' `trend`/`resid` directly, which is
   independent of `_build_ops`'s own construction code).
2. **Input: `log(close / the window's own first close)`**, not `log(close)` directly —
   inherited unchanged from `stl_seasonal_strength`, same reasoning (bit-identity under a
   power-of-two price rescale; STL's degree-1 trend LOESS absorbs an added constant
   exactly).
3. **Window = `length` closes, period fixed at 5.** Same as `stl_seasonal_strength`:
   `period` is a module constant (`PERIOD = 5`, imported transitively via `_build_ops`),
   not a keyword — the issue's own candidate naming (`kats_stl_trend_100`) bakes the
   period into the candidate's identity.
4. **`length` has a floor of 50** (`MIN_LENGTH`, imported from `stl_seasonal_strength`):
   same justification — 10 full 5-bar cycles, so the shared LOESS implementation's own
   window-size requirements are always met.
5. **The drift case: the trend strength of a smooth drift is exactly 1, not just
   "fires".** Unlike `stl_seasonal_strength` (where a drift gives ordinary-looking mid-
   range values, since the drift carries no 5-bar seasonal signal), a noiseless
   deterministic drift of ANY steepness here measures trend strength of 1.0000 at every
   tested g (1e-2 through 1e-10, measured below): the residual is ~0 (a smooth drift has
   no noise for STL to leave behind), so `1 - var(resid)/var(trend+resid) -> 1`. This is
   mathematically expected, not a guard artefact — a pure deterministic drift genuinely
   has no non-trend variation.
6. **The flat/jitter guard, same as `stl_seasonal_strength`.** A window whose log closes
   do not vary beyond the rounding of `log(close)` (standard deviation at most 64 machine
   epsilons times `1 + max|log close|`) is NaN, because `var(trend + resid)` would be a
   rounding artifact (0/0 in the exact-flat case). Imported unchanged (`NOISE_ULPS`).
7. **Bad inputs**, same rule as every other log-based port: a close that is NaN,
   infinite, zero, negative or subnormal (below 2.2e-308) is missing data, and its
   windows are NaN via IEEE 754 NaN poisoning of the shared matrix multiply.
8. **Not clipped to [0, 1].** The issue's formula has no clip, and Kats' own call is not
   independently confirmed to clip either; this port reports the raw ratio. Measured: a
   AR(1)-return random-walk frame reaches as low as 0.9093 (still well inside [0, 1] on
   every frame tested this session — no negative or >1 values were observed, unlike
   `stl_seasonal_strength`, which did go slightly negative on a near-flat drift).

## Gate A — correctness

**Two checks**, both independent of `_build_ops`'s own LOESS/cycle-subseries/low-pass
construction code (unlike `stl_seasonal_strength`'s own fixed-point cross-check, which
shares that code — see Decision 1):

1. **statsmodels' `STL(window, period=5).fit()`** — the exact call the screen prototype
   made — run on **every window** of two 400-bar AR(1) frames (φ = 0.2 and φ = -0.4), at
   lengths 50, 100 and 101, plus a non-multiple-of-5 length (53, exercising the general
   unequal-subseries-length interleaving) on a third frame, comparing this module's
   output against `1 - var(statsmodels resid) / var(statsmodels trend + statsmodels resid)`:

   | frame | length | fits checked | max abs diff |
   |---|---|---|---|
   | AR(1) φ=0.2, 400 bars | 50 | 351 | 1.15e-14 |
   | AR(1) φ=0.2, 400 bars | 100 | 301 | 1.89e-15 |
   | AR(1) φ=0.2, 400 bars | 101 | 300 | 4.55e-15 |
   | AR(1) φ=-0.4, 400 bars | 50 | 351 | 2.73e-14 |
   | AR(1) φ=-0.4, 400 bars | 100 | 301 | 1.99e-14 |
   | AR(1) φ=-0.4, 400 bars | 101 | 300 | 2.74e-14 |
   | AR(1) φ=0.1, 200 bars | 53 (not a multiple of 5) | 148 | 6.44e-15 |

   Every difference is at the ~1e-14 scale or below — rounding, not a modelling gap.
   `test_matches_statsmodels_stl` (lengths 50/100/101) and
   `test_a_length_not_a_multiple_of_5_still_matches` (length 53) pin this; both skip
   where statsmodels is absent (CI). This check is independent of `_build_ops`'s own
   construction code: it compares this module's output against statsmodels' `trend`/
   `resid` attributes directly, not against anything `_build_ops` produces.
2. **A hand-run fixed-point recursion** (`tests/test_stl_trend_strength.py::
   _fixed_point_stl`, used by `test_matches_a_hand_run_fixed_point_recursion` and this
   script's `fixed_point_cross_check`): the same 5-pass inner loop iterated directly by
   calling `stl_seasonal_strength`'s own `_seasonal_op`/`_loess_weights` (not via
   `_build_ops`'s closed-form matrix powers). Matches the module to **1.41e-14** over 201
   windows of a 300-bar AR(1) frame. Like `stl_seasonal_strength`'s own equivalent check,
   this is **not** an independent check of the underlying LOESS math (it calls the same
   `_seasonal_op`/`_loess_weights` functions `_build_ops` itself uses) — it is a second
   route to this module's own ratio for a sanity cross-check, with the statsmodels oracle
   above being the only genuinely independent one.

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
  fire (first at bar 99), all 501 values distinct, range [0.9093, 0.9958] on this AR(1)
  frame (φ=0, the trend component dominates a random-walk log-price window, so the
  strength sits high — consistent with the standard tsfeatures observation that
  trend-strength of a random walk is typically close to 1).
- **Real data:** 390,038 bars non-NaN and non-zero of 398,849 pooled (Gate E run, below).

## Gate D — scale-free

- ×8 and ×64: **bit-identical**, NaN masks matching (`test_price_scale_is_bit_identical`
  — same mechanism as `stl_seasonal_strength`, see Decision 2).
- ×10 and ×3.7: within **2.22e-16** (`test_price_scale_within_tolerance`) — at the limit
  of float64 precision, tighter even than `stl_seasonal_strength`'s 1e-10 on the same
  shared operators (the trend/residual sum evidently cancels the rescale's rounding
  error more completely than the seasonal/residual sum does on this frame; both are well
  inside the 1e-9 Gate D tolerance either way).
- `0 < fires < n`, and the column is not constant (`test_fires_and_is_not_constant`).
- Chunk-size independence: not bit-exact (BLAS's summation order can differ by a
  handful of ULPs across chunk sizes — measured max abs diff **1.11e-16**, tested below
  1e-9), same shape as `stl_seasonal_strength`'s equivalent test
  (`test_chunk_boundaries_do_not_change_values`).

## The flat/jitter guard and the drift case

(`guard`, above; see Decisions 5 and 6.)

| series (300 bars) | fires | range |
|---|---|---|
| `100*(1+1e-2)^t` | 201 of 201 | [1.0000, 1.0000] |
| `100*(1+1e-4)^t` | 201 of 201 | [1.0000, 1.0000] |
| `100*(1+1e-7)^t` | 201 of 201 | [1.0000, 1.0000] |
| `100*(1+1e-8)^t` | 201 of 201 | [1.0000, 1.0000] |
| `100*(1+1e-10)^t` | 201 of 201 | [1.0000, 1.0000] |
| 10.0 with one-ulp jitter | 0 | — |
| exactly flat (150 bars of 10.0) | 0 | — |
| iid log returns, sd 1e-12 | 201 of 201 | — |
| iid log returns, sd 1e-9 | 201 of 201 | — |

Every drift, however shallow, still fires — and measures trend strength of exactly 1.0
to 4-decimal display precision, as expected for a noiseless deterministic trend (see
Decision 5); only the exactly-flat and one-ulp-jitter cases are blanked. Pinned by
`test_a_smooth_drift_still_fires`, `test_flat_prices_are_nan`,
`test_one_ulp_jitter_is_nan`.

## Cost

Machine-dependent (x86_64). Timings are the range over 5 runs with tracemalloc off;
peak memory from a separate run with tracemalloc on (`cost`, above):

| n | length | time | peak memory |
|---|---|---|---|
| 5,000 | 100 | 0.012–0.013 s | 3 MiB |
| 5,000 | 252 | 0.035–0.078 s | 3 MiB |
| 20,000 | 100 | 0.048–0.095 s | 3 MiB |
| 20,000 | 252 | 0.143–0.151 s | 3 MiB |
| 200,000 | 100 | 0.472–0.519 s | 6 MiB |
| 200,000 | 252 | 1.502–1.539 s | 6 MiB |

Same cost profile as `stl_seasonal_strength`: the two fixed `length x length` matrices
(shared with that module via `_build_ops`'s cache) are built once per `length` and
applied to every window by a matrix multiply, so cost scales with `n` and `length^2`
(matrix build, amortised by the shared cache when both indicators run in the same
process) plus `n * length` (applying them).

## Gate E — attribution

Run `is160-stl_trend_strength-bff8ed6e`, 2026-11-24, via
`../Backtesting/Backtesting/scripts/analysis/gate_e_overlap.py run --module
pandas_ta.statistics.stl_trend_strength`. 89 ALTPORT-1 BIST frames, 398,849 pooled bars,
687 comparators (329 `compute_all` + 358 manifest), canary bit-equal (AKBNK.IS, BIENY.IS,
AGHOL.IS, SASA.IS).

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `STLTREND_100` | 0.4498 | `Cloud_Thickness_pct` (manifest) | 390,038 | 0.4530 | **SHIP** |

Next comparator: `ICHI_CLOUD_THICK` (compute_all), also 0.4498. Both well under the 0.76
ship line (`r3-perframe-0.90` bands); 0% of the 89 frames reach the 0.90 per-frame line.
Recorded in `docs/gate_e_ledger.csv`.

## Gate F — suites

Not the whole suite (the launcher runs it). This session's subset, from the repo root:

```
python -m pytest -q tests/test_stl_trend_strength.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

Re-run in this receipt session, after the ledger row was recorded: 1503 passed, 7
skipped (0 failed — the ledger row closes the previously-owed failure).

CPU-variant check (`python docs/measure_stl_trend_strength_cpu.py`,
`NPY_DISABLE_CPU_FEATURES` set to this machine's AVX-512/AVX2/FMA3 features, standing in
for a GitHub runner without AVX-512): all 29 tests passed.

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 385 → 386 (`tests/test_altport2_ports.py`).
- README: 385 → 386 registered, 393 → 394 callable, statistics (74) → (75).
- `docs/IndicatorDictionary.md`, regenerated (`python docs/gen_indicator_dictionary.py`).
- `docs/MLCompanionContract.md`'s running SF tally: 730 → 731 tagged, 364 → 365 `SF`.
- `Category`: `stl_trend_strength` placed alphabetically, after `stl_seasonal_strength`.
