# Ehlers DSP family — screening record (issue #30)

Issue #30 lists a family of Ehlers DSP oscillators "screened and ported one by one". This file
is the running receipt across sessions: one row per candidate named in the issue, its verdict,
and why. Per-indicator measurements live in their own `docs/<Name>Measured.md`.

**Session 2026-11-01 shipped one candidate** — Correlation Cycle, as `correlation_cycle`
(Real/Imag/Angle; market state skipped) — and screened the rest without building them. The
repo's porting rules cap a single session at 3 new `pandas_ta/<category>/*.py` files; "one by
one" is read here as literally one indicator fully through Gates A–D per session, not the whole
family at once. Rows below marked DEFERRED are not reverts: nothing was measured and struck,
they were not attempted that session for the reasons given, and remain open for a future
one-by-one session.

**Receipt session (2026-11-01)** ran Gate E on `correlation_cycle`: `CC_IMAG_20` STRUCK
(pooled |ρ| 0.9353, 100% of 89 BIST frames per-frame median ≥ 0.90, vs `Squeeze_Spread_pct`)
and reverted; `CC_REAL_20` (0.6626 vs `StochRSI_K_Pctl`) and `CC_ANGLE_20` (0.7235 vs
`Squeeze_Spread_pct`) SHIP. Ledger row recorded in `docs/gate_e_ledger.csv`. Full numbers:
`docs/CorrelationCycleMeasured.md`.

| Indicator | Scale-free as published (issue's own note) | Verdict | Reason |
|---|---|---|---|
| Correlation Cycle (angle + market state) | yes, built from correlations | **SHIPPED (partial)**: `CC_REAL_20`, `CC_ANGLE_20` ship; `CC_IMAG_20` Gate E STRUCK and reverted; market state skipped | `pandas_ta/cycles/correlation_cycle.py`; see `docs/CorrelationCycleMeasured.md`. Market state sub-output skipped: no accessible source (no web, no Pine corpus, no `jesse-ai/jesse`) defines Ehlers' exact trend/cycle classification, and inventing thresholds would not be a port. |
| Reflex / Trendflex | yes, normalised by RMS (issue: "from memory, verify") | DEFERRED | Recursive two-pole filters (SuperSmoother-style, like the fork's own `ssf`), which CLAUDE.md explicitly flags for a negative-index causality bug risk on first implementation; this session's file budget (1 of 3 used) and effort went to the lower-risk, non-recursive Correlation Cycle instead. Issue's own pre-registered guess: "best chance" to ship — worth a dedicated session. |
| Roofing filter → Stochastic ("Ehlers Stochastic") | yes, bounded | DEFERRED | Composite of a 2-pole highpass and a SuperSmoother lowpass (the Roofing Filter), both recursive, before a rolling stochastic rescale. Same recursive-filter risk as Reflex/Trendflex; not attempted this session. |
| Decycler oscillator | only as a % of price | DEFERRED | Needs the same recursive highpass machinery as the Roofing Filter, plus the issue's own normalisation choice (% of price) decided at Gate A; not attempted this session. |
| Cyber Cycle | **no**: price-scale, needs a normalisation choice at Gate A | DEFERRED | Issue flags this candidate as needing an owner-level normalisation decision before any port is attempted (Gate A). Not decided or attempted this session. |
| Voss predictor | **no**: price-scale | DEFERRED | Same as Cyber Cycle: normalisation choice owed at Gate A. |
| Ultimate Smoother | **no**: price-scale | DEFERRED | Same as Cyber Cycle. The issue's own pre-registered warning (MLCOL-1) is that a smoother *distance* form is the likeliest revert of the whole family, restating `NWE_MID` / `bias` — worth measuring once a normalisation is chosen, but not attempted this session. |
| AM detector / FM demodulator | **no**: price-scale (volatility envelope) | DEFERRED | Same as Cyber Cycle. |
| Empirical Mode Decomposition (`emd`) | band-pass/peak/valley outputs: price-scale | DEFERRED | Multi-output filter; band-pass/peak/valley sub-outputs need a distance/ratio form decided before Gate A, same open question as the other price-scale candidates. Not attempted this session. |
| Instantaneous Trendline (`itrend`) | only distance/ratio forms (it is a filter) | DEFERRED | Recursive filter; a scale-free form (distance from price) is possible but not attempted this session. |
| Distance Coefficient filter (`edcf`) | only distance/ratio forms | DEFERRED | Same as `itrend`. |
| Band-pass filter (1-pole) | only distance/ratio forms | DEFERRED | Same as `itrend`. |
| High-pass filter (1-pole) | only distance/ratio forms | DEFERRED | Same as `itrend`. |
| High-pass filter (2-pole) | only distance/ratio forms | DEFERRED | Same as `itrend`. Note: `supersmoother` / `supersmoother_3_pole` (jesse's names) are already the fork's `ssf` (`poles=2` or `3`) — not a new port. |

## Gate E ledger note

`correlation_cycle` is the only indicator from this family in `Category`. Its Gate E row
(`CC_REAL_20`, `CC_ANGLE_20`) is recorded in `docs/gate_e_ledger.csv`, measured 2026-11-01;
`CC_IMAG_20` was struck and reverted, so it carries no row (a reverted column is not shipped and
needs none). Reverting `CC_IMAG_20` edited the module file, which invalidates the ledger's
whole-file `module_sha1` for the two surviving rows too, so
`tests/test_gate_e_ledger.py::test_row_still_describes_its_module` reports both as owed (a skip
under CI's `GATE_E_PENDING_OK=1` toward `dev`, a failure locally and toward `main`) until a
fresh Gate E run on the final two-column module is recorded. See
`docs/CorrelationCycleMeasured.md`'s Gate E section for the detail.
