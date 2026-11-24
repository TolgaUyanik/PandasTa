# Position of the largest level shift — measured (`level_shift_idx`)

Issue #159 (KATS-LEVEL-SHIFT-IDX-100), from the owner's library catalog screen, round 5,
of 2026-10-25.

**Source:** Kats tsfeatures (Meta, MIT), `get_level_shift_features` (issue #159's text;
Kats' own line numbers are not independently re-confirmed in this session, no network
access to the Kats source): slide a `window_size`-bar mean across the series, take the
absolute differences between consecutive means, and report `argmax` of those differences
(this column) alongside their `max` (the sibling column `kats_level_shift_size_100`,
issue #162, not this port). The screen prototype
(`docs/issues/screen/ind_screen_r5.py`, candidate `kats_level_shift_idx_100`, local to the
owner's machine) uses `window_size=20` (Kats' default), a 100-bar outer window of log
close, and rounds the diffs to 12 decimals before `argmax` — all three choices are kept
in this port (the window size and rounding as fixed module constants; the outer window
as the `length` keyword).

**Status:**
- Gates A, B and D are measured below. This repo's own test subset (this port's module
  plus the wiring/count/ledger guard modules) is green except the one expected
  ledger-owed failure (see Gate F).
- **Gate E: pending, run by issue-solver after this session.**

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/level_shift_idx.py` | statistics | `LEVELSHIFTIDX_100` | `[0, 1]` or NaN |

Tests: `tests/test_level_shift_idx.py` (31 tests).

Numbers: `python docs/measure_level_shift_idx.py`, run from the repo root. Environment:
Python 3.11.2, pandas 2.3.3, numpy 1.26.4. Measured 2026-11-24.

## Decisions

1. **Input and window.** The input is `log(close)` directly (not returns, unlike
   `stability`/`lumpiness`), and the outer window is `length` closes, so bar T reads
   closes T − length + 1 .. T. This is the convention `stl_seasonal_strength` (#155) uses
   for its own close-level (not return-level) port.
   - Kats applies the function to a whole series. The issue says the 100-bar outer
     window and log close as the input are the prototype's choices; its code
     (`ind_screen_r5.py`) is local to the owner's machine.
2. **`window_size` (20) is a fixed module constant**, not a keyword — the prototype's
   candidate exposes only the outer window (`kats_level_shift_idx_100`), the same
   convention `stability`/`lumpiness` use for their own fixed `window_size=20` tiling.
3. **The 12-decimal rounding before `argmax` is kept from the prototype, not dropped.**
   It is not cosmetic: under a price rescale, `log(close * k)` does not equal
   `log(close) + log(k)` bit-for-bit (finite-precision `np.log` introduces its own
   rounding per element), so two diffs that are mathematically tied (e.g. two windows of
   tick-rounded prices whose 20-bar means step by the same amount) can pick a different
   `argmax` at a different price scale without it. Rounding absorbs that ~1e-15-scale
   noise while leaving genuine level shifts (orders of magnitude larger in real log-price
   data) untouched — this is what makes Gate D's ×8/×64 rescale bit-identical (measured
   below), not merely close.
4. **No rounding-noise guard, unlike `stability`/`lumpiness`.** Those ports z-score
   returns, so a flat or near-flat window's rounding noise gets divided by a
   near-zero standard deviation and blown up to a spurious large value — hence their
   `NOISE_ULPS` guard. This column never divides by a window statistic: a flat window's
   diffs are all exactly 0 (not noise — an exact tie), and `argmax`'s first-tie
   convention deterministically reads `LEVELSHIFTIDX = 0.0`, a real answer. Measured: a
   flat 150-bar series and a one-ulp-jittered flat series both read `0.0` on every fired
   bar (`tie_robustness`, below) — not NaN.
5. **`length` has a floor of `WINDOW_SIZE + 2` (22).** The idx scale's denominator is
   `length − window_size − 1`; below 22 that is 0 (one diff, nothing to pick an index
   among) and would divide by zero. A smaller or missing value falls back to 100, the
   repo's convention (`kpss`, `arch_lm`, `lumpiness`, `stability`).
6. **Bad inputs.** A close that is not finite and positive is missing data. A window
   holding any bad close is NaN — the calling loop masks out any window containing one
   (`ok = ~np.isnan(chunk).any(axis=1)`) before it ever reaches the mean/diff/argmax
   computation, rather than relying on the NaN to propagate through the reduction: it
   would not, since `np.argmax` returns the INDEX of a NaN entry (a plain int), not a
   NaN, so an unmasked bad window would silently produce a bogus non-NaN idx instead of
   being blanked.
7. **A generic future-perturbation causality probe has low power here, and the test
   module uses a different one instead (see Gate B).** `argmax` over a whole window can
   keep returning the SAME (older) index after the window's tail changes, if a larger,
   unrelated shift elsewhere in the window still dominates — this is a structural
   property of an argmax feature, not a bug. The deliberate single-level-shift
   construction in `tests/test_level_shift_idx.py::_step_series` removes that confound.

## Gate A — correctness

Kats' `argmax`-of-diffs formula, transcribed independently as a plain Python loop (not
the module's cumsum vectorisation — `tests/test_level_shift_idx.py::_oracle_idx`), at
every bar of four 1,500-bar frames (GARCH, iid normal, a deliberate level shift, and
tick-rounded data near 5.00 on a 0.01 tick), at lengths 22, 50 and 100:

| frame | length | bars compared | NaN masks equal | max abs diff |
|---|---|---|---|---|
| GARCH(0.10, 0.85) | 22 / 50 / 100 | 1,479 / 1,451 / 1,401 | yes / yes / yes | 0.0 |
| iid normal | 22 / 50 / 100 | 1,479 / 1,451 / 1,401 | yes / yes / yes | 0.0 |
| deliberate step at bar 750 (×1.5) | 22 / 50 / 100 | 1,479 / 1,451 / 1,401 | yes / yes / yes | 0.0 |
| tick-rounded near 5.00 on a 0.01 tick | 22 / 50 / 100 | 1,479 / 1,451 / 1,401 | yes / yes / yes | 0.0 |

Bit-identical to the independent oracle on all 12 frame × length cases.

A closed form is pinned too (`test_closed_form_single_level_shift`): a persistent step at
bar 50 inside a 100-bar window produces a tied plateau of exactly `WINDOW_SIZE` (20)
equal diffs (the sliding mean ramping linearly as the step enters it), and `argmax`'s
first-tie convention picks the plateau's first index deterministically —
`LEVELSHIFTIDX_100 = 30 / 79` exactly, confirmed on this machine.

### Semantics: idx grows with how recent the step is

Same closed-form construction, the step's relative position `p` inside a 100-bar window
varied (`python docs/measure_level_shift_idx.py`):

| step at relative position | `LEVELSHIFTIDX_100` |
|---|---|
| 20 / 99 | 0.0000 |
| 35 / 99 | 0.1899 |
| 50 / 99 | 0.3797 |
| 65 / 99 | 0.5696 |
| 79 / 99 | 0.7468 |

Monotonically increasing — confirms the issue's "scaled to [0, 1] (1 = latest)" reading.

## Gate B — causality

- **The real module never reads the future.** Five deliberate single-level-shift
  series (shift at bar 105, 150, 300, 450 and 590 of a 600-bar frame -- near the
  frame's start and end as well as mid-frame): bars before the shift are bit-identical
  whether or not the shift ever happens, at all five positions
  (`test_real_module_never_reads_the_future`).
- **Mutant.** The chunk write offset `lo = length - 1 + start` is moved to
  `length - 2 + start`, one bar earlier. Live (differs from the real module on a
  600-bar frame) at all five shift positions; and specifically, the bar just before the
  shift (`shift_at - 1`) changes value under the mutant when the shift moves from
  "not yet in this bar's window" to "already leaked in" — while the real module's same
  bar stays identical (`test_mutant_is_caught`).
- **A bad close moves exactly its windows.** A single NaN at bar 300 (window width 100)
  nulls exactly bars 300..399; every other bar is bit-identical
  (`test_a_bad_tick_moves_exactly_its_windows`).

A generic "replace the tail with an unrelated random path" probe (the shape
`stability`/`lumpiness` use) was tried first and found to have near-zero power here: on
a 600-bar GARCH frame, `argmax` is often dominated by one much larger shift elsewhere in
the window, so perturbing the tail from offset `j` on frequently leaves the reported
`argmax` unchanged even under the mutant (see Decision 7). The deliberate single-shift
construction above removes that confound.

## Gate C — reachability

- **Synthetic:** 501 of 600 bars fire (99-bar warm-up) on a GARCH frame, 80 distinct
  values, range `[0.0000, 1.0000]` (`python docs/measure_level_shift_idx.py`,
  `reachability`).
- **Real data:** not yet measured (Gate E owed; run by the launcher).
- What blanks a bar: a bad close blanks the `length` bars whose window holds it
  (Decision 6).

## Gate D — scale-free

- ×8 and ×64, and the non-power-of-two ×10 and ×3.7: **all four bit-identical**, max abs
  diff `0.0`, NaN masks matching (`test_price_scale_is_bit_identical`,
  `test_price_scale_within_tolerance`; confirmed again by
  `python docs/measure_level_shift_idx.py`). Unlike a continuous-valued column, this one
  is not merely "within tolerance" under a non-power-of-two rescale: the output is an
  integer `argmax` index divided by a fixed integer denominator, so as long as the
  12-decimal rounding keeps the same index winning (Decision 3), the result is exactly
  identical, not just close — measured true on every frame tried, including a
  non-power-of-two rescale.
- `0 < fires < n`, and the column is not constant: 501 of 600 fire, 80 distinct values
  (above).

## Cost

Machine-dependent (x86_64). Timings are the range over 5 runs with tracemalloc off; peak
memory from a separate run with tracemalloc on (`python docs/measure_level_shift_idx.py`):

| n | length | time | peak memory |
|---|---|---|---|
| 5,000 | 100 | 0.008–0.011 s | 9 MiB |
| 5,000 | 252 | 0.019–0.026 s | 10 MiB |
| 20,000 | 100 | 0.030–0.032 s | 9 MiB |
| 20,000 | 252 | 0.092–0.099 s | 10 MiB |
| 200,000 | 100 | 0.366–0.382 s | 13 MiB |
| 200,000 | 252 | 0.779–0.818 s | 14 MiB |

Machine load moves these numbers; they are an order of magnitude, not a guarantee.

## Gate E — attribution

**Pending, run by issue-solver after this session.** This session does not run Gate E
(no access to `../Backtesting`); a later receipt session records the measured numbers
and the `docs/gate_e_ledger.csv` row here.

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_level_shift_idx.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

Result: 1 failed, 1489 passed, 7 skipped. The 1 failure is
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` on the owed
`level_shift_idx` row — expected per the issue-solver rules until the launcher's Gate E
run and a receipt session record it, not a defect.

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for a GitHub
runner without AVX-512 — this machine's own dispatchable set per
`numpy.core._multiarray_umath.__cpu_features__`): `python docs/measure_level_shift_idx_cpu.py`
— 31 passed (just `tests/test_level_shift_idx.py`; the ledger/readme/wiring modules above
are not CPU-sensitive and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 384 → 385 (`tests/test_altport2_ports.py`).
- README: 384 → 385 registered, 392 → 393 callable, statistics (73) → (74).
- `docs/MLCompanionContract.md`: 729 → 730 tagged and 363 → 364 `SF` (newest first in the
  chain).
- `docs/IndicatorDictionary.md`, regenerated with this environment's package. Its diff is
  the `level_shift_idx` row (`LEVELSHIFTIDX_100` SF, 99 warm-up), the three header
  counts, the statistics section count, and the SF shortlist, and nothing else.
- `Category`: `level_shift_idx` is placed alphabetically, after `lean_tdd_20` and before
  `lot_zeroret_60`.

All counts are as of this branch, based on `dev` at `6e1e2e8`.
