# Task RD-DIP-DEPTH-10-25 — log

## Implementation (main thread)

Ported `rd_dip_depth_10_25` directly from the issue's own restated formula (not the screen
prototype, per the issue's own Gate A instruction): `numerator = HHV(high, length) - close`,
`denominator = SMA(high, avg_length) - SMA(low, avg_length)`, `RD_DIP_DEPTH_10_25 = numerator /
denominator`, with `+-inf` from a zero denominator replaced by `NaN` — the same guard
`rd_range_contraction` and `rd_std_ratio_20_60` use. Category: momentum (the poster's own claimed
use is an oversold mean-reversion entry, and the issue's own prototype measurement puts the nearest
comparators in momentum: `kdj_J_9_3`, `willr`). Files:

- `pandas_ta/momentum/rd_dip_depth_10_25.py` (new)
- `tests/test_rd_dip_depth_10_25.py` (new, 20 tests)
- `docs/RdDipDepth1025Measured.md` (new, the receipt)
- `docs/measure_rd_dip_depth_10_25.py`, `docs/measure_rd_dip_depth_10_25_cpu.py` (new, reproduce
  the measured numbers; the CPU-variant one runs the suite with
  `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512_SKX AVX2 FMA3"` set before numpy import)
- Wiring: `pandas_ta/momentum/__init__.py`, `pandas_ta/__init__.py` (`Category["momentum"]`,
  alphabetically between `qqe` and `roc`), `pandas_ta/core.py` (accessor)
- Doc/count bookkeeping: `README.md`, `docs/IndicatorDictionary.md` (regenerated via
  `python docs/gen_indicator_dictionary.py`), `docs/MLCompanionContract.md`,
  `tests/test_altport2_ports.py` (`CATEGORY_TOTAL` 415 → 416; `CATEGORY_BUCKETS` unchanged —
  momentum is not one of the three buckets tracked there)

Measured before any review (`python docs/measure_rd_dip_depth_10_25.py`): Gate A independent
sliding-window-view recompute matches on 376/376 compared bars (max|diff| 9.68e-13), hand-derived
fixture bars 3 and 6 match to 6 decimals; Gate B 0/25 real leaks, 25/25 mutant leaks; Gate C
1,176/1,200 fires (24-bar warm-up), range [0.000155, 27.656715], 10/10 independent seeds consistent;
Gate D x8/x64 bit-identical (0 mismatches), x10/x3.7 within ~2.5e-12. Target suite: 1,726 passed, 7
skipped, 1 expected failure (`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
— Gate E owed).

## Review round 1 — VERDICT: PASS

```
VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: pandas_ta/momentum/rd_dip_depth_10_25.py (module docstring) and docs/RdDipDepth1025Measured.md "Decisions" §6
    problem: The port's own prototype Gate E screen (quoted verbatim in the module docstring and in docs/issues/180-rd-dip-depth-10-25.md) puts this candidate's nearest comparators at `kdj_J_9_3` (0.8401, DISCLOSE_GAP) and `willr` (0.8241) — and `willr`'s own formula, `100*(close-HH)/(HH-LL)`, is algebraically the same numerator shape as this port's `(HHV(high,length)-close)`, differing only in the denominator (a same-window HH-LL vs. a separately-averaged high/low range). That is a materially closer structural kinship than `rd_std_ratio_20_60` had to `BB_BWidth_Pctl`/`CHOP` (0.8274), and `rd_std_ratio_20_60`'s module docstring addresses it head-on with an explicit "NON-REDUNDANCY" paragraph naming the comparators and arguing why DISCLOSE_GAP, not STRUCK, is the right read. This port — modeled closely on that very file — has no equivalent paragraph; it only drops a one-line aside under "Category" decision #6 that the nearest comparators happen to be momentum columns, without ever naming `willr`'s formula or arguing why the two aren't the same feature.
    fix: Add a "NON-REDUNDANCY" paragraph to the module docstring (and mirror it in docs/RdDipDepth1025Measured.md), explicitly naming `kdj_J_9_3` and `willr` as the two already-shipped comparators, stating `willr`'s formula side-by-side with this one, and arguing the denominator difference (same-window HH-LL vs. a longer separately-averaged range) as the reason the measured 0.8401/0.8241 sits in DISCLOSE_GAP rather than STRUCK — the same shape `rd_std_ratio_20_60` uses for its own borderline comparator.
SUMMARY: Every number in the receipt reproduces exactly from the committed measurement scripts, Gates A/B/C/D are each correct and causally argued line-by-line against the issue's own rearranged inequality (verified against the actual prototype source and the actual issue text, not just the module's claims), the hand-derived fixture and warm-up arithmetic check out bit-for-bit by hand, the mutant test's target string is unique and genuinely tests causality rather than something cosmetic, every one of the five wiring touch points is correctly and alphabetically wired with no broken concatenation, and the required test command reproduces the exact claimed 1,726 passed / 7 skipped / 1 failed with the sole failure being exactly the expected (and explicitly out-of-scope) ledger test. The only thing worth a mark against this port is that it borrowed `rd_std_ratio_20_60`'s shape everywhere except the one place that shape mattered most — disclosing, by name, why a borderline comparator correlation isn't a redundant restatement — which it should have done here too given `willr`'s near-identical numerator. Ship it, but go write that paragraph before you call it done.
```

## Fixes applied (main thread, even though the verdict was already PASS)

- `pandas_ta/momentum/rd_dip_depth_10_25.py`: added a "NON-REDUNDANCY" paragraph to the module
  docstring naming `kdj_J_9_3` (0.8401) and `willr` (0.8241) as the issue's own prototype screen's
  nearest comparators, stating `willr`'s formula side-by-side (`100*(close-HHV(high,n))/(HHV(high,n)-LLV(low,n))`)
  and arguing the denominator difference (same-window HH-LL vs. this port's separately-averaged
  25-bar mean-high-minus-mean-low) as the reason DISCLOSE_GAP, not STRUCK, is the right read.
- `docs/RdDipDepth1025Measured.md`: mirrored the same paragraph under Gate E.
- Re-ran the target suite and `docs/measure_rd_dip_depth_10_25.py` after the docstring edit: same
  1,726 passed / 7 skipped / 1 expected failure, and the same nine measured Gate A-D numbers
  (the edit only touched a docstring, not the computed arithmetic).

## Outcome

PASS (round 1, with one MINOR applied voluntarily rather than left outstanding).
