# MLCOL-1 — axis 3a on the 13 companions that cleared Gate E

> **RECALL LAW.** Every number below is read out of `../../Backtesting/docs/indicators/_mlcol1_axes.json`, written by `scripts/analysis/measure_mlcol1_axes.py --refresh` on **2026-09-12**.
>
> **Why this ran before anything was built.** `MLCompanionContract.md`: *"Gate E is necessary but not sufficient. Three of these five clear Gate E outright and none survives."* MLCOL-2 shipped 0 of 5. Building first and measuring after is what produced that.
>
> **Procedure.** 5 seeds × 3 chronological splits (0.6/0.7/0.8) = 15 fits per companion per horizon, `HistGradientBoostingClassifier`, `[parent]` vs `[parent, companion, NULL]` where NULL is the companion's own values shuffled. Target: sign of forward close-to-close return at 1 and 5 bars. 6 BIST daily frames.
>
> **The dispersion quoted is the ACROSS-RUN sd**, not the within-fit shuffle sd. Round 1 of MLCOL-2 quoted the latter — ten shuffles of one fitted model at one seed and one split — and shipped a false positive on `mean − 2sd > 0`. Both are printed below so they cannot be confused again.

## Verdict: **6 of 13 show evidence**

| companion | h | ΔAUC | sd across runs | imp. companion | sd across runs | within-fit sd | imp. parent | imp. NULL | beats NULL | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `DMP_14_RATIO_PCT` | 1 | +0.0031 | 0.0077 | +0.00490 | **0.00445** | 0.00322 | +0.02009 | +0.00044 | 14/15 |  |
| `DMP_14_RATIO_PCT` | 5 | +0.0043 | 0.0038 | +0.00387 | **0.00294** | 0.00361 | -0.00323 | -0.00100 | 15/15 | NO EVIDENCE |
| `HALFTREND_DIST_PCT` | 1 | +0.0037 | 0.0042 | +0.00217 | **0.00188** | 0.00274 | +0.01949 | +0.00196 | 8/15 |  |
| `HALFTREND_DIST_PCT` | 5 | +0.0032 | 0.0040 | +0.00224 | **0.00286** | 0.00317 | +0.00168 | -0.00031 | 12/15 | NO EVIDENCE |
| `HA_high_DIST_PCT` | 1 | +0.0119 | 0.0048 | +0.01082 | **0.00361** | 0.00346 | +0.01747 | +0.00090 | 15/15 |  |
| `HA_high_DIST_PCT` | 5 | -0.0003 | 0.0029 | -0.00010 | **0.00172** | 0.00268 | -0.00333 | -0.00048 | 10/15 | EVIDENCE at h=1 |
| `HA_low_DIST_PCT` | 1 | +0.0010 | 0.0040 | -0.00039 | **0.00152** | 0.00319 | +0.01935 | -0.00037 | 8/15 |  |
| `HA_low_DIST_PCT` | 5 | +0.0044 | 0.0034 | +0.00301 | **0.00177** | 0.00223 | +0.00189 | +0.00167 | 11/15 | NO EVIDENCE |
| `HW-LOWER_DIST_PCT` | 1 | +0.0025 | 0.0034 | +0.00184 | **0.00213** | 0.00297 | +0.01967 | -0.00033 | 11/15 |  |
| `HW-LOWER_DIST_PCT` | 5 | +0.0072 | 0.0038 | +0.01066 | **0.00499** | 0.00329 | +0.00630 | +0.00119 | 15/15 | EVIDENCE at h=5 |
| `HW-MID_DIST_PCT` | 1 | +0.0049 | 0.0036 | +0.00314 | **0.00275** | 0.00278 | +0.01961 | +0.00070 | 12/15 |  |
| `HW-MID_DIST_PCT` | 5 | +0.0085 | 0.0047 | +0.00889 | **0.00357** | 0.00362 | +0.00604 | +0.00006 | 15/15 | EVIDENCE at h=5 |
| `HW-UPPER_DIST_PCT` | 1 | +0.0038 | 0.0047 | +0.00190 | **0.00376** | 0.00288 | +0.01840 | +0.00087 | 9/15 |  |
| `HW-UPPER_DIST_PCT` | 5 | +0.0128 | 0.0044 | +0.01151 | **0.00370** | 0.00319 | +0.00815 | -0.00032 | 15/15 | EVIDENCE at h=5 |
| `LDECAY_5_DIST_PCT` | 1 | +0.0030 | 0.0029 | +0.00041 | **0.00170** | 0.00173 | +0.01427 | -0.00018 | 9/15 |  |
| `LDECAY_5_DIST_PCT` | 5 | +0.0026 | 0.0030 | +0.00050 | **0.00101** | 0.00131 | -0.00340 | +0.00012 | 9/15 | NO EVIDENCE |
| `LINREG_DEV_RATIO_PCT` | 1 | -0.0008 | 0.0056 | +0.00198 | **0.00432** | 0.00303 | +0.02258 | -0.00030 | 11/15 |  |
| `LINREG_DEV_RATIO_PCT` | 5 | +0.0003 | 0.0049 | +0.00104 | **0.00354** | 0.00385 | -0.00084 | -0.00014 | 8/15 | NO EVIDENCE |
| `LINREG_LOWER_2_DIST_PCT` | 1 | +0.0039 | 0.0035 | +0.00183 | **0.00231** | 0.00295 | +0.01698 | +0.00085 | 10/15 |  |
| `LINREG_LOWER_2_DIST_PCT` | 5 | +0.0048 | 0.0031 | +0.00747 | **0.00190** | 0.00343 | -0.00041 | +0.00034 | 15/15 | EVIDENCE at h=5 |
| `PDIST_RATIO_PCT` | 1 | +0.0012 | 0.0039 | +0.00740 | **0.00620** | 0.00320 | +0.02250 | +0.00316 | 11/15 |  |
| `PDIST_RATIO_PCT` | 5 | +0.0028 | 0.0048 | +0.00425 | **0.00349** | 0.00351 | -0.00228 | -0.00193 | 15/15 | NO EVIDENCE |
| `PO_14_RATIO_PCT` | 1 | -0.0002 | 0.0033 | -0.00049 | **0.00226** | 0.00127 | +0.01593 | -0.00089 | 7/15 |  |
| `PO_14_RATIO_PCT` | 5 | +0.0026 | 0.0018 | -0.00002 | **0.00113** | 0.00064 | -0.00487 | +0.00061 | 6/15 | NO EVIDENCE |
| `THERMO_20_2_0.5_RATIO_PCT` | 1 | +0.0090 | 0.0057 | +0.01315 | **0.00431** | 0.00406 | +0.02916 | -0.00129 | 15/15 |  |
| `THERMO_20_2_0.5_RATIO_PCT` | 5 | +0.0075 | 0.0053 | +0.00642 | **0.00249** | 0.00390 | +0.00561 | -0.00023 | 15/15 | EVIDENCE at h=5 |

**A companion is reported as showing evidence only if it beats its own shuffled copy in at least 11 of 15 runs AND its across-run `mean − 2sd` is positive.** No threshold is pre-registered as decisive — the contract's own "Thresholds: not pre-registered, and no longer decisive" section says why — so this column reports the evidence, it does not confer a ship.
