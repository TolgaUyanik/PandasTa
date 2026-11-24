# Flat spots of close — measured (`flat_spots`)

Issue #161 (KATS-FLAT-SPOTS-100), from the owner's library catalog screen, round 5, of
2026-10-25.

**Source:** Kats tsfeatures (Meta, MIT), `get_flat_spots` (issue #161's text; Kats' own
line numbers are not independently re-confirmed in this session, no network access to the
Kats source): "max groupby run length per n/10 chunk" -- split the series into
`len(x) // 10` equal time chunks and report the longest run of identical consecutive
values seen in any chunk, after Hyndman's tsfeatures `flat_spots` (R `tsfeatures`, which
cuts the whole series into 10 equal-WIDTH value bins rather than 10 equal-size time
chunks). The port reproduces the prototype's own time-chunked reading of the Kats
description, transcribed from `docs/issues/screen/ind_screen_r5.py` lines 107-116
(local to the owner's machine):

```python
def _flat_spots(W):
    k = W.shape[1] // 10
    C = W[:, :10 * k].reshape(len(W), 10, k)
    eq = C[:, :, 1:] == C[:, :, :-1]
    run = zeros; best = zeros
    for j in range(eq.shape[2]):
        run = where(eq[:, :, j], run + 1, 0)
        best = maximum(best, run)
    return best.max(1) + 1
```

**Status:**
- Gates A, B, C and D are cleared below.
- Gate E: measured 2026-11-24, SHIP (see "Gate E").
- Gate F: this repo's own suite (the module's tests plus the wiring/ledger/dictionary
  guards) is green, including under the CI CPU-feature set (see "Gate F"). Whole suites:
  run by issue-solver in clean worktrees (see the PR body).

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/flat_spots.py` | statistics | `FLATSPOTS_100` | whole number in `[1, 10]`, or NaN |

Tests: `tests/test_flat_spots.py` (24 tests).

Numbers: `python docs/measure_flat_spots.py`, run from the repo root. Environment:
Python 3.11.2, pandas 2.3.3, numpy 1.26.4. Measured 2026-11-24.

## Decisions

1. **Input and window.** The input is close itself, with no returns and no log -- the
   issue's own "scale-free form: on close". The window is `length` closes, so bar T reads
   closes T - length + 1 .. T. This is a level feature, the same convention as `kpss` and
   `level_shift_idx`, not a returns feature like `lumpiness`/`stability`.
   - Kats applies the function to a whole series; the issue says the 100-bar window is the
     prototype's choice. Its code (`ind_screen_r5.py`) is local to the owner's machine.
2. **The chunking is Kats' own description, not Hyndman's R `cut`.** The prototype splits
   the window into 10 equal-size TIME chunks (`CHUNKS = 10`, chunk size `length // 10`),
   not 10 equal-WIDTH VALUE bins over the window's range (the R `tsfeatures::flat_spots`
   reading). The issue's own ref string for this candidate, "max groupby run length per
   n/10 chunk", names the time-chunked form, and the prototype's code implements exactly
   that -- so this module ports the prototype's reading, not R's.
3. **The run is exact equality, not a rounding tolerance.** Two closes tie only if they
   are bit-identical floats. This is what makes the column discrete (an integer count)
   and what gives it its exceptionally strong scale-freedom (Decision 4).
