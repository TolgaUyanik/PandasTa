# Size of the largest level shift — measured (`level_shift_size`)

Issue #163 (KATS-LEVEL-SHIFT-SIZE-100), from the owner's library catalog screen, round 5,
of 2026-10-25.

**Source:** Kats tsfeatures (Meta, MIT), `get_level_shift_features` (issue #163's text;
Kats' own line numbers are not independently re-confirmed in this session, no network
access to the Kats source): slide a `window_size`-bar mean across the series, take the
absolute differences between consecutive means, and report the `max` of those differences
(this column) alongside their `argmax` (the sibling column `level_shift_idx`, issue #159,
already shipped). The screen prototype (`docs/issues/screen/ind_screen_r5.py`, candidate
`kats_level_shift_size_100`, local to the owner's machine) uses `window_size=20` (Kats'
default) and a 100-bar outer window of log close — both choices are kept in this port (the
window size as a fixed module constant imported from `level_shift_idx`; the outer window
as the `length` keyword).

**Status:** shipped. Gates A–F all measured below.

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/level_shift_size.py` | statistics | `LEVELSHIFTSIZE_100` | `>= 0` or NaN |

Tests: `tests/test_level_shift_size.py` (30 tests).

Numbers: `python docs/measure_level_shift_size.py`, run from the repo root. Environment:
Python 3.11.2, pandas 2.3.3, numpy 1.26.4. Measured 2026-11-25.

## Decisions

1. **Input and window.** The input is `log(close)`, and the outer window is `length`
   closes, so bar T reads closes T − length + 1 .. T — the same convention its already-
   shipped companion `level_shift_idx` (#159) uses.
   - Kats applies the function to a whole series. The issue says the 100-bar outer
     window and log close as the input are the prototype's choices; its code
     (`ind_screen_r5.py`) is local to the owner's machine.
2. **`window_size` (20) is imported from `level_shift_idx`, not redefined.** Both
   companions share the one Kats default; a second definition of the same constant would
   be a drift risk for no benefit (the fork's own `stl_spikiness` reuses
   `stl_seasonal_strength`'s constants/operators for the same reason).
3. **The window is fed `log(close / the window's own first close)`, not `log(close)`
   directly — unlike `level_shift_idx`.** That column's output is a scale-invariant
   integer INDEX, so it stabilises against the ~1e-15-scale rounding noise `np.log`
   introduces under a price rescale by rounding the diffs to 12 decimals before
   `argmax`: the index stays the same even though the underlying floats differ slightly
   at different price scales. This column's output is a continuous VALUE — the diff
   itself — so rounding it the same way would blunt genuine small shifts, not just
   absorb noise. Instead the ratio-to-first-bar device `stl_spikiness` /
   `stl_seasonal_strength` use achieves bit-for-bit invariance directly: under a
   power-of-two rescale, both the numerator and denominator of `raw / raw[:, :1]` are
   multiplied by the same exactly-representable factor, so the ratio's correctly-rounded
   result does not move, and neither does `log` of it or anything computed from it.
   Mathematically the ratio and plain `log(close)` are the same value up to an additive
   constant per window, which cancels in every diff either way — the difference is only
   in which one is bit-exact under a rescale.
4. **No rounding-noise guard, unlike `stability`/`lumpiness`.** This column never divides
   by a window statistic: a flat window's diffs are all exactly 0 (an exact tie, not
   noise), so `max` of them reads exactly `0.0`, a real answer, not a guard case.
   Measured: a flat 150-bar series fires `0.0` on every bar; a one-ulp-jittered flat
   series fires a value `< 1e-10` (not a guard-worthy magnitude) — see `tie_robustness`
   below.
5. **`length` has a floor of `WINDOW_SIZE + 1` (21), one less than `level_shift_idx`'s 22.**
   This column's own constraint is just "at least one diff to take a `max` over" (two
   means); it does not additionally divide by a diff count minus one the way the index
   column does. A smaller or missing value falls back to 100, the repo's convention
   (`kpss`, `arch_lm`, `lumpiness`, `stability`, `level_shift_idx`).
6. **Bad inputs.** A close that is not finite and positive is missing data. A window
   holding any bad close is NaN — the calling loop masks out any window containing one
   before it ever reaches the mean/diff/max computation.
7. **Causality test reuses the deliberate single-level-shift construction**
   `level_shift_idx`'s test module introduced (`_step_series`), not a generic
   "swap the tail for an unrelated path" probe: a `max`-of-diffs feature can be
   dominated by an older, larger shift elsewhere in the window, giving the same low-power
   problem its sibling column documents (Decision 7 in `docs/LevelShiftIdxMeasured.md`).

## Gate A — correctness

Kats' `max`-of-diffs formula, transcribed independently as a plain Python loop over raw
`log(close)` (not the module's cumsum-on-ratio vectorisation —
`tests/test_level_shift_size.py::_oracle`), at every bar of four 1,500-bar frames (GARCH,
iid normal, a deliberate level shift, and tick-rounded data near 5.00 on a 0.01 tick), at
lengths 21, 50 and 100:

| frame | length | bars compared | NaN masks equal | max abs diff |
|---|---|---|---|---|
| GARCH(0.10, 0.85) | 21 / 50 / 100 | 1,480 / 1,451 / 1,401 | yes / yes / yes | 2.08e-15 |
| iid normal | 21 / 50 / 100 | 1,480 / 1,451 / 1,401 | yes / yes / yes | 2.30e-15 |
| deliberate step at bar 750 (×1.5) | 21 / 50 / 100 | 1,480 / 1,451 / 1,401 | yes / yes / yes | 2.45e-15 |
| tick-rounded near 5.00 on a 0.01 tick | 21 / 50 / 100 | 1,480 / 1,451 / 1,401 | yes / yes / yes | 6.73e-16 |

