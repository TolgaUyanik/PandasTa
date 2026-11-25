# Task: port `kats_stability_100` as `stability` (issue #158)

Lane: main thread. Round 1 of at most 3.

## Implementation summary

New module `pandas_ta/statistics/stability.py` built on the shape of the near-identical
sibling port `pandas_ta/statistics/lumpiness.py` (issue #156, same Kats tsfeatures family,
same z-score, same `array_split` tiling, same `NOISE_ULPS` rounding guard), reducing each
tile to its MEAN (`stability`) instead of its VARIANCE (`lumpiness`). Wired at all five
touch points (module, `pandas_ta/statistics/__init__.py` export, `Category["statistics"]`,
`df.ta.stability()` accessor, `tests/test_stability.py`). 29 tests cover Gates A/B/C/D, a
semantics check (block-regime drift reads higher than iid), the rounding guard, edge
cases and wiring. Measurement scripts `docs/measure_stability.py` /
`docs/measure_stability_cpu.py` reproduce every number in the receipt
`docs/StabilityMeasured.md`, which marks Gate E pending (launcher runs it) and Gate F as
this session's own partial command (no whole-suite run), per the task's override rules.
Counters bumped: `tests/test_altport2_ports.py` `CATEGORY_TOTAL` 383 → 384,
`docs/MLCompanionContract.md` 728 → 729 / 362 → 363 `SF`, `docs/IndicatorDictionary.md`
regenerated, `README.md` counts and statistics list.

Verification run (the task's own named command plus `tests/test_stability.py`):

```
python -m pytest -q tests/test_stability.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

1 failed, 1479 passed, 7 skipped — the 1 failure is the expected owed
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` row for
`stability`, per the task text.

CPU-feature variant (`python docs/measure_stability_cpu.py`,
`AVX512F AVX512_SKX AVX2 FMA3` disabled): 29 passed.

## Assumptions

- No kats/tsfeatures source line number or commit hash is cited in `stability.py`'s
  docstring, since this session has no network access to verify one (the issue's own text
  gives only the one-line formula). `arch_lm.py`'s docstring follows the same convention
  for Kats-side attribution (formula only, no fabricated citation); `lumpiness.py`'s
  docstring does cite a line/commit, presumably from a session that had network access —
  not reproduced here since it cannot be verified.
- Semantics test (`test_a_block_regime_reads_higher_than_iid`) and its companion
  measurement use a block-regime generator (iid returns plus a mean that flips sign every
  20 bars) designed for this task, rather than reusing `lumpiness`'s GARCH/iid generators,
  since `stability` (variance of tile MEANS) and `lumpiness` (variance of tile VARIANCES)
  are sensitive to different structure — a volatility-clustering generator exercises
  `lumpiness`'s semantics, not `stability`'s.

## Review round 1

```
VERDICT: PASS
FINDINGS:
  (none)
SUMMARY: This is a clean, disciplined port. The math is right — hand-verified the closed-form test (10 returns of +1% then 10 of -1%, length 20, population-std z-score gives exactly ±1, VAR([1,-1])=1.0) and confirmed stability.py's z-score/tiling/guard logic is a faithful, line-matching derivation of the prototype's `_z`/`_tiles`/`roll`/`ret` semantics, differing from lumpiness.py only in reducing each tile to its mean instead of its variance, exactly as claimed. Ran docs/measure_stability.py myself: every number in StabilityMeasured.md (Gate A bit-identical across 20 frame×length cases, the guard table's fire counts/medians, the x10/x3.7 max abs diffs of 5.551e-16/5.274e-16, the semantics medians, the cost table) reproduced exactly. Ran the CPU-feature variant script: 29 passed as claimed. Ran the exact 7-module-plus-test_stability.py verification command from the task text: 1 failed, 1479 passed, 7 skipped, and confirmed by reading the failure's assertion message that the single failure is precisely the expected owed `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` row for `stability` — nothing else broke. The mutant test's off-by-one (`lo = length + start` vs `length - 1 + start`) is a genuine look-ahead bug class and the mutant-target string is unique in the file. The docstring correctly declines to cite a specific Kats line number or commit (unlike lumpiness.py's, since this session had no network access to verify one) and every "identical/every/all" claim traces to a measured number or a shared, previously-pinned test. Wiring is complete and alphabetically placed at all five touch points; scope is exactly one new pandas_ta file (stability.py), no existing helper module (lumpiness.py included) was touched, and every changed/added file falls inside the author's permitted scope list. README/IndicatorDictionary/MLCompanionContract counters all increment consistently and correctly. Nothing to fix.
```

Status: **PASS** on round 1. Marked done.
