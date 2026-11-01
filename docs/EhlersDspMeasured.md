# Ehlers DSP family — screening record (issue #30)

Issue #30 lists a family of Ehlers DSP oscillators "screened and ported one by one". This file
is the running receipt across sessions: one row per candidate named in the issue, its verdict,
and why. Per-indicator measurements live in their own `docs/<Name>Measured.md`.

**This session (2026-11-01) shipped one candidate** — Correlation Cycle, as
`correlation_cycle` (Real/Imag/Angle; market state skipped) — and screened the rest without
building them. The repo's porting rules cap a single session at 3 new
`pandas_ta/<category>/*.py` files; "one by one" is read here as literally one indicator fully
through Gates A–D per session, not the whole family at once. Rows below marked DEFERRED are
not reverts: nothing was measured and struck, they were not attempted this session for the
reasons given, and remain open for a future one-by-one session.

| Indicator | Scale-free as published (issue's own note) | Verdict | Reason |
|---|---|---|---|
| Correlation Cycle (angle + market state) | yes, built from correlations | **SHIPPED** (Real/Imag/Angle; market state skipped) | `pandas_ta/cycles/correlation_cycle.py`; see `docs/CorrelationCycleMeasured.md`. Market state sub-output skipped: no accessible source (no web, no Pine corpus, no `jesse-ai/jesse`) defines Ehlers' exact trend/cycle classification, and inventing thresholds would not be a port. |
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

Only `correlation_cycle` is in `Category` after this session, so it is the only row
`tests/test_gate_e_ledger.py` expects — and its row is intentionally still missing: Gate E is
run by the launcher after this session, per the rules this session operated under. That test
failure is expected, not a regression.
