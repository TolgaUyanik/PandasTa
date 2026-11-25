# Brutally Honest Review — c22-median-freq (issue #138 port)

**Date:** 2026-11-22
**Target:** README.md, docs/IndicatorDictionary.md, docs/MLCompanionContract.md, pandas_ta/__init__.py, pandas_ta/core.py, pandas_ta/statistics/__init__.py, tests/test_altport2_ports.py, docs/C22MedianFreqMeasured.md, docs/measure_c22_median_freq.py, pandas_ta/statistics/c22_median_freq.py, tests/test_c22_median_freq.py
**Type:** code (with a text receipt)
**Verdict:** PASS

Reviewer: fresh read-only `Explore` subagent (Mode A). It did not run Python or pytest; numbers were checked for consistency across receipt, script and tests, not re-executed.

## Findings

### MINOR / NIT
- **MINOR — pandas_ta/statistics/c22_median_freq.py:206-208** (docstring "NaN ... on every window holding a close that is NaN, infinite, zero, negative or subnormal; on a window holding a close PAIR whose ratio overflows") — This "every" claim has no test and no measure-script section behind it. The only bad-data test is the mask mutant, which injects a single NaN; nothing checks that the real module blanks the right windows for a zero, negative, inf or 1e-310 close, or for a ratio overflow (1e300 next to 1e-300). The code path looks right on reading, but CLAUDE.md requires every sentence with "every" to correspond to a run. c22_mode_10 has the same gap: precedent, not an excuse.
  - Fix: Add a parametrized test over {np.nan, np.inf, 0.0, -1.0, 1e-310} written at bar j of `walk`. Assert that bars j..j+LENGTH-1 (j+LENGTH when the close is bar j's) are NaN and that bars j-1 and j+LENGTH+1 fire. Add one case with c[j]=1e300, c[j-1]=1e-300 for the overflow limb.
- **MINOR — pandas_ta/statistics/c22_median_freq.py:167-172; docs/C22MedianFreqMeasured.md:42-48** — "Two choices the definition does not pin" leaves out a third. A one-sided PSD (the Welch convention catch22's sibling `SP_Summaries_welch_rect_*` uses) doubles bins 1..NFFT/2-1 but not DC or Nyquist. That is not "a constant normalisation", so it can move the 50% crossing when the Nyquist bin carries a lot of power. The oracle uses the same no-doubling convention, so Gate A cannot see the difference, and nothing measures how many windows it would decide.
  - Fix: Name the convention ("no one-sided doubling; doubling interior bins would reweight Nyquist ×½"). Add a §A4 to docs/measure_c22_median_freq.py that recomputes the 1,200 sampled windows with interior bins doubled and prints how many outputs move, and put that count in the receipt.
- **MINOR — pandas_ta/statistics/c22_median_freq.py:18-22** (MIN_LENGTH comment) — The reason given is wrong. "Below 8 the zero-padded spectrum has at most 5 frequency bins" is also true AT 8: lengths 5-8 all get NFFT = 8 and the same 5 bins. 8 is not where the bin count changes.
  - Fix: Rewrite it as "8 = the smallest length that fills NFFT = 8 without padding; a module choice", or raise MIN_LENGTH to 9 if NFFT ≥ 16 was the intent. Update test_the_length_guard_band to match.
- **MINOR — docs/C22MedianFreqMeasured.md:186-206 (§E1), :18 (Gate F row)** — Three separate problems:
  - The §E4 owed rule is deferred to "the 89-frame Gate E run", but nothing shows `C22PERIODICITY_100` is in the 687-comparator set, so that pairing may never be measured.
  - §E4 names the issue as #137 and this receipt calls it #138, with no note that they are the same issue.
  - Gate F records only a targeted run, while "Done when" requires both repos' full suites green.
  - Fix: List the §E4 pairing as an owed measurement with the exact command or comparator addition that will produce it. Note "issue #137 in the local tracker = GitHub #138". Add the full `python -m pytest -q` result to §F before merge.
- **NIT — c22_median_freq.py:141,221 vs receipt:9 / test_every_output_is_on_the_frequency_grid** — The docstring says the output is on [0, π] and takes "65 levels". The test asserts v > 0 and the receipt says (0, π]. After demeaning, k = 0 never wins, so only 64 levels are reachable.
  - Fix: "(0, π], one of the NFFT/2 = 64 nonzero grid levels".
- **NIT — c22_median_freq.py:169; receipt:43** — POWER is justified by "the feature's name". `SP_Summaries_fft_wq_50` does not say power; "half the return power" is the issue title's paraphrase.
  - Fix: Cite it as issue #138's definition.
- **NIT — receipt:141-142** — "The cosine frame is constant by construction" overclaims: a zero-padded, phase-shifted cosine leaks into the bins differently at each phase. The value is constant because it was measured that way.
  - Fix: "measured constant (1 distinct value on 1,400 bars, pinned by test_a_period_20_cosine_reads_near_its_own_frequency)".
- **NIT — receipt:22-23** — The environment line (library versions) is not printed by the measure script.
  - Fix: Print `np.__version__`, `pd.__version__`, `scipy.__version__` and `sys.version` next to the peak-memory line.
- **NIT — tests/test_c22_median_freq.py:271** — `"catch22" in s.replace("c22", "")` is a no-op replace, because "catch22" contains no "c22".
  - Fix: `"catch22" in s or "hctsa" in s`.

## Summary

This is a clean port. All five wiring touch points are present and consistent: module, statistics `__init__`, `Category`, a core.py accessor that forwards `length`/`offset`/kwargs under the right names, and the test file. README (368/376, statistics 66), `CATEGORY_TOTAL` 368, the regenerated dictionary row and the MLCompanionContract edit all agree, and 137+348+104+58+43+2+21 = 713 checks out. Gate A has a real FFT-free oracle with exact agreement, guarded by a margin assertion. The Gate B mutants are not vacuous: the chunk-wide ones rely on the one-chunk claim, and 2^19/128 = 4096 rows ≥ 1,400. Gate D covers ×8/×64/×2^±40 bit-identical, ×10/×3.7 price with NaN-mask matching at tolerance, a ×10/×3.7/×0.1 return rescale, and 0 < fires < n. The receipt's numbers trace to the script's prints: 1,200 = 200 × 6, 43 offsets = range(130,1400,30), 114 tests matches the parametrization, and the D2 student-t artifact is printed explicitly. What remains is smaller: one untested "every" bad-data claim, an undisclosed one-sided-doubling convention that the shared-convention oracle cannot catch, a false MIN_LENGTH rationale, and an §E4 owed measurement with no stated path to being run. None ships a bug, so this passes, but fix the four MINORs before the receipt is final.
