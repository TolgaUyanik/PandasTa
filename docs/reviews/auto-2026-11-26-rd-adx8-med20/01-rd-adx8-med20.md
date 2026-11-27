# Task RD-ADX8-MED20 — log

## Implementation (main thread)

Ported `rd_adx8_med20` on the already-merged `rd_adx3_med10` (#171) pattern: `ADX8 = adx(high, low,
close, length=8)["ADX_8"]`, `RD_ADX8_MED20 = ADX8.rolling(20).median()`. Files:

- `pandas_ta/trend/rd_adx8_med20.py` (new)
- `tests/test_rd_adx8_med20.py` (new)
- `docs/RdAdx8Med20Measured.md` (new, the receipt)
- `docs/measure_rd_adx8_med20.py`, `docs/measure_rd_adx8_med20_cpu.py` (new, reproduce the measured
  numbers; the CPU-variant one runs the suite with `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX
  AVX2 FMA3"` set before numpy import)
- Wiring: `pandas_ta/trend/__init__.py`, `pandas_ta/__init__.py` (`Category["trend"]`),
  `pandas_ta/core.py` (accessor)
- Doc/count bookkeeping: `README.md`, `docs/IndicatorDictionary.md` (regenerated via
  `python docs/gen_indicator_dictionary.py`), `docs/MLCompanionContract.md`,
  `tests/test_altport2_ports.py`

Measured before any review: Gate A exact match on 866/866 compared bars; Gate B 0/9 real leaks,
5/9 mutant leaks; Gate C 866/900 fires (34-bar warm-up), 481 distinct values; Gate D x8/x64
bit-identical, x10/x3.7 within ~1.2e-13. Target suite: 1,703 passed, 7 skipped, 1 expected failure
(`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` — Gate E owed).

## Review round 1 — VERDICT: REVISE

```
VERDICT: REVISE
FINDINGS:
  - severity: CRITICAL
    location: pandas_ta/trend/rd_adx8_med20.py:36-39 (docstring) and line 80 (`min_bars = adx_length + max(length, min_periods)`)
    problem: The docstring asserts, unqualified, "Neither '8' nor '20' carries a zero-guard or edge
      case beyond pandas' own `rolling().median()` NaN propagation ... there is nothing else in the
      poster's words to diverge from." That is false, and the Measured.md receipt carries the proof
      of it without drawing the conclusion. `min_bars = adx_length + max(length, min_periods)` = 8 +
      20 = 28, but `adx(length=8)`'s own first-valid output index is 15 (empirically: ADX's true
      first-valid index tracks `2*adx_length - 1`, confirmed by both ports' own measured numbers —
      sibling's ADX_3 first-valid index 5 = 2*3-1, this port's ADX_8 first-valid index 15 = 2*8-1),
      so the rolling-median window (needs `length`=20 consecutive valid ADX values, `min_periods`
      defaults to `length`) cannot produce a single non-NaN value until index 34 — confirmed by
      `python docs/measure_rd_adx8_med20.py`'s own printed "warm-up 34". `verify_series(high, 28)`
      lets any input of length 28..34 through `return series` unchanged (`pandas_ta/utils/_core.py`
      line 121: only rejects `size < min_length`), so for those 7 input lengths the function returns
      a Series of all-NaN instead of `None` — silently wrong, not merely "slow to warm up." The
      sibling `rd_adx3_med10` has the *same* formula bug (min_bars 13 vs true threshold 15, a 2-length
      gap) and its own `docs/RdAdx3Med10Measured.md` Gate C row explicitly discloses it. This port's
      receipt and docstring carry no such disclosure, despite the gap here being more than 3x larger.
    fix: Either (a) fix `min_bars` to reflect ADX's own true warm-up, e.g.
      `min_bars = (2 * adx_length - 1) + max(length, min_periods)`, so `verify_series` correctly
      returns `None` for undersized input instead of an all-NaN Series, and add a regression test at
      the 28..34 boundary; or (b), if a code fix is deferred, add the same "Known slack" disclosure
      the sibling's Gate C row carries and strike the docstring's "nothing else to diverge from"
      sentence, which is not true as written.
  - severity: MAJOR
    location: tests/test_rd_adx8_med20.py:148
    problem: `assert hits >= len(OFFSETS) // 2, ...` — with 9 offsets, `len(OFFSETS) // 2 == 4`, so
      this accepts `hits == 4`, a MINORITY catch, not the majority the test's own name/docstring and
      the module docstring's prose claim. The sibling test uses the strict `assert hits > len(OFFSETS)
      // 2`, a deliberate round-1 review fix on that very sibling. This port reintroduced the exact
      loose form the repo's own history already rejected.
    fix: Change `>=` to `>` to match the sibling and the already-established house standard.
  - severity: NIT
    location: downloaded_files/dashboard.lock (working tree, not part of this port's own diff)
    problem: `git status` shows this tracked placeholder file deleted — a known recurring
      sandbox/environment artifact that reappears after any `pytest` invocation, unrelated to this
      port's own edits (same diagnosis as issues #169/#171's own review rounds).
    fix: Before committing, run `git checkout HEAD -- downloaded_files/dashboard.lock`.
  - severity: MINOR
    location: pandas_ta/trend/rd_adx8_med20.py:54-55 vs tests/test_rd_adx8_med20.py:134-142
    problem: The module docstring says "see the test module's own docstring for the measured count"
      but `test_mutant_is_caught`'s docstring instead points to Measured.md — two hops instead of one.
    fix: State the measured ratio ("5 of 9") directly in `test_mutant_is_caught`'s docstring.
