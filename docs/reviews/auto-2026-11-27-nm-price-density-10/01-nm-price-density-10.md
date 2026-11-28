# Task log — NM-PRICE-DENSITY-10 (issue #186)

## Implementation (main thread)

1. Read the issue's own text, the screen prototype (`docs/issues/screen/ind_screen_r7.py`'s
   `nm_price_density_10` candidate, `sdiv((h - l).rolling(10).sum(), tsmax(h, 10) - tsmin(l, 10))`)
   and `candidates_r7.csv`'s pre-port Gate E row (max |ρ| 0.7289 vs `chop`) to confirm the formula
   and the prior overlap measurement.
2. Dispatched a scout subagent to read the closest existing templates: `chop` (`pandas_ta/trend/chop.py`,
   the rolling-window/denominator idiom), `pdist` (volatility category precedent), and the two most
   recent merged ports `pfe`/`kalman_trend` for the Gate A-D test shape; read `nm_effort_result_20`
   (issue #185, commit `de29a7b`) directly as the closest sibling for the Measured.md/measure-script
   template and the `MIN_LENGTH` forced-constant reasoning.
3. Wrote `pandas_ta/volatility/nm_price_density_10.py`: `numerator = SUM(H-L, length)`,
   `denominator = MAX(H, length) - MIN(L, length)`, `NM_PRICE_DENSITY = numerator/denominator`,
   masked once (`inf -> NaN`), matching the prototype's single `sdiv` call. `MIN_LENGTH = 2`
   (length=1 forces the ratio to 1.0 by construction, same collapse `nm_effort_result_20` guards
   against).
4. Wired all five touch points: `pandas_ta/volatility/__init__.py` (export, alphabetically between
   `massi` and `pdist`), `pandas_ta/__init__.py` (`Category["volatility"]`, between `natr` and
   `pdist`), `pandas_ta/core.py` (accessor, placed after `natr`), `tests/test_nm_price_density_10.py`.
5. Wrote `tests/test_nm_price_density_10.py` (30 tests at this point): Gate A (hand-derived 4-bar
   fixture at length=2, a hand-constructed counterexample showing the ratio is not bounded below
   1.0, independent scalar-loop cross-check), `MIN_LENGTH` forced-constant probes, Gate B
   (future-splice sweep + two mutants: `write-shift`, `forward-hh`), Gate C (reachability, flat-window
   blanking), Gate D (price-only x8/x64 bit-identical, x10/x3.7 tolerance), wiring.
6. Ran the tests, found and fixed one test bug of my own: `test_a_flat_window_blanks_its_own_bar`
   originally asserted the ENTIRE tail from the flat window onward stayed NaN, which is wrong — only
   the bar whose own trailing window is entirely flat is blanked; once the window slides past the
   flat run it picks up a non-flat bar again. Corrected to assert exactly that one bar.
7. Regenerated `docs/IndicatorDictionary.md` (`python docs/gen_indicator_dictionary.py`); the
   generator classified the new column `SF` automatically, warm-up 9.
8. Updated README (420→421 registered, 428→429 callable, `volatility (43)`→`(44)` with the name
   added alphabetically), `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 421,
   `CATEGORY_BUCKETS["volatility"]` 44), `docs/MLCompanionContract.md` (766 tagged / 391 `SF`, new
   chain entry).
9. Wrote and ran `docs/measure_nm_price_density_10.py` and `docs/measure_nm_price_density_10_cpu.py`,
   transcribed every number into `docs/NmPriceDensity10Measured.md`.

## Gate (Fletcher reviewer, round 1)

Dispatched a read-only `Explore` subagent with the Fletcher persona and the full file list,
instructed to independently re-run the tests and measurement script and hand-recompute every Gate A
fixture, including the below-1.0 counterexample and the `MIN_LENGTH` argument.

```
VERDICT: REVISE
FINDINGS:
  - severity: MAJOR
    location: pandas_ta/volatility/nm_price_density_10.py (module docstring, GATE A paragraph);
      also docs/NmPriceDensity10Measured.md Decisions item 3
    problem: The docstring claimed, unconditionally, "denominator[t] == 0 forces numerator[t] == 0
      too ... the masked case is always 0/0, never a genuine nonzero/0." False whenever a malformed
      bar has Low > High somewhere in the window (the module never validates High >= Low) --
      counterexample H=[5,2], L=[5,8], length=2: numerator=-6, denominator=0, a genuine nonzero/0
      the docstring said was impossible. This fork's sibling indicators (har_park, corwin_schultz,
      g191_158) know not to assume High >= Low unconditionally; this one asserted it unconditionally
      in prose while silently depending on the caller never passing malformed OHLC -- exactly the
      "claim written before it was measured" defect CLAUDE.md names as this process's dominant
      failure mode.
    fix: Qualify the claim to disclose the OHLC-consistency precondition (unvalidated by this
      function) and note the malformed case still gets masked because it divides to -inf, caught by
      the same `.replace([inf, -inf], nan)` mask -- in both the module docstring and the Measured.md
      Decisions item.
SUMMARY: The arithmetic is clean -- every hand-derived Gate A number, every mutant string, every
wiring touch point, every counter, and the full Gate F pytest run all independently reproduce
exactly as claimed. The one defect is documentation-correctness, not runtime: an unmeasured absolute
claim about an unvalidated precondition.
```

## Fixes applied (round 1 -> round 2)

- `pandas_ta/volatility/nm_price_density_10.py`'s module docstring paragraph rewritten to state the
  `0/0`-only claim holds "On OHLC-CONSISTENT input (`H[t] >= L[t]` on every bar — NOT validated by
  this function...)" and walks through the exact H=[5,2]/L=[5,8] counterexample to show the
  malformed case still lands on `-inf`, caught by the same mask.
- `docs/NmPriceDensity10Measured.md`'s Decisions item 3 reworded the same way, with a note that this
  was found by the round-1 review.
- Added `test_a_malformed_bar_low_above_high_is_still_masked_not_a_silent_number` to
  `tests/test_nm_price_density_10.py`, using the exact H=[5,2]/L=[5,8]/length=2 counterexample,
  asserting NaN.
- Updated every test-count reference (30 → 31 tests; 1,776 → 1,777 passed in the full required
  subset; both the plain and CPU-variant runs) across `docs/NmPriceDensity10Measured.md`.

## Gate (Fletcher reviewer, round 2)

Re-dispatched a fresh read-only `Explore` subagent against the fix, instructed to hand-verify the
new docstring wording, hand-recompute the new counterexample test, and re-run the full required
test subset plus the CPU-variant script.

```
VERDICT: PASS
FINDINGS:
  (none)
SUMMARY: The docstring paragraph now says what it should: the 0/0-only claim is explicitly
conditioned on OHLC-consistent input that this function does not validate, and it walks through the
exact H=[5,2]/L=[5,8] counterexample to show the malformed case still lands on -inf, caught by the
same `.replace([inf, -inf], nan)` mask rather than surfacing as a silent wrong number. The new
regression test reproduces that counterexample by hand and asserts NaN, which is correct. 31 passed
under both the plain and CPU-variant runs of `tests/test_nm_price_density_10.py`; the full required
subset shows 1,777 passed, 1 failed (the expected owed Gate E ledger row naming only
nm_price_density_10), 7 skipped -- exact match. Nothing in Gates A-D, the wiring counters, or
CATEGORY_TOTAL shows any sign of disturbance beyond the scoped edit. That was acceptable. Barely.
```

PASS on round 2 — one REVISE round, fixed, re-reviewed, closed within the 3-round cap.
