# Auto run ttr-snr-20 — 2026-11-23

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | TTR-SNR-20 | issue #149 (`/brutally-honest-review --auto` free-form task) | Port R TTR's `SNR.R` signal-to-noise ratio as `ttr_snr_20` (volatility) through Gates A-D, wiring, tests, and `docs/TtrSnr20Measured.md`; Gate E and both whole suites are run by the launcher afterwards. |

## Clarifications (asked ONCE, before execution)
- none needed — the task text, the issue text, and the system-prompt overrides (no Gate E,
  no whole-suite runs, docs/issues/ read-only) fully specified scope. One judgment call made
  without asking (logged as an ASSUMPTION in `01-ttr-snr-20.md`): `atr(mamode="wrma")` rather
  than this fork's own `atr()` default (`"rma"`), to match the cited source formula's `ATR(n)`
  (TTR's own default smoothing is Wilder's) rather than this package's own default — the
  smaller-blast-radius reading is the one that matches the cited source, not the one that
  silently substitutes this fork's unrelated default.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| TTR-SNR-20 | main thread | single task, sequential (implement -> gate), no parallel benefit |
