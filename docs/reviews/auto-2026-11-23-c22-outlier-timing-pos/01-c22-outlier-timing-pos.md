# 01-c22-outlier-timing-pos.md

**Task:** port catch22's `DN_OutlierInclude_p_001_mdrmd` as `c22_outlier_timing_pos` (issue #143),
through Gates A-D, wiring, tests, and `docs/C22OutlierTimingPosMeasured.md`.

**Lane:** main thread (see `00-manifest.md` Phase 3 — no parallelizable scope).

## Implementation summary

- `pandas_ta/statistics/c22_outlier_timing_pos.py`: ported the feature from catch22's published
  one-line definition ("timing of extreme events above the mean") and the hctsa family's naming
  convention, never from the GPL-3.0 reference (not installed in this environment). Implemented
  as a closed-form weighted median over the swept 0.01-step z-score threshold grid.
- Performance: the first closed-form pass (full re-sort of the running included-set per threshold
  level) measured 4.5 s/column on a 1,500-bar frame — too slow for Gate B's repeated
  recomputation. Rewrote the hot loop to maintain the running included-positions list and its
  sorted gap list incrementally via `bisect`, reaching 0.37 s/column (12x), then RE-RAN Gate A's
  brute-force-oracle check to confirm the rewrite changed no output (768/768 exact agreement,
  same as before the rewrite).
- Wired all five touch points: `pandas_ta/statistics/__init__.py`, `pandas_ta/__init__.py`
  (`Category["statistics"]`), `pandas_ta/core.py` (accessor), the module itself, the test module.
- `tests/test_c22_outlier_timing_pos.py`: 100 tests — brute-force oracle (Gate A), future-splice +
  mutant causality with multi-splice-per-offset detection (Gate B), reachability (Gate C),
  scale-free + length-guard + bad-input edge cases (Gate D), wiring, dictionary-row checks.
- `docs/measure_c22_outlier_timing_pos.py` / `_cpu.py`: measurement harness and CPU-restricted
  rerun wrapper, mirroring this fork's other catch22 ports.
- Doc/count updates: `README.md` (389 registered / 77 statistics / 397 accessor),
  `docs/MLCompanionContract.md` (734 tagged / 368 `SF`), `docs/IndicatorDictionary.md`
  (regenerated), `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 388 -> 389). Numbers
  updated post-review to the rebase onto `dev`'s state (which had landed
  `c22_outlier_timing_neg` and `tdi` in the meantime).
- `docs/C22OutlierTimingPosMeasured.md`: full receipt, Gate E marked pending per the issue-solver
  rules (the launcher runs Gate E; this session never touches `../Backtesting`).

## Review round 1

**Verdict: PASS**

```
VERDICT: PASS
FINDINGS:
  - severity: NIT
    location: pandas_ta/statistics/c22_outlier_timing_pos.py:323 (and docs/C22OutlierTimingPosMeasured.md header row, column 2)
    problem:  The docstring and the receipt both claim the column's range is "a gap fraction in (0, 1]". It isn't. A gap between two distinct integer time positions in a `length`-bar window is at most `length-1`, so the output is bounded above by `(length-1)/length`, strictly less than 1, for every `length >= 2`.
    fix:      State the true bound: `(0, 1)` if you want to stay loose, or `(0, (length-1)/length]` if you want to be exact, in both the module docstring's Returns line and the Measured.md header row.
SUMMARY: I went looking for the bug everyone insisted had to be hiding in a bisect-maintained
sorted list with three insertion branches, and I didn't find one -- I hand-traced the six-point
example through all three branches, got 0.5, matched the code, matched the oracle, then
independently re-ran the actual measurement harness myself (not trusted it) and reproduced every
single number in the receipt -- 768/768 Gate A agreement, the 0.19/0.1392 bursty figures, the
24-56 distinct-value Gate C table, the 0/43 and 12/43 Gate B splice counts, the student-t
1,183-NaN-mask artifact, and the exact 243-passed/8-skipped and 1-failed/1,250-passed Gate F
counts -- bit for bit. The weight formula's clip-then-ceil ordering is the one place I expected a
boundary bug and it turns out to be an exact identity (ceil commutes with max), the
tied-order-statistic zero-weight handling is provably inert, and the three disclosed
interpretive choices are argued honestly rather than oversold -- including correctly identifying
that Gate A here is self-consistency against a brute-force oracle, not validation against the
GPL reference it cannot run. The wiring diff is clean and alphabetically placed, the five counts
move together consistently across every file that has to agree, and I could not manufacture a
single scenario where the bisect incremental maintenance diverges from a from-scratch resort.
That was acceptable. Barely.
```

**Applied:** fixed the NIT in both files (exact bound `(0, (length - 1) / length]`, spelled out as
`(0, 0.99]` at the default length in the receipt). Re-ran the targeted test subset after the fix:
243 passed, 8 skipped (unchanged).

PASS on round 1 with no CRITICAL/MAJOR findings and the NIT already fixed: per the user's
"Review loop" override (stop early on PASS), no further rounds.
