# Effort vs result: relative volume over relative range (20) — measured (`nm_effort_result_20`)

Issue #185 (NM-EFFORT-RESULT-20), from the 2026-10-25 follow-up of round 7
(`docs/issues/screen/candidates_r7.csv`). Named in TWO Reddit threads only (tier
4): Wyckoff's "effort vs result" (volume vs price response, `rd:Daytrading:1k9oyhh`)
and a separate "Volume Range Events" thread (volume change vs candle range
change, round 6). Neither thread states a formula; the issue's own "What"
line discloses this explicitly ("this prototype's formalisation: no
published formula was found"), so there is no second, independent source
formula to derive this port from — unlike `nm_mmi_250` (issue #184), Gate A
here is a faithful translation of the issue's own stated expression, not a
derivation checked against a separate citation. Existence, not evidence:
nothing here tests Wyckoff's claim on real data.

**Status:** Gates A-D measured below, verdict not yet determined (Gate E
pending). Whole-suite run is owed to the launcher, per the issue-solver's
own rules (it must not run the whole suite).

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/volume/nm_effort_result_20.py` | volume | `NM_EFFORT_RESULT_20` | unbounded, ratio of two ratios; measured 0.056419 .. 1109.604108 on a 1,500-bar synthetic frame below, or NaN |

Tests: `tests/test_nm_effort_result_20.py` (37 tests). Numbers: `python
docs/measure_nm_effort_result_20.py`, run from the repo root. Environment:
Python 3.11.2, pandas 2.3.3, numpy 1.26.4. Measured 2026-11-27.

## Decisions

1. **The formula is read directly from the issue's own "What" line**, not
   independently re-derived from a published source, because none exists —
   the issue's own text states this plainly. It is identical to the screen
   prototype's own formalisation
   (`docs/issues/screen/ind_screen_r7.py`'s `nm_effort_result_20`:
   `sdiv(sdiv(v, mean(v, 20)), sdiv(h - l, mean(h - l, 20)))`). This is a
   disclosed limitation of Gate A for this port specifically, not a
   shortcut taken against the issue's own instruction ("Gate A starts from
   the source formula, not the prototype") — the source formula AND the
   prototype's formalisation are the same expression here.
2. **`length` is a parameter, not hard-coded**, defaulting to `20` — the
   issue's own stated window, matching this fork's standing convention for
   every other rolling-window port.
3. **Each of the three divisions is masked independently** (`rel_volume`,
   `rel_range`, and the final ratio), matching the prototype's own nested
   `sdiv` calls rather than only masking the final division — a flat
   trailing volume or range window blanks its own bar before the outer
   division ever runs, rather than surfacing as `inf` and only then being
   caught.
4. **`MIN_LENGTH = 2`, not 1.** At `length = 1`, a 1-bar rolling mean is the
   identity, so `rel_volume[t] = V[t]/V[t]` and `rel_range[t] = range[t]/range[t]`
   are each FORCED to `1.0` (or `NaN` on an exact zero) — never anything
   else (measured: 3,000 random 1-bar draws all land on `{1.0}`). At
   `length = 2` the ratio reads a second, different bar and is no longer
   pinned to one value (measured: 3,000 random 2-bar draws give 3,000
   distinct values — not a degenerate collapse).
5. **Column name carries the one parameter**, `NM_EFFORT_RESULT_{length}` —
   e.g. `NM_EFFORT_RESULT_20` at the default, `NM_EFFORT_RESULT_50` at
   `length=50`.

## Gate A — correctness

The issue's own stated formula, read with this fork's standing rolling-mean
convention (trailing, ending at and including the current bar):

```
range[t]        = H[t] - L[t]
mean_volume[t]  = SMA(V, length)[t]
mean_range[t]   = SMA(range, length)[t]
rel_volume[t]   = V[t] / mean_volume[t]            (inf -> NaN)
rel_range[t]    = range[t] / mean_range[t]          (inf -> NaN)
NM_EFFORT_RESULT[t] = rel_volume[t] / rel_range[t]   (inf -> NaN)
```

A hand-derived fixture, chosen on paper before the module ever ran
(`tests/test_nm_effort_result_20.py::test_hand_derived_four_bars`):
`V = [100, 200, 150, 300]`, `range = H - L = [2, 4, 1, 5]`, `length=2`.
Bar 1: `rel_volume = 200/150 = 4/3`, `rel_range = 4/3`, ratio exactly
`1.0`. Bar 2: `rel_volume = 150/175 = 6/7`, `rel_range = 1/2.5 = 2/5`,
ratio `15/7`. Bar 3: `rel_volume = 300/225 = 4/3`, `rel_range = 5/3`,
ratio `4/5 = 0.8`. Module's measured output (`python
docs/measure_nm_effort_result_20.py`): `1.0`, `2.142857142857143`
(`15/7 = 2.142857142857142857...` repeating, matching to float64),
`0.7999999999999999` (float64's own representation of `0.8`, not a
disagreement) — all three within the test's `pytest.approx(..., abs=1e-12)`.

Cross-checked against an independent per-bar Python loop (plain Python
`sum()`/division, no `.rolling()` calls, no shared helper with the module
except the input series themselves) on a 400-bar synthetic frame
(`length=50`, 351 defined bars): NaN masks identical, **max |diff| 0.0** on
this machine (`test_matches_an_independent_scalar_loop`), within the test's
pinned `< 1e-9` band — not tightened to exact bit equality per the
issue-solver's own CPU-variant rule (the oracle sums with plain Python
while the module uses numpy's rolling sum, and the two reduction paths
could in principle round differently on a CPU with different dispatched
kernels).

## Gate B — causality

- **The real module never reads the future, swept, not spot-checked.** A
  1,500-bar synthetic OHLCV frame, spliced at `J` with 3 independent
  random futures (high, low AND volume all replaced from `J` onward):
  bars `< J` come only from the original path in both the base and the
  spliced series, so if the module reads no later bar than `T` its output
  on `[0, J)` cannot move. Measured over **36 swept J values** (`J` = 60,
  100, ..., 1460, past the 20-bar default warm-up;
  `python docs/measure_nm_effort_result_20.py`): **real module leaked at 0
  of 36.**
- **Two independent mutants, each `importlib`-read and `exec`'d in memory,
  each live (differs from the real module) and each caught at every one of
  the same 36 swept offsets:**
  - `write-shift`: the final write (`result = (rel_volume / rel_range)...`)
    shifted `length` bars into the future (`.shift(-length)` appended), so
    bar `T`'s output actually describes the window ending at `T + length`.
  - `forward-mean-volume`: `mean_volume` built from a FORWARD-looking
    window (`.shift(-length)` appended after the trailing rolling mean), so
    bar `T`'s "mean volume" reads `V[T+1 .. T+length]`, none of which
    overlaps the trailing window the real module reads.

  Measured leak counts (`python docs/measure_nm_effort_result_20.py`, out
  of the same 36 swept offsets as the real module above): **both mutants,
  36 of 36.**

## Gate C — reachability

Synthetic, from the port session, one 1,500-bar frame at the default
`length=20` (`python docs/measure_nm_effort_result_20.py`):

| frame | fires | warm-up | min | max | distinct values |
|---|---|---|---|---|---|
| synthetic walk (seed 11) | 1,481 of 1,500 | 19 | 0.056419 | 1109.604108 | 1,481 |

Every fired bar reads a genuine spread of distinct values (1,481 of 1,481
fired bars distinct), not a narrow or degenerate subset. The warm-up is
`length - 1 = 19` bars (not `length`), matching pandas' own
`rolling(length, min_periods=length)` convention: the first full window
ends at index `length - 1`. The wide max (1109.6) reflects this synthetic
frame's own occasional near-zero `range` bars (a thin spread relative to
its own 20-bar baseline divides a normal `rel_volume` by a tiny
`rel_range`), not a bug — a zero-range bar is blanked (see below), a
near-zero one is not.

A flat (all-equal) trailing VOLUME window blanks nothing by itself if the
flat level is non-zero (`V[t]/mean(V) = 1.0` cleanly); only an all-ZERO
volume window blanks its own bar (`0/0 = NaN`,
`test_a_flat_volume_window_blanks_its_own_bar`). A flat (zero-range, i.e.
every `H == L`) trailing RANGE window blanks every bar once the window is
full, because `mean_range == 0` makes `rel_range` either `0/0 = NaN` or,
on the rare in-window exception, `nonzero/0 = inf -> NaN`
(`test_a_flat_range_window_blanks_its_own_bar`, every bar from `length - 1`
onward NaN when `high == low` throughout).

## Gate D — scale-free, two independent axes

- **Bit-identical under a power-of-two PRICE rescale (x8/x64); bit-identical
  under a power-of-two VOLUME rescale (x8/x64); bit-identical under BOTH
  together (x8/x64).** `range = H - L` scales exactly by a power-of-two
  price factor `k` (the multiply introduces no rounding), so `mean_range`
  scales by the same exact `k` and `rel_range = range/mean_range` is
  UNCHANGED; `rel_volume` does not involve price at all. Symmetrically for
  a volume rescale `j` on `mean_volume`/`rel_volume`, with `rel_range`
  untouched. Measured on the 1,500-bar frame
  (`python docs/measure_nm_effort_result_20.py`): **price x8/x64: 0 exact
  mismatches on 1,481 co-finite cells, max\|diff\| 0.0. Volume x8/x64: 0
  mismatches, max\|diff\| 0.0. Combined x8/x64: 0 mismatches, max\|diff\|
  0.0.**
- A non-power-of-two rescale (`x10`, `x3.7`) is not exact at the scalar
  multiply, so `H*k`, `L*k` (hence `range`) and `V*j` each pick up
  independent last-bit rounding noise before the rolling sums run on
  already-rounded inputs — the algebraic cancellation then holds only to
  within float64 tolerance, not bit-for-bit. Measured on the same frame:
  **price x10: 1,466 of 1,481 cells differ EXACTLY (not bit-identical), but
  max\|diff\| 1.288e-09; price x3.7: 1,463 differ, max\|diff\| 4.695e-09;
  volume x10: 749 differ, max\|diff\| 2.274e-13; volume x3.7: 808 differ,
  max\|diff\| 5.684e-14; combined x10: 1,467 differ, max\|diff\| 1.288e-09;
  combined x3.7: 1,466 differ, max\|diff\| 4.695e-09** — every one of these
  is float64 rounding noise many orders of magnitude under
  `tests/test_nm_effort_result_20.py`'s pinned `1e-6` tolerance, not a
  disagreement; NaN masks matched exactly in every case. The "almost every
  cell differs by a tiny amount" pattern (rather than "a few cells differ
  by a whole step", as `nm_mmi_250`'s comparison-based metric showed) is
  expected here: this column is a continuous ratio of sums, so a
  non-power-of-two rescale's rounding noise propagates into nearly every
  bar's last bit rather than only flipping an occasional discrete
  comparison.
- `0 < 1,481 fires < 1,500`, 1,481 distinct values: not constant.

## Gate E — attribution

Run by the launcher. The screen prototype's own pre-port measurement
(issue text, `docs/issues/screen/candidates_r7.csv`): max \|ρ\| **0.6713**
vs `vol_at_low_ratio` (`compute_all`, n = 395,776), top-5 per-frame max
median **0.6329** → **SHIP** at the prototype stage (`screen_r7_20261025`,
89 ALTPORT-1 frames, 398,849 bars, 329 + 358 comparators, canary bit-equal).
Next comparators: `VOL_RATIO` and `Volume_Ratio_20`, also 0.6713. This
port's own re-run is pending — the issue-solver must not run Gate E itself.

**Gate E: pending, run by issue-solver after this session.**

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole
suite):

```
python -m pytest -q tests/test_nm_effort_result_20.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

**1,775 passed, 1 failed, 7 skipped.** The 1 failure is
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
owed for `['nm_effort_result_20']` only — expected per the issue-solver's
own rules (this session must not run Gate E or record the ledger row).
`tests/test_nm_effort_result_20.py` alone: **37 passed.**

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in
for a GitHub runner without AVX-512 — the four features issue-solver's
rules name, not this machine's full dispatchable set, which also has
`AVX512CD`/`AVX512_CLX`/`AVX512_CNL`/`AVX512_ICL` enabled):
`python docs/measure_nm_effort_result_20_cpu.py` — **37 passed** (just
`tests/test_nm_effort_result_20.py`; the ledger/readme/wiring modules above
are not CPU-sensitive and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 419 → 420 (`tests/test_altport2_ports.py`);
  `CATEGORY_BUCKETS["volume"]` 48 → 49.
- README: 419 → 420 registered, 427 → 428 callable, volume (48) → (49).
- `docs/MLCompanionContract.md`: 764 → 765 tagged and 389 → 390 `SF` (newest
  first in the chain). `NM_EFFORT_RESULT_20` tags `SF` because `rel_volume`
  cancels any positive volume rescale and `rel_range` cancels any positive
  price rescale, on two independent axes — measured bit-identical under
  x8/x64 price-only, volume-only, and combined rescales.
- `docs/IndicatorDictionary.md`, regenerated with this environment's
  package (`python docs/gen_indicator_dictionary.py`): adds
  `nm_effort_result_20` under `## volume (50)`, tagged `SF`, warm-up 19
  (`length - 1`). Its diff is the `nm_effort_result_20` row, the three
  header counts, the volume section count, and the no-transform-needed
  shortlist, and nothing else (checked: `git diff docs/IndicatorDictionary.md`).
- `Category`: `nm_effort_result_20` is placed alphabetically between `mfi`
  and `nvi` in `volume`.
- Module sha1 (LF-normalised, for the later `docs/gate_e_ledger.csv` row):
  `65935caa43d55281397b04960e1f152aa5100ba0` (measured, `python
  docs/measure_nm_effort_result_20.py`).

## Next step

Gates A-D measured and clean. Gate E owed to the launcher; once run, record
the ledger row (`python docs/gate_e_ledger.py record <run dir> --measured
YYYY-MM-DD`) and update this file's Gate E section with the result (SHIP /
DISCLOSE / DISCLOSE_GAP ships disclosed, STRUCK reverts per the issue's own
"Done when" clause: a measured revert closes the issue exactly as well as
a ship).
