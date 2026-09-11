# MLCOL-1 — screening all 137 `PX` companions before building any

> **RECALL LAW.** Every ρ and every n below is read out of `../../Backtesting/docs/indicators/_mlcol1_screen.json`, written by `scripts/analysis/measure_mlcol1_screen.py --refresh` on **2026-09-12**. Nothing is hand-typed.
>
> **Why a screen and not 137 companions.** `MLCompanionContract.md` is explicit that MLCOL-1 must *"screen a proposed `DIST_PCT` against the engine's existing distance columns before building it"*, and that *"Gate E is necessary but not sufficient"* — MLCOL-2 shipped 0 of 5 after three of them cleared Gate E outright.
>
> **Measurement base.** 3 cleaned BIST daily frames (AKBNK, GARAN, THYAO), 5748–6762 bars, against **535 comparators** — the engine's full production set through `_comparators.py`, so the 7 non-numeric columns are included. Coverage floor 50%.

## 1. Verdict

| Verdict | n | Meaning |
|---|---:|---|
| **BUILD** | 13 | max ρ below 0.76 — worth building, then the two incremental axes the contract still requires |
| **BUILD-WITH-DISCLOSURE** | 36 | 0.76–0.90 |
| **DO-NOT-BUILD** | 82 | ρ ≥ 0.90 — the companion restates a shipped column |
| **EXCLUDED-NON-CAUSAL** | 2 | the PARENT reads the future, measured — a companion built on it inherits the leak |
| **SKIP** | 4 | parent not emitted on real frames, or companion constant |
| **total** | 137 | |

**82 of 137 proposed companions restate something the engine already ships.** Building all 137 would have added 82 columns of duplicated signal to the miner's feature space.

## 2. The parent shape problem, measured

The contract defines ONE distance shape, `(close - parent) / close`, which is right for a **level** parent and wrong-shaped for a **difference** parent already centred on zero — there it evaluates to about 1.0 with the signal in the fourth decimal. Classified by measurement (median |parent| against median close, plus whether the parent changes sign): **100 level**, **35 difference**. The difference parents are screened as `100 * parent / close` instead, and that deviation from the contract is recorded here rather than applied silently. **The companion is NAMED for its shape** — `_DIST_PCT` for a level parent, `_RATIO_PCT` for a difference parent — because naming is API in this fork and a mined rule matches on the string; calling `parent / close` a "distance" would misdescribe it permanently.

## 3. Every column