Agrees with the independent oracle to within ~1e-15 on all 12 frame × length cases — the
residual is exactly the rounding noise Decision 3 describes (the oracle uses plain
`log(close)`, the module uses the ratio-to-first-bar form); `tests/test_level_shift_size.py`
pins this at `rtol=1e-9`.

A closed form is pinned too (`test_closed_form_single_level_shift`): a persistent step of
log-size `V` at bar 50 inside a 100-bar window produces a tied plateau of exactly
`WINDOW_SIZE` (20) equal diffs of `V/20` each (the sliding mean ramping linearly as the
step enters it), and the `max` is that same value — `LEVELSHIFTSIZE_100 = V/20` exactly,
confirmed on this machine for four values of `V` (0.02, 0.05, 0.10, 0.20; `semantics`,
below) — matching `V/20` in every case.

## Gate B — causality

- **The real module never reads the future.** Five deliberate single-level-shift
  series (shift at bar 105, 150, 300, 450 and 590 of a 600-bar frame): bars before the
  shift are bit-identical whether or not the shift ever happens, at all five positions
  (`test_real_module_never_reads_the_future`).
- **Mutant.** The chunk write offset `lo = length - 1 + start` is moved to
  `length - 2 + start`, one bar earlier. Live (differs from the real module on a
  600-bar frame) at all five shift positions; the bar just before the shift
  (`shift_at - 1`) changes value under the mutant while the real module's same bar stays
  identical (`test_mutant_is_caught`).
- **A bad close moves exactly its windows.** A single NaN at bar 300 (window width 100)
  nulls exactly bars 300..399; every other bar is bit-identical
  (`test_a_bad_tick_moves_exactly_its_windows`).

Reuses `level_shift_idx`'s deliberate single-shift construction rather than a generic
tail-perturbation probe, for the same low-power reason (Decision 7).

## Gate C — reachability

- **Synthetic:** 501 of 600 bars fire (99-bar warm-up) on a GARCH frame, 110 distinct
  values, range `[0.006342, 0.019263]` (`python docs/measure_level_shift_size.py`,
  `reachability`). All fired values are `>= 0`, as the formula guarantees
  (`test_fires_and_is_not_constant`).
- Real-data reachability: pending the Gate E run (below).
- What blanks a bar: a bad close blanks the `length` bars whose window holds it
  (Decision 6).

## Gate D — scale-free

- ×8 and ×64: bit-identical, max abs diff `0.0`, NaN masks matching
  (`test_price_scale_is_bit_identical`; confirmed again by
  `python docs/measure_level_shift_size.py`, `scale_tolerance` reports the non-power-of-two
  cases).
- ×10 and ×3.7 (not powers of two, so not bit-exact by construction — Decision 3):
  within tolerance, max abs diff 1.11e-16 / 8.33e-17
  (`test_price_scale_within_tolerance`; `scale_tolerance`, below the test's 1e-9 bound by
  several orders of magnitude).
- `0 < fires < n`, and the column is not constant: 501 of 600 fire, 110 distinct values
  (above).

## Cost

Machine-dependent (x86_64). Timings are the range over 5 runs with tracemalloc off; peak
memory from a separate run with tracemalloc on (`python docs/measure_level_shift_size.py`):

| n | length | time | peak memory |
|---|---|---|---|
| 5,000 | 100 | 0.009–0.012 s | 13 MiB |
| 5,000 | 252 | 0.018–0.019 s | 14 MiB |
| 20,000 | 100 | 0.029–0.032 s | 14 MiB |
| 20,000 | 252 | 0.070–0.078 s | 14 MiB |
| 200,000 | 100 | 0.282–0.286 s | 16 MiB |
| 200,000 | 252 | 0.678–0.685 s | 17 MiB |

Machine load moves these numbers; they are an order of magnitude, not a guarantee.

## Gate E — attribution

Run by issue-solver (`gate_e_overlap.py run --module pandas_ta.statistics.level_shift_size`),
89 ALTPORT-1 frames, n = 390,038, canary bit-equal, recorded in `docs/gate_e_ledger.csv`
(measured 2026-11-25):

| column | max \|rho\| | against | n | per-frame max median \|rho\| | verdict |
|---|---|---|---|---|---|
| `LEVELSHIFTSIZE_100` | 0.6322 | `natr` | 390,038 | 0.5951 | SHIP |

Below the 0.76 ship line (CLAUDE.md Gate E bands). Matches the prototype's own screen
measurement in issue #163 (0.6322 vs `natr`). Column ships as-is.

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_level_shift_size.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

1,544 passed, 7 skipped, 1 failed (`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
— expected and documented in this issue's rules: the ledger row is recorded in a later
receipt session, after the launcher's Gate E run).

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for a GitHub
runner without AVX-512 — the four features issue-solver's rules name, not this machine's
full dispatchable set): `python docs/measure_level_shift_size_cpu.py` — 30 passed (just
`tests/test_level_shift_size.py`; the ledger/readme/wiring modules above are not
CPU-sensitive and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 391 → 392 (`tests/test_altport2_ports.py`).
- README: 391 → 392 registered, 399 → 400 callable, statistics (79) → (80).
- `docs/MLCompanionContract.md`: 736 → 737 tagged and 368 → 369 `SF` (newest first in the
  chain).
- `docs/IndicatorDictionary.md`, regenerated with this environment's package. Its diff is
  the `level_shift_size` row (`LEVELSHIFTSIZE_100` SF, 99 warm-up), the three header
  counts, the statistics section count, and the SF shortlist, and nothing else.
- `Category`: `level_shift_size` is placed alphabetically, after `level_shift_idx` and
  before `lot_zeroret_60`.

All counts are as of this branch, based on `dev` at `a395bca`.