SUMMARY: The arithmetic, wiring, and doc/count bookkeeping are all genuinely clean and reproduce
exactly. But this port inherited its sibling's known min_bars-vs-true-warm-up slack bug, let it get
substantially worse (a 7-length silent-all-NaN window instead of the sibling's disclosed 2), and
then shipped a docstring sentence claiming no such edge case exists. It also quietly reverted an
already-fixed test assertion (`>=` for `>`) back to a weaker form the repo's own history rejected
once already. Both are concrete, fixable, and neither requires touching Gate E or the whole-suite
runs — fix the disclosure/formula and the operator, then this ships.
```

## Fixes applied (main thread)

- `pandas_ta/trend/rd_adx8_med20.py`: `min_bars` changed from `adx_length + max(length, min_periods)`
  to `2 * adx_length + max(length, min_periods)` (28 → 36), matching the house convention already
  used for the same quantity in `adxr.py` (`verify_series(high, 2 * length)`). Docstring's false
  "nothing else to diverge from" sentence replaced with an accurate description of the one divergence
  (the min-length guard) and a pointer to the new regression test.
- `tests/test_rd_adx8_med20.py`: added `test_min_bars_boundary` (asserts `None` at n=27 and n=35,
  a non-null finite result at n=36 — verified by tracing `adx()`'s own RMA warm-up, `ADX_8`'s first
  non-NaN value sits at index 15, so the tight bound would be 35 bars; 36 is deliberately one bar
  more conservative, same magnitude of slack `adxr.py` itself carries). Tightened
  `test_mutant_is_caught`'s assertion from `hits >= len(OFFSETS) // 2` to `hits > len(OFFSETS) // 2`.
  Stated the mutant's measured 5-of-9 catch ratio directly in that test's docstring.
- `docs/RdAdx8Med20Measured.md`: added a "Round-1 review fix, same session" paragraph disclosing the
  `min_bars` fix and the test tightening; test count 13 → 14; re-ran `docs/measure_rd_adx8_med20.py`
  (all nine measured numbers unchanged — the fix only changes the guard threshold, and the 900-bar
  measurement frame was always well past both the old and new threshold) and
  `docs/measure_rd_adx8_med20_cpu.py` (14/14 passed under the CPU-variant flags); updated the Gate D
  row and "Final suite run" section to the new counts.
- Restored `downloaded_files/dashboard.lock` (sandbox artifact, `git restore --source=HEAD --staged
  --worktree`) after each pytest run.

Target suite re-run after fixes: 1,704 passed, 7 skipped, 1 expected failure (Gate E owed) — one
more pass than round 1, from the new boundary test.

## Review round 2 — VERDICT: PASS

```
VERDICT: PASS
FINDINGS:
  - severity: NIT
    location: downloaded_files/dashboard.lock (git status, sandbox-only)
    problem:  Running the target pytest command in this review sandbox turns
      `downloaded_files/dashboard.lock` into a deleted entry in `git status --short`, same as round-1
      flagged. Before my own pytest run the working tree was clean; it only reappeared after I
      executed the test suite myself.
    fix:      No action needed — this is the same recurring sandbox artifact already diagnosed and
      restored by the session before commit. Confirms the round-1/round-2 diagnosis; not a
      regression.
SUMMARY: All four round-1 findings are genuinely fixed, not just narrated as fixed. CRITICAL:
`min_bars` is now `2 * adx_length + max(length, min_periods)` (=36); traced the actual warm-up chain
(`true_range` → `rma`'s `ewm(min_periods=length)` → double-RMA in `adx`) and confirmed ADX_8's first
non-NaN really lands at index 15 on a long series, so the true one-output floor is 35 bars and the
shipped 36 is deliberately one bar more conservative, matching `adxr.py`'s own `2 * length`
convention; `test_min_bars_boundary` correctly asserts `None` at n=27/35 and a non-null result at
n=36, and the full 14-item file passes. MAJOR: the mutant assertion is now strict `hits >
len(OFFSETS) // 2`, matching the sibling's house standard, and holds at the measured 5-of-9. MINOR:
`test_mutant_is_caught`'s docstring states the ratio directly. Ran the full target suite and got
exactly the expected 1704 passed / 7 skipped / 1 failed (the owed Gate E ledger row, by design).
Cross-checked counts for drift across `tests/test_altport2_ports.py`, `README.md`,
`docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md` — all internally consistent, no
accidental drift from the round-2 fix. `docs/RdAdx8Med20Measured.md` discloses the fix accurately
without overclaiming. Clean round — ship it.
```