| Column | indicator | parent | companion form | max ρ | vs | n | vs the named distance cols | verdict |
|---|---|---|---|---:|---|---:|---|---|
| `ABER_ATR_5_15` | `aberration` | difference | `100 * parent / close` | +0.9639 | `natr` | 19227 | -0.2136 vs `ATR_POSITION` | **DO-NOT-BUILD** |
| `ABER_SG_5_15` | `aberration` | level | `100 * (close - parent) / close` | +0.9045 | `dist_from_high_5` | 19227 | +0.7460 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `ABER_XG_5_15` | `aberration` | level | `100 * (close - parent) / close` | +0.8855 | `dist_low_5` | 19227 | +0.6764 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |
| `ABER_ZG_5_15` | `aberration` | level | `100 * (close - parent) / close` | +0.8402 | `dist_from_high_5` | 19260 | +0.7608 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |
| `ACCBL_20` | `accbands` | level | `100 * (close - parent) / close` | +0.9533 | `NWE_LOWER_200_8.0_8.0` | 18672 | +0.9084 vs `bias` | **DO-NOT-BUILD** |
| `ACCBM_20` | `accbands` | level | `100 * (close - parent) / close` | +1.0000 | `bias` | 19215 | +1.0000 vs `bias` | **DO-NOT-BUILD** |
| `ACCBU_20` | `accbands` | level | `100 * (close - parent) / close` | +0.9676 | `NWE_UPPER_200_8.0_8.0` | 18672 | +0.9286 vs `ATR_POSITION` | **DO-NOT-BUILD** |
| `ALMA_10_6.0_0.85` | `alma` | level | `100 * (close - parent) / close` | +0.9447 | `cg` | 19242 | +0.9410 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `AO_5_34` | `ao` | difference | `100 * parent / close` | +0.9515 | `tsi` | 19173 | +0.7579 vs `bias` | **DO-NOT-BUILD** |
| `APO_12_26` | `apo` | difference | `100 * parent / close` | +0.9997 | `ppo_PPO_12_26_9` | 19197 | +0.6561 vs `bias` | **DO-NOT-BUILD** |
| `ATR2_14` | `atr2` | difference | `100 * parent / close` | +0.9701 | `natr` | 19233 | -0.2091 vs `ATR_POSITION` | **DO-NOT-BUILD** |
| `ATRr_14` | `atr` | difference | `100 * parent / close` | +0.9703 | `natr` | 19230 | -0.2090 vs `ATR_POSITION` | **DO-NOT-BUILD** |
| `BBL_5_2.0` | `bbands` | level | `100 * (close - parent) / close` | +0.8016 | `dist_low_5` | 19257 | +0.5307 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |
| `BBM_5_2.0` | `bbands` | level | `100 * (close - parent) / close` | +0.8279 | `NWOG_BOTTOM` | 19260 | +0.7456 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |
| `BBU_5_2.0` | `bbands` | level | `100 * (close - parent) / close` | +0.7989 | `dist_from_high_5` | 19257 | +0.5303 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |
| `BEARP_13` | `eri` | difference | `100 * parent / close` | +0.9411 | `NWE_MID_200_8.0_8.0` | 18672 | +0.9411 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `BULLP_13` | `eri` | difference | `100 * parent / close` | +0.9364 | `NWE_MID_200_8.0_8.0` | 18672 | +0.9364 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `CKSPl_10_3_20` | `cksp` | level | `100 * (close - parent) / close` | +0.9265 | `ICHI_PRICE_VS_KIJUN` | 19185 | +0.8737 vs `bias` | **DO-NOT-BUILD** |
| `CKSPs_10_3_20` | `cksp` | level | `100 * (close - parent) / close` | +0.9333 | `ICHI_PRICE_VS_KIJUN` | 19185 | +0.8778 vs `bias` | **DO-NOT-BUILD** |
| `DCL_20_20` | `donchian` | level | `100 * (close - parent) / close` | +0.9882 | `dist_low_20` | 19215 | +0.8408 vs `bias` | **DO-NOT-BUILD** |
| `DCM_20_20` | `donchian` | level | `100 * (close - parent) / close` | +0.9649 | `bias` | 19215 | +0.9649 vs `bias` | **DO-NOT-BUILD** |
| `DCU_20_20` | `donchian` | level | `100 * (close - parent) / close` | +0.9856 | `dist_from_high_20` | 19215 | +0.8457 vs `BB_%B` | **DO-NOT-BUILD** |
| `DD` | `drawdown` | difference | `100 * parent / close` | +1.0000 | `drawdown_DD_LOG` | 19272 | -0.3629 vs `ATR_POSITION` | **DO-NOT-BUILD** |
| `DEMA2_10` | `dema2` | level | `100 * (close - parent) / close` | +0.9166 | `cfo` | 19233 | +0.5795 vs `dist_to_psar_pct` | **DO-NOT-BUILD** |
| `DEMA_10` | `dema` | level | `100 * (close - parent) / close` | +0.9164 | `cfo` | 19233 | +0.5800 vs `dist_to_psar_pct` | **DO-NOT-BUILD** |
| `DMN_14` | `dm` | difference | `100 * parent / close` | +0.8152 | `DMN` | 19230 | -0.6827 vs `ATR_POSITION` | **BUILD-WITH-DISCLOSURE** |
| `DMP_14` | `dm` | difference | `100 * parent / close` | +0.7325 | `NWE_LOWER_200_8.0_8.0` | 18672 | +0.4873 vs `bias` | **BUILD** |
| `DPO_20` | `dpo` | — | — | — | — | — | — | **SKIP** — parent READS THE FUTURE -- altering only bars >= 75% moves earlier bars by 1.576123 |
| `DSP_14` | `dsp` | difference | `100 * parent / close` | +0.9966 | `NWE_MID_200_8.0_8.0` | 18672 | +0.9966 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `EFI_13` | `efi` | difference | `100 * parent / close` | +0.9342 | `efi` | 19236 | +0.8469 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `EMA2_10` | `ema2` | level | `100 * (close - parent) / close` | +0.9835 | `NWE_MID_200_8.0_8.0` | 18672 | +0.9835 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `EMA_10` | `ema` | level | `100 * (close - parent) / close` | +0.9835 | `NWE_MID_200_8.0_8.0` | 18672 | +0.9835 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `FWMA_10` | `fwma` | level | `100 * (close - parent) / close` | +0.8336 | `dist_from_high_5` | 19245 | +0.7906 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |
| `HALFTREND` | `halftrend` | level | `100 * (close - parent) / close` | +0.7245 | `NWE_MID_200_8.0_8.0` | 18672 | +0.7245 vs `NWE_MID_200_8.0_8.0` | **BUILD** |
| `HA_close` | `ha` | level | `100 * (close - parent) / close` | +0.8596 | `VOL_DELTA` | 19272 | +0.3189 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |
| `HA_high` | `ha` | level | `100 * (close - parent) / close` | +0.7035 | `DIST_PREV_HIGH` | 19269 | +0.4181 vs `NWE_MID_200_8.0_8.0` | **BUILD** |
| `HA_low` | `ha` | level | `100 * (close - parent) / close` | +0.6952 | `AVWAP_Z_W` | 14921 | +0.4264 vs `NWE_MID_200_8.0_8.0` | **BUILD** |
| `HA_open` | `ha` | level | `100 * (close - parent) / close` | +0.8760 | `PDFIB_MID` | 19269 | +0.7370 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |
| `HILO_13_21` | `hilo` | level | `100 * (close - parent) / close` | +0.9721 | `bias` | 19210 | +0.9721 vs `bias` | **DO-NOT-BUILD** |
| `HILOl_13_21` | `hilo` | level | `100 * (close - parent) / close` | +0.9363 | `bias` | 12320 | +0.9363 vs `bias` | **DO-NOT-BUILD** |
| `HILOs_13_21` | `hilo` | level | `100 * (close - parent) / close` | +0.9271 | `bias` | 10967 | +0.9271 vs `bias` | **DO-NOT-BUILD** |
| `HL2` | `hl2` | level | `100 * (close - parent) / close` | +0.8954 | `VOL_DELTA` | 19272 | +0.3041 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |
| `HLC3` | `hlc3` | level | `100 * (close - parent) / close` | +0.8954 | `VOL_DELTA` | 19272 | +0.3041 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |
| `HMA_10` | `hma` | level | `100 * (close - parent) / close` | +0.8160 | `PDFIB_MID` | 19239 | +0.2928 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |
| `HW-LOWER` | `hwc` | level | `100 * (close - parent) / close` | -0.6087 | `ppo_PPOs_12_26_9` | 19197 | +0.3918 vs `dist_to_psar_pct` | **BUILD** |
| `HW-MID` | `hwc` | level | `100 * (close - parent) / close` | +0.6257 | `cfo` | 19233 | +0.4434 vs `dist_to_psar_pct` | **BUILD** |
| `HW-UPPER` | `hwc` | level | `100 * (close - parent) / close` | +0.6103 | `cfo` | 19233 | +0.4402 vs `dist_to_psar_pct` | **BUILD** |
| `ICS_26` | `ichimoku` | — | — | — | — | — | — | **SKIP** — parent READS THE FUTURE -- altering only bars >= 75% moves earlier bars by 3.457598 |
| `IKS_26` | `ichimoku` | — | — | — | — | — | — | **SKIP** — length mismatch against the engine frame |
| `ISA_9` | `ichimoku` | — | — | — | — | — | — | **SKIP** — length mismatch against the engine frame |
| `ISB_26` | `ichimoku` | — | — | — | — | — | — | **SKIP** — length mismatch against the engine frame |
| `ITS_9` | `ichimoku` | — | — | — | — | — | — | **SKIP** — length mismatch against the engine frame |
| `JMA_7_0` | `jma` | level | `100 * (close - parent) / close` | +0.8495 | `PDFIB_MID` | 19254 | +0.5551 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |
| `KAMA_10_2_30` | `kama` | level | `100 * (close - parent) / close` | +0.9198 | `NWE_MID_200_8.0_8.0` | 18672 | +0.9198 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `KCBe_20_2` | `kc` | level | `100 * (close - parent) / close` | +0.9787 | `bias` | 19215 | +0.9787 vs `bias` | **DO-NOT-BUILD** |
| `KCLe_20_2` | `kc` | level | `100 * (close - parent) / close` | +0.9633 | `NWE_LOWER_200_8.0_8.0` | 18672 | +0.8860 vs `bias` | **DO-NOT-BUILD** |
| `KCUe_20_2` | `kc` | level | `100 * (close - parent) / close` | +0.9790 | `NWE_UPPER_200_8.0_8.0` | 18672 | +0.9196 vs `ATR_POSITION` | **DO-NOT-BUILD** |
| `LDECAY_5` | `decay` | level | `100 * (close - parent) / close` | -0.4530 | `true_range` | 19269 | +0.1633 vs `NWE_MID_200_8.0_8.0` | **BUILD** |
| `LINREG_DEV` | `linreg_channel` | difference | `100 * parent / close` | +0.7331 | `natr` | 19215 | -0.1720 vs `ATR_POSITION` | **BUILD** |
| `LINREG_LOWER_1` | `linreg_channel` | level | `100 * (close - parent) / close` | +0.7934 | `cfo` | 19215 | +0.6133 vs `dist_to_psar_pct` | **BUILD-WITH-DISCLOSURE** |
| `LINREG_LOWER_2` | `linreg_channel` | level | `100 * (close - parent) / close` | +0.7186 | `cfo` | 19215 | +0.5191 vs `dist_to_psar_pct` | **BUILD** |
| `LINREG_UPPER_1` | `linreg_channel` | level | `100 * (close - parent) / close` | +0.7836 | `cfo` | 19215 | +0.6556 vs `dist_to_psar_pct` | **BUILD-WITH-DISCLOSURE** |
| `LINREG_UPPER_2` | `linreg_channel` | level | `100 * (close - parent) / close` | +0.7706 | `dist_from_high_5` | 19215 | +0.5955 vs `dist_to_psar_pct` | **BUILD-WITH-DISCLOSURE** |
| `LINREG_VALUE` | `linreg_channel` | level | `100 * (close - parent) / close` | +0.8080 | `cfo` | 19215 | +0.6619 vs `dist_to_psar_pct` | **BUILD-WITH-DISCLOSURE** |
| `LR_14` | `linreg` | level | `100 * (close - parent) / close` | +0.9629 | `cfo` | 19233 | +0.5915 vs `dist_to_psar_pct` | **DO-NOT-BUILD** |
| `MACD_12_26_9` | `macd` | difference | `100 * parent / close` | +0.9820 | `tsi` | 19197 | +0.7191 vs `bias` | **DO-NOT-BUILD** |
| `MACDh_12_26_9` | `macd` | difference | `100 * parent / close` | +0.8769 | `MACDh_12_26_9` | 19173 | +0.8031 vs `bias` | **BUILD-WITH-DISCLOSURE** |
| `MACDs_12_26_9` | `macd` | difference | `100 * parent / close` | +0.9958 | `trix_TRIX_14_9` | 19173 | +0.5021 vs `bias` | **DO-NOT-BUILD** |
| `MAD_30` | `mad` | difference | `100 * parent / close` | +0.7883 | `BB_BWidth` | 19185 | -0.0434 vs `dist_to_psar_pct` | **BUILD-WITH-DISCLOSURE** |
| `MCGD_10` | `mcgd` | level | `100 * (close - parent) / close` | +0.9519 | `RSI` | 19230 | +0.9507 vs `bias` | **DO-NOT-BUILD** |
| `MEDIAN_30` | `median` | level | `100 * (close - parent) / close` | +0.9537 | `bias` | 19185 | +0.9537 vs `bias` | **DO-NOT-BUILD** |
| `MIDPOINT_2` | `midpoint` | level | `100 * (close - parent) / close` | +1.0000 | `percent_return` | 19269 | +0.4276 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `MIDPRICE_2` | `midprice` | level | `100 * (close - parent) / close` | +0.9503 | `PDFIB_MID` | 19269 | +0.4778 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `MMAR_10` | `mmar` | level | `100 * (close - parent) / close` | +0.9835 | `NWE_MID_200_8.0_8.0` | 18672 | +0.9835 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `MMAR_15` | `mmar` | level | `100 * (close - parent) / close` | +0.9945 | `NWE_MID_200_8.0_8.0` | 18672 | +0.9945 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `MMAR_20` | `mmar` | level | `100 * (close - parent) / close` | +0.9787 | `bias` | 19215 | +0.9787 vs `bias` | **DO-NOT-BUILD** |
| `MMAR_25` | `mmar` | level | `100 * (close - parent) / close` | +0.9815 | `cmo` | 19200 | +0.9610 vs `bias` | **DO-NOT-BUILD** |
| `MMAR_30` | `mmar` | level | `100 * (close - parent) / close` | +0.9812 | `cmo` | 19185 | +0.9352 vs `bias` | **DO-NOT-BUILD** |
| `MMAR_35` | `mmar` | level | `100 * (close - parent) / close` | +0.9742 | `RSI` | 19170 | +0.9071 vs `bias` | **DO-NOT-BUILD** |
| `MOM_10` | `mom` | difference | `100 * parent / close` | +0.9046 | `bias` | 19215 | +0.9046 vs `bias` | **DO-NOT-BUILD** |
| `NWE_SLOPE_200_8.0_8.0` | `nadaraya_watson_envelope` | difference | `100 * parent / close` | +0.9964 | `bias` | 18669 | +0.9964 vs `bias` | **DO-NOT-BUILD** |
| `OHLC4` | `ohlc4` | level | `100 * (close - parent) / close` | +0.8596 | `VOL_DELTA` | 19272 | +0.3189 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |
| `PDIST` | `pdist` | difference | `100 * parent / close` | +0.7590 | `HARPARK_1_5_22_500` | 17775 | -0.0468 vs `ATR_POSITION` | **BUILD** |
| `PMAX_E_10_3.0` | `pmax` | level | `100 * (close - parent) / close` | +0.8685 | `QQE_RSIMA` | 19230 | +0.8176 vs `bias` | **BUILD-WITH-DISCLOSURE** |
| `PO_14` | `po` | difference | `100 * parent / close` | +0.7050 | `ha_HA_low` | 19233 | +0.0555 vs `ATR_POSITION` | **BUILD** |
| `PSARl_0.02_0.2` | `psar` | level | `100 * (close - parent) / close` | +1.0000 | `dist_to_psar_pct` | 10347 | +1.0000 vs `dist_to_psar_pct` | **DO-NOT-BUILD** |
| `PSARs_0.02_0.2` | `psar` | level | `100 * (close - parent) / close` | +1.0000 | `dist_to_psar_pct` | 8919 | +1.0000 vs `dist_to_psar_pct` | **DO-NOT-BUILD** |
| `PVOL` | `pvol` | difference | `100 * parent / close` | +1.0000 | `Volume` | 19272 | +0.0878 vs `BB_%B` | **DO-NOT-BUILD** |
| `PWMA_10` | `pwma` | level | `100 * (close - parent) / close` | +0.9610 | `week_trend` | 19245 | +0.8852 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `QS_10` | `qstick` | difference | `100 * parent / close` | +0.8593 | `qstick` | 19245 | +0.5582 vs `ATR_POSITION` | **BUILD-WITH-DISCLOSURE** |
| `QTL_30_0.5` | `quantile` | level | `100 * (close - parent) / close` | +0.9537 | `bias` | 19185 | +0.9537 vs `bias` | **DO-NOT-BUILD** |
| `RAINBOW_1` | `rainbow` | level | `100 * (close - parent) / close` | +1.0000 | `percent_return` | 19269 | +0.4276 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `RAINBOW_10` | `rainbow` | level | `100 * (close - parent) / close` | +0.9603 | `week_trend` | 19242 | +0.9069 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `RAINBOW_2` | `rainbow` | level | `100 * (close - parent) / close` | +0.9413 | `PDFIB_MID` | 19266 | +0.5401 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `RAINBOW_3` | `rainbow` | level | `100 * (close - parent) / close` | +0.9108 | `PDFIB_MID` | 19263 | +0.6219 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `RAINBOW_4` | `rainbow` | level | `100 * (close - parent) / close` | +0.8497 | `PDFIB_MID` | 19260 | +0.6878 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |
| `RAINBOW_5` | `rainbow` | level | `100 * (close - parent) / close` | +0.8262 | `NWOG_BOTTOM` | 19257 | +0.7432 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |
| `RAINBOW_6` | `rainbow` | level | `100 * (close - parent) / close` | +0.8583 | `week_trend` | 19254 | +0.7890 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |
| `RAINBOW_7` | `rainbow` | level | `100 * (close - parent) / close` | +0.9112 | `week_trend` | 19251 | +0.8270 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `RAINBOW_8` | `rainbow` | level | `100 * (close - parent) / close` | +0.9454 | `week_trend` | 19248 | +0.8588 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `RAINBOW_9` | `rainbow` | level | `100 * (close - parent) / close` | +0.9610 | `week_trend` | 19245 | +0.8852 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `RMA2_10` | `rma2` | level | `100 * (close - parent) / close` | +0.9803 | `bias` | 19215 | +0.9803 vs `bias` | **DO-NOT-BUILD** |
| `RMA_10` | `rma` | level | `100 * (close - parent) / close` | +0.9804 | `bias` | 19215 | +0.9804 vs `bias` | **DO-NOT-BUILD** |
| `SINWMA_14` | `sinwma` | level | `100 * (close - parent) / close` | +0.9821 | `NWE_MID_200_8.0_8.0` | 18672 | +0.9821 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `SLOPE_1` | `slope` | difference | `100 * parent / close` | +1.0000 | `percent_return` | 19269 | +0.4276 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `SMA_10` | `sma` | level | `100 * (close - parent) / close` | +0.9485 | `NWE_MID_200_8.0_8.0` | 18672 | +0.9485 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `SQZPRO_20_2.0_20_2_1.5_1` | `squeeze_pro` | difference | `100 * parent / close` | +0.9860 | `coppock` | 19203 | +0.8243 vs `bias` | **DO-NOT-BUILD** |
| `SQZ_20_2.0_20_1.5` | `squeeze` | difference | `100 * parent / close` | +0.9860 | `coppock` | 19203 | +0.8243 vs `bias` | **DO-NOT-BUILD** |
| `SSF_10_2` | `ssf` | level | `100 * (close - parent) / close` | +0.8699 | `PDFIB_MID` | 19269 | +0.6350 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |
| `STCmacd_10_12_26_0.5` | `stc` | difference | `100 * parent / close` | +0.9820 | `tsi` | 19197 | +0.7191 vs `bias` | **DO-NOT-BUILD** |
| `STDEV_30` | `stdev` | difference | `100 * parent / close` | +0.7946 | `BB_BWidth` | 19185 | -0.0401 vs `dist_to_psar_pct` | **BUILD-WITH-DISCLOSURE** |
| `SUM_10` | `rolling_sum` | difference | `100 * parent / close` | -0.9485 | `NWE_MID_200_8.0_8.0` | 18672 | -0.9485 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `SUPERT2_7_3.0` | `supertrend2` | level | `100 * (close - parent) / close` | +0.8720 | `ICHI_PRICE_VS_KIJUN` | 19197 | +0.8643 vs `bias` | **BUILD-WITH-DISCLOSURE** |
| `SUPERT2l_7_3.0` | `supertrend2` | level | `100 * (close - parent) / close` | +0.9196 | `NWE_LOWER_200_8.0_8.0` | 10104 | +0.7838 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `SUPERT2s_7_3.0` | `supertrend2` | level | `100 * (close - parent) / close` | +0.9356 | `NWE_UPPER_200_8.0_8.0` | 8568 | +0.8511 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `SUPERT_7_3.0` | `supertrend` | level | `100 * (close - parent) / close` | +0.8711 | `ICHI_PRICE_VS_KIJUN` | 19197 | +0.8635 vs `bias` | **BUILD-WITH-DISCLOSURE** |
| `SUPERTl_7_3.0` | `supertrend` | level | `100 * (close - parent) / close` | +0.9191 | `NWE_LOWER_200_8.0_8.0` | 10103 | +0.7838 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `SUPERTs_7_3.0` | `supertrend` | level | `100 * (close - parent) / close` | +0.9337 | `NWE_UPPER_200_8.0_8.0` | 8569 | +0.8485 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `SWMA_10` | `swma` | level | `100 * (close - parent) / close` | +0.9442 | `week_trend` | 19245 | +0.9198 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `T3_10_0.7` | `t3` | level | `100 * (close - parent) / close` | +0.9302 | `NWE_MID_200_8.0_8.0` | 18672 | +0.9302 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `T3tv_10_0.7` | `t3_tv` | level | `100 * (close - parent) / close` | +0.9302 | `NWE_MID_200_8.0_8.0` | 18672 | +0.9302 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `TEMA2_10` | `tema2` | level | `100 * (close - parent) / close` | +0.8864 | `cfo` | 19233 | +0.2195 vs `dist_to_psar_pct` | **BUILD-WITH-DISCLOSURE** |
| `TEMA_10` | `tema` | level | `100 * (close - parent) / close` | +0.8863 | `cfo` | 19233 | +0.2203 vs `dist_to_psar_pct` | **BUILD-WITH-DISCLOSURE** |
| `THERMO_20_2_0.5` | `thermo` | difference | `100 * parent / close` | +0.4669 | `natr` | 19233 | -0.0457 vs `ATR_POSITION` | **BUILD** |
| `THERMOma_20_2_0.5` | `thermo` | difference | `100 * parent / close` | +0.9156 | `natr` | 19215 | -0.1656 vs `ATR_POSITION` | **DO-NOT-BUILD** |
| `TRIMA_10` | `trima` | level | `100 * (close - parent) / close` | +0.9408 | `NWE_MID_200_8.0_8.0` | 18672 | +0.9408 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `TRUERANGE_1` | `true_range` | difference | `100 * parent / close` | +0.7676 | `HARPARK_1_5_22_500` | 17775 | -0.0658 vs `ATR_POSITION` | **BUILD-WITH-DISCLOSURE** |
| `VIDYA_14` | `vidya` | level | `100 * (close - parent) / close` | +0.9220 | `close_vs_qtr_mean_pct` | 19086 | +0.8422 vs `bias` | **DO-NOT-BUILD** |
| `VWAP_D` | `vwap` | level | `100 * (close - parent) / close` | +0.8840 | `VOL_DELTA` | 18604 | +0.3089 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |
| `VWMACD_12_26_9` | `vwmacd` | difference | `100 * parent / close` | +0.9783 | `ppo_PPO_12_26_9` | 19197 | +0.6738 vs `bias` | **DO-NOT-BUILD** |
| `VWMACDh_12_26_9` | `vwmacd` | difference | `100 * parent / close` | +0.8961 | `ppo_PPOh_12_26_9` | 19169 | +0.5596 vs `bias` | **BUILD-WITH-DISCLOSURE** |
| `VWMACDs_12_26_9` | `vwmacd` | difference | `100 * parent / close` | +0.9776 | `ppo_PPOs_12_26_9` | 19169 | +0.4325 vs `bias` | **DO-NOT-BUILD** |
| `VWMA_10` | `vwma` | level | `100 * (close - parent) / close` | +0.9276 | `NWE_MID_200_8.0_8.0` | 18670 | +0.9276 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `WCP` | `wcp` | level | `100 * (close - parent) / close` | +0.8954 | `VOL_DELTA` | 19272 | +0.3041 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |
| `WMA_10` | `wma` | level | `100 * (close - parent) / close` | +0.9147 | `week_trend` | 19245 | +0.8919 vs `NWE_MID_200_8.0_8.0` | **DO-NOT-BUILD** |
| `WRMA_10` | `wilder_rma` | level | `100 * (close - parent) / close` | +0.9804 | `bias` | 19215 | +0.9804 vs `bias` | **DO-NOT-BUILD** |
| `ZL_EMA_10` | `zlma` | level | `100 * (close - parent) / close` | +0.8806 | `PDFIB_MID` | 19245 | +0.4311 vs `NWE_MID_200_8.0_8.0` | **BUILD-WITH-DISCLOSURE** |

