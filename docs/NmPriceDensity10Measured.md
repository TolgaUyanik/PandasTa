# Kaufman's price density (10) — measured (`nm_price_density_10`)

Issue #186 (NM-PRICE-DENSITY-10), from the 2026-10-25 follow-up of round 7
(`docs/issues/screen/candidates_r7.csv`). Named, undefined, in two Reddit
threads only (tier 4): rd:algotrading:15xt5xt, rd:algotrading:1nrkjby. The
definition comes from Kaufman 2013, Trading Systems and Methods, 5th ed.,
ch. 1 "Other Measurements of Noise" (ResearchIntel book chunk), not from
either Reddit thread — neither states a formula. Existence, not evidence:
nothing here tests Kaufman's own claim on real data.

**Status:** Gates A-F measured below. Gate E: **SHIP** (max \|ρ\| 0.7289 vs
`chop`, under the 0.76 ship line). Whole suites run by the launcher in
clean worktrees: **0 regressions in either repo** — PandasTa 17,174 passed /
1 pre-existing failure (base: 17,135 / 1), Backtesting 2,211 passed / 32
failed / 4 errors, identical at base and HEAD (launcher run at 56d901a, before the
origin/dev merge).

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/volatility/nm_price_density_10.py` | volatility | `NM_PRICE_DENSITY_10` | unbounded above, not bounded below by 1.0 (see Decisions); measured 0.428180 .. 4.144955 on a 1,500-bar synthetic frame below, or NaN |

Tests: `tests/test_nm_price_density_10.py` (31 tests). Numbers: `python
docs/measure_nm_price_density_10.py`, run from the repo root. Environment:
Python 3.11.2, pandas 2.3.3, numpy 1.26.4. Measured 2026-11-27.

## Decisions

1. **The formula is Kaufman's own published chapter formula**, read with
   this fork's standing rolling convention (trailing window ending at and
   including the current bar), not an independently re-derived one — the
   issue names exactly one source (Kaufman 2013) and the screen prototype's
   own formalisation (`docs/issues/screen/ind_screen_r7.py`'s
   `nm_price_density_10`: `sdiv((h - l).rolling(10).sum(), tsmax(h, 10) -
   tsmin(l, 10))`) is a direct transcription of that same chapter formula,
   not a second, independent reading. This is a disclosed limitation of
   Gate A for this port specifically (the source formula and the
   prototype's formalisation are the same expression), not a shortcut
   taken against the issue's own instruction.
2. **`length` is a parameter, not hard-coded**, defaulting to `10` —
   Kaufman's own example period, matching this fork's standing convention
   for every other rolling-window port.
3. **The single division is masked once** (`numerator / denominator`,
   `inf -> NaN`), matching the prototype's own `sdiv`
   (`sdiv(a, b) = (a / b).replace([inf, -inf], nan)`). Unlike
   `nm_effort_result_20`'s three independently-masked divisions, there is
   only one division here. On OHLC-CONSISTENT input (`H[t] >= L[t]` on
   every bar — NOT validated by the module, the same unstated precondition
   `har_park`/`corwin_schultz` rely on), `denominator == 0` forces
   `numerator == 0` too (every bar's own high equals its own low across
   the whole window), so the masked case is always `0/0`. On a malformed
   bar (`L[t] > H[t]`) this no longer holds — `numerator` can be negative
   while `denominator` is still 0 (`H=[5,2]`, `L=[5,8]`, `length=2`:
   `numerator=-6`, `denominator=0`) — but the result is still masked,
   because that case divides to `-inf`, which `.replace([inf, -inf],
   nan)` catches the same as `+inf`. Found by the Fletcher review round 1
   (CRITICAL/MAJOR gate): the module docstring originally stated the
   `0/0`-only claim unconditionally; both it and this file now disclose
   the OHLC-consistency precondition.
4. **`MIN_LENGTH = 2`, not 1.** At `length = 1`, a 1-bar rolling
   sum/max/min is each the identity, so `numerator[t] = range[t]` and
   `denominator[t] = H[t] - L[t] = range[t]` are FORCED equal — the ratio
   is pinned to `1.0` (or `NaN` on an exact zero range) — never anything
   else (measured: 3,000 random 1-bar draws all land on `{1.0}`). At
   `length = 2` the ratio reads a second, different bar and is no longer
   pinned to one value (measured: 3,000 random 2-bar draws give 2,998
   distinct values — not a degenerate collapse).
5. **The ratio is NOT bounded below by 1.0 in general**, unlike a naive
   reading of "sum of parts over the whole". A window spanning a gap can
   read below 1.0: hand-constructed counterexample `H = [5, 1]`,
   `L = [4, 1]`, `length=2` gives `numerator = (5-4) + (1-1) = 1`,
   `denominator = max(5,1) - min(4,1) = 4`, ratio `0.25` — confirmed by the
   measure script and pinned by
   `tests/test_nm_price_density_10.py::test_a_window_spanning_a_gap_can_read_below_one`.
6. **Column name carries the one parameter**, `NM_PRICE_DENSITY_{length}` —
   e.g. `NM_PRICE_DENSITY_10` at the default, `NM_PRICE_DENSITY_50` at
   `length=50`.

## Gate A — correctness

Kaufman's own chapter formula, read with this fork's standing rolling-window
convention (trailing, ending at and including the current bar):

```
range[t]        = H[t] - L[t]
numerator[t]    = SUM(range, length)[t]
hh[t]           = MAX(H, length)[t]
ll[t]           = MIN(L, length)[t]
denominator[t]  = hh[t] - ll[t]
NM_PRICE_DENSITY[t] = numerator[t] / denominator[t]   (inf -> NaN)
```

A hand-derived fixture, chosen on paper before the module ever ran
(`tests/test_nm_price_density_10.py::test_hand_derived_four_bars`):
`H = [10, 12, 11, 9]`, `L = [8, 9, 7, 8]` (`range = [2, 3, 4, 1]`),
`length=2`. Bar 1 (window [0,1]): `numerator = 2+3 = 5`,
`denominator = max(10,12)-min(8,9) = 4`, ratio `5/4 = 1.25`. Bar 2 (window
[1,2]): `numerator = 3+4 = 7`, `denominator = max(12,11)-min(9,7) = 5`,
ratio `7/5 = 1.4`. Bar 3 (window [2,3]): `numerator = 4+1 = 5`,
`denominator = max(11,9)-min(7,8) = 4`, ratio `5/4 = 1.25`. Module's
measured output (`python docs/measure_nm_price_density_10.py`): `1.25`,
`1.4`, `1.25` — exact, within the test's `pytest.approx(..., abs=1e-12)`.

A second hand-constructed case shows the ratio is NOT bounded below by
1.0 (see Decisions item 5): `H = [5, 1]`, `L = [4, 1]`, `length=2` reads
`0.25`, measured exactly by the script and pinned by
`test_a_window_spanning_a_gap_can_read_below_one`.

Cross-checked against an independent per-bar Python loop (plain Python
`sum()`/`max()`/`min()`, no `.rolling()` calls, no shared helper with the
module except the input series themselves) on a 400-bar synthetic frame
(`length=50`, 351 defined bars): NaN masks identical, **max |diff| 0.0** on
this machine (`python docs/measure_nm_price_density_10.py`), within the
test's pinned `< 1e-9` band (`test_matches_an_independent_scalar_loop`) —
not tightened to that exact bit-equality in the test assertion itself per
the issue-solver's own CPU-variant rule (the oracle sums with plain Python
while the module uses numpy's rolling sum/max/min, and the two reduction
paths could in principle round differently on a CPU with different
dispatched kernels).

## Gate B — causality

- **The real module never reads the future, swept, not spot-checked.** A
  1,500-bar synthetic OHLC frame, spliced at `J` with 3 independent random
  futures (high AND low both replaced from `J` onward): bars `< J` come
  only from the original path in both the base and the spliced series, so
  if the module reads no later bar than `T` its output on `[0, J)` cannot
  move. Measured over **36 swept J values** (`J` = 60, 100, ..., 1460, past
  the 10-bar default warm-up; `python docs/measure_nm_price_density_10.py`):
  **real module leaked at 0 of 36.**
- **Two independent mutants, each `importlib`-read and `exec`'d in memory,
  each live (differs from the real module) and each caught at every one of
  the same 36 swept offsets:**
  - `write-shift`: the final write (`result = (numerator /
    denominator)...`) shifted `length` bars into the future
    (`.shift(-length)` appended), so bar `T`'s output actually describes
    the window ending at `T + length`.
  - `forward-hh`: `hh` (window high) built from a FORWARD-looking window
    (`.shift(-length)` appended after the trailing rolling max), so bar
    `T`'s "window high" actually reads `H[T+1 .. T+length]`, none of which
    overlaps the trailing window the real module reads.

  Measured leak counts (`python docs/measure_nm_price_density_10.py`, out
  of the same 36 swept offsets as the real module above): **both mutants,
  36 of 36.**

## Gate C — reachability

Synthetic, from the port session, one 1,500-bar frame at the default
`length=10` (`python docs/measure_nm_price_density_10.py`):

| frame | fires | warm-up | min | max | distinct values |
|---|---|---|---|---|---|
| synthetic walk (seed 11) | 1,491 of 1,500 | 9 | 0.428180 | 4.144955 | 1,491 |

Every fired bar reads a genuine spread of distinct values (1,491 of 1,491
fired bars distinct), not a narrow or degenerate subset. The warm-up is
`length - 1 = 9` bars (not `length`), matching pandas' own
`rolling(length, min_periods=length)` convention: the first full window
ends at index `length - 1`. The measured minimum, 0.428180, is below 1.0 —
consistent with Decisions item 5 (the ratio is not bounded below by 1.0 in
general) on this synthetic frame's own occasional near-gap bars, not a bug.

A window whose high equals its low across every bar (every bar a flat
doji, constructed by setting `length` consecutive bars' high and low to
the same constant) blanks the bar whose OWN trailing window is entirely
flat, and the next bar is defined again once the window slides past the
flat run (`test_a_flat_window_blanks_its_own_bar`). A window flat everywhere except
its own LAST bar is never blanked
(`test_a_non_flat_window_is_never_blanked`).

## Gate D — scale-free

- **Bit-identical under a power-of-two PRICE rescale (x8/x64).**
  `range = H - L` scales exactly by a power-of-two factor `k` (the
  multiply introduces no rounding), so `numerator` scales by the same
  exact `k`; `hh`/`ll` scale by `k` too (a positive scalar multiply
  preserves argmax/argmin), so `denominator` scales by `k` as well, and
  `NM_PRICE_DENSITY = numerator / denominator` is UNCHANGED. Measured on
  the 1,500-bar frame (`python docs/measure_nm_price_density_10.py`):
  **x8: 0 exact mismatches on 1,491 co-finite cells, max\|diff\| 0.0. x64:
  0 mismatches, max\|diff\| 0.0.**
- A non-power-of-two rescale (`x10`, `x3.7`) is not exact at the scalar
  multiply, so `H*k` and `L*k` (hence `range`) each pick up independent
  last-bit rounding noise before the rolling reductions run on
  already-rounded inputs — the algebraic cancellation then holds only to
  within float64 tolerance, not bit-for-bit. Measured on the same frame:
  **x10: 1,449 of 1,491 cells differ EXACTLY (not bit-identical), but
  max\|diff\| 1.954e-14; x3.7: 1,439 differ, max\|diff\| 1.421e-14** —
  both many orders of magnitude under
  `tests/test_nm_price_density_10.py`'s pinned `1e-6` tolerance, not a
  disagreement; NaN masks matched exactly in both cases.
- `0 < 1,491 fires < 1,500`, 1,491 distinct values: not constant.

## Gate E — attribution

Run by the launcher on this port's own module (not the prototype),
`pandas_ta.volatility.nm_price_density_10`. The screen prototype's own
pre-port measurement (issue text, `docs/issues/screen/candidates_r7.csv`):
max \|ρ\| **0.7289** vs `chop` (`compute_all`, n = 397,450), top-5
per-frame max median **0.7269** → **SHIP** at the prototype stage
(`screen_r7_20261025`, 89 ALTPORT-1 frames, 398,849 bars, 329 + 358
comparators, canary bit-equal). Next comparators: `CHOP` 0.6377,
`EFFICIENCY_RATIO` 0.5283.

**Launcher's own re-run on the port module** (run `is186-nm_price_density_10-dc9aa7c9`,
`NM_PRICE_DENSITY_10`): max \|ρ\| **0.7288775406417091** vs `chop`
(`compute_all`, n = 397,450), per-frame max median \|ρ\| **0.7269026478909781**
(89 frames, 0.0% of frames ≥ 0.90), manifest max \|ρ\| 0.5171 vs `er_Pctl`
(n = 392,692), 687 comparators, 0 degenerate columns, canary bit-equal
(`AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS`). Matches the prototype's own
pre-port number almost exactly (0.72888 vs 0.7289). The run's own
`overlap_max.csv` reports verdict `SHIP`; CLAUDE.md's Gate E bands
(`r3-perframe-0.90`) put the ship line at `< 0.76`, and this run's own max
\|ρ\| is 0.7289 — under 0.76 — so the harness's own SHIP label and this
fork's own band agree: **SHIP**, not DISCLOSE. Pooled 0.7289 < 0.90 and
per-frame max median 0.7269 < 0.90, so not STRUCK either.

**Gate E verdict: SHIP.** Recorded in `docs/gate_e_ledger.csv`
(`python docs/gate_e_ledger.py record
{run-dir}/gatee/is186-nm_price_density_10-dc9aa7c9
--measured 2026-11-27`).

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole
suite):

```
python -m pytest -q tests/test_nm_price_density_10.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

