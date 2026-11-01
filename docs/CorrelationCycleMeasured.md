# Correlation Cycle — measured (`correlation_cycle`)

John Ehlers' correlation-based cycle/phase detector, named in issue #30 as the sibling of the
fork's shipped `cti` (Correlation Trend Indicator): same author, same year (2020). `cti`
correlates price against a straight ramp (`linreg(r=True)`); Correlation Cycle correlates price
against a cosine and a sine reference wave of one fixed period, producing a Real part, an
Imaginary part, and an Angle. Found by the ResearchIntel library sweep of 2026-10-24
(`PandasTaIndicatorCandidates-2026-10-22.md`, Round 3b).

**Status: Gates A, B, D cleared (measured below); Gate C synthetic only; Gate E PENDING —
run by issue-solver after this session. Do not merge to `main` before Gate E**:
`correlation_cycle` is in `Category`, so any `df.ta.strategy()` sweep in the parent repo
picks it up.

Shipped: `pandas_ta/cycles/correlation_cycle.py`, three columns `CC_REAL_<length>`,
`CC_IMAG_<length>`, `CC_ANGLE_<length>` (default `CC_REAL_20`, `CC_IMAG_20`, `CC_ANGLE_20`).
Tests: `tests/test_correlation_cycle.py` (14). Numbers: `python
docs/measure_correlation_cycle_proxy.py`. Environment: pandas 2.3.3, numpy 1.26.4,
Python (this worktree's interpreter). Measured 2026-11-01.

## What ships vs what is skipped

The issue's table lists this row as "Correlation Cycle (angle + market state)". Only
Real / Imag / Angle ship. **Market state is skipped**, with a one-line reason: per issue #30,
no file in the owner's local Pine corpus mentions Correlation Cycle, so the only possible Gate A
references are Ehlers' papers or a library's source — and this environment has neither web
access nor access to the Pine corpus or to `jesse-ai/jesse`'s `correlation_cycle.py`. Inventing
threshold values for a "trend vs cycle" classifier and calling it Ehlers' market state would not
be a port. The Pearson-correlation arithmetic itself needs no such citation (see Gate A).

## Gate A — self-consistency, not a source citation

No independent oracle is reachable from this environment (no web, no Pine corpus). What is
checked instead is a closed-form identity, derived independently of the module's own code: for
two sinusoids of the same frequency sampled at `length` equally spaced points covering exactly
one period, their Pearson correlation equals the cosine of their phase difference (a standard
discrete-Fourier orthogonality identity: both series have zero mean over an exact period, and the
cross term reduces to `cos(phase) * length/2` against a reference power of `length/2`). Feeding
the module a pure cosine (or sine) wave at exactly `length` therefore predicts its Real/Imag
output in closed form, checked to `atol=1e-9` on 300 bars:

| input | expected `CC_REAL_20` | expected `CC_IMAG_20` |
|---|---|---|
| `cos(2*pi*i/20)` | `cos(2*pi*(t+1)/20)` | `-sin(2*pi*(t+1)/20)` |
| `sin(2*pi*i/20)` | `sin(2*pi*(t+1)/20)` | `cos(2*pi*(t+1)/20)` |

Both predictions passed exactly (`test_pure_cosine_matches_closed_form`,
`test_pure_sine_matches_closed_form`). `CC_ANGLE` was separately checked to equal
`degrees(atan2(Imag, Real))` elementwise on a 400-bar random walk.

What is NOT verified here: Ehlers' own convention for which end of the window is lag zero, and
the sign of his sine reference — a different, equally defensible, convention would mirror this
module's Angle about 0 and/or 90 degrees. Column values are therefore not claimed to match any
published Ehlers chart bit-for-bit; only the arithmetic (a Pearson correlation against a fixed
sinusoid) is pinned.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass (self-consistency; no source oracle reachable in this environment) | pure cosine/sine inputs match the closed-form phase identity to 1e-9; Angle == `degrees(atan2(Imag, Real))` elementwise; flat window reads NaN, not an error |
| B Causality | pass | 31-offset future-perturbation sweep (`test_pfe.py`'s harness shape): real module 0 leaks on `CC_REAL_20`/`CC_IMAG_20`; two mutants (`real_shift`, `imag_shift`, each shifts one rolling window one bar into the future) proven live, then caught 31 of 31 |
| C Reachability | synthetic only | 3,000-bar tick-rounded walk (seed 1, tick 0.05): 2,981 of 3,000 bars finite per column (19-bar warm-up, `length - 1`), 2,981 distinct values each on `CC_REAL_20` and `CC_IMAG_20`. **Real-data counts owed to Gate E.** |
| D Scale-free | pass | x8 / x64 bit-identical on all three columns (Real/Imag are Pearson correlation coefficients, provably scale- and location-invariant for `close -> close*k`, `k>0`; Angle inherits it through `atan2`); x10 / x3.7 within 1.5e-11 (measured: Real 9.53e-13 / 1.22e-12, Imag 6.29e-13 / 1.10e-12, Angle 1.49e-11 / 7.26e-12); 2,981 finite of 3,000 satisfies `0 < fires < n`; bounds `\|Real\|, \|Imag\| <= 1 + 1e-9`, `Angle` in `(-180, 180]`, held on the same walk |
| E Attribution | **PENDING** — run by issue-solver after this session | `../Backtesting/Backtesting/scripts/analysis/gate_e_overlap.py run --module pandas_ta.cycles.correlation_cycle --name correlation_cycle` |
| F Suites | this repo only, this session | `python -m pytest -q tests/test_correlation_cycle.py`: 14 passed. Full-suite run and parent-repo suite are run by the launcher. |

## Proxy overlap (NOT Gate E)

Spearman ρ on one synthetic tick-rounded GBM walk (σ=0.02, seed 1, n=3,000), against the
columns the issue pre-registered as most likely to restate this family (`ebsw`, `ht_sine`,
`cti`, `lrsi`), plus `fisher` as a fourth oscillator:

| comparator | ρ vs `CC_REAL_20` | ρ vs `CC_IMAG_20` | ρ vs `CC_ANGLE_20` |
|---|---|---|---|
| `CTI_12` | 0.4991 | −0.7030 | −0.5514 |
| `EBSW_40_10` | 0.5256 | −0.3191 | −0.2741 |
| `FISHERt_9_1` | 0.4425 | −0.6850 | −0.5411 |
| `LRSI_13_0.2` | 0.4784 | −0.6309 | −0.5047 |
| `HT_SINE` | 0.6631 | −0.1424 | −0.1316 |

Maximum |ρ| on this proxy is **0.7030** (`CC_IMAG_20` vs `CTI_12`), below CLAUDE.md's
0.76 SHIP line and below the pre-registered "best chance to ship" guess being falsified into a
revert. One synthetic walk is not Gate E: the owner's `r3-perframe-0.90` bands run over 89 real
BIST frames against 687 comparators, which this proxy does not reach.

## To close

1. Run Gate E (`gate_e_overlap.py run --module pandas_ta.cycles.correlation_cycle --name
   correlation_cycle`) and record the row in `docs/gate_e_ledger.csv`.
2. Apply CLAUDE.md's `r3-perframe-0.90` bands to the recorded max |ρ|. On SHIP, this file's
   status line and the Gate E row above are updated. On DISCLOSE / DISCLOSE_GAP, note it in
   `docs/IndicatorDictionary.md`. On STRUCK, revert the module, its wiring and its tests, and
   keep this file as the receipt (a measured revert is DONE, not blocked).
3. Fill Gate C from real BIST frames in the same Gate E run.
4. Screen the rest of the Ehlers DSP family named in issue #30 one by one; see
   `docs/EhlersDspMeasured.md` for the full table and why each other candidate is still open.
