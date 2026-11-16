# Brutally Honest Review — bos-causal

**Date:** 2026-11-16
**Target:** README.md (task list said "EADME.md", a typo), docs/IndicatorDictionary.md, docs/MLCompanionContract.md, pandas_ta/__init__.py, pandas_ta/core.py, pandas_ta/trend/__init__.py, tests/test_altport2_ports.py, docs/BosCausalMeasured.md, docs/measure_bos_causal.py, pandas_ta/trend/bos_causal.py, tests/test_bos_causal.py
**Type:** code (dominant) plus receipt text
**Verdict:** REVISE

## Findings

### MAJOR
- **Whole change vs the ask** (`pandas_ta/trend/bos.py`, `pandas_ta/trend/choch.py`, `tests/test_bos_lookahead.py`, `CLAUDE.md` ~127-131, `docs/indicators/`) — Issue #332 is "a bug fix to shipped modules, not a new indicator", with output names unchanged and values changed. The author added a seventh indicator `bos_causal` with new `BOSC_*` names. `bos` and `choch` still read 1 to 4 bars ahead. The look-ahead test is not deleted. `CLAUDE.md` still lists `bos` as OPEN and does not record that `choch` had the same defect. There is no `docs/indicators/bos_causal.md`. The category total, README counts and dictionary counts rose by one, which the issue never asked for. The issue's done-when allows only "ship through Gates A-F" or "measure and revert"; this is neither. The mutant test targets `bos_causal`; the centred `bos`/`choch` are only probed, not replaced.
  - Fix: Rewrite `bos.py` and `choch.py` to use the causal swing confirmation, keeping their column names. Remove `bos_causal` from `Category`, `core.py`, `trend/__init__.py`, the README counts, `CATEGORY_TOTAL` and the dictionary. Alternatively, if a new indicator is a deliberate call, get the owner's explicit sign-off first; then still delete or repoint `tests/test_bos_lookahead.py`, update `CLAUDE.md`, regenerate `docs/indicators/`, and fix the receipt wording.

- **docs/BosCausalMeasured.md, "Overlap on synthetic frames"** — The criterion is that every receipt number is reproducible by `docs/measure_bos_causal.py`. The script reproduces the Gate C counts, the 3,743 tie bars, the Gate D results and the reach table. It does not print the Spearman medians (0.7361, 0.7249, 0.7020, 0.6903, -0.0695, -0.0699) or the "0 mismatches over 16 frames" `SWINGEQ_BOS_*_2_2` rising-edge claim, and it does not exercise Gate A or the mutant. The receipt itself admits those numbers come from an earlier analysis, so they are unbacked claims in a shipped receipt.
  - Fix: Add the Spearman computation and the SWINGEQ rising-edge check to `measure_bos_causal.py`, or delete those two sentences from the receipt. Point the Gate A and mutant lines at `pytest tests/test_bos_causal.py` explicitly.

### MINOR / NIT
- **docs/BosCausalMeasured.md Gate B table; tests/test_bos_causal.py docstring** (MINOR) — The `choch` reach of 1/2/1/1 is non-monotone in L and the receipt admits it is a lower bound. The test asserts only `> 0` for `choch` and uses 300 probes, which is slow (the reviewer's run of the suite took about 42s).
  - Fix: State the `choch` figure only as "at least N". Cut the probe count, or probe at event-dense positions.
- **pandas_ta/trend/bos_causal.py:26, `_confirm`** (NIT) — `_confirm` returns `(out, k)` and the low side discards `k` with `sl, _`.
  - Fix: Return only `out` and compute `k` once in `bos_causal`.

## Summary

The reviewer found the code correct and faithful to the issue's formula: ties, NaN and warm-up are handled right, the wiring and counts are consistent, and the mutant back-dates the write index and is proved live. The reviewer ran `tests/test_bos_causal.py`, `tests/test_readme_counts.py` and `tests/test_bos_lookahead.py` (36 passed), and the script's printed counts match the receipt. But the change does not do what was asked: it adds a parallel indicator and leaves the defective `bos` and `choch` shipping, with `CLAUDE.md` still calling `bos` OPEN. The receipt also contains numbers its own script cannot reproduce. An in-place fix, or an owner-approved new-indicator route with the cleanup done, is the minimum to pass.

Skipped by the reviewer: it read `README.md` only through the diff, did not check `docs/indicators/` content, and did not run the full suite or Gate E.
