# STL residual spikiness of log price — measured (`stl_spikiness`)

Issue #162 (KATS-STL-SPIKE-100), from the owner's library catalog screen, round 5, of
2026-10-25.

**Source:** Kats tsfeatures (Meta, MIT), `get_stl_features`:
`var(nanvar of leave-one-out resid)` (issue text). Kats' own `get_stl_features` control
flow — which STL parameters it passes, if any beyond `period` — is not independently
re-confirmed in this session (no network access to the Kats source). The screen prototype
(`docs/issues/screen/ind_screen_r5.py`, candidate `kats_stl_spike_100`, local to the
owner's machine) calls `statsmodels.tsa.seasonal.STL(window, period=5).fit()` — i.e. every
STL parameter at its statsmodels default (`robust=False`) — on a 100-bar rolling window of
log close.

STL itself is Cleveland, Cleveland, McRae & Terpenning (1990), *STL: A Seasonal-Trend
Decomposition Procedure Based on LOESS*, J. Official Statistics 6, 3-73. `statsmodels` is
a dev-only dependency (`setup.py`'s `extras_require["dev"]`) and is never imported by
shipped code. This module does **not** re-derive the STL decomposition from scratch:
`pandas_ta.statistics.stl_seasonal_strength` (issue #155) already reimplements it in plain
numpy — `_build_ops`, the two fixed `length x length` operators the 5-iteration inner loop
collapses to under `robust=False` — and checks that reimplementation against statsmodels'
own STL as an oracle. This module imports `_build_ops` and three constants (`NOISE_ULPS`,
`MIN_LENGTH`, `CHUNK_CELLS`) from that module rather than duplicating the
LOESS/cycle-subseries/low-pass math. Unlike `stl_seasonal_strength`/`stl_trend_strength`
(both a ratio against the trend or seasonal component), this module needs only the
residual `R = Y - S - T`, which it feeds into a closed-form leave-one-out variance
(see Decision 1).

**Status:**
- Gates A, B and D are cleared, and this repo's test subset
  (`tests/test_stl_spikiness.py` plus the wiring/count suites named below) is green,
  which is the half of Gate F that runs here.
- **Gate E: SHIP.** Max |ρ| 0.6321 vs `natr` (n = 390,038); per-frame max median 0.5918 — see
  below.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/stl_spikiness.py` | statistics | `STLSPIKE_100` | unbounded, non-negative (a variance of variances; measured [1.46e-12, 4.92e-12] on a quiet AR(1) synthetic frame, up to 1.15e-10 on a frame with injected jumps — see Gate C) |

Tests: `tests/test_stl_spikiness.py` (30 tests). Three test functions (five parametrized
cases) call statsmodels as an oracle and skip where it is absent (CI); the rest, including
a hand-run fixed-point cross-check and a closed-form-vs-brute-force check that do not
depend on statsmodels, run everywhere.

Numbers: `python docs/measure_stl_spikiness.py`, from the repo root; needs statsmodels for
the Gate A oracle. Environment: Python 3.11.2, pandas 2.3.3, numpy 1.26.4. CPU-variant
check: `python docs/measure_stl_spikiness_cpu.py`. Measured 2026-11-24.

## Decisions

1. **Leave-one-out variance in closed form, not a per-window `np.delete` loop.** The
   issue's own formula — "var(nanvar of leave-one-out resid)" — reads naturally as: for
   every bar `i` of the window's residual, drop it and take the variance of what's left,
   then take the variance of that whole array of leave-one-out variances. Looping
   `np.delete(r, i)` for every `i` of every window is `O(length^2)` per window and the
   literal reading, so it is kept as the test suite's oracle
   (`tests/test_stl_spikiness.py::_brute_force_spikiness`) rather than discarded. The
   shipped module instead uses the closed form: for a length-`n` residual with sum `S1`
   and sum of squares `S2`, dropping element `i` leaves `n - 1` elements with sum
   `S1 - r_i` and sum of squares `S2 - r_i**2`, so that sub-array's own population mean and
   variance (`ddof=0`, matching `numpy`'s and Kats' presumed default) follow directly with
   no re-summation. Checked identical to the brute-force loop to float rounding
   (`test_closed_form_matches_brute_force_on_an_arbitrary_array`, on plain random data with
   no STL involved; `test_matches_a_hand_run_fixed_point_recursion` and
   `test_matches_statsmodels_stl`, through the full STL chain).
2. **Reuse `stl_seasonal_strength`'s `_build_ops`, not a re-derivation.** Same STL
   decomposition (`period=5`, same `seasonal`/`trend`/`low_pass` windows, same
   `robust=False` linearisation into two fixed `length x length` matrices) as its two
   siblings, with a different final step (this module stops at the residual; the two
   siblings go on to compute a ratio). A second, independently written copy of the
   LOESS/cycle-subseries/low-pass math would be a correctness risk of its own — the two
   copies drifting apart on a future fix to one — not a benefit, so `stl_spikiness.py`
   imports `_build_ops` (plus `NOISE_ULPS`, `MIN_LENGTH`, `CHUNK_CELLS`) from
   `pandas_ta.statistics.stl_seasonal_strength` directly. The shared `_OP_CACHE` (keyed by
   window `length` alone) is the same dict object across all three modules — verified in
   `test_build_ops_is_shared_with_stl_seasonal_strength`.
3. **Input: `log(close / the window's own first close)`**, not `log(close)` directly —
   inherited unchanged from `stl_seasonal_strength`/`stl_trend_strength`, same reasoning
   (bit-identity under a power-of-two price rescale; STL's degree-1 trend LOESS absorbs an
   added constant exactly).
4. **Window = `length` closes, period fixed at 5.** Same as its siblings: `period` is a
   module constant (`PERIOD = 5`, imported transitively via `_build_ops`), not a keyword —
   the issue's own candidate naming (`kats_stl_spike_100`) bakes the period into the
   candidate's identity.
5. **`length` has a floor of 50** (`MIN_LENGTH`, imported from `stl_seasonal_strength`):
   same justification — 10 full 5-bar cycles, so the shared LOESS implementation's own
   window-size requirements are always met, and the leave-one-out arithmetic always has
   `length - 1 >= 49` elements to vary over.
6. **The flat/jitter guard, same as its siblings.** A window whose log closes do not vary
   beyond the rounding of `log(close)` (standard deviation at most 64 machine epsilons
   times `1 + max|log close|`) is NaN, because the residual would be a rounding artifact
   rather than a genuine (near-zero) reading. Imported unchanged (`NOISE_ULPS`).
7. **Bad inputs**, same rule as every other log-based port: a close that is NaN, infinite,
   zero, negative or subnormal (below 2.2e-308) is missing data, and its windows are NaN
   via IEEE 754 NaN poisoning of the shared matrix multiply and the closed-form arithmetic
   that follows.
8. **Not clipped.** The issue's formula has no clip (it is a variance of variances, so it
   is non-negative by construction, but otherwise unbounded), and Kats' own call is not
   independently confirmed to clip either; this port reports the raw value.
9. **The dictionary probe's `CONST` tag is a fixture artifact, not a defect.** Run directly
   on `docs/gen_indicator_dictionary.py`'s own literal probe construction (same `N=600`,
   `rng = np.random.default_rng(7)`, `ret = rng.normal(0, 0.012, N)`, `close = 100 *
   exp(cumsum(ret))` — reproduced, not imported, in `measure_stl_spikiness.py`'s
   `reachability` to avoid re-triggering that script's own full-package probe on import),
   `STLSPIKE_100` fires on 501 of 600 bars with 501 distinct values, range
   **[1.649e-13, 9.672e-13]** (measured below, Gate C) — real, distinct values, but all
   round to `0.000000000` at the dictionary's 9-decimal classification threshold, so the
   generator tags the column `CONST`. This is the same fixture-sensitivity already on record
   for `flat_spots`,
   `lot_zeroret_60` and `ts_reoccur_20` (`docs/IndicatorDictionary.md`'s own "Never fires on
   the probe" section) — a different root cause each time, confirmed non-constant here by
   `test_fires_and_is_not_constant` and by the spiky-frame comparison in Gate C below,
   which measures the column rising by over an order of magnitude when the window actually
   holds a dominant spike. Do NOT delete this column over the dictionary's `CONST` tag
   alone; the underlying values are not equal, only small enough that quiet synthetic noise
   rounds them together at 9 decimals.

## Gate A — correctness

**Two independent checks**, both using the brute-force leave-one-out loop
(`_brute_force_spikiness`) as the formula oracle — the literal reading of "var(nanvar of
leave-one-out resid)" — rather than the module's own closed-form shortcut:

1. **statsmodels' `STL(window, period=5).fit()`** — the exact call the screen prototype
   made — run on **every window** of two 400-bar AR(1) frames (φ = 0.2 and φ = -0.4), at
   lengths 50, 100 and 101, plus a non-multiple-of-5 length (53, exercising the general
   unequal-subseries-length interleaving) on a third frame, comparing this module's output
   against `_brute_force_spikiness(statsmodels resid)`:

   | frame | length | fits checked | max abs diff |
   |---|---|---|---|
   | AR(1) φ=0.2, 400 bars | 50 | 351 | 4.06e-24 |
   | AR(1) φ=0.2, 400 bars | 100 | 301 | 1.31e-24 |
   | AR(1) φ=0.2, 400 bars | 101 | 300 | 1.56e-24 |
   | AR(1) φ=-0.4, 400 bars | 50 | 351 | 2.13e-24 |
   | AR(1) φ=-0.4, 400 bars | 100 | 301 | 1.30e-24 |
   | AR(1) φ=-0.4, 400 bars | 101 | 300 | 1.36e-24 |
   | AR(1) φ=0.1, 200 bars | 53 (not a multiple of 5) | 148 | 1.01e-23 |

   Every difference is at the ~1e-23/1e-24 scale — far below even the magnitude of the
   values themselves (~1e-12, see Gate C), i.e. rounding, not a modelling gap.
   `test_matches_statsmodels_stl` (lengths 50/100/101) and
   `test_a_length_not_a_multiple_of_5_still_matches` (length 53) pin this; both skip where
   statsmodels is absent (CI).
2. **A hand-run fixed-point recursion** (`tests/test_stl_spikiness.py::_fixed_point_stl`,
   used by `test_matches_a_hand_run_fixed_point_recursion` and this script's
   `fixed_point_cross_check`): the same 5-pass inner loop iterated directly by calling
   `stl_seasonal_strength`'s own `_seasonal_op`/`_loess_weights` (not via `_build_ops`'s
   closed-form matrix powers), with the residual fed through the brute-force leave-one-out
   loop. Matches the module to **1.44e-24** over 201 windows of a 300-bar AR(1) frame.

Additionally, `test_closed_form_matches_brute_force_on_an_arbitrary_array` isolates the
closed-form leave-one-out shortcut itself (no STL at all) against the brute-force loop on
plain random arrays of length 5, 10, 50 and 101: exact to float rounding (<1e-10 abs diff)
at every length tried.

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

- **Synthetic, quiet AR(1) frame** (`reachability`; also `test_fires_and_is_not_constant`):
  501 of 600 bars fire (first at bar 99), all 501 values distinct, range
  [1.459e-12, 4.922e-12] — small, because this frame's residual is close to homoskedastic
  Gaussian noise with no dominant outlier (every leave-one-out variance is close to every
  other, so the variance of THOSE variances is small).
- **Synthetic, frame with injected jumps**: the same AR(1) construction with ~2% of bars
  given an extra ±8-20% one-bar move (`reachability` in the measure script). 501 of 600
  bars fire, 501 distinct, range [2.930e-13, 1.152e-10] — the maximum is **23.4x** the
  quiet frame's maximum, confirming the column responds to genuine residual spikes rather
  than reading a near-constant artifact of this particular synthetic generator (see
  Decision 9 on the dictionary probe's unrelated `CONST` tag).
- **`docs/gen_indicator_dictionary.py`'s own literal probe frame** (reproduced exactly in
  `measure_stl_spikiness.py`'s `reachability`, not imported — see Decision 9): 501 of 600
  bars fire, 501 distinct, range **[1.649e-13, 9.672e-13]** — the number Decision 9 cites
  for why the dictionary tags this column `CONST`.
- **Real data (Gate E):** 390,038 of 398,849 bars non-NaN and non-zero, no degenerate.csv
  row (`gate_e_overlap.py run`, 89 ALTPORT-1 frames, canary bit-equal on AKBNK.IS, BIENY.IS,
  AGHOL.IS, SASA.IS).

## Gate D — scale-free

- ×8 and ×64: **bit-identical**, NaN masks matching (`test_price_scale_is_bit_identical` —
  same mechanism as `stl_seasonal_strength`/`stl_trend_strength`, see Decision 3).
- ×10 and ×3.7: within **5.09e-26** (`test_price_scale_within_tolerance`) — at the limit of
  float64 precision on values this small, far inside the 1e-9 Gate D tolerance.
- `0 < fires < n`, and the column is not constant (`test_fires_and_is_not_constant`).
- Chunk-size independence: not bit-exact (BLAS's summation order can differ by a handful of
  ULPs across chunk sizes — measured max abs diff **9.77e-26**, tested below 1e-9), same
  shape as its siblings' equivalent test (`test_chunk_boundaries_do_not_change_values`).

## The flat/jitter guard and the drift case

(`guard`, above; see Decision 6.)

| series (300 bars) | fires | range |
|---|---|---|
| `100*(1+1e-2)^t` | 201 of 201 | [8.70e-65, 1.38e-64] |
| `100*(1+1e-4)^t` | 201 of 201 | [3.44e-70, 6.83e-69] |
| `100*(1+1e-7)^t` | 201 of 201 | [4.26e-70, 1.12e-68] |
| `100*(1+1e-8)^t` | 201 of 201 | [1.04e-69, 8.85e-69] |
| `100*(1+1e-10)^t` | 201 of 201 | [3.23e-84, 1.11e-68] |
| 10.0 with one-ulp jitter | 0 | — |
| exactly flat (150 bars of 10.0) | 0 | — |
| iid log returns, sd 1e-12 | 201 of 201 | — |
| iid log returns, sd 1e-9 | 201 of 201 | — |

Every drift, however shallow, still fires, at a value many orders of magnitude smaller
than the AR(1) frame's (a noiseless deterministic drift has essentially zero residual, so
every leave-one-out variance of that residual is essentially the same tiny rounding-level
number, and the variance of those is smaller still) — mathematically expected, not a guard
artefact. Only the exactly-flat and one-ulp-jitter cases are blanked. Pinned by
`test_a_smooth_drift_still_fires`, `test_flat_prices_are_nan`, `test_one_ulp_jitter_is_nan`.

## Cost

Machine-dependent (x86_64). Timings are the range over 5 runs with tracemalloc off; peak
memory from a separate run with tracemalloc on (`cost`, above):

| n | length | time | peak memory |
|---|---|---|---|
| 5,000 | 100 | 0.017–0.056 s | 4 MiB |
| 5,000 | 252 | 0.043–0.111 s | 4 MiB |
| 20,000 | 100 | 0.062–0.077 s | 4 MiB |
| 20,000 | 252 | 0.177–0.200 s | 4 MiB |
| 200,000 | 100 | 0.665–0.725 s | 7 MiB |
| 200,000 | 252 | 2.023–2.692 s | 7 MiB |

Same cost profile as its siblings: the two fixed `length x length` matrices (shared with
`stl_seasonal_strength`/`stl_trend_strength` via `_build_ops`'s cache) are built once per
`length` and applied to every window by a matrix multiply, plus the closed-form
leave-one-out arithmetic which is linear in `n * length`.

## Gate E — attribution

Run `is162-stl_spikiness-0cd2d7cf`, `gate_e_overlap.py run --module
pandas_ta.statistics.stl_spikiness --fn stl_spikiness`, 89 ALTPORT-1 frames, 398,849 bars,
329 + 358 comparators (687 total), canary bit-equal on AKBNK.IS, BIENY.IS, AGHOL.IS,
SASA.IS. Measured 2026-11-24.

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `STLSPIKE_100` | 0.6321 | `natr` | 390,038 | 0.5918 | SHIP |

0.6321 < 0.76 (SHIP line, `r3-perframe-0.90` band): ship as-is, no column struck.

## Gate F — suites

Not the whole suite (the launcher runs it). This session's subset, from the repo root:

```
python -m pytest -q tests/test_stl_spikiness.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` passes as of
this receipt session: the launcher's run recorded above into `docs/gate_e_ledger.csv`.

CPU-variant check (`python docs/measure_stl_spikiness_cpu.py`,
`NPY_DISABLE_CPU_FEATURES` set to this machine's AVX-512/AVX2/FMA3 features, standing in
for a GitHub runner without AVX-512): all 30 tests passed.

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 390 → 391 (`tests/test_altport2_ports.py`).
- README: 390 → 391 registered, 398 → 399 callable, statistics (78) → (79).
- `docs/IndicatorDictionary.md`, regenerated (`python docs/gen_indicator_dictionary.py`);
  `STLSPIKE_100` lands in the "Never fires on the probe" section tagged `CONST` — a fixture
  artifact of the probe's quiet synthetic frame, not a defect (Decision 9).
- `Category`: `stl_spikiness` placed alphabetically, between `stl_seasonal_strength` and
  `stl_trend_strength`.
