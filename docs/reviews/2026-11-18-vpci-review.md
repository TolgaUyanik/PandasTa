# Brutally Honest Review — vpci port (issue #264)

**Date:** 2026-11-18
**Target:** README.md, docs/IndicatorDictionary.md, docs/MLCompanionContract.md, pandas_ta/__init__.py, pandas_ta/core.py, pandas_ta/volume/__init__.py, tests/test_altport2_ports.py, docs/VpciMeasured.md, docs/measure_vpci.py, pandas_ta/volume/vpci.py, tests/test_vpci.py
**Type:** code (plus text/analysis for the receipt)
**Verdict:** PASS

## Findings

### MINOR / NIT
- **MINOR — tests/test_vpci.py:26 (module docstring, CORRECTNESS bullet)** — The docstring says "three bars against a plain-numpy per-bar loop (`|diff|` 1.6e-16 / 0 / 0 there)". The test checks bars 300 / 600 / 899 of the 900-bar frame. Those three diffs come from the script's bars 300 / 900 / 1499 on the 1,500-bar frame. No run measured the test's bars 600 and 899, but the sentence reads as if the numbers belong to the test's own three bars.
  - Fix: Name the frame and bars: "(`docs/measure_vpci.py`, bars 300 / 900 / 1499 of 1,500: `|diff|` 1.6e-16 / 0 / 0)". Or change the test's bars to (300, 900, 1499) on a 1,500-bar `_frame(1500)` so the numbers belong to it.
- **MINOR — tests/test_vpci.py:33-35 (ZERO VOLUME bullet)** — The docstring says "Five zero bars at 700..704 **of the script's frame** blank exactly 1 bar". `test_all_zero_short_volume_window_is_nan_not_inf` runs on `_frame(1000)`. That is a different frame: volume is drawn after the n close values, so the volume path differs from the 1,500-bar one. The result is `[704]` on both frames (the test passes and the script prints `1 newly-NaN bars 704..704`), but the docstring cites the wrong frame.
  - Fix: Change it to "on a 1,000-bar frame here, and on the script's 1,500-bar frame".
- **MINOR — tests/test_vpci.py:27-29 (SCALE-FREE bullet)** — "measured max `|diff|` 6.91e-16" has no frame attached. The value is the script's 1,500-bar ×3.7 "both" case. The 900-bar frames in this file were never measured, and the tests only assert `< 1e-12`.
  - Fix: Add "(×3.7 both, on the script's 1,500-bar frame)" after the number.
- **MINOR — docs/VpciMeasured.md:52** — "Exact ties do not land on exactly 0" is a universal claim, and the receipt's own Gate A row disproves it. Bar 2 of the hand-derived example is an exact tie, and the script prints exactly `0.0` there.
  - Fix: Reword to "Exact ties need not land on exactly 0: with constant volume over a 30-bar slice …". Keep the measured 1.38e-16 / 11-bar figures.
- **NIT — pandas_ta/volume/vpci.py:47-54** — The "No `inf` can arise" argument covers only volume. It silently assumes close is non-negative. A signed or shifted close series can make `SMA_long` or `SMA_short` exactly 0 while VWMA is not, which gives ±inf. The same caveat is already written out for signed volume.
  - Fix: Add "and non-negative close" to the condition, next to the signed-volume caveat.

## Summary

The port is right: all 11 targeted files reach the acceptance criteria, and the only faults are four docstring citations and one boundary caveat. The reviewer worked through the formula by hand. The derivation at bars 2–4 is exact (-1/68 · 45/46 = -45/3128; -1/30 · 23/24 · 6/5 = -23/600), and rolling windows, `min_periods`, warm-up 19 and the NaN-on-zero-volume-sum rule all follow the issue line by line. All five wiring touch points are in place and the accessor forwards `short`/`long`/`offset` under their own names. The tests have a real in-memory `mutant` test that catches the one-bar look-ahead at every offset, `scale` tests at ×8/×64 bit-identical and ×10/×3.7 within tolerance with NaN masks compared, and a `0 < fires < n` check, so `tests/test_gate_e_ledger.py`'s name check is satisfied. The reviewer re-ran `docs/measure_vpci.py`, and every number in `docs/VpciMeasured.md` matches its output: 1,481/1,500 fires, 729/752/0 signs, the scale diffs, 3.14e-16 / 897 / 1.12e-10 for the vwma/sma reference, 0/35 and 35/35 for causality, 1.38e-16 over 11 bars, and the ρ values. `tests/test_vpci.py` passes 24 of 24. The receipt's guard run reproduces exactly (1229 passed, 8 skipped). The package reads back 358 in `Category` and 43 in `volume`, matching README.md, `CATEGORY_TOTAL` and `CATEGORY_BUCKETS`. The faults are sloppy frame attribution in the test docstring (numbers from the script's 1,500-bar frame quoted as if they came from the test's 900- and 1,000-bar frames, plus the loop-bar mismatch) and one over-general "do not land on exactly 0" sentence that the receipt's own hand example contradicts. Fix those five sentences.

The reviewer did not run the full suite or the parent repo, and did not regenerate `docs/IndicatorDictionary.md` to diff it. It took the dictionary as regenerated from its diff (new date, 358/366 counts, `VPCI_5_20 SF` row with warm-up 19).
