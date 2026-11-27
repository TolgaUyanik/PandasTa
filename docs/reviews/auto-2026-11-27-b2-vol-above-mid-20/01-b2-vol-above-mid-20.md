# Brutally Honest Review — B2-VOL-ABOVE-MID-20 (`b2_vol_above_mid_20`)

**Date:** 2026-11-27
**Target:** `pandas_ta/volume/b2_vol_above_mid_20.py`, `tests/test_b2_vol_above_mid_20.py`,
`docs/B2VolAboveMid20Measured.md`, `docs/measure_b2_vol_above_mid_20.py`,
`docs/measure_b2_vol_above_mid_20_cpu.py`, and the five wiring/doc touch
points (`pandas_ta/__init__.py`, `pandas_ta/core.py`,
`pandas_ta/volume/__init__.py`, `tests/test_altport2_ports.py`,
`README.md`, `docs/MLCompanionContract.md`, `docs/IndicatorDictionary.md`).
**Type:** code
**Verdict:** PASS

## Findings

None.

## Summary

The reviewer traced the Gate A fixture arithmetic by hand, cross-checked
against an independent oracle, and reran the measurement scripts directly —
the `2/3` fixture result, the 1,481/1,500 Gate C fire count with matching
min/max, the Gate D mismatch counts at every scale factor, the 0/36
real-module leak and 36/36 leak for both Gate B mutants, the module sha1,
and the 767-tagged/392-`SF` dictionary counts all reproduced bit-for-bit
against what is written in `docs/B2VolAboveMid20Measured.md`. Causality is
genuinely enforced (the `sliding_window_view` row aligns exactly with
`mid_tail`'s own index, reading only `[t-19, t]`), the strict `>` matches
the prototype's own `cw > mid[t]`, and both mutants are real forward-looking
leaks rather than cosmetic no-ops. The zero-volume-blanks vs.
flat-price-defined-zero distinction is both correctly implemented and
non-tautologically tested. Wiring, category alphabetization, and every
touched counter (README, dictionary, ML contract, `CATEGORY_TOTAL`/
`CATEGORY_BUCKETS`) check out self-consistently, and the full required test
command reproduces exactly "1,788 passed, 7 skipped, 1 failed", with the one
failure being the expected, out-of-scope Gate E ledger gap. PASS, round 1.