Re-run at HEAD, after the Gate E ledger row was recorded (commit 79b4698):
**1,785 passed, 7 skipped, 0 failed.** The prior owed-row failure
(`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`,
owed for `['nm_price_density_10']`) is now clear — `docs/gate_e_ledger.csv:113`
carries the row.
`tests/test_nm_price_density_10.py` alone: **31 passed** (30 at port time,
+1 added during the Fletcher review round for the malformed-input
regression, see Decisions item 3).

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in
for a GitHub runner without AVX-512 — the four features issue-solver's
rules name, not this machine's full dispatchable set, which also has
`AVX512CD`/`AVX512_CLX`/`AVX512_CNL`/`AVX512_ICL` enabled):
`python docs/measure_nm_price_density_10_cpu.py` — **31 passed** (just
`tests/test_nm_price_density_10.py`; the ledger/readme/wiring modules
above are not CPU-sensitive and are not re-run under this flag).

After merging `origin/dev` (357cadb): same targeted command, **1,801 passed, 7 skipped,
0 failed**; `tests/test_gate_e_ledger.py` strict (no `GATE_E_PENDING_OK`) **1,626 passed**.

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

Rebased onto `origin/dev` at merge 357cadb (#188 and #139 landed first); at port time
(pre-merge) these were 420 → 421, 428 → 429 and 765 → 766 / 390 → 391.

- `CATEGORY_TOTAL` 422 → 423 (`tests/test_altport2_ports.py`);
  `CATEGORY_BUCKETS["volatility"]` 43 → 44.
- README: 422 → 423 registered, 430 → 431 callable, volatility (43) → (44).
- `docs/MLCompanionContract.md`: 767 → 768 tagged and 392 → 393 `SF`
  (newest first in the chain). `NM_PRICE_DENSITY_10` tags `SF` because the
  numerator scales linearly with a positive price rescale and the
  denominator (window high minus window low) scales by the same exact
  factor, cancelling in the ratio — measured bit-identical under x8/x64.
- `docs/IndicatorDictionary.md`, regenerated with this environment's
  package (`python docs/gen_indicator_dictionary.py`): adds
  `nm_price_density_10` under `## volatility (44)`, tagged `SF`, warm-up 9
  (`length - 1`). Its diff is the `nm_price_density_10` row, the three
  header counts, the volatility section count, and the no-transform-needed
  shortlist, and nothing else (checked: `git diff docs/IndicatorDictionary.md`).
- `Category`: `nm_price_density_10` is placed alphabetically between
  `natr` and `pdist` in `volatility`.
- Module sha1 (LF-normalised, for the `docs/gate_e_ledger.csv` row):
  `780876290eca809775d3d70b0882f57bbd689576` (re-measured at HEAD, `python
  docs/measure_nm_price_density_10.py`; matches `docs/gate_e_ledger.csv:113`
  `module_sha1` and the launcher's `meta.json` `candidate_source_sha1`).

## Next step

None. Gate E ran SHIP, ledger row recorded, module stays. Done per the
issue's own "Done when": shipped through Gates A-F with the numbers here.