4. **Scale-free, more strongly than a ratio-based column.** `==` is a deterministic
   function of its two operands' bits: if `a == b` before a uniform rescale by any finite
   `k`, then `a * k == b * k` after it (not only when `k` is a power of two) -- so the
   column is bit-identical under ANY uniform price rescale, as long as neither operand
   under/overflows. Measured: x8 and x64 are bit-identical (boolean `==`,
   `test_price_scale_is_bit_identical`); x10 and x3.7 are exactly 0.0 max abs diff, not
   merely within a tolerance (`measure_flat_spots.py`'s `scale_tolerance`) -- stronger
   than the ×10/×3.7 TOLERANCE a ratio-based sibling (`stability`, `kpss`) needs.
5. **Chunks never span a chunk boundary, and never span the warm-up.** A run cannot
   straddle two chunks (the prototype's `eq` is computed only within each `(length //
   10)`-wide block), so a tie between the LAST bar of one chunk and the FIRST bar of the
   next is invisible to the column -- measured directly (`test_a_tie_moves_exactly_its_
   windows`): forcing one tie in an otherwise strictly increasing 600-bar series lifts 90
   of the 99 windows that hold it, and the other 9 (one in ten, by construction) sit
   exactly on a chunk boundary and are untouched.
6. **Non-finite closes are bad data; zero and negative closes are not.** A NaN or
   infinite close is masked to NaN before the window loop, since `NaN == NaN` is `False`
   (so a NaN would read as "a bar that ties with nothing", not propagate the way
   arithmetic NaNs do) and `inf == inf` is `True` (so two missing bars would read as a
   false tie). Unlike every return-based kats_* sibling, this column never divides, so
   zero and negative closes are ordinary values for equality, not missing data
   (`test_zero_and_negative_closes_are_valid`).
7. **`length` floor of `2 * CHUNKS` (20).** A 1-bar chunk (`length < 20`) has no adjacent
   pair to compare, so every window would read the constant 1 and the column would fail
   Gate D's "not constant" requirement. A smaller or missing value falls back to 100, the
   repo's convention (`kpss`, `stability`, `level_shift_idx`).
8. **`length` not a multiple of 10 drops the window's newest bars, not its oldest.**
   `W[:, :10k]` keeps the window's first `10k` columns (oldest-to-newest order), so the
   dropped `length % 10` bars are the ones closest to bar T -- measured directly
   (`test_length_not_a_multiple_of_ten`, length=25: the newest 5 of the window's 25 bars
   are never checked for a flat run). The default length=100 has no remainder.

## Gate A — correctness

The prototype's `_flat_spots`, transcribed verbatim as a per-window oracle
(`tests/test_flat_spots.py::_kats`), compared bit-identically to the module at every bar,
on three synthetic frames (one continuous-float, two tick-rounded) at lengths 20/30/100
(`measure_flat_spots.py`'s `gate_a`):

| frame | length | bit-identical to oracle | NaN masks equal | bars compared |
|---|---|---|---|---|
| continuous, 300 bars | 20 / 30 / 100 | True / True / True | True / True / True | 281 / 271 / 201 |
| ticky (seed 2), 300 bars | 20 / 30 / 100 | True / True / True | True / True / True | 281 / 271 / 201 |
| ticky (seed 3), 300 bars | 20 / 30 / 100 | True / True / True | True / True / True | 281 / 271 / 201 |

- The port is bit-identical to the oracle on all 9 frame × length cases, every bar.
- The test oracle (`tests/test_flat_spots.py::test_matches_the_prototype_oracle`) checks
  the same thing per-test, at lengths 20/30/100 on a ticky frame, and
  `test_matches_the_prototype_oracle_various_frames` repeats it on both a continuous and a
  ticky frame at length 20.
- Two closed forms are pinned: a 100-bar window, strictly increasing except one 10-bar
  chunk forced to a single repeated value, reads exactly 10 (the chunk size, the maximum
  possible at length 100); the same window with no forced repeat reads exactly 1.

## Gate B — causality

- **Future perturbation:** 16 offsets, each forcing a tie between bars `j - 1` and `j` in
  an otherwise strictly increasing series (chosen because a single changed VALUE rarely
  moves this discrete, run-length statistic -- most single bars are not part of the
  longest run -- so the probe forces a tie rather than merely changing a value). The real
  module shows 0 of 16 leaks (`test_real_module_never_reads_the_future`): a window ending
  before `j` never reads bar `j` at all, so it cannot see the forced tie.
- **Mutant:** the chunk write offset `lo = length - 1 + start` is moved to `lo = length -
  2 + start`, one bar earlier. The mutant is live (shifts the warm-up boundary by one bar,
  so `.equals()` already differs on an untouched, tie-free series) and is caught at 16 of
  16 offsets (`test_mutant_is_caught`): writing a window's result one bar too early means
  the bar it is written to displays a value computed from one bar INTO ITS OWN FUTURE.

## Gate C — reachability

- **Synthetic:** 501 of 600 bars fire (99-bar warm-up, `length - 1`), 4 distinct values,
  range [2, 5], on a ticky 0.01-tick frame near price 5
  (`test_fires_and_is_not_constant`, `measure_flat_spots.py`'s `reachability`).
- **Real data** (Gate E run `is161-flat_spots-2695ebb4`, 89 ALTPORT-1 frames,
  398,849 pooled bars): 390,038 non-NaN, the same 390,038 non-zero
  (`overlap_max.csv` `non_nan`/`non_zero`); `FLATSPOTS_100` is not in
  `degenerate.csv` (its one row is the comparator `squeeze_SQZ_NO`), so the
  column is non-constant on real data -- the `CONST` dictionary tag is the
  probe fixture, as §Gate C ⚠ below argues.
- What blanks a bar: a non-finite close (NaN or ±inf) blanks the `length` bars whose
  window holds it (`test_a_non_finite_close_blanks_its_windows`).
- ⚠ **The generated `docs/IndicatorDictionary.md` tags `FLATSPOTS_100` as `CONST`.** Its
  probe is one 600-bar continuous-float synthetic frame where no close ever repeats, so
  the column reads the constant 1 there -- the same situation `ts_reoccur_20` and
  `lot_zeroret_60` are already in (`docs/TsReoccur20Measured.md` §C1), for the identical
  reason (a tie needs two equal closes, which that one frame never has). The `semantics()`
  table below measures the SAME continuous generator this way (median 1.00, 1 distinct
  value) and a ticky generator the opposite way (median 4.00, 6 distinct values) --
  confirming the CONST tag is the probe frame's fixture, not a defect in the column.
  `docs/MLCompanionContract.md`'s counts move accordingly (734 -> 735 tagged, 43 -> 44
  `CONST`, not `SF`).

## Gate D — scale-free

- ×8 and ×64: bit-identical with matching NaN masks (boolean `==`,
  `test_price_scale_is_bit_identical`).
- ×10 and ×3.7: measured max abs diff exactly 0.0, not merely within a tolerance --
  `==` is a deterministic function of its operands' bits, so it survives ANY uniform
  rescale exactly (Decision 4; `test_price_scale_within_tolerance`,
  `measure_flat_spots.py`'s `scale_tolerance`).
- `0 < fires < n` and not constant: 501 of 600 fire, more than 1 distinct value
  (`test_fires_and_is_not_constant`).

## Semantics — what FLATSPOTS_100 reads

10 paths × 600 bars per row, 500 values per path (`measure_flat_spots.py`'s `semantics`):

| closes | pooled median | pooled mean | p90 | distinct values |
|---|---|---|---|---|
| continuous (random walk, continuous floats) | 1.00 | 1.000 | 1.00 | 1 |
| ticky (0.01 tick near price 5) | 4.00 | 3.831 | 5.00 | 6 |

- **It reads the constant 1 on continuously-varying prices**, where no two closes are
  ever bit-identical -- the column has nothing to measure there, by construction (the
  same fact the `CONST` dictionary tag reports, Gate C above).
- **It rises sharply on a tick-rounded price**, where the rounding step is large relative
  to the move size, so several consecutive bars commonly print the identical close:
  median 4.00 versus the continuous frame's 1.00. This is the column's whole point --
  how much the printed price is quantised relative to its own movement, inside a 100-bar
  window.
- Medians are RNG-stream dependent (NEP 19) for the ticky frame's exact digits, but the
  qualitative ordering (ticky > continuous) follows directly from the tick size, not from
  the RNG seed.

## Cost

Machine-dependent (x86_64). Timings come from 5 runs per invocation, tracemalloc off;
peak memory from a separate run with tracemalloc on:

| n | length | time | peak memory |
|---|---|---|---|
| 5,000 | 100 | 0.002–0.004 s | 3 MiB |
| 5,000 | 252 | 0.004 s | 3 MiB |
| 20,000 | 100 | 0.009 s | 3 MiB |
| 20,000 | 252 | 0.017 s | 3 MiB |
| 200,000 | 100 | 0.085–0.087 s | 6 MiB |
| 200,000 | 252 | 0.163–0.167 s | 6 MiB |

Machine load moves these numbers; they are an order of magnitude, not a guarantee.

## Gate E — attribution

Run by issue-solver, Backtesting `gate_e_overlap.py run --module pandas_ta.statistics.flat_spots`,
89 ALTPORT-1 BIST frames, 398,849 pooled bars, 687 comparators (329 `compute_all` + 358
`ml_features` manifest), canary bit-equal on AKBNK.IS/BIENY.IS/AGHOL.IS/SASA.IS. Outputs:
`overlap_max.csv` / `meta.json`, run `is161-flat_spots-2695ebb4`.

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `FLATSPOTS_100` | 0.6192 | `ZIGZAG` | 32,802 | 0.6074 | SHIP |

- 0.6192 < 0.76 (SHIP line) and the per-frame max median 0.6074 < 0.90: not a restatement
  of any single comparator on any frame. Ledger row recorded 2026-11-24
  (`docs/gate_e_ledger.csv`).

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole suite):

```
python -m pytest -q tests/test_flat_spots.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

Result (at the port commit, before the ledger row is recorded): 1 failed, 1522 passed, 7
skipped. The 1 failure is
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` on the owed
`flat_spots` row -- expected per the issue-solver rules until the launcher's Gate E run
and a receipt session record it, not a defect.

Re-run, this receipt session, after the ledger row was recorded (same command as
above): 1530 passed, 7 skipped, 0 failed -- the one pre-ledger failure
(`test_every_indicator_that_needs_a_row_has_one`) now passes with the recorded
row. Whole-suite comparison is the launcher's (`tests.md`), not re-run here.

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for a GitHub
runner without AVX-512 -- this machine's own dispatchable set per
`numpy.core._multiarray_umath.__cpu_features__`): `python docs/measure_flat_spots_cpu.py`
-- 24 passed (just `tests/test_flat_spots.py`; the ledger/readme/wiring modules above are
not CPU-sensitive and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 389 → 390. Statistics is not in `CATEGORY_BUCKETS`.
- README: 389 → 390 registered, 397 → 398 callable, statistics (77) → (78).
- `docs/MLCompanionContract.md`: 734 → 735 tagged and 43 → 44 `CONST` (newest first in the
  chain).
- `docs/IndicatorDictionary.md`, regenerated with this environment's package. Its diff is
  the `flat_spots` row (`FLATSPOTS_100` CONST, 99 warm-up), one *Never fires on the probe*
  row (the same generic fallback text `ts_reoccur_20`/`lot_zeroret_60` carry, not a
  registration problem -- `flat_spots` is in `Category["statistics"]` and on `df.ta`,
  pinned by `test_name_registration_and_accessor`), the three header counts, and the
  statistics section count, and nothing else.
- `Category`: `flat_spots` is placed alphabetically, after `firstzero_ac` and before
  `g191_026`.

All counts are as of this branch, based on `dev` at `f0b3501`.
