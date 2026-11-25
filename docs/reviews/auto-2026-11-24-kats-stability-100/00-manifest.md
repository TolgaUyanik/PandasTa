# Manifest — KATS-STABILITY-100 (issue #158)

## Task

> KATS-STABILITY-100: port the indicator of issue #158 through Gates A-D, the wiring, the
> tests and docs/<Name>Measured.md, per the issue and the rules in your system prompt
> (stability: variance of tile means of z-scored returns (100). Source: Kats tsfeatures
> (Meta, MIT) — `get_stability: var([mean(tile) for tile in array_split(x, n//20 + 1)])`.).
> Gate E and the whole suites are run by the launcher afterwards. You and every subagent
> verify with `python -m pytest -q <the port's test modules> tests/test_readme_counts.py
> tests/test_altport2_ports.py tests/test_wiring_accessors.py tests/test_ml_companions.py
> tests/test_gate_e_ledger.py tests/test_pine_coverage_csv.py
> tests/test_prose_counts_match_the_csvs.py` plus any PandasTa test module a finding names,
> never the whole suite (the launcher runs it). Until the launcher's Gate E run and the
> receipt record this port's ledger row, `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
> fails: expected, not a finding.

Run folder: `docs/reviews/auto-2026-11-24-kats-stability-100/`.

## Phase 2 — clarify

None needed. The issue text is self-contained and a near-identical sibling port
(`lumpiness`, issue #156, `pandas_ta/statistics/lumpiness.py`) already exists in the repo
as a working template for the same Kats tsfeatures family (z-scored window, Kats
`array_split` tiling, same NOISE_ULPS rounding guard) — the only formula difference is
reducing each tile to its mean (`stability`) instead of its variance (`lumpiness`).

## Phase 3 — execution map

Single task, main thread (no parallel lane needed — one indicator, one module, scope
entirely within the five wiring touch points plus docs).

| task | lane | why |
|---|---|---|
| port `kats_stability_100` as `stability` (statistics) | main thread | single indicator, sequential wiring edits, no independent sub-scopes |

## What was done

1. New module `pandas_ta/statistics/stability.py`: `stability(close, length=None, offset=None, **kwargs)`,
   column `STABILITY_{length}`, built on `lumpiness.py`'s shape (same z-score, same
   `_tiles` Kats `array_split`, same `NOISE_ULPS` rounding guard), reducing each tile to
   its mean instead of its variance.
2. Wiring: `pandas_ta/statistics/__init__.py` export, `pandas_ta/__init__.py` `Category["statistics"]`
   entry (alphabetical, after `skew`), `pandas_ta/core.py` `df.ta.stability()` accessor
   (alphabetical, after `skew`, before `stdev`).
3. Tests: `tests/test_stability.py` (29 tests) — Gate A (Kats-verbatim oracle +
   closed-form), Gate B (future-perturbation + mutant), Gate C (fires/not-constant), Gate D
   (×8/×64 bit-identical, ×10/×3.7 tolerance), a semantics test (block-regime drift reads
   higher than iid), the rounding guard, edge cases, and wiring.
4. `docs/measure_stability.py` and `docs/measure_stability_cpu.py`: reproduce the measured
   numbers, and run the test module with the CI CPU-feature set (`AVX512F AVX512_SKX AVX2
   FMA3` disabled) disabled before numpy import.
5. `docs/StabilityMeasured.md`: the receipt, with Gate E marked pending (per this
   session's override rules — the launcher runs Gate E) and Gate F limited to this
   session's own test command (no whole-suite run).
6. Counters: `tests/test_altport2_ports.py` `CATEGORY_TOTAL` 383 → 384;
   `docs/MLCompanionContract.md` 728 → 729 tagged / 362 → 363 `SF`;
   `docs/IndicatorDictionary.md` regenerated; `README.md` counts and statistics list.

## Verification run

```
python -m pytest -q tests/test_stability.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

Result: 1 failed, 1479 passed, 7 skipped. The 1 failure is
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` on the owed
`stability` row — expected per the task's own text, not a finding.

Also ran the CPU-feature variant (`python docs/measure_stability_cpu.py`,
`AVX512F AVX512_SKX AVX2 FMA3` disabled): 29 passed.
