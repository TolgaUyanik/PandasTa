# Correlation Cycle — measured (`correlation_cycle`)

John Ehlers' correlation-based cycle/phase detector, named in issue #30 as the sibling of the
fork's shipped `cti` (Correlation Trend Indicator): same author, same year (2020). `cti`
correlates price against a straight ramp (`linreg(r=True)`); Correlation Cycle correlates price
against a cosine and a sine reference wave of one fixed period, producing a Real part, an
Imaginary part, and an Angle. Found by the ResearchIntel library sweep of 2026-10-24
(`PandasTaIndicatorCandidates-2026-10-22.md`, Round 3b).

**Status: Gates A-F all cleared. Gate E measured: `CC_IMAG_20` STRUCK and reverted;
`CC_REAL_20` and `CC_ANGLE_20` SHIP, re-run against the post-revert module file and recorded
in the ledger (run `is30-correlation_cycle-19b830f6`, same numbers as the pre-revert-file run,
see Gate E below) — closed.**
`correlation_cycle` is in `Category`, so any `df.ta.strategy()` sweep in the parent repo
picks it up.

Shipped: `pandas_ta/cycles/correlation_cycle.py`, two columns `CC_REAL_<length>`,
`CC_ANGLE_<length>` (default `CC_REAL_20`, `CC_ANGLE_20`). `CC_IMAG_<length>` is computed
internally (Angle needs it) but is not a shipped column — see Gate E below.
Tests: `tests/test_correlation_cycle.py` (13). Numbers: `python
docs/measure_correlation_cycle_proxy.py`. Environment: pandas 2.3.3, numpy 1.26.4,
Python (this worktree's interpreter). Measured 2026-11-01.

## What ships vs what is skipped

The issue's table lists this row as "Correlation Cycle (angle + market state)". Only
Real / Angle ship. **Market state is skipped**, with a one-line reason: per issue #30,
no file in the owner's local Pine corpus mentions Correlation Cycle, so the only possible Gate A
references are Ehlers' papers or a library's source — and this environment has neither web
access nor access to the Pine corpus or to `jesse-ai/jesse`'s `correlation_cycle.py`. Inventing
threshold values for a "trend vs cycle" classifier and calling it Ehlers' market state would not
be a port. The Pearson-correlation arithmetic itself needs no such citation (see Gate A).
**Imag is skipped too, for a measured reason**: Gate E struck `CC_IMAG_20` (pooled |ρ| 0.9353,
100% of 89 frames per-frame median ≥ 0.90, against `Squeeze_Spread_pct`) — see Gate E below. It
is still computed internally since `Angle = atan2(Imag, Real)` needs it; it is just not shipped
as a column.

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
| A Correctness | pass (self-consistency; no source oracle reachable in this environment) | pure cosine/sine inputs match the closed-form phase identity to 1e-9 (Real directly, Angle via the circular identity `(angle - expected + 180) mod 360 - 180 == 0`); flat window reads NaN, not an error |
| B Causality | pass | 31-offset future-perturbation sweep (`test_pfe.py`'s harness shape): real module 0 leaks on `CC_REAL_20`/`CC_ANGLE_20`; two mutants (`real_shift`, `imag_shift`, each shifts one rolling window one bar into the future) proven live, then caught 31 of 31 — `imag_shift` is still live even though `CC_IMAG_20` is no longer shipped, because `CC_ANGLE_20` reads the internal `imag` |
| C Reachability | measured on real data via Gate E (89 BIST frames); synthetic floor: 3,000-bar tick-rounded walk (seed 1, tick 0.05), 2,981 of 3,000 bars finite per column (19-bar warm-up, `length - 1`), 2,981 distinct values on `CC_REAL_20` | Gate E `n` column: 391,017 (`CC_REAL_20`) / 397,158 (`CC_ANGLE_20`) non-NaN bars pooled over 89 frames |
| D Scale-free | pass | x8 / x64 bit-identical on `CC_REAL_20`/`CC_ANGLE_20` (Real is a Pearson correlation coefficient, provably scale- and location-invariant for `close -> close*k`, `k>0`; Angle inherits it through `atan2` on Real and the internal Imag); x10 / x3.7 within 1.5e-11 (measured: Real 9.53e-13 / 1.22e-12, Angle 1.49e-11 / 7.26e-12); 2,981 finite of 3,000 satisfies `0 < fires < n`; bounds `\|Real\| <= 1 + 1e-9`, `Angle` in `(-180, 180]`, held on the same walk |
| E Attribution | **measured 2026-11-01** — SHIP / SHIP / STRUCK, see table below; ledger closed on the post-revert module file (run `is30-correlation_cycle-19b830f6`) | `gate_e_overlap.py run --module pandas_ta.cycles.correlation_cycle`, recorded in `docs/gate_e_ledger.csv` |
| F Suites | this repo only, this session | `python -m pytest -q tests/test_correlation_cycle.py`: 13 passed (post-revert). Full-suite run and parent-repo suite are run by the launcher. |

## Gate E — measured 2026-11-01

First run `is30-correlation_cycle-4c728c83` (pre-revert-file three-column module) found
`CC_IMAG_20` STRUCK; the module was then edited to drop it. A second run,
`is30-correlation_cycle-19b830f6`, against the post-revert two-column module file
(`pandas_ta_src_sha1` `d4290382a6ffe4adf06f3e69c6d92d423d5fdc17`, `candidate_source_sha1`
`1015d669f979086eacd0906858be86357b9f8a9b`), reproduced identical `CC_REAL_20`/`CC_ANGLE_20`
numbers — the revert only removed a column, it did not touch the Real/Angle calculation —
and is the run recorded in `docs/gate_e_ledger.csv`. 89 BIST frames, 687 comparators (329
`compute_all` + 358 `ml_features` manifest 1d), `r3-perframe-0.90` bands:

| column | max \|ρ\| | against | n | per-frame max median \|ρ\| | verdict |
|---|---|---|---|---|---|
| `CC_REAL_20` | 0.6626 | `StochRSI_K_Pctl` | 391,017 | 0.6606 | SHIP |
| `CC_IMAG_20` | 0.9353 | `Squeeze_Spread_pct` | 397,158 | 0.9372 | **STRUCK** (100% of 89 frames per-frame median ≥ 0.90) |
| `CC_ANGLE_20` | 0.7235 | `Squeeze_Spread_pct` | 397,158 | 0.7233 | SHIP |

`CC_IMAG_20` is over the 0.90 STRUCK line both pooled and per-frame (100% of frames), so it is
reverted: the module still computes `imag` internally (`CC_ANGLE_20` needs it) but no longer
emits it as a column, and its row is removed from `docs/gate_e_ledger.csv` (a reverted column
ships no row). `CC_REAL_20` and `CC_ANGLE_20` are under the 0.76 SHIP line and ship as measured,
with their rows kept in the ledger.

Closed: reverting `CC_IMAG_20` edited the module file, which would have invalidated the
ledger's `module_sha1` for the two surviving rows (`module_sha1` hashes the whole file, not
per-column) — that is why the second run above, against the post-revert file, was needed.
`python docs/gate_e_ledger.py record <run dir> --measured 2026-11-01` recorded it;
`tests/test_gate_e_ledger.py::test_row_still_describes_its_module` passes.

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

Maximum |ρ| on this proxy was **0.7030** (`CC_IMAG_20` vs `CTI_12`), below CLAUDE.md's
0.76 SHIP line — this one synthetic walk missed the real Gate E strike on `CC_IMAG_20`
(pooled 0.9353, 100% of 89 frames per-frame median ≥ 0.90, against `Squeeze_Spread_pct`, a
comparator not in this proxy's four-column set). The pre-registered "best chance to ship"
guess for Correlation Cycle is confirmed half right: `CC_IMAG_20` struck, `CC_REAL_20` and
`CC_ANGLE_20` ship. One synthetic walk is not Gate E, which is exactly why this proxy is
labelled NOT Gate E and why the real run (above) is the receipt that governs the verdict.

## Closed

Gate E ran 2026-11-01 (table above) and the ledger row is recorded. `CC_IMAG_20` reverted;
`CC_REAL_20` and `CC_ANGLE_20` ship. `docs/IndicatorDictionary.md` and
`docs/MLCompanionContract.md` regenerated/updated to drop `CC_IMAG_20`.

Open: screen the rest of the Ehlers DSP family named in issue #30 one by one; see
`docs/EhlersDspMeasured.md` for the full table and why each other candidate is still open.
