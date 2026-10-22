# Brutally Honest Review — pfe port (successor to reverted signed_er)

**Date:** 2026-10-22
**Target:** `pandas_ta/momentum/pfe.py`, `tests/test_pfe.py`, `docs/PfeMeasured.md`, `docs/measure_pfe_proxy.py`, `docs/SignedErMeasured.md`, plus the wiring in `pandas_ta/momentum/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `README.md` and `tests/test_altport2_ports.py`
**Type:** code + text
**Verdict:** REVISE

Main thread re-checked the three central claims: the band misquote (`PfeMeasured.md:84` against `CLAUDE.md:113`), the round-trip count (seed 11 gives 6, seed 1 gives 20), and the dictionary generator (no reference to Backtesting).

## Findings

### CRITICAL
- **docs/PfeMeasured.md:84-85** — The doc invents a "0.76–0.90 ship with disclosure" band. CLAUDE.md:113 has three bands: ≈0.9 revert, 0.76–0.80 disclosure, <0.76 ship. Every proxy ρ against sign-carrying momentum is above 0.80 (CMO_10 0.8743, ROC_10 0.8559, SLOPE_10 0.8487, CMO_14/RSI_14 0.8011), and the CMO_10 figure reaches 0.9001 at σ 5%.
  - Fix: quote CLAUDE.md exactly. State that 0.874 is above the disclosure band, in the range CLAUDE.md leaves undefined below the ≈0.9 revert line, so the proxy leans toward revert. Note that a revert was also the pre-registered expectation.
- **docs/PfeMeasured.md:53** — The doc says the round-trip test "pins this on 20 such bars". The test uses `_walk(3000, tick=0.05)` at seed 11, which has 6 such bars. The 20 comes from seed 1.
  - Fix: change 20 to 6, assert `same.sum() == 6` in the test, and add the count to `measure_pfe_proxy.py`.

### MAJOR
- **PfeMeasured.md "To close" step 4; docs/IndicatorDictionary.md; README.md:9-11** — The dictionary has not been regenerated. It still shows 233 / 241 with no PFE row, so README's "All of them are in the dictionary" is false. The stated reason, that both generators need the parent repo, is wrong: `gen_indicator_dictionary.py` never references Backtesting.
  - Fix: run `python docs/gen_indicator_dictionary.py` and check for 234 / 242 and a `PFE_10_5` row. Only `gen_indicator_pages.py` reads PARENT, so state that only `docs/indicators/pfe.md` is blocked.
- **Done-when criterion; PfeMeasured.md status line and Gate E/F rows** — `../Backtesting` does not exist on this machine. That rules out real-data Gate C, Gate E, and Gate F for the parent repo. Neither "shipped through A–F" nor "measured and reverted" is true.
  - Fix: report the task as BLOCKED/PENDING, or have the owner decide to revert now on the proxy evidence, with PfeMeasured.md kept as the receipt and stating "reverted on proxy, Gate E not run".
- **PfeMeasured.md Gate A row; pfe.py docstring** — Gate A has no source oracle. The independent loop implements the fork's own modified formula. The "10 bars, 9 segments, sqrt(dC²+100)" claim and the TASC Jan 1994 attribution cite no page.
  - Fix: label Gate A "pass (self-consistency; no source oracle)". Add a hand-written Hannula raw-price reference test. Cite the Kaufman 2013 ch20 page, or mark these details unverified.

### MINOR / NIT
- **MINOR tests/test_pfe.py:223-225** — The `0 < fires < n` check is vacuous. The 10 warm-up NaNs make `< n` hold automatically, and a constant ±100 column would pass.
  - Fix: assert `nunique() > 100`, assert both signs are present, and pin the 612 / 578 split.
- **MINOR docs/measure_pfe_proxy.py** — Without a pip install it fails with `ModuleNotFoundError`. It also does not print every number the docstring claims (the Gate D diffs, the round-trip count, 47.8).
  - Fix: add the `sys.path.insert` that `gen_indicator_dictionary.py` uses, then either print those numbers or narrow the docstring.
- **MINOR docs/SignedErMeasured.md:31-41** — The Gate B/D rows came from the deleted, never-committed `test_signed_er.py`, so the doc's "reproduce every number" line is false for them.
  - Fix: say those rows are not reproducible.
- **MINOR pfe.py / PfeMeasured.md:28-42** — Volatility saturation makes PFE close to a smoothed `100·sign(ROC_10)` on calm or intraday frames, which is redundant by construction.
  - Fix: either vol-scale the horizontal leg and re-measure, or list saturation as a revert reason.
- **NIT pfe.py docstring** — `|pfe| max` is 100.00000000000001 at length=1.
  - Fix: write "up to rounding", or add `clip`.
- **NIT PfeMeasured.md / tests** — The doc does not say the pre-registered guess (high ρ vs `er`) was falsified (ER_10 −0.0027). `offset` and `fillna` are untested.
  - Fix: add one sentence to the doc and two one-line tests.

## Summary

The code is sound. The mutant test is genuine (31/31 caught), ×8/×64 is bit-identical, and the proxy numbers reproduce. The text is not. It invents a disclosure band that turns proxy evidence pointing to a revert into "ship with disclosure", states a count no run produces, and excuses an unregenerated dictionary with a false dependency claim. Above all, the task is not done. The parent repo is absent, so real-data Gate C, Gate E and Gate F cannot run. Report it as pending, or let the owner revert on the proxy.

Reviewer test run: `tests/test_pfe.py` 17/17 passed. The targeted set gave 6 failed / 103 passed / 3 skipped, and none of the failures involve pfe (they are pandas 3.0.6 environment issues). The full suite gave 42 failed / 3087 passed / 85 skipped / 1 error, matching the doc's Gate F line. The pre-port baseline was not verified.
