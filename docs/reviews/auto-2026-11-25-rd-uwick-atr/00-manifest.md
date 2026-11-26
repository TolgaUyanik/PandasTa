# RD-UWICK-ATR auto run — manifest

**Task:** RD-UWICK-ATR: port the indicator of issue #172 through Gates A-D, the wiring,
the tests and `docs/RdUwickAtrMeasured.md`, per the issue and the issue-solver system
prompt. Formula: `(high - max(open, close)) / ATR(5)` — upper wick in ATR5 units. Source:
Reddit, tier 4 (ResearchIntel kb/reddit.db): rd:Daytrading:1rjq7kd (2026-03-03). Gate E and
the whole suites are run by the launcher afterwards.

**Mode:** C (batch task execution), single task. `--fletcher` on automatically.

## Clarifications (Phase 2)

No AskUserQuestion available in this headless session; ambiguities resolved by the most
conservative reading and logged as ASSUMPTIONs below (ties broken toward smaller
scope/blast radius):

- **ASSUMPTION — category placement.** The issue names no category. Placed in `candles`
  alongside the fork's other wick-based Reddit ports (`rd_wick_pressure_10`,
  `rd_horseshoe`), the smallest-blast-radius reading (keeps all `rd_*` wick/candle ports
  co-located, consistent with existing precedent) rather than `volatility` (where `atr`
  itself lives).
- **ASSUMPTION — ATR smoothing method.** The poster's words name "ATR" without a smoothing
  method. Adopted the screen prototype's own disclosed choice (`atr_wilder`,
  `ewm(alpha=1/5, adjust=False)`), carried through via this fork's own shipped Wilder
  smoothing (`atr(mamode="wrma")`) rather than re-implementing the recursion inline (the
  "import a helper from its own module" rule) or inventing a different smoothing. Recorded
  as Decision 1 in `docs/RdUwickAtrMeasured.md`.
- **ASSUMPTION — column naming.** The issue's own title ("RD-UWICK-ATR") carries no
  numeric suffix (unlike `rd_wick_pressure_10`'s "(10)"), so the column is named
  `RD_UWICK_ATR` with no suffix, matching the candidate screen's sibling `rd_body_atr`/
  `rd_lwick_atr` naming. `length` (the ATR period) is still a parameter, defaulting to 5,
  this fork's convention for a fixed-period port.
- **ASSUMPTION — MAE scope.** The issue's own text already excludes the poster's MAE
  mention ("needs forward bars (a label, not a feature)"); not re-litigated here.

## Execution map (Phase 3)

Single task, implemented on the main thread (judgment-heavy: Gate A/B/D derivation,
wiring across 5 touch points, counter updates across 6 files) — not parallelized, no
scope overlap with anything else.

## Gate (Phase 4)

Fletcher reviewer dispatched per round below; log in `01-rd-uwick-atr.md`.
