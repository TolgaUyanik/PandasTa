# The ML companion contract (MLCOL-0)

> **Note (2026-10-24, Backtesting #107):** the `measure_*` scripts this record cites were never
> committed. The rebuilt Gate E harness is `../Backtesting/Backtesting/scripts/analysis/gate_e_overlap.py`,
> and its comparator set differs: 329 + 358 columns today vs the 485/492-column engine of 2026-09,
> which no longer exists. The text below is left as it was run.

> **Goal (user):** *"We should optimize each indicator for ML. Each indicator
> should show binary fields like cheap, expensive or buy & sell type of things.
> Also it should include percentage based analysis."*

**Decision (user, 2026-09-06): hand-authored per indicator, not a generic
transform layer.** The threshold that means "expensive" is indicator-specific,
and a generic percentile is wrong for a bounded oscillator and meaningless for
an event flag.

This document is the contract. It is designed on three indicators chosen to be
the three *shapes* the fork actually contains, so the remaining rollout is
mechanical rather than a fresh decision each time.

---

## Why three shapes, not 201 decisions

`docs/IndicatorDictionary.md` already classifies every shipped column by its observed ML form.

Measured on the live package (parsed from the dictionary, 684 tagged columns): **137 `PX`** (price-level), **324 `SF`** (scale-free), **104 `BIN`** (binary), 54 `ORD`, 42 `CONST`, 2 `PX2`, 21 `??`. (683 -> 684 / 53 -> 54 `ORD` on issue #100's `ts_cross_mean_20` port (statistics): `TS_CROSS_MEAN_20`, how many of the 19 adjacent pairs of a 20-bar window of LOG closes straddle that window's own mean -- tsfresh's `number_crossing_m(x, m=mean)`. It lands in the `ORD` tally rather than the `SF` one for the same reason `TS_PEAKS_20_2` does: `classify` tags a column `ORD` when the probe sees at most 12 distinct values and all are integers, which a count is. That is right -- it is scale-free by construction, reading only the ORDER of the log closes against their own mean, so it is bit-equal under `price ** 2`, `price ** 0.5` and even `1 / price`, but it is coarse and heavily tied (19 reachable values, 13 of them on a 1,500-bar walk, the value 1 taking 339 of 1,481 bars). Three things a consumer must know before using it. ⚠ It is a CHOPPINESS reading: a monotone window reads 1 whatever its slope and an alternating one reads 19, so on six synthetic frames it reads +0.5289 .. +0.6296 against the shipped `chop`, -0.4813 .. -0.5607 against `vhf`, and +0.2171 .. +0.4812 / +0.2145 .. +0.3540 against `TS_PERMENT_20_3` / `TS_PEAKS_20_2`, which read the SAME 20 closes. ⚠ It is a window-DISPERSION reading upside down -- Spearman -0.6827 against the window's own log-close standard deviation on a walk -- while being nearly blind to realised volatility (+0.1045) and to the price level (-0.1178). ⚠ Its floor is the only thing standing between it and the arithmetically impossible value 0: the unguarded spelling reports 0 on all 281 windows of a flat frame, and 0 cannot occur for a window whose closes are not all equal. Gate E pending, run by issue-solver after this session; the 2026-10-24 screen measured its PROTOTYPE at max |rho| 0.5500 vs `BB_BWidth_Pctl` over n = 391,907 (SHIP), and this port is bit-equal to that prototype on 1,481 of 1,481 bars of each of nine frames. See `docs/TsCrossMean20Measured.md`.) (682 -> 683 / 323 -> 324 `SF` on issue #99's `ts_imq_20` port (statistics): `TS_IMQ_20`, the index mass quantile of a 20-|return| window at q = 0.5 -- WHERE in the window half of the absolute-return mass has piled up, as a fraction of it. Scale-free beyond a price rescale: multiplying every |return| by any positive constant cannot move it (bit-identical at `r x 2`, `r x 0.5`, `r x 1e-6` on all 1,480 fired bars of a walk), so it reads Spearman -0.0156 against that window's return sd. ⚠ It is an ORDINAL, not a continuum: at most `length` values, `k / 20` for k in 1..20, and a frame may reach as few as 2 of them (a two-point frame) or all 20 (heavy-tailed). ⚠ It overlaps the shipped `TFCENTROID_20` -- the energy-weighted MEAN position of the same 20 returns against this absolute-mass MEDIAN position -- at pooled +0.8466 over nine synthetic frames, per-frame |rho| median 0.8545, max 0.8857, 0 of 9 at or above 0.90: DISCLOSE_GAP under `r3-perframe-0.90`, not STRUCK, and no real-frame figure for the pair exists. Gate E SHIP, max |rho| 0.5254 vs `ATR_Ratio_5_20_Pctl` over n = 391,818, per-frame max median 0.5258 vs `ATR_Ratio_5_20` over 89 frames, 0 of 89 frames at or above 0.90 (run `is99-ts_imq_20-d5aaa69c`, 2026-11-14) -- which settles the band but not the `TFCENTROID_20` pair above, since the 687 comparators hold no pandas_ta port. See `docs/TsImq20Measured.md`.) (681 -> 682 / 52 -> 53 `ORD` on issue #152's `firstzero_ac` port (statistics): `FIRSTZEROAC_100` (`ORD`); Gate E pending, revert this with the port -- see `docs/FirstzeroAcMeasured.md`.) (680 -> 681 / 322 -> 323 `SF` on issue #183's `edge` port (volatility): `EDGE_21`; Gate E pending, revert this with the port -- see `docs/EdgeMeasured.md`.) (679 -> 680 / 321 -> 322 `SF` on issue #154's `arch_lm` port (statistics): `ARCHLM_100`; Gate E pending, revert this with the port -- see `docs/ArchLmMeasured.md`.) (678 -> 679 / 320 -> 321 `SF` on issue #156's `lumpiness` port (statistics): `LUMPINESS_100`; Gate E pending, revert this with the port -- see `docs/LumpinessMeasured.md`.) (677 -> 678 / 319 -> 320 `SF` on issue #153's `diff2_acf1` port (statistics): `DIFF2ACF1_100`; Gate E pending, revert this with the port -- see `docs/Diff2Acf1Measured.md`.) (676 -> 677 / 318 -> 319 `SF` on issue #4's `halflife` port (statistics): `HLIFE_100`; Gate E pending, revert this with the port.) (675 -> 676 / 317 -> 318 `SF` on issue #98's `ts_medskew_20` port (statistics): `TS_MEDSKEW_20`, `(mean - median) / sd` of a 20-return window -- the NONPARAMETRIC skewness, Pearson's second coefficient without its factor 3. Scale-free well beyond a price rescale: the statistic is invariant to any affine map of the RETURNS with a positive slope, so it reads Spearman +0.0800 against the same window's return standard deviation, -0.1129 against its mean return and +0.0737 against the close itself on a walk. Three things a consumer must know before using it. ⚠ It OVERLAPS the column merged earlier the SAME day (`6ace3dd`, merge `b99eeb5`, 2026-11-13): `TS_ABOVE_MEAN_20` (issue #97) is a backwards skewness reading over the SAME 20 returns, and the pair measures -0.8885 on a walk and -0.9025 on a heavy-tailed frame -- SYNTHETIC figures, with the real-frame number being the screen's pooled **0.8428** of 2026-10-24, which is DISCLOSE_GAP and not STRUCK under `r3-perframe-0.90`. Gate E cannot see the pair at all, because its 687 comparators are the engine's and hold no pandas_ta port; if the owner reads 0.8428 as a restatement, this is the column to revert, and `docs/TsMedskew20Measured.md` §O is the receipt. It also reads +0.6485 / +0.8028 against the shipped `OSAP_RETSKEW_21` on those two frames. ⚠ It is BOUNDED by sqrt(19/20) = 0.974679 (a theorem, `|mean - median| <= sd_pop`), the largest value any window built for the receipt reaches is 0.881631, and its neighbour is a trap: an 11/9 split of a two-level window reads 0.8816 where a 10/10 split reads 0. ⚠ Its one lossy case is a path whose returns have `|mean|/sd` = 1e5, where `mean - median` cancels five digits and the agreement with an exact rational oracle falls from 3.3e-16 to 4.3e-11. Gate E SHIP, max |rho| 0.3727 vs `PVT_Slope_norm` over n = 396,970, per-frame max median 0.3693 vs the same comparator over 89 frames, 0 of 89 frames at or above 0.80 on any of the top five (run `is98-ts_medskew_20-3303ebf4`, 2026-11-13) -- which settles the band but not the 0.8428 pair above, since the comparator set cannot see it. See `docs/TsMedskew20Measured.md`.) (674 -> 675 / 316 -> 317 `SF` on issue #97's `ts_above_mean_20` port (statistics): `TS_ABOVE_MEAN_20`, the share of a 20-return window's returns that sit strictly above that window's own mean -- tsfresh's `count_above_mean / n`. Scale-free well beyond a price rescale: the COUNT is invariant to any affine map of the RETURNS, so it reads Spearman -0.0746 against the same window's return standard deviation and 0.0699 against its mean return on a walk. Two things a consumer must know before using it. It is a SKEWNESS reading and it reads BACKWARDS -- a few large gains pull the mean up and push the column DOWN -- so it overlaps the shipped `OSAP_RETSKEW_21` at -0.6141 on a walk, -0.8581 on a heavy-tailed frame and -0.9619 on a two-point frame, where returns take two values and the column is a relabelling of "how many up-returns". Those three are SYNTHETIC and they are the only measurement of that pair that exists: Gate E's 687 comparators hold no pandas_ta port, and the screen's real-frame fork overlap (max |rho| 0.2405 vs `qqe:QQEs_14_5_4.236`, 12 frames) predates `osap_retskew_21` by nine days, so it cannot bound this pair. The adverse real-frame number that DOES exist is pooled 0.8428 against the screen's `ts_medskew_20` candidate, `(mean - median)/std` on the same 20 returns -- not shipped (issue #98), but the pair to decide if it ever is. ⚠ That last clause was written on 2026-11-13 and went stale the same day: `ts_medskew_20` SHIPPED under #98, so the 0.8428 is an IN-FORK pair from that commit on, and the decision it names is now live rather than hypothetical -- see `docs/TsMedskew20Measured.md` §O. The same stale wording survives in `pandas_ta/statistics/ts_above_mean_20.py`'s docstring ("still a prototype and not shipped") and in `docs/TsAboveMean20Measured.md` §5 ("no module in `pandas_ta/`"), neither of which issue #98's session was allowed to edit. And it is COARSE: 19 reachable values, 0.05 .. 0.95, with 0.50 taking 402 of 1,480 bars of a walk, so it is `SF` in form but heavily tied in practice. Gate E SHIP, max |rho| 0.3594 vs `PVT_Slope_norm` over n = 396,970, per-frame max median 0.3581 vs the same comparator over 89 frames (run `is97-ts_above_mean_20-5d78f565`, 2026-11-13). See `docs/TsAboveMean20Measured.md`.) (673 -> 674 / 315 -> 316 `SF` on issue #96's `ts_aggac_60` port (statistics): `TS_AGGAC_60_10`, the MEAN of the lag-1..lag-10 return autocorrelations of 60 returns -- invariant to any affine map of the returns, so it is neither a volatility nor a direction column, and bounded in [-0.310043, +0.915798] with the two ends deliberately asymmetric; Gate E SHIP, max |rho| 0.2676 vs `mad_pct` over n = 393,509, per-frame max median 0.2634 vs `MACD_Cross_Age` over 89 frames (run `is96-ts_aggac_60-d6ed198b`, 2026-11-13). Two things a consumer must know before using it: it is NOT a restatement of the shipped `TS_AC1_60` (Spearman 0.3739 / 0.0008 / 0.3787 / -0.2027 on four synthetic frames), and it is BLIND to a seasonality whose period divides 10 -- a path repeating every 2, 5 or 10 bars reads ~0 where the lag-1 column reads -1.0000 / -0.5872 / -0.5674. See `docs/TsAggac60Measured.md`.) (672 -> 673 / 314 -> 315 `SF` on issue #95's `ts_cid_ce_20` port (statistics): `TS_CID_CE_20`, tsfresh's CID-CE complexity estimate of 20 returns -- invariant to any affine map of the returns, so it is NOT a volatility column (Spearman 0.0072 against the same window's standard deviation, where tsfresh's `normalize=False` mode reads 0.8243), and bounded in [0.701759, 8.916700]; Gate E SHIP, 0.2641 vs `chop` in `docs/gate_e_ledger.csv`, which is the screen prototype's figure at the screen's own n = 396,927 -- and note it is a near-monotone restatement of the lag-1 return autocorrelation AT THE SAME WINDOW, so it reads -0.9777 against `ts_ac1_60` at `length` 20 and -0.4218 against the shipped `TS_AC1_60`, see `docs/TsCidCe20Measured.md`.) (671 -> 672 / 313 -> 314 `SF` on issue #94's `ts_ac1_60` port (statistics): `TS_AC1_60`, the lag-1 autocorrelation of 60 returns -- invariant to any affine map of the returns, so it is neither a volatility nor a direction column; Gate E SHIP, 0.2536 vs `mad_pct` in `docs/gate_e_ledger.csv` -- and note this column is NOT the one issue #94's screen measured, though the run landed within 0.0003 of the screen's figure anyway, see `docs/TsAc160Measured.md`.) (670 -> 671 / 312 -> 313 `SF` on issue #93's `ts_kurt_60` port (statistics): `TS_KURT_60`, the excess kurtosis of 60 returns -- scale-free in the returns themselves, not only in the price level, which is why it is not a volatility column; Gate E SHIP, 0.2501 vs `ZIGZAG` in `docs/gate_e_ledger.csv` -- see `docs/TsKurt60Measured.md`.) (669 -> 670 / 51 -> 52 `ORD` on issue #92's `ts_peaks_20` port (statistics): `TS_PEAKS_20_2`, an integer 0..6 -- `classify` tags a column `ORD` when the probe observes at most 12 distinct values and all are integers, which a count is, so this one lands in the `ORD` tally and not the `SF` one. That is right: it is scale-free by construction (it reads only comparisons) but coarse and heavily tied. Gate E SHIP, 0.2453 vs `BB_Lower` in `docs/gate_e_ledger.csv` -- see `docs/TsPeaks20Measured.md`.) (668 -> 669 / 311 -> 312 `SF` on issue #91's `ts_perment_20` port (statistics): `TS_PERMENT_20_3`; Gate E pending, run by issue-solver after this session -- and note this column is NOT the one issue #91's screen measured, see `docs/TsPerment20Measured.md`.) (667 -> 668 / 310 -> 311 `SF` on issue #87's `lean_tdd_20` port (statistics): `LEAN_TDD_20`; Gate E pending, run by issue-solver after this session -- see `docs/LeanTdd20Measured.md`.) (666 -> 667 / 309 -> 310 `SF` on issue #89's `ts_binent_20` port (statistics): `TS_BINENT_20_5`; Gate E pending, run by issue-solver after this session -- see `docs/TsBinent20Measured.md`.) (665 -> 666 / 308 -> 309 `SF` on issue #88's `ts_c3_20` port (statistics): `TS_C3_20_1`; Gate E pending, run by issue-solver after this session -- see `docs/TsC320Measured.md`.) (664 -> 665 / 307 -> 308 `SF` on issue #86's `lean_momersion_20` port (momentum): `LEAN_MOMERSION_20`; Gate E SHIP, 0.2560 vs `chop` in `docs/gate_e_ledger.csv` -- see `docs/LeanMomersion20Measured.md`.) (663 -> 664 / 306 -> 307 `SF` on issue #85's `lean_hurst_100` port (statistics): `LEAN_HURST_100_20`; Gate E pending, run by issue-solver after this session -- see `docs/LeanHurst100Measured.md`.) (662 -> 663 / 305 -> 306 `SF` on issue #84's `g191_110` port (momentum): `G191_110_20`; Gate E pending, run by issue-solver after this session -- and note this column restates `brar`'s `BR` at a different length, see `docs/G191110Measured.md`.) (661 -> 662 / 304 -> 305 `SF` on issue #83's `g191_188` port (volatility): `G191_188_11_2`; Gate E pending, run by issue-solver after this session -- see `docs/G191188Measured.md`.) (660 -> 661 / 303 -> 304 `SF` on issue #82's `g191_022` port (momentum): `G191_022_6_3_12_1`; Gate E pending, run by issue-solver after this session -- see `docs/G191022Measured.md`.) (659 -> 660 / 302 -> 303 `SF` on issue #81's `g191_158` port (volatility): `G191_158`; Gate E pending, run by issue-solver after this session -- see `docs/G191158Measured.md`.) (658 -> 659 / 301 -> 302 `SF` on issue #79's `g191_003` port (momentum): `G191_003_6`; Gate E pending, run by issue-solver after this session -- see `docs/G191003Measured.md`.) (657 -> 658 / 300 -> 301 `SF` on issue #78's `g191_145` port (volume): `G191_145_9_26_12`; Gate E pending, run by issue-solver after this session -- see `docs/G191145Measured.md`.) (656 -> 657 / 299 -> 300 `SF` on issue #77's `g191_040` port (volume): `G191_040_26`; Gate E pending, run by issue-solver after this session -- see `docs/G191040Measured.md`.) (655 -> 656 / 298 -> 299 `SF` on issue #76's `g191_109` port (volatility): `G191_109_10_2_10_2`; Gate E pending, run by issue-solver after this session -- see `docs/G191109Measured.md`.) (654 -> 655 / 297 -> 298 `SF` on issue #75's `g191_129` port (momentum): `G191_129_12`; Gate E pending, run by issue-solver after this session -- see `docs/G191129Measured.md`.) (653 -> 654 / 296 -> 297 `SF` on issue #74's `g191_174` port (volatility): `G191_174_20_20_1`; Gate E pending, run by issue-solver after this session -- see `docs/G191174Measured.md`.) (652 -> 653 / 295 -> 296 `SF` on issue #73's `g191_023` port (volatility): `G191_023_20_20_1`; Gate E pending, run by issue-solver after this session -- see `docs/G191023Measured.md`.) (651 -> 652 / 294 -> 295 `SF` on issue #72's `g191_169` port (momentum): `G191_169_9_1_12_26_10_1`; Gate E pending, run by issue-solver after this session -- see `docs/G191169Measured.md`.) (650 -> 651 / 293 -> 294 `SF` on issue #71's `g191_111` port (volume): `G191_111_11_2_4_2_20`; Gate E pending, run by issue-solver after this session -- see `docs/G191111Measured.md`.) (649 -> 650 / 292 -> 293 `SF` on issue #70's `g191_069` port (trend): `G191_069_20`; Gate E pending, run by issue-solver after this session -- see `docs/G191069Measured.md`.) (648 -> 649 / 291 -> 292 `SF` on issue #69's `g191_043` port (volume): `G191_043_6`; Gate E pending, run by issue-solver after this session -- see `docs/G191043Measured.md`.) (647 -> 648 / 290 -> 291 `SF` on issue #68's `g191_167` port (momentum): `G191_167_12`; Gate E pending, run by issue-solver after this session -- see `docs/G191167Measured.md`.) (646 -> 647 / 289 -> 290 `SF` on issue #67's `g191_160` port (volatility): `G191_160_20_20_1`; Gate E pending, run by issue-solver after this session -- see `docs/G191160Measured.md`.) (645 -> 646 / 288 -> 289 `SF` on issue #66's `g191_152` port (momentum): `G191_152_9_9_1_12_26_9_1`; Gate E pending, run by issue-solver after this session -- see `docs/G191152Measured.md`.) (644 -> 645 / 287 -> 288 `SF` on issue #65's `g191_187` port (momentum): `G191_187_20`; Gate E pending, run by issue-solver after this session -- see `docs/G191187Measured.md`.) (643 -> 644 / 286 -> 287 `SF` on issue #64's `g191_080` port (volume): `G191_080_5`; Gate E pending, run by issue-solver after this session -- see `docs/G191080Measured.md`.) (642 -> 643 / 285 -> 286 `SF` on issue #63's `g191_002` port (momentum): `G191_002_1`; Gate E pending, run by issue-solver after this session -- see `docs/G191002Measured.md`.) (641 -> 642 / 284 -> 285 `SF` on issue #62's `g191_093` port (momentum): `G191_093_20`; Gate E pending, run by issue-solver after this session -- see `docs/G191093Measured.md`.) (640 -> 641 / 283 -> 284 `SF` on issue #61's `g191_189` port (statistics): `G191_189_6_6`; Gate E pending, run by issue-solver after this session -- see `docs/G191189Measured.md`.) (639 -> 640 / 282 -> 283 `SF` on issue #60's `g191_044` port (statistics): `G191_044_10_7_6_4_3_10_15`; Gate E pending, run by issue-solver after this session -- see `docs/G191044Measured.md`.) (638 -> 639 / 281 -> 282 `SF` on issue #59's `g191_190` port (statistics): `G191_190_20`; Gate E pending, run by issue-solver after this session -- see `docs/G191190Measured.md`.) (637 -> 638 / 280 -> 281 `SF` on issue #58's `g191_098` port (trend): `G191_098_100_3_0.05`; Gate E pending, run by issue-solver after this session -- see `docs/G191098Measured.md`.) (636 -> 637 / 279 -> 280 `SF` on issue #57's `g191_144` port (volume): `G191_144_20`; Gate E pending, run by issue-solver after this session -- see `docs/G191144Measured.md`.) (635 -> 636 / 278 -> 279 `SF` on issue #56's `g191_026` port (statistics): `G191_026_7_230_5`; Gate E pending, run by issue-solver after this session -- see `docs/G191026Measured.md`.) (634 -> 635 / 277 -> 278 `SF` on issue #55's `g191_165` port (statistics): `G191_165_48`; Gate E pending, run by issue-solver after this session -- see `docs/G191165Measured.md`.) (633 -> 634 / 276 -> 277 `SF` on issue #54's `g191_076` port (volume): `G191_076_20`; Gate E pending, run by issue-solver after this session -- see `docs/G191076Measured.md`.) (632 -> 633 / 275 -> 276 `SF` on issue #53's `g191_191` port (volume): `G191_191_20_5`; Gate E pending, run by issue-solver after this session -- see `docs/G191191Measured.md`.) (631 -> 632 / 274 -> 275 `SF` on issue #52's `g191_146` port (momentum): `G191_146_61_2_20_60_2`; Gate E pending, run by issue-solver after this session -- see `docs/G191146Measured.md`.) (630 -> 631 / 273 -> 274 `SF` on issue #51's `a101_007` port (momentum): `A101_007_20_7_60`; Gate E pending, run by issue-solver after this session -- see `docs/A101007Measured.md`.) (629 -> 630 / 272 -> 273 `SF` on issue #44's `a101_026` port (volume): `A101_026_5_5_5_3`; Gate E pending, run by issue-solver after this session -- see `docs/A101026Measured.md`.) (628 -> 629 / 271 -> 272 `SF` on issue #206's `mtd_ret` port (performance): `MTD_RET`; Gate E owed -- see `docs/MtdRetMeasured.md`.) (627 -> 628 / 270 -> 271 `SF` on issue #50's `a101_035` port (volume): `A101_035_32_16_32`; Gate E pending, run by issue-solver after this session -- see `docs/A101035Measured.md`.) (626 -> 627 / 269 -> 270 `SF` on issue #49's `a101_046` port (momentum): `A101_046_10`; Gate E pending, run by issue-solver after this session -- see `docs/A101046Measured.md`.) (625 -> 626 / 268 -> 269 `SF` on issue #48's `a101_053` port (momentum): `A101_053_9`; Gate E pending, run by issue-solver after this session -- see `docs/A101053Measured.md`.) (624 -> 625 / 267 -> 268 `SF` on issue #47's `a101_023` port (momentum): `A101_023_20_2`; Gate E pending, run by issue-solver after this session -- see `docs/A101023Measured.md`.) (623 -> 624 / 266 -> 267 `SF` on issue #46's `a101_043` port (momentum): `A101_043_20_20_7_8`; Gate E pending, run by issue-solver after this session -- see `docs/A101043Measured.md`.) (622 -> 623 / 103 -> 104 `BIN` on issue #45's `a101_021` port (momentum): `A101_021_8_2_20`; the 600-bar synthetic probe observes only the two values -1/1, so the generator tags it `BIN` -- Gate E pending, run by issue-solver after this session -- see `docs/A101021Measured.md`.) (601 -> 616 / 246 -> 261 `SF` on issue #34's A158GAPS trio: `RANK_5`..`RANK_60` (statistics), `WVMA_5`..`WVMA_60` (volatility), `VSUMD_5`..`VSUMD_60` (volume) -- 15 columns, all `SF`; then 616 -> 613 / 261 -> 258 `SF` once Gate E measured `RANK_20`, `RANK_30` and `RANK_60` STRUCK (pooled |rho| 0.9767 / 0.9788 / 0.9403 vs `BB_%B` / `zscore` / `Range_Pos_60`) and all three were reverted, leaving `RANK_5`/`RANK_10` (both DISCLOSE_GAP vs `Dist_to_FWMA_pct`) and all five `WVMA_*`/`VSUMD_*` (all SHIP) -- see `docs/Alpha158Measured.md`.) (599 -> 600 / 244 -> 245 `SF` on issue #27's `seas` port (performance): `SEAS_21_1`; Gate E pending, run by issue-solver after this session -- see `docs/SeasMeasured.md`.) (198 -> 206 `SF` on PINEBI-1b tranche 1: `KCWe_20_2.0`, `RWIh_14`, `RWIl_14`, `PZO_14`, `VZO_14`, `SZO_14`, `RMS_DIST_PCT_14` and `WPO_14` — all eight scale-free, which is the point of the tranche: `rms` is the only one of the seven whose natural output is a price level, and it ships the percent distance with the level behind `raw=True`.) (546 -> 549 on ALTPORT-2: `CVI_10_10` and `MFI_BW_SF_20` are `SF`, `SMC_SWEEP_15_1.5` is `BIN`.) (565 -> 566 / 212 -> 213 `SF` on the RAG-scan round-2 `pfe` port: `PFE_10_5`; Gate E STRUCK at 0.9285, kept under waiver #23 in `docs/gate_e_ledger.csv`; revert this with the port if #23 decides so.) (566 -> 568 / 213 -> 215 `SF` on the RAG-scan round-2 `kalman_trend` port: `KFT_DIST_0.01_0.0001`, `KFT_VEL_0.01_0.0001`; Gate E DISCLOSE_GAP 0.8791 and STRUCK 0.9938, the latter kept under waiver #22 in `docs/gate_e_ledger.csv`; revert with what #22 decides.) (568 -> 569 / 49 -> 50 `ORD` on the `range_compress_run` port, `RCR_100`, which left this sentence unedited; then 569 -> 570 / 215 -> 216 `SF` on the Reddit-KB batch-2 `maxvol_adv` port: `MAXVOLADV_14_50`; Gate E SHIP on both, `RCR_100` 0.4827 and `MAXVOLADV_14_50` 0.7003 in `docs/gate_e_ledger.csv`. Then 570 -> 573 / 216 -> 219 `SF` on issue #10's liquidity trio: `CS_1`, `ROLL_20` (volatility) and `AMIHUD_21` (volume); Gate E SHIP on all three, `CS_1` 0.5671, `ROLL_20` 0.5375 and `AMIHUD_21` 0.6431 in `docs/gate_e_ledger.csv`.) (573 -> 574 / 219 -> 220 `SF` on the Lean-screen round-2 `adxr` port: `ADXR_14`; Gate E DISCLOSE_GAP, 0.8838 vs `ADX` in `docs/gate_e_ledger.csv`.) (574 -> 575 / 220 -> 221 `SF` on the TSFEL-sourced `tf_centroid_20` port (statistics): `TFCENTROID_20`; Gate E SHIP, 0.5943 vs `ATR_Ratio_5_20_Pctl` in `docs/gate_e_ledger.csv`, see `docs/TfCentroid20Measured.md`.) (575 -> 576 / 221 -> 222 `SF` on the J-MEDIAN-AD-5 port: `MEDIANAD_HL2_5`; Gate E SHIP, 0.4989 vs `natr` in `docs/gate_e_ledger.csv`.) (576 -> 577 / 222 -> 223 `SF` on the Kats-screen `kpss` port, #157: `KPSS_100`; Gate E SHIP, 0.2256 vs `ICHI_TK_CROSS_AGE` in `docs/gate_e_ledger.csv`.) (577 -> 578 / 223 -> 224 `SF` on the AFML `cusum` port, #16: `CUSUM_100`; Gate E DISCLOSE, 0.7767 vs `dist_low_60` in `docs/gate_e_ledger.csv`.) (578 -> 579 / 224 -> 225 `SF` on the B2-GAPM-40 `gapm` port: `GAPM_40_20`; Gate E SHIP, 0.3738 vs `ZIGZAG` in `docs/gate_e_ledger.csv`.) (579 -> 580 / 225 -> 226 `SF` on the lottery-effect `max_return` port, #12: `MAXRET_21`; Gate E SHIP, 0.6716 vs `natr` in `docs/gate_e_ledger.csv`.) (580 -> 581 / 226 -> 227 `SF` when the TSFEL `tf_median_absdiff_20` port, #118, entered `Category`: `MEDABSDIFF_20`; Gate E SHIP, 0.7422 vs `natr` in `docs/gate_e_ledger.csv`.) (581 -> 582 / 227 -> 228 `SF` on the AFML ch. 18 `entlz` port, #11: `ENTLZ_20`; Gate E pending, run by issue-solver after this session.) (582 -> 583 / 228 -> 229 `SF` on the AFML `ffd` port, #13: `FFD_0.4_0.0001`; Gate E DISCLOSE_GAP, 0.8494 vs `Dist_to_SMA_200_pct` -- see `docs/FfdMeasured.md`.) in `docs/gate_e_ledger.csv`.) (583 -> 586 / 229 -> 232 `SF` on the Alpha Architect / Quantpedia `ovn_split` port, #14: `OVNSUM_21`, `INTSUM_21`, `OVNINTDIFF_21`; Gate E SHIP on `OVNSUM_21` (0.5789 vs `brar_BR_26`) and
`OVNINTDIFF_21` (0.6675 vs `rvgi_RVGIs_14_4`), DISCLOSE_GAP on `INTSUM_21` (0.8368 vs
`rvgi_RVGIs_14_4`, no waiver needed as DISCLOSE_GAP is not STRUCK) in `docs/gate_e_ledger.csv`.) (586 -> 587 / 232 -> 233 `SF` on the RAG-scan `volvol` port, #15: `VOLVOL_20_14`; Gate E SHIP, 0.6408 vs `natr`,`.) (587 -> 590 / 233 -> 236 `SF` on the RANGEVOL port, #17: `GKVOL_20`, `RSVOL_20`, `YZVOL_20`; Gate E pending, run by issue-solver after this session -- see `docs/RangeVolMeasured.md.) (581 -> 582 /
227 -> 228 `SF` on issue #18's `pvcorr` port (volume): `PVCORR_20`; Gate E pending, run by
issue-solver after this session`.) (590 -> 591 / 236 -> 237 `SF` on the ResearchIntel RAG-scan round-2 `volcv` port, #19: `VOLCV_20`; Gate E pending, run by issue-solver after this session, see `docs/VolcvMeasured.md`.) (591 -> 593 / 237 -> 238 `SF` / 50 -> 51 `ORD` on the AFML `trend_scan` port, #20: `TSCAN_T_5-10-20-40-60` (`SF`), `TSCAN_L_5-10-20-40-60` (`ORD`); Gate E SHIP 0.2909 (`TSCAN_L` vs `Supertrend_Flip_Age`) / DISCLOSE_GAP 0.8804 (`TSCAN_T` vs `Dist_to_Cloud_pct`), both columns shipped -- see `docs/TrendScanMeasured.md in `docs/gate_e_ledger.csv`.) (593 -> 594 / 238 -> 239 `SF` on the jesse-screen `dx` port, #120 / J-DX-14: `DX_14`; Gate E pending, run by issue-solver, (Was 551 / 200 `SF` / 50 `ORD` before TALIB-1's Gate E reverts deleted `SAREXTd`/`SAREXTs`, `HT_TRENDLINE_DIST` and `MAMAf`/`MAMAd` — five columns that measured 0.9148–0.9850 against `bias`, `QQE_RSIMA`, `dist_to_psar_pct`, `NWE_MID_200_8.0_8.0` and `PSAR_Signal`, all already shipped.) (595 -> 598 / 240 -> 243 `SF` on issue #21's `crsi` port: `CRSI_3_2_100`, `CRSI_STREAK_2`, `CRSI_PCTRANK_100`; then 598 -> 596 / 243 -> 241 `SF` once Gate E measured `CRSI_3_2_100` and `CRSI_PCTRANK_100` STRUCK (pooled |rho| 0.9265 / 0.9717 vs `log_return`) and both were reverted, leaving only `CRSI_STREAK_2` (DISCLOSE_GAP, 0.8362 vs `increasing`) -- see `docs/CrsiMeasured.md`.) (596 -> 597 / 241 -> 242 `SF` on the ResearchIntel RAG-scan round-3 `ie_asym` port, issue #28: `IEASYM_260_2.0`; Gate E pending, run by issue-solver after this session -- see `docs/IeAsymMeasured.md`.) (597 -> 600 / 242 -> 245 `SF` on issue #30's `correlation_cycle` port (cycles): `CC_REAL_20`, `CC_IMAG_20`, `CC_ANGLE_20`; then 600 -> 599 / 245 -> 244 `SF` once Gate E measured `CC_IMAG_20` STRUCK (pooled |rho| 0.9353 vs `Squeeze_Spread_pct`) and it was reverted, leaving `CC_REAL_20` (SHIP, 0.6626 vs `StochRSI_K_Pctl`) and `CC_ANGLE_20` (SHIP, 0.7235 vs `Squeeze_Spread_pct`) -- see `docs/CorrelationCycleMeasured.md`.) (600 -> 606 / 245 -> 251 `SF` on issue #29's `ewmac` port (momentum): `EWMAC_2_8_35`, `EWMAC_4_16_35`, `EWMAC_8_32_35`, `EWMAC_16_64_35`, `EWMAC_32_128_35`, `EWMAC_64_256_35` -- all six scale-free by construction (a price difference over a price-point standard deviation); then 606 -> 601 / 251 -> 246 `SF` once Gate E measured the first five STRUCK (pooled |rho| 0.9739/0.9829/0.9945/0.9175/0.9298 vs `pgo`/`smi_SMI_5_20_5`/`tsi`/`ICHI_CHIKOU_VS_CLOUD`/`Dist_to_SMA_200_pct`) and reverted, leaving `EWMAC_64_256_35` (DISCLOSE_GAP, 0.8744 vs `SMA_200_Slope_pct`) -- see `docs/EwmacMeasured.md`.) (613 -> 614 / 258 -> 259 `SF` on issue #33's `demand` port (volume): `DEMAND_10_10`; Gate E pending, run by issue-solver after this session -- see `docs/DemandMeasured.md`.) (614 -> 615 / 259 -> 260 `SF` on issue #36's `osap_retskew_21` port (statistics): `OSAP_RETSKEW_21`; Gate E pending, run by issue-solver after this session -- see `docs/OsapRetskew21Measured.md`.) (615 -> 616 / 260 -> 261 `SF` on issue #37's `osap_mrrev` port (momentum): `MRREV_252_378`; Gate E pending, run by issue-solver after this session -- see `docs/OsapMrrevMeasured.md`.) (616 -> 617 / 261 -> 262 `SF` on issue #38's `osap_voltrend_60` port (volume): `VOLTREND_60`; Gate E pending, run by issue-solver after this session -- see `docs/OsapVoltrend60Measured.md`.) (617 -> 618 / 41 -> 42 `CONST` on issue #39's `lot_zeroret_60` port (statistics): `LOT_ZERORET_60` is tagged `CONST` because the dictionary's 600-bar probe is a continuous-valued synthetic walk, which essentially never produces an exact price tie (`r == 0`) across 600 bars. UNLIKE `cdl_pattern`'s 23 `CONST` columns above, this one has no `DEAD_TASKS` entry in `docs/gen_indicator_dictionary.py` -- that file is outside this session's allowed-modify list -- so `docs/IndicatorDictionary.md`'s "Never fires on the probe" table still shows `lot_zeroret_60` under the script's generic fallback text, "unregistered, file one" (shared by other already-registered, shipped indicators such as `vfi` and `xsignals`, not a claim that the column is actually unregistered: it is, in `Category["statistics"]` and `core.py`'s accessor, per `tests/test_lot_zeroret_60.py::test_name_registration_and_accessor`). The disclosure that the column fires and is non-constant lives HERE and in `docs/LotZeroret60Measured.md`, not in that table row: 3 distinct values, 0 < 1,540 fires < 1,600, once the synthetic frame has forced exact ties. Gate E's real-data run (pending, run by issue-solver after this session) is the number that decides ship/revert, same as any other column.) (618 -> 619 / 262 -> 263 `SF` on issue #40's `osap_intmom` port (momentum): `INTMOM_126_252`; Gate E pending, run by issue-solver after this session -- see `docs/OsapIntmomMeasured.md`.) (619 -> 620 / 263 -> 264 `SF` on issue #43's `vol_sign_rev` port (volume): `VSR`; Gate E pending, run by issue-solver after this session -- see `docs/VolSignRevMeasured.md`.) (620 -> 621 / 264 -> 265 `SF` on issue #41's `a101_048` port (momentum): `A101_048_250`; Gate E pending, run by issue-solver after this session -- see `docs/A101048Measured.md`.) (621 -> 622 / 265 -> 266 `SF` on issue #42's `a101_058` port (volume): `A101_058_4_8_6`; Gate E pending, run by issue-solver after this session -- see `docs/A101058Measured.md`.) Every figure in this sentence is read out of a `Counter` over `docs/IndicatorDictionary.md` (generated; see its header), not typed; `tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts` re-derives it. (An earlier revision of this paragraph, added on 2026-09-08 to keep that guard green, quoted 530 / 182 `SF` / 91 `BIN` and then narrated CANDLE-1's 22 columns as "8 BIN confirmation flags and `*_PEND`, 4 SF `*_AGE`, 6 event-sparse magnitudes" -- three counts, all three wrong, inside the document whose job is to stop exactly that. The real split, from the Counter: **8 `BIN`** confirmation flags, **3 `ORD`** `*_PEND` counts, **4 `SF`** `*_AGE` columns, **3 `SF`** `TRIW_SLOPE_UP` / `TRIW_SLOPE_DN` / `TRIW_WIDTH`, and **4 `??`** magnitudes -- `HS_TGT_PCT`, `TRPL_TGT_PCT`, `CUP_DEPTH`, `CUP_CURV` -- which the 600-bar synthetic probe frame cannot reach because no pattern confirms on it. Those four are scale-free by construction and bit-identical under x8/x64; they are measured on real data in `docs/CandlePatternsMeasured.md` §2.)

⚠ **`*_PEND` counts were being tagged `BIN`, and one case was NOT CANDLE-1's.** The probe reads observed cardinality, so a net pending-pattern count that happens to take only two values on a 600-bar synthetic frame is indistinguishable from a flag. Measured over 40 BIST daily frames / 71,402 bars, `HS_PEND` spans [-2, +2] (5 distinct) and `DTDB_PEND` -- which shipped long before CANDLE-1 -- spans [-2, +2] as well; both had been tagged `BIN`. `FLAG_PEND` genuinely spans only [-1, +1], so `BIN` is correct for it and a blanket "`*_PEND` is ordinal" rule would have mislabelled it. `gen_indicator_dictionary.py`'s `FORM_OVERRIDES` therefore lists the two measured cases explicitly, with the measurement, rather than pattern-matching the name.

⚠ An earlier draft of this paragraph said 128/172/92/3 and called them measured. They were not; `tests/test_ml_companions.py` now parses the dictionary and asserts these.

Those forms, not the indicator names, decide what a companion must do:

| shape | reference | what is wrong with the parent column | what the companion must supply |
|---|---|---|---|
| bounded oscillator | `rsi` → `RSI_14` (SF, 0–100) | nothing is *wrong*; it is already scale-free. But a tree must rediscover "70 is extended" at every split | the regime, named |
| price-scaled overlay | `sma` → `SMA_10` (PX) | **unusable as a feature.** A tree cannot compare 41.72 to a price that was 12 two years ago | a scale-free relation to price |
| event flag | `fvg` → `FVG_BULL` (BIN) | fires and vanishes; a tree sees only the bar it fired on | persistence and recency |

⚠ **A percentile is the wrong companion for two of these three.** Rolling-rank
an already-bounded oscillator and you double-weight the same signal — the
`MULTIL-0` finding, where `RSI_14` vs `RSI_28` measured ρ 0.936 and reverted.
Rolling-rank a binary and you get the event *rate*, which is a different and
usually more useful column, but it is not "the same indicator as a percentage".

---

## The contract

For each parent column, a companion set of at most three columns:

### 1. STATE — a small ordinal, never a bare boolean pair

    <PARENT>_STATE   ∈ {-2, -1, 0, 1, 2}

`-2` deeply cheap · `-1` cheap · `0` neutral · `+1` expensive · `+2` deeply
expensive. One ordinal column, not four one-hot booleans: a tree splits an
ordinal in one node and needs four to reassemble a one-hot set, and the
one-hot version quadruples the column count for no information.

**The thresholds are per indicator and are written down, not inferred.** For a
bounded oscillator they are the documented levels. For anything unbounded they
are quantiles of a *causal trailing window*, never of the whole series.

⚠ **A trailing quantile on a price LEVEL does not give the nominal tails.** Measured
on a 1500-bar random walk at `length=252`: `|STATE| == 2` covers **31.4%** of settled
bars, not the 10% the 5/95 split implies — a non-stationary series sits at its own
window extreme constantly. Ranking the DISTANCE instead brings it to **9.9%**.
**So a `PX` parent's STATE is computed on its `DIST_PCT`, never on the raw level.**
That is what the `PX` shape is for, and the first draft of this contract walked
straight past it.

### 2. DISTANCE — the scale-free relation (PX parents only)

    <PARENT>_DIST_PCT = (close - parent) / close

This is the column that makes a `PX` parent usable at all. It is the
`ichimoku_ml` precedent, which the fork already ships: five price lines became
eight scale-free causal columns.

⚠ Emit this **instead of**, not in addition to, any raw-level companion. A
`PX` column plus its distance form is the same information twice.

### 3. PERSISTENCE — for event flags only

    <PARENT>_BARS_SINCE   integer, capped
    <PARENT>_RATE_<W>     fraction of the trailing W bars where the flag fired

A flag is invisible to a tree on every bar except the one it fires on.
`BARS_SINCE` is capped (default 100) so a never-fired series does not emit an
unbounded ordinal that dominates every split.

---

## Rules every companion obeys

1. **Causal.** Trailing windows only. A whole-series quantile leaks the future
   into every bar — the defect `normalize` is warned about in PINEBI-1e.
2. **Scale-free.** A companion may not reintroduce a price level. If the parent
   is `PX`, the companion is a ratio or a distance.
3. **Named by the parent.** `<PARENT>_STATE`, not `RSI_STATE_14` — the parent
   column name already encodes its parameters, and mined rules in
   `StrategyMaster.csv` match on these strings.
4. **Gate E applies.** A companion derived from a column is correlated with it
   *by construction*; that is exactly what the revert band exists to catch.
   MLCOL-2 measures every companion against its parent and against the shipped
   set, and anything in the revert band is **deleted, not shipped**.
5. **No companion for a column nothing selects.** INDREF-2 is the honest test:
   an indicator mining never picks does not need three more columns.

---

## The three reference implementations

| parent | shape | companions | MLCOL-2 verdict |
|---|---|---|---|
| `RSI_14` (engine: `RSI`) | bounded SF | `RSI_STATE` (thresholds 20/30/70/80, documented levels) | **DELETED** — a deterministic coarsening of `RSI`; permutation importance +0.00013 ± 0.00067 over 15 fits, beats a shuffled null 7/15 |
| `SMA_10` | PX | `SMA_10_DIST_PCT`, then `SMA_10_DIST_PCT_STATE` (quantiles of a trailing 252-bar window **of the distance**, not the level) | **BOTH DELETED** — `_DIST_PCT` ρ 0.9462 vs the already-shipped `NWE_MID_200_8.0_8.0` (revert band); `_STATE` adds nothing measurable |
| `FVG_BULL` | BIN | `FVG_BULL_BARS_SINCE`, `FVG_BULL_RATE_60` | **BOTH DELETED** — both clear Gate E (0.586 / 0.553) and both fail the incremental axes; `BARS_SINCE`'s within-bin ρ is matched by its own parent (excess +0.0004) |

⚠ **ALL 5 are deleted.** Measured 2026-09-08 on 139,657 BIST daily bars against
the engine's production column set — see *Measured — MLCOL-2* at the end of
this document. Round 1 of that section shipped 2 of the 5; both were reversed
in round 2 by controls round 1 did not run (a placebo on the conditional axis,
an across-seed band on the model axis). Do not re-derive any of the five in
MLCOL-1 without reading that section: the reasons generalise.

Implementation: `pandas_ta/ml/companions.py`. Tests:
`tests/test_ml_companions.py`.

⚠ **`RSI` gets no DISTANCE and no RATE.** It is already scale-free, and a rate
of a continuous column is meaningless. The contract says *at most* three
companions; two of the three shapes take fewer, and resisting the urge to emit
a uniform triple is the point of designing on three shapes first.

---

## What this contract does NOT settle

- **The rollout order.** MLCOL-1 orders by the dictionary's
  *"Needs a transform before modelling"* table, because those parents are
  unusable today and pay back first.
- **Whether all 137 `PX` parents deserve a companion.** They do not: many are
  intermediate lines of a multi-column indicator whose useful form is already
  emitted elsewhere. MLCOL-1 decides per indicator, not per column.
- **The trailing-window length for STATE quantiles.** 252 is a placeholder,
  chosen as one trading year. It is a parameter to measure, not a constant to
  believe.

---

# Measured — MLCOL-2 (2026-09-08, round 2)

Rule 4 above says a companion gets no Gate E waiver for being derived. This
section is that measurement.

> ## **Result: 0 of 5 ship. All five reference companions are deleted.**
>
> Round 1 of this section claimed 2 of 5 shipped. Both SHIPs were wrong, and
> both were caught by controls that round 1 did not run: a **placebo** on the
> conditional axis and an **across-seed error band** on the model axis. The
> three round-1 DELETEs were re-verified and stand unchanged.

**Harness:** `../Backtesting/scripts/analysis/measure_ml_companion_overlap.py`.
**CSVs:** `../Backtesting/backtest_results/tvpta6/` —
`mlcol2_companion_overlap_gridA_full.csv` (2,425 cells),
`mlcol2_companion_verdicts.csv`, `mlcol2_companion_model_runs.csv` (75 fits),
`mlcol2_companion_sensitivity.csv`.

**Grid.** 30 BIST_100 daily frames from `datastore/cache` with >= 400 bars,
**139,657 pooled bars**. Comparator set: the **485** numeric columns of
`IndicatorEngine(include_advanced=True).compute_all()` — the config
`batch_runner.py` wires in production, and the larger of the two available
comparator sets. (`measure_fvg/ifvg/madiv_overlap_full.py` used
`include_advanced=False` and so never scored against the columns `True` adds,
`natr` among them.) ⚠ **485 is 2 optimistic and includes 5 non-features:**
5 of the 485 are the raw OHLCV inputs, and `TOD_SLOT_RVOL_20_20` /
`TOD_SLOT_VVOL_20_20` are intraday-only and all-NaN on daily bars, scoring 0
cells (`note = n<100`, n = 0) — so **483 columns are effective, 478 computed**.

Exact invocation and versions, from the run's own `PROVENANCE` lines:

    scripts/analysis/measure_ml_companion_overlap.py --stage 2 --work <cache>
    python=3.11.9 pandas=2.3.3 numpy=1.26.4 scipy=1.13.0 sklearn=1.4.2

⚠ **The contract writes the RSI parent as `RSI_14`; the engine ships it as
`RSI`**, and it is `rsi(Close, length=14)` (`speedy_indicators.py:30`). The
measurement uses the name production emits.

## Gate E — rho vs parent and vs the shipped set

| companion | parent | ρ vs parent | ρ vs parent (Fisher-z, 30 frames) | max abs ρ vs shipped set (excl. parent) | against | n (that cell) | Gate E |
|---|---|---|---|---|---|---|---|
| `RSI_STATE` | `RSI` | +0.5886 | +0.5876 | 0.5950 | `ATR_BREAKOUT_UP` | 139,237 | SHIP |
| `SMA_10_DIST_PCT` | `SMA_10` | +0.0079 | +0.0051 | **0.9462** | `NWE_MID_200_8.0_8.0` | 133,657 | **REVERT** |
| `SMA_10_DIST_PCT_STATE` | `SMA_10_DIST_PCT` | +0.8877 | +0.8929 | 0.8347 | `NWE_MID_200_8.0_8.0` | 133,657 | DISCLOSE |
| `FVG_BULL_BARS_SINCE` | `FVG_BULL` | −0.6260 | −0.6255 | 0.5861 | `CCI` | 138,692 | SHIP |
| `FVG_BULL_RATE_60` | `FVG_BULL` | +0.1604 | +0.1523 | 0.5533 | `ICHI_CHIKOU_VS_CLOUD` | 137,347 | SHIP |

The pooled-bar ρ and the per-frame Fisher-z pooled ρ agree to within 0.009 on
every row (largest gap `FVG_BULL_RATE_60`, 0.1604 vs 0.1523), so the pooled
figure is not a frame-length artefact. **Gate E alone would ship three of these
five.** It ships none.

## Axis 3a — model, over 5 seeds × 3 split points (15 fits per companion)

Chronological split per ticker at 0.6 / 0.7 / 0.8; `HistGradientBoostingClassifier`
on `[parent]` versus `[parent, companion, NULL]`, where **NULL is the
companion's own values shuffled** — same marginal distribution, zero
information, so its measured importance is this procedure's noise floor rather
than an assumed one.

| companion | AUC parent | AUC +companion | Δ (sd across runs) | perm. imp. companion (**sd across runs**) | within-fit shuffle sd | perm. imp. **parent** | perm. imp. NULL | beats NULL |
|---|---|---|---|---|---|---|---|---|
| `RSI_STATE` | 0.5087 | 0.5090 | +0.0002 (0.0024) | +0.00013 (**0.00067**) | 0.00015 | +0.00885 | +0.00000 | 7/15 |
| `SMA_10_DIST_PCT` | 0.5038 | 0.5046 | +0.0008 (0.0053) | +0.00194 (**0.00239**) | 0.00166 | +0.00216 | −0.00034 | 13/15 |
| `SMA_10_DIST_PCT_STATE` | 0.5044 | 0.5045 | +0.0001 (0.0016) | +0.00028 (**0.00226**) | 0.00215 | +0.00689 | +0.00009 | 9/15 |
| `FVG_BULL_BARS_SINCE` | 0.4999 | 0.5018 | +0.0018 (0.0023) | +0.00128 (**0.00264**) | 0.00192 | −0.00001 | +0.00055 | 9/15 |
| `FVG_BULL_RATE_60` | 0.4999 | 0.5009 | +0.0009 (0.0044) | +0.00079 (**0.00392**) | 0.00220 | −0.00024 | +0.00036 | 8/15 |

⚠ **Round 1's error is visible in this table's last three columns.** It
reported `FVG_BULL_BARS_SINCE` at +0.00468 ± 0.00190 and shipped it on
mean − 2sd = +0.0009. That ±0.00190 was ten shuffles of ONE fitted model at
ONE seed and ONE split — shuffle noise only, with learner-seed and split
variance excluded, and those are the dominant terms at AUC ≈ 0.50. The
across-run sd is 0.00264 against a mean of 0.00128, so mean − 2sd is
**negative**. Round 1's own output already contained the calibration that
proved it: `perm_imp_parent` was **negative** for a parent the model was
fitted on, which puts procedure noise at O(0.002–0.004). That column existed
in `mlcol2_companion_verdicts.csv` and round 1 did not print it. It is printed
here, and it is the reason no companion clears this axis.

**No companion clears axis 3a.** Every one fails mean − 2·(across-run sd) > 0,
and none beats the shuffled NULL in more than 13 of 15 runs.

## Axis 3b — conditional rank correlation, against a PLACEBO

Inside each bin of the parent, Spearman ρ between the companion and the forward
return, Fisher-z pooled — and **the identical statistic run on the PARENT over
the same bins and the same rows**. Comparing the companion's within-bin ρ to
zero, as round 1 did, is the wrong null.

| companion | h | companion ρ (z) | **placebo parent ρ (z)** | excess | paired bootstrap 95% CI (300 ticker resamples) | bins | n |
|---|---|---|---|---|---|---|---|
| `RSI_STATE` | 1 | −0.0099 (−1.11) | −0.0151 (−1.70) | −0.0053 | — | 3 | 12,565 |
| `RSI_STATE` | 5 | −0.0372 (−4.17) | **−0.0226 (−2.53)** | +0.0146 | [+0.0026, +0.0281], 99.3% > 0 | 3 | 12,529 |
| `SMA_10_DIST_PCT` | 1 | +0.0165 (+3.38) | −0.0029 (−0.59) | +0.0136 | [−0.0062, +0.0205], 88.7% > 0 | 10 | 41,881 |
| `SMA_10_DIST_PCT` | 5 | +0.0253 (+5.17) | −0.0118 (−2.42) | +0.0134 | [−0.0238, +0.0328], 75.0% > 0 | 10 | 41,761 |
| `SMA_10_DIST_PCT_STATE` | 1 | +0.0040 (+0.81) | +0.0016 (+0.32) | +0.0024 | — | 10 | 41,881 |
| `SMA_10_DIST_PCT_STATE` | 5 | −0.0067 (−1.36) | +0.0036 (+0.74) | +0.0030 | — | 10 | 41,761 |
| `FVG_BULL_BARS_SINCE` | 1 | −0.0093 (−1.91) | +0.0021 (+0.43) | +0.0072 | — | 1 | 41,881 |
| `FVG_BULL_BARS_SINCE` | 5 | −0.0166 (−3.39) | **+0.0162 (+3.31)** | **+0.0004** | [−0.0116, +0.0114], **52.7% > 0** | 1 | 41,761 |
| `FVG_BULL_RATE_60` | 1 | +0.0031 (+0.63) | +0.0021 (+0.43) | +0.0010 | — | 1 | 41,881 |
| `FVG_BULL_RATE_60` | 5 | +0.0060 (+1.24) | +0.0162 (+3.31) | −0.0101 | — | 1 | 41,761 |

The bootstrap resamples whole tickers with replacement, because the companion's
ρ and the placebo's are computed on the same rows and are strongly dependent —
their separate z-scores say nothing about whether the *difference* is real.
It is run only on cells that reach |z| >= 2.5, since a cell that fails on z
cannot be rescued by it.

**`FVG_BULL_BARS_SINCE` is settled by this table.** Its round-1 headline
(|ρ| 0.0166 at fwd5, z −3.39) is almost exactly matched by the placebo
(|ρ| 0.0162, z +3.31) on the same rows: excess **+0.0004**, bootstrap CI
straddling zero, positive in **52.7%** of resamples. A coin flip. The parent
carries that relation; the companion restates it.

⚠ **Both `FVG_BULL` companions condition on 1 bin.** `FVG_BULL` is binary, so
binning its raw values collapses to its two levels and only the zero level has
both ≥ 100 rows and a non-constant companion. "Conditioning on the parent" for
these two therefore means "restricting to bars where the flag did not fire" —
weaker conditioning than the ten-bin case, and stated rather than hidden.
(Round 1 reported 9 bins here. That was a defect: it binned
`rank(method="first")`, which makes every rank unique, so `qcut` never saw a
duplicate edge, `duplicates="drop"` and its `except ValueError` were dead code,
and a 2-valued parent was sliced **by row order**. Round 2 bins raw values.)

### Why `RSI_STATE` is deleted even though it beats its placebo

`RSI_STATE` is the one cell where the companion's within-bin |ρ| genuinely
exceeds the parent's: 0.0372 vs 0.0226 at fwd5, and the paired bootstrap puts
the excess above zero in 297 of 300 ticker resamples. That is a real measured
difference and it is not thrown away.

It is still not a reason to ship, for a reason of principle that the numbers
then confirm:

`ml_state(source, kind="rsi")` (`companions.py`) is a **memoryless monotone
step function of the current RSI value and nothing else**. Inside a bin of the
parent it is a *coarsening* of the parent — a subset of its information, never
a superset. So it cannot carry information the parent lacks, and a larger
within-bin Spearman does not contradict that: **Spearman measures monotone rank
association, not information.** A two-level step can track a non-monotone
within-bin relation better than the underlying continuous value does, which is
precisely what these numbers show.

That makes the benefit **representational, not informational** — worth
something only to a learner that cannot express the step itself. This fork's
consumer is a **tree-based miner**, which can express it, and the axis that
uses such a learner says so plainly: permutation importance +0.00013 ± 0.00067
across 15 runs, beating the shuffled NULL in **7 of 15** — worse than chance.
The tree finds the threshold on its own and gains nothing from being handed it.

⚠ **Round 1's line 214 said the opposite in plain English** — that `RSI_STATE`
carries ρ −0.037 "that the raw RSI value does not". The raw RSI value
*determines* which side of the threshold the bar is on. That sentence was false
as information, and it was the whole SHIP argument. It is retracted.

The harness now encodes this: companions flagged
`deterministic_of_parent=True` in the `COMPANIONS` registry (`RSI_STATE`,
`SMA_10_DIST_PCT_STATE`) cannot ship on the conditional axis at all; the model
axis decides for them. `SMA_10_DIST_PCT` (also reads `Close`),
`FVG_BULL_BARS_SINCE` and `FVG_BULL_RATE_60` (read the parent's *history*) are
not deterministic functions of the current parent value and keep both axes.

## Thresholds: not pre-registered, and no longer decisive

⚠ **`COND_Z_MIN = 3.0` and `COND_RHO_FLOOR = 0.01` were written after round 1's
numbers were on screen, and the harness is untracked, so nothing orders the
constants before the data.** They were also decisive at the margin in round 1:
`RSI_STATE`'s fwd1 |ρ| = 0.00987 sat 1.3% under the floor while fwd5 cleared,
and `FVG_BULL_BARS_SINCE` sat at |z| 2.58 / 2.65 against a 3.0 bar.

Two corrections:

1. **Multiplicity.** The conditional axis is an OR over 2 horizons × 5
   companions = **10 tests**; at an uncorrected |z| >= 3 the family-wise error
   is not 5%. The harness now applies a two-sided Bonferroni correction over
   that family: critical **|z| = 2.807**, printed by the run.
2. **Sensitivity.** The full verdict table is recomputed over
   z ∈ {2.5, 3.0, 3.5} × ρ_floor ∈ {0.005, 0.01, 0.02}
   (`mlcol2_companion_sensitivity.csv`). **All 9 cells return DELETE for all 5
   companions; the run reports `verdicts that MOVE across the grid: none`.**
   The 0-of-5 result does not depend on either constant.

## Verdicts

| companion | Gate E | axis 3a (model) | axis 3b (conditional vs placebo) | verdict |
|---|---|---|---|---|
| `RSI_STATE` | SHIP (0.595) | fails: +0.00013 ± 0.00067, beats NULL 7/15 | not competent — deterministic coarsening of parent | **DELETE** |
| `SMA_10_DIST_PCT` | **REVERT** (0.9462) | fails: +0.00194 ± 0.00239 | excess +0.0134, CI straddles 0 | **DELETE** |
| `SMA_10_DIST_PCT_STATE` | DISCLOSE (0.8877 vs parent) | fails: +0.00028 ± 0.00226 | not competent — deterministic | **DELETE** |
| `FVG_BULL_BARS_SINCE` | SHIP (0.586) | fails: +0.00128 ± 0.00264, beats NULL 9/15 | excess **+0.0004**, 52.7% > 0 | **DELETE** |
| `FVG_BULL_RATE_60` | SHIP (0.553) | fails: +0.00079 ± 0.00392 | excess −0.0101 | **DELETE** |

**`SMA_10_DIST_PCT` deserves its own note**, because the shape did work: ρ
against its own parent `SMA_10` is +0.0079, so the distance form really did
strip out the price level. It dies on redundancy — the engine already ships
this construction under other names. `NWE_MID_200_8.0_8.0` is
`(close − nw_mid) / close * 100`
(`pandas_ta/overlap/nadaraya_watson_envelope.py:47`) at ρ 0.946, and `bias` is
`(close − SMA_20) / SMA_20` (`indicator_engine.py:1151`) at ρ 0.849 — the same
construction on a different smoother and a different length. Then `week_trend`
0.909, `kdj_J_9_3` 0.883, `BB_%B` / `ZSCORE_20` 0.875, `willr` 0.860,
`CCI` 0.852.

⚠ **This is a re-derivation, not a discovery.** `iama`'s
%-distance-from-MA column was wired, measured against the same
`NWE_MID_200_8.0_8.0` at **ρ 0.9498**, and un-wired for it on **2026-08-14** —
recorded at `../Backtesting/scripts/utils/gen_indicator_register.py:643-645`.
That MLCOL-2 independently landed within 0.004 of the August figure is
corroboration; that the screen it now recommends was already known in August
and not applied to the contract is the more useful finding.

**Nothing is removed from `pandas_ta/ml/companions.py`.** That module ships the
four *primitives*, not per-parent columns, and no measurement in either round
found a defect in any primitive. What is deleted is the reference COLUMN SET.

## Causality is a PRECONDITION of the incremental axis, not a parallel check

Added 2026-09-11, from MLCOL-1's screen, because it inverts how the axis reads.

`dpo` defaults to `centered=True`, which `PandasTa/CLAUDE.md` names as one of
exactly **two** known non-causal columns in the entire package (the other is
`ichimoku`'s `ICS_26`). Measured directly: altering only bars from index 300
onward moves `dpo`'s output on bars *before* 300 by up to **24.0**; at
`centered=False` the same perturbation moves it by **0.000000**.

MLCOL-1 screened a companion off that parent and axis 3a **ranked it first**:

    DPO_20_RATIO_PCT   dAUC +0.0473   perm. importance +0.35693   15/15 beats NULL

against a field where every honest candidate scored ~0.01 and dAUC ~0.008.

**That is the lesson, and it generalises past `dpo`.** Leakage is the
strongest signal a model can be handed, so an incremental axis does not merely
fail to catch a non-causal feature — it *promotes* it to the top of the
ranking, with a clean-looking 15/15 against its own shuffled null. Every
control in the procedure behaves exactly as designed and the answer is still
wrong, because all of them ask "is this better than noise", and leaked future
is much better than noise.

So the order is fixed:

1. **Causality, measured per parent** — perturb the tail, assert the prefix is
   bit-identical. Not read off a list: a list only contains the cases someone
   already knew about, and `MLCOL-1`'s guard is a measurement precisely so it
   catches the ones nobody has written down.
2. Gate E.
3. The incremental axes.

A companion whose parent fails (1) is not a weak candidate to be weighed
against the others — it is not a candidate. `measure_mlcol1_screen.py`
excludes it as `EXCLUDED-NON-CAUSAL` before any correlation is computed.

## What MLCOL-1 must do differently

1. **Gate E is necessary but not sufficient.** Three of these five clear Gate E
   outright and none survives. `FVG_BULL_RATE_60` passes at 0.553 and dies.
2. **Screen a proposed `DIST_PCT` against the engine's existing distance
   columns before building it** — `NWE_MID_200_8.0_8.0`, `bias`,
   `dist_to_psar_pct`, `ATR_POSITION`, `BB_%B`, `ZSCORE_20`. This was already
   known on 2026-08-14 (above). For the number of `PX` parents this applies to,
   read the opening paragraph of this document; it is `Counter`-derived from
   the generated dictionary and asserted by
   `tests/test_ml_companions.py`. **Do not retype it here** — four different
   numbers for that one quantity were in circulation on 2026-09-08.
3. **A STATE companion on a continuous parent is a deterministic coarsening.**
   It cannot add information, only representation, and a tree does not need the
   representation. Both STATE companions measured here died. Do not emit STATE
   for a continuous parent without a specific argument that the *consumer*
   cannot express the threshold.
4. **Run both incremental axes with their controls** — the placebo on the
   conditional axis, and across-seed/across-split bands plus a shuffled NULL on
   the model axis. Round 1 ran neither and produced two false SHIPs out of two.

## Not measured

- **Hourly frames.** Daily only. The event-flag companions are the most
  bar-size sensitive and nothing here speaks to that.
- **The other `PX`, `SF` and `BIN` parents.** MLCOL-1 is deferred; this proves
  the method, not the answers.
- **Any target other than forward close-to-close return** at 1 and 5 bars. The
  live books trade path-dependent exits (SL / TS / max-hold); a companion
  useless for direction could still be useful for exit timing.
- **US frames, and BIST_100 tickers past the first 30** with a cached daily
  parquet of >= 400 bars. `--max-tickers` raises the grid.
- **Whether a companion helps a NON-tree consumer.** The `RSI_STATE` deletion
  turns on this fork's consumer being tree-based. A linear or rank-based model
  downstream would change that verdict, and no such consumer was tested.
