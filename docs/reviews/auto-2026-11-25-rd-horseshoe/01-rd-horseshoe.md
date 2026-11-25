# RD-HORSESHOE — task log

## Implementation summary

- Added `pandas_ta/candles/rd_horseshoe.py`: `RD_HORSESHOE` column, +1 bull / -1 bear / 0,
  bar1..bar4 read as `.shift(3)`..unshifted-current, outer bound `max`/`min(open1, close4)`
  per the issue's own formula (not the screen prototype). Gate A/B/D arguments carried in
  the module docstring, matching the repo's `a101_007`-style convention.
- Wired all five touch points: the module, `pandas_ta/candles/__init__.py` (export),
  `pandas_ta/__init__.py` (`Category["candles"]`, appended alphabetically after `ha`),
  `pandas_ta/core.py` (`df.ta.rd_horseshoe()` accessor), `tests/test_rd_horseshoe.py`.
- `tests/test_rd_horseshoe.py` (21 tests): two hand-derived fixtures (bull/bear) with
  on-paper-first arithmetic, two outer-bound-violation fixtures, a doji-breaks-the-pattern
  fixture, warm-up/offset/short-input edge cases, a Gate B future-perturbation + mutant
  sweep (293 J values: real 0 leaks, mutant leaks at 24 — the `smc_sweep` low-power
  pattern from `test_altport2_ports.py`, not a single fixed J), Gate D scale tests
  (x8/x64/x10/x3.7, all bit-identical), a reachability test (both signs fire, not
  constant), and wiring tests (column name/category, `Category` membership, accessor
  parity).
- `docs/measure_rd_horseshoe.py` and `docs/measure_rd_horseshoe_cpu.py`: reproduce every
  number quoted in the receipt, including the CPU-feature-disabled run issue-solver's
  rules require.
- `docs/RdHorseshoeMeasured.md`: Gates A–D measured and cited to their source (fixture,
  test, or measure-script line); Gate E marked pending per the issue-solver rules
  (launcher runs it, a later receipt session records the ledger row); Gate F records only
  the commands run in this session and their actual counts.
- Counters bumped: `CATEGORY_TOTAL` 392→393, README (392→393 registered, 400→401
  callable, candles (5)→(6)), `docs/MLCompanionContract.md` (737→738 tagged, 104→105
  `BIN`), `docs/IndicatorDictionary.md` regenerated (diff checked to be exactly the new
  row + the three header counts + the candles section count + the BIN/ORD shortlist,
  nothing else).
- Required test command run repeatedly through the session; final state: **1,543 passed,
  7 skipped, 1 failed** — the one failure is
  `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`, expected
  per the task's own instructions (Gate E owed).

## Gate (round 1)

Dispatched a Fletcher reviewer (`Explore` subagent, read-only) against the full file set
with the original task text and the issue text verbatim, plus explicit instructions to
hand-verify at least one arithmetic claim and to re-run the required pytest command
itself rather than trust the receipt's numbers.

Verdict, quoted verbatim:

```
VERDICT: PASS
FINDINGS:
  - severity: NIT
    location: pandas_ta/core.py:895 (rd_horseshoe accessor method)
    problem:  The new `rd_horseshoe` accessor is inserted between `cdl_z` (line 887) and `ha` (line 903), breaking the alphabetical ordering the surrounding candle methods otherwise follow (`cdl_doji`, `cdl_inside`, `cdl_pattern`, `cdl_z`, `ha` was alphabetical; `rd_horseshoe` belongs after `ha`, matching where it sits in `Category["candles"]`).
    fix:      Move the `rd_horseshoe` method below `ha`'s in core.py so accessor order matches both alphabetical convention and the `Category` list order. Cosmetic only, no behavioral effect.
  - severity: NIT
    location: tests/test_rd_horseshoe.py:9-13 (module docstring)
    problem:  The docstring says "a fixture showing the outer-bound check actually gates the pattern" (singular) when there are in fact two such fixtures (`test_outer_bound_violation_blocks_the_bull_pattern` and `..._bear_pattern`).
    fix:      Reword to "two fixtures" (or "one per side") so the docstring's own count matches what's actually pinned, consistent with this repo's own rule that counts in prose must correspond to what was measured/written.
SUMMARY: This is a clean, disciplined port. Gate A's bar indexing was hand-verified against both fixtures (bull: max(100,101)=101, highs 100.7/100.9 both <=101; bear: min(100,99)=99, lows 99.3/99.8 both >=99) and matches the issue text, the module docstring, and the screen prototype's own shift pattern bit-for-bit. The Gate B mutant is a genuine future-leak (append `.shift(-1)` to the final masked write) and is proven live and caught; every number quoted in docs/RdHorseshoeMeasured.md (0/293 real leaks, 24/293 mutant leaks, 79/84/1834 bull/bear/zero on the 2,000-bar frame, 0 mismatches on 597 cells under x8/x64/x10/x3.7, seed-by-seed bull/bear ranges, 1,543 passed/7 skipped/1 failed, 21 passed under disabled AVX-512) reproduced exactly when I re-ran `docs/measure_rd_horseshoe.py`, `docs/measure_rd_horseshoe_cpu.py`, and the required pytest subset myself — nothing was invented. Gate D's scale-free argument is sound (every comparison is like-for-like price terms, so a positive rescale cannot flip any truth value, discrete output needs no tolerance). All five wiring touch points are present and correct, the diffs to README/IndicatorDictionary/MLCompanionContract/test_altport2_ports are each exactly the expected delta and nothing else, and no file outside the allowed set was touched. The only Gate E ledger failure is the explicitly expected one. Two cosmetic NITs noted above; neither blocks shipping.
```

## Outcome

PASS on round 1 (NIT-only, no CRITICAL/MAJOR). Both NITs were cheap and unambiguous, so
applied immediately even though PASS does not require a fix-and-re-review round:

- Moved the `rd_horseshoe` accessor in `pandas_ta/core.py` to after `ha`'s, matching
  `Category["candles"]`'s alphabetical order.
- Reworded `tests/test_rd_horseshoe.py`'s module docstring: "a fixture" → "two fixtures
  (one per side)" for the outer-bound-violation claim.

Required test command re-run after the fixes: unchanged, **1,543 passed, 7 skipped,
1 failed (expected)**. Marked done; no second review round needed (PASS already reached,
fixes were cosmetic and verified not to regress anything).
