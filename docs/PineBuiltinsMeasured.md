# PINEBI-1b — Gate E for the 16 ported Pine built-ins

> **RECALL LAW.** Every rho and every n below is read out of `../../Backtesting/docs/indicators/_pinebi1b_gate_e.json`, written by `scripts/analysis/measure_pinebi1b_gate_e.py --refresh` on **2026-09-11**. Nothing is hand-typed.
>
> **Measurement base.** 6 cleaned BIST daily frames (AKBNK, EREGL, GARAN, SISE, THYAO, TUPRS), 5682–6762 bars, against **492 comparators** — the engine's full production column set through `_comparators.py`, so the 7 non-numeric columns are INCLUDED.
>
> **Coverage floor 50%.** The reported comparator must overlap at least that share of the candidate's own non-NaN bars. Without it a sparse comparator restricts the sample to its own support and reads rho 1.0 for a reason unrelated to the candidate; the raw uncovered maximum is carried in the JSON alongside.
>
> **Ship line** (`CLAUDE.md`): ρ ≈ 0.9 → revert · 0.76–0.80 → ship with disclosure · below 0.76 → ship.

**Verdict: 4 SHIP, 6 DISCLOSE, 6 REVERT.**

🔴 **The REVERT rows were acted on: those modules are DELETED from the fork**, unregistered from `Category`, their accessors removed and their tests dropped. `docs/pine_builtin_coverage.csv` records each one under `n/a - measured and reverted on Gate E` with its ρ, and `REVERTED_ON_GATE_E` in `docs/gen_pine_builtin_coverage.py` carries the reason — so the next session cannot re-port what was already measured as redundant. `CLAUDE.md`: *"Deleting an over-correlated column you just built is the expected outcome, not a failure."*

⚠ **`ift`'s ρ = 1.0000 is structural, not incidental.** The inverse Fisher transform is `tanh`, strictly monotone, so it is rank-identical to whatever drives it and Spearman is a RANK correlation. No choice of driver changes that, and a tree splitting on thresholds gains nothing from a monotone re-expression of a column it already has. **Any strictly monotone transform of a shipped column is dead on arrival under this gate.**

⚠ **`dm` (0.8992) was reverted on the APPROXIMATE reading of the ship line.** `CLAUDE.md` writes "ρ ≈ 0.9 → revert"; a hard 0.90 cutoff would have shipped it on the fourth decimal. The table below is rendered with the hard cutoff, so `dm` prints as `disclose` there and is reverted here — the discrepancy is deliberate and is the judgement, not a rendering bug.

| Indicator | column | fires | max ρ | vs | n | verdict |
|---|---|---:|---:|---|---:|---|
| `demarker` | `DEM_14` | 6 | +0.8992 | `vortex_VTXP_14` | 37059 | **disclose** |
| `frama` | `FRAMA_DIST_PCT_16` | 6 | +0.8540 | `NWE_MID_200_8.0_8.0` | 35944 | **disclose** |
| `ht` | `HT_PCT` | 6 | +0.7660 | `ebsw` | 36910 | **disclose** |
| `ift` | `IFT_RSI_14` | 6 | +1.0000 | `RSI` | 37060 | **REVERT** |
| `kcw` | `KCWe_20_2.0` | 6 | +0.9843 | `natr` | 37030 | **REVERT** |
| `pzo` | `PZO_14` | 6 | +0.7877 | `psl` | 37066 | **disclose** |
| `relative_volume` | `RVOL_20` | 6 | +0.9980 | `VOL_RATIO` | 37024 | **REVERT** |
| `rms` | `RMS_DIST_PCT_14` | 6 | +0.9900 | `NWE_MID_200_8.0_8.0` | 35944 | **REVERT** |
| `rwi` | `RWIh_14` | 6 | +0.9366 | `vortex_VTXP_14` | 37060 | **REVERT** |
| `rwi` | `RWIl_14` | 6 | +0.9399 | `vortex_VTXM_14` | 37060 | **REVERT** |
| `stc_tv` | `STCTV_23_50_10_3_3` | 6 | +0.8136 | `rsx` | 36738 | **disclose** |
| `szo` | `SZO_14` | 6 | +0.7289 | `aobv_AOBV_LR_2` | 37066 | **ship** |
| `vstop` | `VSTOP_DIST_PCT_20_1.0` | 6 | +0.7503 | `dist_from_high_5` | 37132 | **ship** |
| `vstop` | `VSTOP_TREND_20_1.0` | 6 | +0.7271 | `kdj_J_9_3` | 37072 | **ship** |
| `vstop2` | `VSTOP2_DIST_PCT_20_1.0` | 6 | +0.7492 | `dist_from_high_5` | 37132 | **ship** |
| `vstop2` | `VSTOP2_TREND_20_1.0` | 6 | +0.7271 | `kdj_J_9_3` | 37072 | **ship** |
| `vzo` | `VZO_14` | 6 | +0.7760 | `NWE_MID_200_8.0_8.0` | 35944 | **disclose** |
| `williams_fractal` | `WF_DN_2` | 6 | +0.9853 | `FRACTAL_DN` | 37144 | **REVERT** |
| `williams_fractal` | `WF_UP_2` | 6 | +0.9884 | `FRACTAL_UP` | 37144 | **REVERT** |
| `wpo` | `WPO_14` | 6 | +0.6477 | `psl` | 37066 | **ship** |

## Per-indicator verdict

- **`demarker`** — DISCLOSE: `DEM_14` vs `vortex_VTXP_14` rho +0.8992 (n=37059)
- **`frama`** — DISCLOSE: `FRAMA_DIST_PCT_16` vs `NWE_MID_200_8.0_8.0` rho +0.8540 (n=35944)
- **`ht`** — DISCLOSE: `HT_PCT` vs `ebsw` rho +0.7660 (n=36910)
- **`ift`** — REVERT: `IFT_RSI_14` restates `RSI` at rho +1.0000 (n=37060)
- **`kcw`** — REVERT: `KCWe_20_2.0` restates `natr` at rho +0.9843 (n=37030)
- **`pzo`** — DISCLOSE: `PZO_14` vs `psl` rho +0.7877 (n=37066)
- **`relative_volume`** — REVERT: `RVOL_20` restates `VOL_RATIO` at rho +0.9980 (n=37024)
- **`rms`** — REVERT: `RMS_DIST_PCT_14` restates `NWE_MID_200_8.0_8.0` at rho +0.9900 (n=35944)
- **`rwi`** — REVERT: `RWIl_14` restates `vortex_VTXM_14` at rho +0.9399 (n=37060)
- **`stc_tv`** — DISCLOSE: `STCTV_23_50_10_3_3` vs `rsx` rho +0.8136 (n=36738)
- **`szo`** — SHIP: max rho +0.7289 (`SZO_14` vs `aobv_AOBV_LR_2`, n=37066)
- **`vstop`** — SHIP: max rho +0.7503 (`VSTOP_DIST_PCT_20_1.0` vs `dist_from_high_5`, n=37132)
- **`vstop2`** — SHIP: max rho +0.7492 (`VSTOP2_DIST_PCT_20_1.0` vs `dist_from_high_5`, n=37132)
- **`vzo`** — DISCLOSE: `VZO_14` vs `NWE_MID_200_8.0_8.0` rho +0.7760 (n=35944)
- **`williams_fractal`** — REVERT: `WF_UP_2` restates `FRACTAL_UP` at rho +0.9884 (n=37144)
- **`wpo`** — SHIP: max rho +0.6477 (`WPO_14` vs `psl`, n=37066)

