# Brutally Honest Review — vwd port (issue #202)

**Date:** 2026-11-25
**Target:** README.md, docs/IndicatorDictionary.md, docs/MLCompanionContract.md, pandas_ta/__init__.py, pandas_ta/core.py, pandas_ta/momentum/__init__.py, tests/test_altport2_ports.py, docs/VwdMeasured.md, docs/measure_vwd.py, pandas_ta/momentum/vwd.py, tests/test_vwd.py
**Type:** code (with text: receipt and docstrings)
**Verdict:** REVISE

## Findings

### MAJOR
- **docs/VwdMeasured.md:126, docs/measure_vwd.py:249, tests/test_vwd.py:41** — Three files quote "1.930e-14 and 2.359e-16" as the uniform-rescale first-catch moves for the `vp-lead` and `vs-lead` mutants. No section of `measure_vwd.py` prints either number. The receipt admits the run is "not reproduced", yet its header says "Every number below is printed by `python docs/measure_vwd.py`", and these two are not among its three named exceptions. That breaks the acceptance criterion and the CLAUDE.md rule against unmeasured claims. The comment at `measure_vwd.py:249` says "(measured ...)" for a run the script does not contain. The pinning test `test_a_uniform_suffix_rescale_cannot_see_a_vp_lead` checks only `vp-lead`, so the `vs-lead` half of the claim has no check at all.
  - Fix: Add a section `B1U` to `measure_vwd.py`. It should apply a uniform ×1.03 suffix at `OFFSETS[0]` to the `vp-lead` and `vs-lead` mutants on `SWEPT` and print `_abs(prefix, perturbed prefix)`. Quote its output in all three places, or delete the numbers everywhere and keep only "< 1e-9". Parametrize the test over `CAUSALITY_MUTANTS[3]` and `[4]` so `vs-lead` is checked as well.

### MINOR / NIT
- **MINOR — pandas_ta/momentum/vwd.py:64 (and the oracles in tests/test_vwd.py:220 and docs/measure_vwd.py:165)** — `rng.where(rng > 0.0)` blanks bars where H < L as well as H == L. The source formula is finite there. The docstring, receipt and module comment all say "blank if H == L", so this is an undisclosed deviation. The oracle uses the same `> 0.0` gate, so Gate A cannot see it.
  - Fix: Either use `!= 0.0` in both the module and the oracle, as the source computes, or keep `> 0` and write "blank where H <= L (H < L is corrupt data)". In both cases add a test with one H < L bar that pins the chosen behaviour.
- **MINOR — docs/VwdMeasured.md:169-174 (§C3)** — The receipt says the gap between n = 383,681 and an "ideal" 397,692 is "consistent with §C2's H == L blanking". That n is Gate E's pairwise sample against `Dist_to_Nearest_Fib_pct`, so the attribution is unsupported. The figure 397,692 is also hand arithmetic, not script output and not a named exception.
  - Fix: Delete the attribution sentence and the 397,692 figure, or say plainly that n is the pairwise count and cannot be read as VWD's fire count.
- **NIT — pandas_ta/momentum/vwd.py:56-60, 108-111; docs/VwdMeasured.md "Choices made"** — The docstring says the literal form "differs only where V == 0". It also differs where V is NaN, and that case is neither disclosed nor measured.
  - Fix: Change the text to "where V == 0 or V is NaN" and extend §A4 and `test_volume_cancels_except_where_it_is_zero` with a NaN-volume bar.
- **NIT — docs/measure_vwd.py:173 vs tests/test_vwd.py:228** — The two "same" oracles differ: the script has a redundant `or math.isnan(vp[i])`.
  - Fix: Delete that clause so the two oracles match token for token.
- **NIT — docs/VwdMeasured.md:221** — The "0.85 equivalence line" is defined neither in CLAUDE.md nor in the issue.
  - Fix: Cite the issue's 0.90 restatement line, or the CLAUDE.md Gate E bands.

## Summary

The maths is right and checked. The reviewer re-ran `measure_vwd.py`, and every figure in A1–D4 and in L matches the receipt to the printed digit. The five touch points are wired. The core.py accessor has no parameters it could forward wrong. README, the dictionary, MLCompanionContract and `CATEGORY_TOTAL` agree with the package. The mutant, scale and reachability tests are real and pass.

The port fails review on its own discipline rule: two numbers (1.930e-14 / 2.359e-16) are presented in three files as measurements, and no run in the tree produces them, under a receipt header that promises every number is reproducible. The test that is meant to stand in for them checks only half of the claim. Below that are an undisclosed H < L blanking that the oracle shares and so cannot catch, and a speculative real-data gap attribution in §C3.

Not counted as a finding: `test_the_category_count_moved_by_exactly_three` fails (393 vs 396) when `tests/test_wiring_accessors.py` runs before it. This is the known pre-existing bug where `df.ta.strategy("<category>")` mutates `Category` in place (`pandas_ta/core.py:690-692`), and it is out of scope for this issue.
