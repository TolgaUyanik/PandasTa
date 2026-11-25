# Task 01 — rd_outside_bar port (issue #167)

## Implementation summary

Ported `rd_outside_bar` (Reddit tier-4, rd:Trading:1og1s0z / rd:Daytrading:1gxmcnv) as
`pandas_ta/candles/rd_outside_bar.py`: `RD_OUTSIDE_BAR = 1 IF high > high[1] AND
low < low[1] ELSE 0`, the mirror of upstream `cdl_inside`. Wired all 5 touch points
(module, `candles/__init__.py` export, `Category` entry, `core.py` accessor taking only
`high`/`low`, `tests/test_rd_outside_bar.py`). Wrote `docs/measure_rd_outside_bar.py` +
`_cpu.py` and ran both. Wrote `docs/RdOutsideBarMeasured.md` with Gates A-D measured and
Gate E marked pending. Bumped `CATEGORY_TOTAL` (395->396), README's three counts and
candles list, `MLCompanionContract.md`'s tagged/BIN counts, regenerated
`docs/IndicatorDictionary.md`.

Modeled closely on the already-merged `rd_horseshoe` (#164) — same test structure
(hand fixtures, future-splice causality probe + sweep mutant, scale-invariance sweep,
reachability on synthetic frames), same Measured.md shape.

## Review round 1

Dispatched Fletcher reviewer (Explore subagent, read-only, full tool access including
Bash to independently re-run the measure script and pytest).

```
VERDICT: PASS
FINDINGS:
  - severity: MINOR
    location: tests/test_rd_outside_bar.py (whole file)
    problem:  No test exercises the case where `high` and `low` have different lengths
      (e.g. `high` is below the 2-bar minimum while `low` is not). `verify_series` is
      called on each independently and the function does correctly bail out, but
      nothing pins that the two null-checks are actually independent.
    fix:      Add a one-line test next to `test_short_input_returns_none`.
  - severity: NIT
    location: pandas_ta/candles/rd_outside_bar.py:59
    problem:  The warm-up mask only checks `prior_high.notna()`, not `prior_low.notna()`.
      Not a live bug for clean OHLC input; matches the same shortcut already shipped in
      `rd_horseshoe.py:89`.
    fix:      Leave as-is (matches precedent) or mask both as a separate cross-cutting
      cleanup -- not blocking.
SUMMARY: Cleanest port in this series -- every number in docs/RdOutsideBarMeasured.md
reproduced bit-for-bit on independent re-run; Gate A formula, the cdl_inside mirror
claim, all 5 wiring touch points, and every bumped counter agree with the source. Two
trivial dockable points, both already shipped identically in the precedent
rd_horseshoe, neither worth a REVISE round. Ship it.
```

## Outcome

PASS, round 1. MINOR/NIT findings only (missing asymmetric-length edge-case test;
single-field NaN warm-up mask, matching existing `rd_horseshoe` precedent) — not
blocking per the gate rule (CRITICAL/MAJOR -> REVISE only). Not applied: both are
optional polish on an already-shipped pattern, not defects.

## Assumptions

None beyond what's already logged in `00-manifest.md`.
