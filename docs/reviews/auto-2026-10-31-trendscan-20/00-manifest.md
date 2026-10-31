# Mode C manifest — TRENDSCAN (issue #20)

## Original ask (verbatim)

> TRENDSCAN: port the indicator of issue #20 through Gates A-D, the wiring, the tests and
> docs/<Name>Measured.md, per the issue and the rules in your system prompt (for each
> horizon `L` in a set, the t-statistic of the slope of the trend of log price on time over
> the). Gate E and the suites are run by the launcher afterwards.

## Phase 1 — Select

One task: port the trailing trend-scan indicator (max-\|t\| OLS trend t-stat across a
horizon set) described in issue #20, through Gates A-D, wiring, tests, and the measured
doc. Gate E (parent-repo overlap) and both repos' full suites are explicitly out of scope
for this session (run by the issue-solver launcher afterwards).

Run folder: `docs/reviews/auto-2026-10-31-trendscan-20/`.

## Phase 2 — Clarify

`AskUserQuestion` is unavailable in this headless session (issue-solver rule: take the
most conservative reading and log as ASSUMPTION). One gap found, no question asked:

- **The horizon set.** The issue names the feature ("for each horizon `L` in a set...")
  but states "The horizon set" as a bare decision line with no values given, and no
  reachable owner/user to ask. **ASSUMPTION**: `(5, 10, 20, 40, 60)` — the port's own
  choice, documented in `pandas_ta/statistics/trend_scan.py`'s `DEFAULT_HORIZONS` comment
  and `docs/TrendScanMeasured.md`'s "Decisions the issue left open" section, with the
  reasoning (same order of magnitude as this repo's other multi-week params) and an
  explicit escape hatch (`horizons=` is a caller-settable kwarg).

A second point, not a gap but a deliberate deviation worth logging alongside it: **Gate D
anchor locality.** The issue says `P_ref` should be taken "inside the window." This port
uses ONE series-wide anchor instead, for the O(n)-per-horizon cost the issue's own bullet
also demands, on the argument that OLS slope/SE/t are shift-invariant so a window-local
and a series-wide anchor give the identical statistic (measured in
`docs/TrendScanMeasured.md`). ASSUMPTION / reasoned override, not an unambiguous reading
of the issue's literal text — disclosed in the module docstring and the Measured doc, and
logged here so this manifest doesn't under-count what the issue's wording was not followed
literally on.

No other gaps: the rest of the issue (trailing-only causality, Gate E/F deferred to the
launcher) is unambiguous and matches this repo's established precedent (`ffd`,
`kalman_trend`).

## Phase 3 — Plan execution

Single task, no parallel lanes: one new module
(`pandas_ta/statistics/trend_scan.py`), its wiring (4 touch points: package export, core
accessor, `Category`, `tests/test_altport2_ports.py`'s pinned total), its test suite
(`tests/test_trend_scan.py`), the measurement script
(`docs/measure_trend_scan_proxy.py`) and the receipt (`docs/TrendScanMeasured.md`), plus
the three doc files whose counts are generated/asserted against the live package
(`README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`). All on the
main thread — every file either depends on the module existing first, or is a doc/count
file with no meaningful parallel-isolation benefit for a single indicator.

## Gate

Fletcher reviewer (`Explore`, read-only), full theatrics, against the complete diff.
Round cap: 4 total (round 1 + up to 3 re-runs), per the user's standing override of BHR's
own 3-round cap. Reports in this folder as `01-trend-scan*.md`.
