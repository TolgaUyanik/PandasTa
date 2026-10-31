# Task: CRSI port (issue #21)

## Implementation summary

Ported Connors RSI as `pandas_ta/momentum/crsi.py`, shipping three columns:
`CRSI_3_2_100` (composite), `CRSI_STREAK_2`, `CRSI_PCTRANK_100` (components). `RSI(close, 3)`
is computed internally but not shipped as its own column — it is exactly `ta.rsi(close, 3)`,
already available, so shipping it again would be a redundant column (CLAUDE.md's
non-redundant rule; also the issue's own guess). Wired all five touch points (module,
`momentum/__init__.py`, `Category`, `core.py` accessor, `tests/test_crsi.py`). Wrote
`docs/measure_crsi_proxy.py` and `docs/CrsiMeasured.md` with Gates A, B, D cleared, Gate C
synthetic-only, Gate E marked PENDING (run by issue-solver after this session, per the
system prompt's override). Updated README.md / IndicatorDictionary.md / MLCompanionContract.md
counts and `tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` (259 -> 260) to match.

Assumptions made without asking (AskUserQuestion unavailable this session; conservative
reading logged per the system prompt's override rule) — full detail in `00-manifest.md`:
1. Ship all three columns now, defer the ship/revert decision to the post-Gate-E receipt
   session, matching the `pfe`/`kalman_trend` precedent already in this repo.
2. Do not ship `RSI(close, 3)` as its own column (redundant with `rsi`).
3. `PercentRank` = Pine's `ta.percentrank` convention (ties excluded, previous `n` values).

Gate B's causality test needed two iterations: the first perturbation technique (splicing
in an unrelated random walk's tail, the `pfe`/`kalman_trend` precedent) proved flaky for a
sign-based mutation (measured well under 28/28 detections across several attempts) because
the two walks' relative level drifts unpredictably over a long path. Switched to shifting
the SAME series by a large additive constant in both directions, which closed the gap to
28/28 for both mutants. Documented in `docs/CrsiMeasured.md` and the test file.

## Review round 1

Dispatched Fletcher reviewer (`Explore`, read-only) against all new/modified files plus the
manifest. Full prompt and file list: see the Agent tool call in this session (not persisted
separately — reproduced in full below for the record).

```
VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: docs/CrsiMeasured.md:58 ("Shifting the SAME series by a huge constant...
      measured 9 to 24 hits out of 28... across several attempts")
    problem:  This figure is not reproducible by docs/measure_crsi_proxy.py or any other
      committed script, unlike every other number in the doc.
    fix:      Either delete the specific range and say "measured informally during
      development, not reproducible from a committed script" or add a throwaway script
      that regenerates it.
  - severity: MINOR
    location: tests/test_crsi.py:173-184 (`_leaks` docstring)
    problem:  The additive +/-1e6 perturbation has an undocumented blind spot: a
      look-ahead expressed as a difference/ratio between two points that both fall
      inside the shifted region is invariant to a constant shift and would go
      undetected.
    fix:      Add a sentence to the `_leaks` docstring flagging the blind spot.
SUMMARY: Clean, disciplined port -- every number in docs/CrsiMeasured.md and the test
docstrings was independently re-run and matched exactly, the full suite's failure count
reproduced bit-for-bit with the same three pre-existing failures, all five wiring touch
points are genuinely wired, the RSI(close,3)-is-redundant claim is literally true by
inspection, the scale-invariance claims are structurally guaranteed by the formula's
arithmetic, and every changed file sits inside the task's allowed scope with no creep.
The two findings are housekeeping, not defects in the shipped indicator.
```

## Fixes applied (both MINOR; PASS already met, applied anyway since trivial)

1. `docs/CrsiMeasured.md`: reworded the "9 to 24 hits" sentence to state plainly that it
   is an informal development observation, not a number any committed script reproduces.
2. `tests/test_crsi.py`: added a "Known blind spot" paragraph to `_leaks`'s docstring.

Re-ran `tests/test_crsi.py` after both edits: 14 passed, no change in behavior (doc/comment
only).

## Outcome

**PASS.** No re-review round needed (both findings were MINOR, already addressed).
