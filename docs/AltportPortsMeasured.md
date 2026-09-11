# ALTPORT-2 — the three survivors, ported and measured

Twenty AlternativeRepos gap rows entered ALTPORT-0. **Three ship.** The other
seventeen are recorded here with the measurement that stopped them, because the
deletions are the deliverable as much as the ports —
`docs/TalibPortsMeasured.md` set that precedent.

## What shipped

| column | module | Gate E max \|ρ\| | against | n | verdict |
|---|---|---|---|---|---|
| `CVI_10_10` | `pandas_ta/volatility/cvi.py` | **0.501290** | `CHOP` | 405,514 | SHIP |
| `MFI_BW_SF_20` | `pandas_ta/volume/bw_mfi.py` | **0.578897** | `vol_at_low_ratio` | 394,399 | SHIP |
| `SMC_SWEEP_15_1.5` | `pandas_ta/trend/smc_sweep.py` | **0.161383** | `CCI` | 406,562 | SHIP |

Gate E measured by ALTPORT-1 over 89 BIST_100 daily frames / 408,253 pooled bars
against **492** comparators — the corrected set including the engine's 7
non-numeric columns, not the 485 every prior sweep used.
⚠ `MFI_BW_SF_20` re-measured **0.536816 → 0.578897** once tti's `.round(4)` was
removed. Rounding is not always conservative; it had been suppressing the
correlation by 0.042.

Attribution — both MIT, neither vendored:
`cvi` and `smc_sweep` from **pandas-ta-classic**; `bw_mfi` from **tti**
(vsaveris). ⚠ For `bw_mfi` the debt is the QUESTION, not the arithmetic: tti
returns `(high−low)/volume` and the shipped form multiplies volume back out, so
the only upstream term is `(high−low)`. Said in the module rather than implied.

## What did not ship, and why

| candidate | measurement that stopped it |
|---|---|
| `C_POSC_14` | **STRUCK at Gate E**: pooled 0.894742 vs `cfo`, per-frame median 0.910212, ≥ 0.90 on 62.9% of 89 frames |
| `C_HVOL_20` | question-redundancy skip: 0.834724 vs `natr`, and `natr` IS "how volatile is this stock" |
| `C_PB_WIDTH_PCT` | question-redundancy skip: 0.874411 vs `natr` — a range-width restating a range-width |
| `C_WAD_BAR_SF` | question-redundancy skip: 0.889416 vs `percent_return` — it IS the signed daily return |
| `C_PB_UP_DIST_PCT` | owner ruling NO on slope-correction being a new question (0.773573 vs `dist_from_high_5`) |
| `C_PB_LO_DIST_PCT` | owner ruling NO, together with its mirror (0.727354 vs `cfo`) |

Plus the 13 struck at triage — `fosc` `dx` `adxr` `avolume` `VolatilityChaikins`
`Envelopes` `RelativeMomentumIndex` `ce` `SwingIndex` `RangeIndicator` `msw`
`vosc` `mavp` — each with its measurement in `docs/AltportTriage.md`.

**Ported: 3 of 20.** That ratio is the screen working. Every candidate struck
cost a measurement instead of a port through six gates and a revert.

## Gate notes worth keeping

**Gate A could not be bit-equality, and the divergences are stated rather than
chased.** classic's `ma("rma")`/`ema` SMA-seed where the fork's do not; tti
`.round(4)`s its output (`.round(10)` on the MFI, whose values are ~1e-7). The
oracle is the upstream package called directly — never a fork-helper
transcription compared to a fork column, which has no failure mode and produced
three false identities in ALTPORT-0 round 1.

**Gate B swept J.** A single perturbation point is not enough: CANDLE-1's mutant
escaped at J=200 for one module and J≥250 for another.

**The half-degenerate mutant.** `smc_sweep` reads a swing LOW and a swing HIGH.
Back-dating only the low makes the bull branch arithmetically impossible while
`bear_sweep` keeps firing — 28 events on the test fixture. A mutant that is
degenerate on one branch and live on the other is worse than either: it still
looks like it detects something. `_mutate` now takes a tuple and patches both.

**`smc_sweep` stays SIGNED** (+1 bull / −1 bear). An unsigned flag nonzero only
on its own support correlates ρ ≈ 1.0000 with any other such column — the
tied-zero trap that killed six CANDLE-1 columns. The sign is load-bearing.

**Gate D was re-run on the fork implementations, not inherited.** ALTPORT-1
measured every tti-derived column failing ×8 bit-identity (MFI 0.00419) — that
is tti's rounding, and a fork reimplementation does not carry it. Inheriting the
screen's result would have imported a defect that does not exist here.
