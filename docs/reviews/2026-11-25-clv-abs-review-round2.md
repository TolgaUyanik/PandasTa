# Brutally Honest Review — clv-abs (issue #200 port), round 2

**Date:** 2026-11-25
**Target:** docs/MLCompanionContract.md, pandas_ta/candles/__init__.py, tests/test_altport2_ports.py, docs/ClvAbsMeasured.md, docs/measure_clv_abs.py, pandas_ta/candles/clv_abs.py, tests/test_clv_abs.py, docs/reviews/2026-11-25-clv-abs-review.md (scope: round-1 CRITICAL/MAJOR resolution + files changed since round 1)
**Type:** code (plus its measurement receipt as text)
**Verdict:** PASS

## Round-1 findings

| round-1 finding | status |
|---|---|
| CRITICAL — `ta.sma` na rule unverified, port propagated na | RESOLVED. The module now skips na. The Remarks sentence is labelled "recalled, not fetched" in Decision 2, the module docstring and MLCompanionContract.md, with the v6 URL for the owner. A three-way fixture (skip 0.875 / propagate NaN / flat-as-zero 0.625) passes. |
| MAJOR — 0.2770 fork-overlap figure not scripted | RESOLVED. `fork_overlap()` in `docs/measure_clv_abs.py` reproduced 0.2269 `RPO_VA_WIDTH_PCT_110_80` and the next four values. The 0.2770 is marked as superseded. |
| MAJOR — `_reference` shared the module's NaN guess | RESOLVED as far as it can be without Pine. The plain-float loop follows the stated rule, and the fixture separates the readings. It still shares the module's reading of the na bar itself (see MINOR). |
| Round-1 MINOR/NIT | RESOLVED. Counts pinned (1986/1986/1928), the `[0, 1]` caveat added, the import sorted. |

## Findings

### MINOR / NIT
- **MINOR — pandas_ta/candles/clv_abs.py:66-67** — The round-1 fix added a crash. `vp_abs.dropna().rolling(...).mean().reindex(vp_abs.index)` raises `ValueError: cannot reindex on an axis with duplicate labels` when the input index has a repeated timestamp. The reviewer checked it: an 8-bar DatetimeIndex with one duplicated date makes `clv_abs` raise, while `pandas_ta.overlap.sma` on the same series returns values. Round 0 used a plain rolling mean and did not have this failure.
  - Fix: Align by position, not by label: `valid = vp_abs.notna().to_numpy(); clvabs = pd.Series(np.nan, index=vp_abs.index); clvabs[valid] = vp_abs[valid].rolling(length, min_periods=length).mean().to_numpy(); clvabs = clvabs.ffill()`. Then add `test_duplicate_index_does_not_raise`, using a frame with one duplicated date that matches `_reference`.
- **MINOR — tests/test_altport2_ports.py:196 (CATEGORY_TOTAL comment); pandas_ta/candles/clv_abs.py:128-129 (Calculation block); docs/ClvAbsMeasured.md Gate A code block** — The hedge is applied unevenly. Decision 2, the NA RULE paragraph and MLCompanionContract.md:27 correctly say "recalled, not fetched". These three places still state "as Pine's ta.sma skips na" as fact.
  - Fix: Add "(Pine reference sentence recalled, not fetched; owner to confirm)" to each of the three places, or change the wording to "skips na, per the recalled Pine `ta.sma` Remarks".
- **MINOR — pandas_ta/candles/clv_abs.py:35-37; docs/ClvAbsMeasured.md Decision 2** — Even if the recalled sentence is right, it says which values the mean is computed over. It does not say what Pine returns on the na bar itself, which could be the prior mean or na. The forward fill is the port's reading, but the text presents it as following from the sentence ("therefore"). `_reference` encodes the same reading, so Gate A cannot test it. The same goes for a trailing NaN, which carries the last value forward.
  - Fix: Change "therefore" to "this port's reading, which the recalled sentence does not settle: the na bar repeats the prior mean". Add that reading to the list of things the owner confirms on the TradingView page.
- **MINOR — tests/test_clv_abs.py (no test of a missing input)** — The docstring says a NaN bar (zero-range or a missing input) contributes nothing, but every test drives only the zero-range path. A NaN `close` in the middle and a NaN at the end are never tested. The reviewer checked by hand that both forward-fill.
  - Fix: Add `test_missing_input_is_skipped_like_a_flat_bar`. Use the 7-row zero-range fixture, set `close[6] = NaN`, assert bar 6 == bar 5 == 0.625, and add one variant with `high[-1] = NaN` that asserts the last value equals the one before it. Compare both against `_reference`.

## Summary

All three round-1 findings are fixed. The four lower findings are MINOR, so the gate is PASS. The ta.sma na rule is now na-skipping and honestly labelled as recalled rather than fetched. The fork-overlap figure is scripted and reproduced. The reference follows the stated rule, and a fixture tells the three readings apart. Every receipt number reproduced exactly when the reviewer re-ran the script: Gate A diffs and masks, Gate B 0/0/285 of 293, Gate C 1986/1928/0.1224–0.6602 and the 10 seeds, Gate D 0/0/1978/1980 and 1.94e-14/1.79e-14, sha1 `4664bc09…`. `tests/test_clv_abs.py` gives 26 passed, and the receipt's Gate F subset gives 1,551 passed, 8 skipped. Remaining: the `reindex` added in round 1 crashes on a duplicate index; three short summaries still state the recalled rule as fact; the text presents the na-bar forward fill as following from the sentence when it is the port's own reading; and the missing-input path has no test.

Not checked: the live TradingView `ta.sma` page (no web access), the full test suite, and Gate E (owed).