## 3b. The five SKIPs are `ichimoku`, and they already have a companion

All five skipped columns (`ITS_9`, `IKS_26`, `ISA_9`, `ISB_26`, `ICS_26`) come from `ichimoku`, whose frame is LONGER than its input because the Senkou spans are projected forward — so it cannot be length-matched against an engine frame. That is structural, not a measurement failure. It is also already solved: `ichimoku_ml` is the fork's existing scale-free conversion of exactly these five lines into eight causal columns, and `MLCompanionContract.md` §2 cites it as the DISTANCE precedent. **No companion is owed for these five.**

## 4. What to build

The 13 that clear Gate E:

- **`DMP_14_RATIO_PCT`** (from `dm`, difference parent) — max ρ +0.7325 vs `NWE_LOWER_200_8.0_8.0`, n=18672
- **`HALFTREND_DIST_PCT`** (from `halftrend`, level parent) — max ρ +0.7245 vs `NWE_MID_200_8.0_8.0`, n=18672
- **`HA_high_DIST_PCT`** (from `ha`, level parent) — max ρ +0.7035 vs `DIST_PREV_HIGH`, n=19269
- **`HA_low_DIST_PCT`** (from `ha`, level parent) — max ρ +0.6952 vs `AVWAP_Z_W`, n=14921
- **`HW-LOWER_DIST_PCT`** (from `hwc`, level parent) — max ρ -0.6087 vs `ppo_PPOs_12_26_9`, n=19197
- **`HW-MID_DIST_PCT`** (from `hwc`, level parent) — max ρ +0.6257 vs `cfo`, n=19233
- **`HW-UPPER_DIST_PCT`** (from `hwc`, level parent) — max ρ +0.6103 vs `cfo`, n=19233
- **`LDECAY_5_DIST_PCT`** (from `decay`, level parent) — max ρ -0.4530 vs `true_range`, n=19269
- **`LINREG_DEV_RATIO_PCT`** (from `linreg_channel`, difference parent) — max ρ +0.7331 vs `natr`, n=19215
- **`LINREG_LOWER_2_DIST_PCT`** (from `linreg_channel`, level parent) — max ρ +0.7186 vs `cfo`, n=19215
- **`PDIST_RATIO_PCT`** (from `pdist`, difference parent) — max ρ +0.7590 vs `HARPARK_1_5_22_500`, n=17775
- **`PO_14_RATIO_PCT`** (from `po`, difference parent) — max ρ +0.7050 vs `ha_HA_low`, n=19233
- **`THERMO_20_2_0.5_RATIO_PCT`** (from `thermo`, difference parent) — max ρ +0.4669 vs `natr`, n=19233

⚠ **Clearing this screen is NOT approval to ship.** The contract requires two further axes for anything built — a model axis over 5 seeds × 3 split points against a shuffled null, and a conditional rank axis against a placebo. MLCOL-2 ran neither in its round 1 and produced two false SHIPs out of two.
