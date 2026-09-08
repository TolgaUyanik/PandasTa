# Chart Patterns — what was built, what was measured, what was reverted (CANDLE-1)

Status: results document for **CANDLE-1**. It records, per pattern, the fire rate, the Gate D
result, the Gate E maximum with the column it hit and the sample size, and a SHIP / DISCLOSE /
REVERT verdict. **Reverted columns stay in the table** — deleting an over-correlated column you
just built is this repo's expected outcome, not a failure, and hiding the attempt would remove the
only evidence that the question was asked.

Companion documents: `docs/CandlePatternShortlist.md` (CANDLE-0 — *what to build* and why it is not
already shipped) and `CLAUDE.md` (the gates).

Every number below comes from one script,
`../Backtesting/scripts/analysis/measure_candle1_overlap_full.py`, whose CSV outputs are in
`../Backtesting/scripts/analysis/candle1_out/`. §7 gives the command. **That script is written to
disk and `untracked`, like CANDLE-0's harness before it; committing was outside this session's
authority.**

---

## 0. The sample, stated once

| item | value | how |
|---|---|---|
| tickers | **50** BIST daily Parquet frames, ≥400 bars, sorted order | harness `_tickers` |
| pooled bars | **91,197** | `pooled_meta.csv` |
| engine config | `IndicatorEngine(include_advanced=True)` | harness `build_pool` |
| shipped columns swept | **485** numeric engine columns | `pooled_meta.csv` |
| new columns after the cut | **22** | `pooled_meta.csv` |

`include_advanced=True` is load-bearing. `include_advanced=False` silently drops `natr`, among
others, so a candidate could clear a sweep that never contained its most likely comparator. Same
config as `measure_ml_companion_overlap.py`.

**This is the Gate E that CANDLE-0 could not run.** `CandlePatternShortlist.md` §5 item 3 recorded
its own sweep as 112 columns from 16 modules chosen for collision risk, and said CANDLE-1 must
re-run it in full. It is re-run in full here.

---

## 1. What shipped

Four modules under `pandas_ta/trend/`, covering eight of the eleven shortlisted patterns. Fully
wired across all five touch points (`CLAUDE.md`): module, category `__init__`, `Category`,
`core.py` accessor, test module.

| module | patterns covered | columns | default suffix |
|---|---|---|---|
| `head_shoulders` | head & shoulders, inverse head & shoulders | 5 | `_5_5_0.03_60` |
| `triple_top_bottom` | triple top, triple bottom | 5 | `_5_5_0.03_60` |
| `triangle_wedge` | ascending / descending / symmetrical triangle, rising / falling wedge | 7 | `_5_5_60` |
| `rounding_cup` | cup & handle / rounding bottom, rounding top | 5 | `_40_10_0.6_0.1_0.05` |

**Eight patterns ship, not nine.** The rectangle was built, measured against its pre-registered
trigger, and **SKIPPED** — §6. It is listed in §4's table with its verdict, as a reverted candidate
must be.

`pandas_ta/trend/_patternlib.py` holds the shared pivot stream and validators. It is
underscore-prefixed and defines no public indicator, so it does not violate the one-indicator-one-
module rule; `dtdb` set the precedent for sharing `_confirm_pivots` across siblings.

### Naming — two defects found in round 2, both fixed

`CandlePatternShortlist.md` §4's rule is "structural parameters in signature order, then
tolerances, then the bar budget". The rule held; the two modules that broke it did so in opposite
directions, and both broke it in a way `test_column_names_carry_the_parameter_tuple_in_signature_order`
— four literal-string assertions — could not see.

- **`rounding_cup` dropped a LIVE parameter from its name.** `min_depth` changes the output and was
  not in the suffix. Measured on an 800-bar seed-11 walk: `min_depth=0.05` fires `CUP_CONF_BULL`
  **4** times, `min_depth=0.30` fires it **0** times, and both emitted
  `CUP_CONF_BULL_30_5_0.6_0.1`. Naming is API here — the parent repo matches mined-strategy rules
  on these strings — so that is a silent collision in someone else's backtest. Shipped suffix is
  now `_{length}_{handle}_{curv_min}_{sym_tol}_{min_depth}`.
- **`triangle_wedge` advertised a DEAD one.** `tol` was in the suffix and never read:
  `tol=0.03` and `tol=0.99` gave **bit-identical** output under
  `TRIW_CONF_BEAR_3_3_0.03_60` and `TRIW_CONF_BEAR_3_3_0.99_60`. It was accepted "for suffix parity
  with the sibling matchers"; parity with a dead parameter is not parity. Deleted from the
  signature and the name, so the suffix is `_{left}_{right}_{max_wait}`.

The four literal assertions are replaced by a **property test** over every numeric parameter,
perturbed one at a time: *output changed ⇒ name changed*, and *output unchanged ⇒ name unchanged*.
`test_the_naming_property_catches_both_defects_it_was_written_for` rebuilds both defects as
`importlib` + `exec` mutants and asserts the property fires on each, so the detector is pinned and
not decoration.

One deviation from §4 remains, recorded rather than hidden: it wrote the cup default as `..._0.10`,
and Python renders the float `0.10` as `0.1`, so `CUP_CONF_BULL_40_10_0.6_0.10` is not a name this
package can produce.

**Four patterns, one module, no one-hot flags.** `triangle_wedge` does not emit five shape flags:
ascending / descending / symmetrical / rising-wedge / falling-wedge is the sign pair of
`TRIW_SLOPE_UP` and `TRIW_SLOPE_DN`, two splits for a tree. This is `CandlePatternShortlist.md`
§4's decision, applied.

⚠ That derivation is an APPROXIMATION and §6.2 is the cost of forgetting it: the two slope columns
are aggregated by max-|value| across every pattern confirming on the bar, so on a multi-pattern bar
they describe whichever pattern was steeper. Round 1 built the rectangle count on exactly that
inference and measured the wrong population.

---

## 2. Gate C — reachability, at the default parameters

Measured over the 91,197-bar pool. `reachability.csv`. **0 of 22 columns are dead.**

| column | non-null | non-zero | % non-zero | min | max |
|---|---|---|---|---|---|
| `HS_CONF_BEAR_5_5_0.03_60` | 90,497 | 180 | 0.199 | 0 | 1 |
| `HS_CONF_BULL_5_5_0.03_60` | 90,497 | 180 | 0.199 | 0 | 1 |
| `HS_TGT_PCT_5_5_0.03_60` | 90,497 | 360 | 0.398 | 0 | 2.761 |
| `HS_PEND_5_5_0.03_60` | 90,497 | 10,805 | 11.94 | −2 | 2 |
| `HS_AGE_5_5_0.03_60` | 90,497 | 90,137 | 99.60 | 0 | 1 |
| `TRPL_CONF_BEAR_5_5_0.03_60` | 90,497 | 187 | 0.207 | 0 | 1 |
| `TRPL_CONF_BULL_5_5_0.03_60` | 90,497 | 219 | 0.242 | 0 | 1 |
| `TRPL_TGT_PCT_5_5_0.03_60` | 90,497 | 406 | 0.449 | 0 | 0.805 |
| `TRPL_PEND_5_5_0.03_60` | 90,497 | 11,313 | 12.50 | −3 | 3 |
| `TRPL_AGE_5_5_0.03_60` | 90,497 | 90,091 | 99.55 | 0 | 1 |
| `TRIW_CONF_BEAR_5_5_60` | 90,547 | 1,586 | 1.752 | 0 | 1 |
| `TRIW_CONF_BULL_5_5_60` | 90,547 | 1,619 | 1.788 | 0 | 1 |
| `TRIW_SLOPE_UP_5_5_60` | 90,547 | 3,191 | 3.524 | −0.0440 | 0.0771 |
| `TRIW_SLOPE_DN_5_5_60` | 90,547 | 3,188 | 3.521 | −0.0194 | 0.0815 |
| `TRIW_WIDTH_5_5_60` | 90,547 | 3,204 | 3.539 | 0 | 4.772 |
| `TRIW_PEND_5_5_60` | 90,547 | 5,870 | 6.483 | 0 | 4 |
| `TRIW_AGE_5_5_60` | 90,547 | 87,343 | 96.46 | 0 | 1 |
| `CUP_CONF_BULL_40_10_0.6_0.1_0.05` | 88,747 | 406 | 0.458 | 0 | 1 |
| `CUP_CONF_BEAR_40_10_0.6_0.1_0.05` | 88,747 | 312 | 0.352 | 0 | 1 |
| `CUP_DEPTH_40_10_0.6_0.1_0.05` | 88,747 | 718 | 0.809 | 0 | 0.518 |
| `CUP_CURV_40_10_0.6_0.1_0.05` | 88,747 | 718 | 0.809 | −0.1921 | 0.1013 |
| `CUP_AGE_40_10_0.6_0.1_0.05` | 88,747 | 88,029 | 99.19 | 0 | 1 |

**The `TRIW_*` counts are POST-SKIP.** Round 1 measured `TRIW_CONF_BEAR` 1,788 and `TRIW_CONF_BULL`
1,833 with the rectangle branch live; removing it (§6) drops them to 1,586 / 1,619, and
`TRIW_PEND`'s non-zero bars from 10,646 to 5,870 — rectangles were a large share of the pending
inventory because a flat-boundary box survives its bar budget more often than a converging one.

**The shipped modules reproduce CANDLE-0's prototype counts on the identical pool**, which is the
strongest available evidence that the implementation matches the detector the shortlist measured:

| pattern | CANDLE-0 prototype | shipped module | note |
|---|---|---|---|
| H&S bear | 180 | **180** | exact |
| H&S bull | 180 | **180** | exact |
| triple top | 187 | **187** | exact |
| triple bottom | 219 | **219** | exact |
| cup / rounding bottom | 406 | **406** | exact |
| rounding top | 241 | **312** | differs — see below |
| triangle / wedge, all shapes | 3,680 (incl. rectangle) | **3,205** | differs — chain below |

Two deliberate divergences, both disclosed:

- **rounding top 241 → 312.** CANDLE-0's probe gated its rounding-TOP branch on the CUP depth
  `(rim − low) / rim` with `rim = max(ends)`. This module uses the mirrored guard
  `(high − rim) / high` with `rim = min(ends)`, which is the correct mirror and admits 71 more.
- **triangles 3,680 → 3,205, in two measured steps.** Stated as a chain because an earlier
  revision of this paragraph did not reconcile — it credited the superset with "+416" and the
  removal with "−475", which does not sum (3,680 + 416 ≠ 3,621) and reached the right endpoint
  only by conflating the two deltas.

  | step | count | delta |
  |---|---|---|
  | CANDLE-0 probe, rectangle-inclusive | 3,680 | — |
  | shipped module, PRE-skip (1,788 bear + 1,833 bull) | 3,621 | **−59** — branch-enumeration difference. The probe enumerated named branches (`TRI_UP`, `TRI_DN`, `TRI_SYM`, `WEDGE_RISE`, `WEDGE_FALL`, `RECT`) and dropped any converging pair matching none of them; this module accepts every converging shape, a superset there, but applies the `w1 > 0.02` body test only to rectangles. The two effects net to −59. |
  | shipped module, POST-skip (1,586 + 1,619) | **3,205** | **−416 confirmations**, on **475** rectangle bars (248 up + 227 down). The two numbers differ because **59 of those 475 bars also carried a non-rectangle pattern that still confirms**, so the bar keeps its flag. 475 is the rectangle population; 416 is what removing it costs. |

---

## 3. Gate D — scale invariance, per column

`tests/test_candle1_patterns.py::test_gate_d_*`. The ×8 / ×64 comparison is `(a != b).sum()` —
**exact equality, no tolerance**.

**Round 1 reported this per MODULE and the aggregate was misleading.** It said "0 mismatches over
3,430 / 2,940 / 3,928 / 3,262 co-finite cells", which invites a reader to think the gate was
exercised thousands of times. It was not: those totals are dominated by the flags, `*_PEND` and
`*_AGE`, whose scale invariance is trivial. On that 500-bar frame the columns whose arithmetic
could actually break — the magnitudes — carried `HS_TGT_PCT` **2** nonzero cells, `CUP_DEPTH` 7,
`CUP_CURV` 7 and the three `TRIW_*` magnitudes 31 each. Not vacuous, but roughly 1,700× less
exercise than the headline implied.

Two changes followed. The frame is now **4 seeds × 2,000 bars**, and
`test_gate_d_is_not_vacuous_column_by_column` **fails** if any column contributes fewer than 20
nonzero co-finite cells — so a matcher that tightens until a magnitude stops firing can no longer
take Gate D down with it silently.

Per column, ×8, over 4 × 2,000 bars (seeds 11–14). `nonzero` is the count that actually exercises
the gate:

| column | co-finite cells | **nonzero** | mismatches |
|---|---|---|---|
| `HS_CONF_BEAR_3_3_0.03_60` | 7,960 | 28 | **0** |
| `HS_CONF_BULL_3_3_0.03_60` | 7,960 | 36 | **0** |
| `HS_TGT_PCT_3_3_0.03_60` | 7,960 | 64 | **0** |
| `HS_PEND_3_3_0.03_60` | 7,960 | 1,832 | **0** |
| `HS_AGE_3_3_0.03_60` | 7,960 | 7,896 | **0** |
| `TRPL_CONF_BEAR_3_3_0.03_60` | 7,960 | 150 | **0** |
| `TRPL_CONF_BULL_3_3_0.03_60` | 7,960 | 137 | **0** |
| `TRPL_TGT_PCT_3_3_0.03_60` | 7,960 | 287 | **0** |
| `TRPL_PEND_3_3_0.03_60` | 7,960 | 4,978 | **0** |
| `TRPL_AGE_3_3_0.03_60` | 7,960 | 7,673 | **0** |
| `TRIW_CONF_BEAR_3_3_60` | 7,964 | 209 | **0** |
| `TRIW_CONF_BULL_3_3_60` | 7,964 | 187 | **0** |
| `TRIW_SLOPE_UP_3_3_60` | 7,964 | 396 | **0** |
| `TRIW_SLOPE_DN_3_3_60` | 7,964 | 396 | **0** |
| `TRIW_WIDTH_3_3_60` | 7,964 | 396 | **0** |
| `TRIW_PEND_3_3_60` | 7,964 | 683 | **0** |
| `TRIW_AGE_3_3_60` | 7,964 | 7,568 | **0** |
| `CUP_CONF_BULL_30_5_0.6_0.1_0.05` | 7,864 | 78 | **0** |
| `CUP_CONF_BEAR_30_5_0.6_0.1_0.05` | 7,864 | 79 | **0** |
| `CUP_DEPTH_30_5_0.6_0.1_0.05` | 7,864 | 157 | **0** |
| `CUP_CURV_30_5_0.6_0.1_0.05` | 7,864 | 157 | **0** |
| `CUP_AGE_30_5_0.6_0.1_0.05` | 7,864 | 7,707 | **0** |

Suffixes here are the PROBE parameters (`left=right=3`, cup `30/5`), not the shipped defaults —
Gate D runs at settings that fire often enough to test. The shipped-default names are in §2.

The thinnest column is still `HS_CONF_BEAR` at 28: a head and shoulders is a rare shape and four
2,000-bar walks is what it takes to clear 20. That is disclosed rather than smoothed over.

×10 and ×3.7 are checked with a tolerance and matching NaN masks; worst deviation anywhere is
5.4e-15 (`triangle_wedge`), then 2.1e-15 (`rounding_cup`), 9.0e-16 (`triple_top_bottom`), 4.2e-16
(`head_shoulders`).

One place where bit-identity COULD break, stated rather than assumed: `triangle_wedge` divides by
`max(hy1, 1e-9)`. On a series whose pivots sit below 1e-9 the clamp engages at one scale and not
the other. No BIST or US equity frame reaches that, and the test does not manufacture one.

`test_gate_d_no_column_is_constant` also pools four seeds, because on a single seed-11 frame
`HS_CONF_BULL` never fires. A property of the sample; the fix was a bigger sample, not a weaker
assertion.

## 3b. Gate B — causality

Future-perturbation mutants, four modules, in `tests/test_candle1_patterns.py::test_gate_b_*`. Every
bar from `J` onward is bumped by +50; nothing before `J` may move. The mutant is an `importlib` +
`exec` copy of the real source with the confirmation write index moved from `T` to `T // 2`.

Measured on a 600-bar seed-7 frame, all four real modules leak **0.0** at every
`J ∈ {150, 200, 250, 300}`. The mutant is caught (leak 1.0) at J=150 for all four; at J=200 the
`triangle_wedge` mutant escapes and at J≥250 the `rounding_cup` mutant escapes, because that module
fires only 6 times in 600 bars and never after bar 222. The test therefore requires the real module
clean at **every** J and the mutant caught at **some** J. Pinning one lucky J would have been a
weaker claim dressed as a stronger one.

Prefix truncation is not used and is not evidence — `CLAUDE.md` Gate B.

---

## 4. Gate E — the per-pattern table

Max |Spearman ρ| of each shipped column against all **485** production columns, pooled over
**91,197** bars. `gate_e_max.csv`; the 25 strongest pairings per column are in `gate_e_top.csv`.
Ship line: |ρ| ≈ 0.9 revert · 0.76–0.80 disclose · below 0.76 ship.

**Column names in this table are abbreviated to their stem** — `HS_CONF_BEAR`, not
`HS_CONF_BEAR_5_5_0.03_60` — purely so the rows fit. The shipped columns ARE suffixed; §2 and the
CSVs carry the full names, and `docs/CandlePatternShortlist.md` §4's naming rule is followed, not
ignored. `triangle_wedge`'s suffix is `_5_5_60` (three parameters, not four) because its `tol` was
dead and was deleted; `rounding_cup`'s is `_40_10_0.6_0.1_0.05` because `min_depth` is live and was
missing. Both changes are in §1.

**MINOR 6, applied.** An earlier revision reported any pairing with n ≥ 100. At n = 120 the
standard error of a null ρ is ≈ 0.09, so a spurious 0.30 could have become this document's
headline — "the largest ρ anywhere" was partly a property of that floor. The floor is now
**n ≥ 5,000**, and `gate_e_max.csv` carries a SECOND maximum restricted to **n ≥ 50,000** so a
reader can see whether a headline rests on a well-sampled comparator. No verdict changed.

| pattern | column | fire rate | Gate D | Gate E max \|ρ\| | against | n | verdict |
|---|---|---|---|---|---|---|---|
| **Head & shoulders (bear)** | `HS_CONF_BEAR` | 0.199% | pass | 0.0651 | `BOS_BEAR` | 90,497 | **SHIP** |
| **Inverse H&S (bull)** | `HS_CONF_BULL` | 0.199% | pass | 0.0553 | `ZSCORE_20` | 90,497 | **SHIP** |
| | `HS_TGT_PCT` | 0.398% | pass | 0.0449 | `EQH_5_5` | 90,497 | **SHIP** |
| | `HS_PEND` | 11.94% | pass | 0.0799 | `DTDB_PEND_8_0.5_0.15` | 90,397 | **SHIP** |
| | `HS_AGE` | 99.60% | pass | 0.1991 | `RPO_VA_WIDTH_PCT_110_80` | 85,697 | **SHIP** |
| | ~~`HS_SYM`~~ | 0.390% | pass | 0.0454 | `EQH_5_5` | 90,497 | **REVERT (internal)** |
| | ~~`HS_HEAD_EXC`~~ | 0.398% | pass | 0.0448 | `EQH_5_5` | 90,497 | **REVERT (internal)** |
| **Triple top** | `TRPL_CONF_BEAR` | 0.207% | pass | 0.1028 | `EQH_5_5` | 90,497 | **SHIP** |
| **Triple bottom** | `TRPL_CONF_BULL` | 0.242% | pass | 0.0922 | `EQL_5_5` | 90,497 | **SHIP** |
| | `TRPL_TGT_PCT` | 0.449% | pass | 0.0678 | `EQL_5_5` | 90,497 | **SHIP** |
| | `TRPL_PEND` | 12.50% | pass | 0.1266 | `dist_from_yr_high_pct` | 78,647 | **SHIP** |
| | `TRPL_AGE` | 99.55% | pass | 0.2911 | `RPO_VA_WIDTH_PCT_110_80` | 85,697 | **SHIP** |
| | ~~`TRPL_SPREAD`~~ | 0.449% | pass | 0.0678 | `EQL_5_5` | 90,497 | **REVERT (internal)** |
| **Asc / desc triangle · symmetrical triangle · rising / falling wedge** | `TRIW_CONF_BEAR` | 1.752% | pass | 0.1275 | `EQH_5_5` | 90,547 | **SHIP** |
| | `TRIW_CONF_BULL` | 1.788% | pass | 0.1353 | `EQL_5_5` | 90,547 | **SHIP** |
| | `TRIW_SLOPE_UP` | 3.524% | pass | 0.1038 | `kst_KSTs_9` | 88,597 | **SHIP** |
| | `TRIW_SLOPE_DN` | 3.521% | pass | 0.0869 | `aroon_AROOND_25` | 89,947 | **SHIP** |
| | `TRIW_WIDTH` | 3.539% | pass | 0.1043 | `CHOP` | 89,847 | **SHIP** |
| | `TRIW_PEND` | 6.483% | pass | 0.1667 | `SRCOR_WIDTH_ATR_8_5_0.6` | 81,138 | **SHIP** |
| | `TRIW_AGE` | 96.46% | pass | 0.2073 | `ADX` | 89,847 | **SHIP** |
| | ~~`TRIW_CONV`~~ | 3.998% | pass | 0.1071 | `CHOP` | 89,847 | **REVERT (internal ρ)** |
| **Rectangle** | — (never emitted) | **0.5246%** pre-skip | — | — | — | — | **SKIP (pre-registered trigger, §6)** |
| **Cup & handle / rounding bottom** | `CUP_CONF_BULL` | 0.458% | pass | 0.0812 | `log_return` | 88,747 | **SHIP** |
| **Rounding top** | `CUP_CONF_BEAR` | 0.352% | pass | 0.0730 | `log_return` | 88,747 | **SHIP** |
| | `CUP_DEPTH` | 0.809% | pass | 0.0481 | `FSME_CE_SCORE_BEAR_5` | 5,249 | **SHIP** |
| | `CUP_CURV` | 0.809% | pass | 0.1090 | `log_return` | 88,747 | **SHIP** |
| | `CUP_AGE` | 99.19% | pass | 0.2203 | `RPO_VA_WIDTH_PCT_110_80` | 85,697 | **SHIP** |
| | ~~`CUP_R2`~~ | 0.809% | pass | 0.0482 | `FSME_CE_SCORE_BEAR_5` | 5,246 | **REVERT (internal)** |
| | ~~`CUP_SYM`~~ | 0.807% | pass | 0.0480 | `FSME_CE_SCORE_BEAR_5` | 5,246 | **REVERT (internal)** |
| **Broadening / megaphone** | — | — | — | — | — | — | **NOT BUILT** — CANDLE-0 DEFER, honoured |
| **Double top / bottom** | — | — | — | — | — | — | **NOT BUILT** — `dtdb` ships it |
| **Flag / pennant** | — | — | — | — | — | — | **NOT BUILT** — `flag_breakout` ships it |
| **62 TA-Lib candles** | — | — | — | — | — | — | **NOT BUILT** — reachable today (CANDLE-2) |

The Rectangle row's fire rate is **475 / 90,547 = 0.5246%** — the count of BARS on which a
rectangle confirmed, pre-skip, over `TRIW`'s non-null bars. It is not 416/90,547 = 0.4595%, which
is the count of confirmations *removed* by the skip; the two differ by the 59 bars that also
carried a surviving pattern (§2). An earlier revision printed 0.466%, which tied to neither run.

**Headline: not one of the 28 built columns was near the shipped set.** The largest |ρ| anywhere
against 485 production columns is **0.2911** (`TRPL_AGE` × `RPO_VA_WIDTH_PCT_110_80`, n = 85,697 —
well-sampled, so it is not a small-n artefact), against a 0.76 disclosure line and a 0.9 revert
line. CANDLE-0's 112-column sweep put the largest at 0.1452; widening to 485 raised it to 0.2911
and changed no verdict.

⚠ **"against" names ONE of several rank-tied comparators.** `idxmax` breaks ties by column
order, so where several shipped columns reach the same |ρ| to four decimals the name in this table
is arbitrary. Measured — `n_tied_at_max` in `gate_e_max.csv` — **4 of the 22 columns tie**:
`CUP_CONF_BULL` (0.0812), `CUP_CONF_BEAR` (0.0730) and `CUP_CURV` (0.1090) each tie **three**
comparators (`log_return`, `percent_return`, `VELOCITY`), and `HS_CONF_BULL` (0.0553) ties **two**.
The other 18 have a unique maximum. Where the tie count is > 1 the "against" column names one
member of the set, not the answer; no verdict depends on which.

Under the n ≥ 50,000 floor, **exactly one column's maximum moves**: `CUP_DEPTH` drops from 0.0481
(`FSME_CE_SCORE_BEAR_5`, n = 5,249) to 0.0383 (`RPO_BREAK_UP_110_80`, n = 85,647). Every other
column's strongest pairing is already well-sampled. That is the whole practical content of MINOR 6
on this data — but the floor is now in the code, so the claim no longer depends on having got
lucky.

Three of the four largest are the `*_AGE` columns against `RPO_VA_WIDTH_PCT_110_80` (0.1991 /
0.2911 / 0.2203). That is a shared slow-moving-regime component, not a restatement of a pattern.

`CUP_DEPTH` peaks against `FSME_CE_SCORE_BEAR_5` at **n = 5,249**, a small overlap: that comparator
is populated on only ~6% of the pool. Its largest well-sampled pairing is `RPO_BREAK_UP_110_80` at
ρ = 0.0383, n = 85,647. Both are in `gate_e_max.csv`; the verdict is SHIP either way.

---

## 5. The six columns that were built, measured and deleted

**Every one of them cleared Gate E against the shipped set** (the `Gate E max |ρ|` column in §4
for the struck-through rows is from the first, 28-column run). They were deleted on the **internal**
overlap — new column against new column — which is a check `CLAUDE.md`'s gate table does not name
but its non-redundancy contract requires.

**The evidence is reproducible, deliberately.** Once the six columns left `pandas_ta/`, the harness
could no longer produce them by calling the shipped modules, and the numbers below would have been
a claim with no run behind them — the exact defect `CLAUDE.md` names as this repo's dominant one.
So `measure_candle1_overlap_full.py --reverted` RE-DERIVES all six from the raw frames using the
formulas the modules used before the cut, and writes `reverted_internal_overlap.csv`. That file is
an audit trail, not a candidate for re-shipping: it is a second implementation of the same scan and
is not itself gate-tested. Run against the shipped code it reproduces every figure in the table
below to four decimal places — 1.0000 / 1.0000 / 1.0000 / 0.9986 / 0.9986 / 0.9902 / 0.9902 /
−0.8928 — which is also the check that the re-derivation is faithful.

| pair | ρ | n | action |
|---|---|---|---|
| `TRPL_TGT_PCT` × `TRPL_SPREAD` | **1.0000** | 90,497 | drop `TRPL_SPREAD` |
| `HS_TGT_PCT` × `HS_HEAD_EXC` | **1.0000** | 90,497 | drop `HS_HEAD_EXC` |
| `CUP_DEPTH` × `CUP_R2` | **1.0000** | 88,747 | drop `CUP_R2` |
| `CUP_R2` × `CUP_SYM` | 0.9986 | 88,747 | drop `CUP_SYM` |
| `CUP_DEPTH` × `CUP_SYM` | 0.9986 | 88,747 | (same two) |
| `HS_TGT_PCT` × `HS_SYM` | 0.9902 | 90,497 | drop `HS_SYM` |
| `HS_SYM` × `HS_HEAD_EXC` | 0.9902 | 90,497 | (same two) |
| `TRIW_CONV` × `TRIW_WIDTH` | −0.8928 pre-skip · **−0.9994** post-skip | 90,547 | drop `TRIW_CONV` |

**The mechanism, because it generalises.** A magnitude that is nonzero on exactly its own event's
support and 0.0 everywhere else is, to a rank correlation, mostly a DESCRIPTION OF THAT SUPPORT:
90,137 tied zeros against 360 nonzero values, so the zero/nonzero split dominates and the ordering
*within* the support barely moves the coefficient. Two such columns on the SAME support are
therefore near-perfectly rank-correlated no matter what they measure. `HS_SYM` (shoulder asymmetry)
and `HS_HEAD_EXC` (head dominance) are genuinely different quantities and it did not save them.

**What escapes it, measured:** a SIGNED magnitude.

    CUP_DEPTH x CUP_CURV    spearman rho = 0.1307    n = 88,747

`CUP_CURV` is positive on the 406 cup bars and negative on the 312 rounding-top bars, so it splits
the support into three rank blocks instead of two and stops being a description of the support
alone. That is why `rounding_cup` keeps two magnitudes where `head_shoulders` and
`triple_top_bottom` keep one. If the deleted columns are ever wanted back, the routes are: give
them a sign, or publish them CONTINUOUSLY over the pending window instead of only on the break bar.
Both are redesigns and neither was attempted here.

**`TRIW_CONV` was the one judgement call in the list, and it stopped being one.** When it was
deleted, the measured pair was **−0.8928** — between this repo's stated disclosure band (0.76–0.80)
and its stated revert point ("ρ ≈ 0.9"), and 0.8928 was read as ≈ 0.9. Re-measured on the
population that actually ships, after the rectangle skip, it is **−0.9994**: an unambiguous revert,
no reading required.

The move is not noise and the mechanism is the §5 mechanism again. Pre-skip, rectangles sat in the
support with `CONV ≈ 0` and a large `WIDTH`, which broke the monotone relation between the two and
held |ρ| down. Post-skip every accepted pattern converges by construction, so `CONV` and `WIDTH` are
nonzero on exactly the same 3,204 bars and vary together — and two magnitudes on one support go to
±1. The original tiebreaker (that `CONV`'s only job was to say the boundaries converged, which the
acceptance rule now guarantees) turns out to be the same fact stated qualitatively.

⚠ **This was ALSO found as a measurement bug, and it is worth recording how.** An earlier round-3
run reported −0.9415 for this pair. That number was an artefact: the harness re-derived `TRIW_CONV`
from a duplicated copy of the triangle loop that still accepted rectangles, while `TRIW_WIDTH` came
from the shipped, post-skip module — two different populations compared to each other. The fix was
to have `_scan` return `conv` and delete the duplicate, so the reverted column and the shipped one
are now the same code on the same population. **A re-derivation of a deleted column is only
evidence if it is re-derived on the population the survivors are measured on.**

**Re-measured after the cut and after the rectangle skip**, the largest surviving internal pair is
`CUP_CONF_BULL` × `CUP_CURV` at **0.7533**, then `CUP_CONF_BULL` × `CUP_DEPTH` 0.7505,
`TRPL_CONF_BULL` × `TRPL_TGT_PCT` 0.7336, `HS_CONF_BEAR` × `HS_TGT_PCT` 0.7066, `TRIW_CONF_BULL` ×
`TRIW_WIDTH` 0.7037. Every one is a flag against its own magnitude — the shape `dtdb` already ships at 0.7829
and discloses — and every one is now **below** the 0.76 disclosure line. Nothing among the 22 is in
the disclosure band, let alone the revert band. (This is a second full run of the harness against
the post-cut modules, not the first run's table with rows removed; the `_work` cache was deleted
first, so the CSVs in `candle1_out/` describe exactly what ships.)

Also proposed by `CandlePatternShortlist.md` §4 and **never built**: `TRPL_TOUCHES`. This matcher
only accepts three same-side touches, so the column would be 3.0 on every confirmation bar — a
rescaled copy of the flags, constant on its own support. Recorded so the proposal is answered.

---

## 6. The rectangle — the pre-registered trigger FIRED, and it is honoured

**Verdict: SKIP. `triangle_wedge` no longer matches the rectangle.** Round 1 of this document
shipped it. That was wrong twice over, and both errors pushed the same way.

### 6.1 The trigger, as it was written before the module existed

`docs/CandlePatternShortlist.md` §5 item 5, pre-registered on RECALL rather than on ρ:

> *"if the real module's ±3-bar recall against `LCB_BREAKOUT_*` stays at or above ~0.69 at
> production parameters, rectangle becomes SKIP — covered, whatever ρ says."*
> Plus a second, independent condition: *"A full-Gate-E |ρ| above 0.76 against any LCB column flips
> it as well."*

### 6.2 Error one — the population was wrong

Round 1 derived the rectangle mask from the SHIPPED columns:

    TRIW_CONF_* == 1  AND  |TRIW_SLOPE_UP| < 0.0015  AND  |TRIW_SLOPE_DN| < 0.0015

That mask is **neither necessary nor sufficient** for the matcher's own rectangle branch
(`flat_h and flat_l and w1 > 0.02`), because `TRIW_SLOPE_UP` / `TRIW_SLOPE_DN` are aggregated by
**max-|value| across every pattern confirming on the bar**. This repo's own fixture
(`tests/test_candle1_patterns.py`, descending-triangle, bar 29) pins that `SLOPE_UP` can come from
one pattern while `WIDTH` comes from another.

- **False negatives.** A genuine rectangle co-confirming with a steeper triangle has its flat
  slopes overwritten and vanishes from the count. Crowded multi-pattern bars are plausibly where an
  LCB breakout is most likely, so this erasure biases recall **downward** — toward the answer
  round 1 reached.
- **False positives.** A `conv`-branch pattern whose two per-bar slopes both sit under 0.0015
  (0.0014/bar over 40 bars is 5.6% drift, comfortably a triangle) but which never passed
  `w1 > 0.02` was counted as a rectangle.

**The fix.** `pandas_ta/trend/triangle_wedge.py` now factors the loop into `_scan`, which returns
`rect_up` / `rect_dn` set on a confirmation bar only when the pattern that broke was accepted by
the rectangle branch. `triangle_wedge` calls that same function and publishes a subset of it, so
the measured population and the shipped behaviour are **one piece of code**, not a reconstruction.

**The error is measured, not asserted.** `rect_lcb.csv` carries both masks, derived from the SAME
`include_rect=True` scan so the comparison is about the mask and not about two code paths. On the
identical 50-ticker / 91,197-bar pool round 1 used:

| | proxy (round 1) | exact | error |
|---|---|---|---|
| RECT_UP events | 214 | **248** | 34 false negatives, **0 false positives** |
| RECT_DN events | 202 | **227** | 25 false negatives, **0 false positives** |
| RECT_UP ±3-bar recall | 0.6869 | **0.6976** | +0.0107 |
| RECT_DN ±3-bar recall | 0.6881 | **0.7048** | +0.0167 |

The proxy rows reproduce round 1's published figures exactly — 214 / 202 events, 0.6869 / 0.6881 —
which is the check that this reconstruction of round 1's mask is faithful rather than a
convenient one.

**All 59 errors are false negatives and none is a false positive**, so the bias was entirely in one
direction: the proxy under-counted rectangles, and it under-counted them on precisely the crowded
multi-pattern bars where a co-confirming steeper triangle overwrote the flat slopes. Both recalls
moved UP when the population was corrected. The false-positive branch was reasoned about in
advance and turned out to be empty on this data; it is left in the disclosure because nothing
guarantees that at other parameters.

⚠ **Disclosed, because it is a real limitation of the shipped surface:** the published columns
CANNOT express this mask exactly. Anything downstream that needs the exact shape of a specific
pattern must read `_scan`; the two-split slope rule is an approximation with error in both
directions, quantified in the `proxy_round1` rows of `rect_lcb.csv`.

### 6.3 Error two — the sample was too small to decide

Round 1 used 50 tickers → 202–214 rectangle events → recall SE ≈ 0.032. It measured
0.6869 / 0.6881, noted "this measurement does not distinguish 0.688 from 0.69", and then shipped
anyway on the third decimal. That is the textbook case pre-registration exists to prevent.

Worth stating plainly, because it is the sharpest version of the criticism: **under the tie-break
rule below, round 1's OWN numbers already fire the trigger.** 0.69 sits inside [0.6552, 0.7186] and
[0.6555, 0.7207]. No new data was needed to reach the right answer — only a rule fixed in advance
of looking. The enlarged sample and the corrected mask make the answer unambiguous; they were not
what changed it.

**Tie-break rule, now written down and applied** (round 2, adopted before the enlarged run was
read): *when the pre-registered threshold lies inside the measured statistic's 1-SE band, the
trigger is treated as **FIRED** unless a larger sample resolves it.* Both `trigger_fires_1se_rule`
and `trigger_fires_literal` are columns in `rect_lcb.csv` and `rect_lcb_large.csv`, so the rule
cannot be re-litigated after the fact.

### 6.4 The enlarged run, corrected mask — `rect_lcb_large.csv`

**250 tickers / 343,638 bars**, population read out of `_scan`:

| rectangle | vs | events | LCB fires | same-bar | ±3-bar recall | SE | 1-SE band | base | lift | literal | 1-SE rule |
|---|---|---|---|---|---|---|---|---|---|---|---|
| break up | `LCB_BREAKOUT_UP_5` | 811 | 14,594 | 307 | **0.7102** | 0.0159 | [0.6943, 0.7262] | 0.2722 | 2.61× | **FIRES** | **FIRES** |
| break down | `LCB_BREAKOUT_DN_5` | 756 | 14,741 | 267 | **0.6958** | 0.0167 | [0.6790, 0.7125] | 0.2676 | 2.60× | **FIRES** | **FIRES** |
| break up | `LCB_FORMED_5` | 811 | 29,478 | 45 | 0.4020 | 0.0172 | [0.3848, 0.4192] | 0.5170 | 0.78× | no | no |
| break down | `LCB_FORMED_5` | 756 | 29,478 | 43 | 0.4868 | 0.0182 | [0.4686, 0.5050] | 0.5170 | 0.94× | no | no |

**The trigger fires on the LITERAL reading, not merely the noise-aware one.** Both point estimates
clear 0.69, and 0.69 sits *below* the 1-SE band in both directions — the enlarged sample did not
leave it ambiguous, it moved it decisively across.

Delta against round 1, which is the whole point of §6.2 and §6.3:

| | round 1: proxy mask, 50 tickers | round 2a: exact mask, 50 tickers | round 2b: exact mask, 250 tickers |
|---|---|---|---|
| rectangle events | 416 (214 up / 202 dn) | 475 (248 / 227) | **1,567 (811 / 756)** |
| recall up / down | 0.6869 / 0.6881 | 0.6976 / 0.7048 | **0.7102 / 0.6958** |
| SE | 0.0317 / 0.0326 | 0.0292 / 0.0303 | **0.0159 / 0.0167** |
| literal (≥ 0.69) | no / no | **yes / yes** | **yes / yes** |
| 1-SE rule | **fires** / **fires** | **fires** / **fires** | **fires** / **fires** |
| verdict | shipped it | SKIP | **SKIP** |

The middle column isolates the two errors: correcting the MASK alone, at round 1's own sample size,
already flips the literal reading. Enlarging the sample then removes the remaining doubt.

The second trigger condition — Gate E |ρ| > 0.76 against any LCB column — is **definitively not
met**: no `TRIW_*` column reaches |ρ| 0.14 against ANY of the 485 (§4). The rectangle is skipped on
recall alone, exactly as the pre-registration said it could be.

Against `LCB_FORMED_5` the lift is **below 1** (0.78 / 0.94): a rectangle break is if anything
*less* likely near a compression box than baseline. That does not rescue it — the trigger was
written against `LCB_BREAKOUT_*`, not against `LCB_FORMED_5`.

### 6.5 What was struck

Round 1 justified shipping with three tiebreakers. **All three were reasons discovered AFTER the
number came back, none appears in the pre-registration, and all three are withdrawn:**

1. *"the rectangle is only 11.5% of `triangle_wedge`'s confirmations"* — a cost-of-removal
   argument, not evidence about coverage. (It is also now the measured cost of honouring the
   trigger: 811 of 6,951 bull and 756 of 6,386 bear confirmations, 11.7% / 11.8%, are gone.)
2. *"it costs no column of its own"* — same.
3. *"removing it would mean adding a rejection rule rather than deleting a column"* — a statement
   about implementation effort, offered as if it were about the feature's value. The rejection rule
   is one line.

### 6.6 What the skip does, and what it does not

`_scan(..., include_rect=False)` — the default and the shipped path — rejects a pattern whose shape
test says rectangle **outright**, including one that would also have qualified as converging. "Skip
the rectangle" has to mean the module emits none.

`_scan(..., include_rect=True)` restores the branch for one caller,
`measure_candle1_overlap_full.py`, so the measurement that fired the trigger stays reproducible now
that the trigger has been honoured. Honouring a decision must not delete its evidence.
`tests/test_candle1_patterns.py::test_the_rectangle_is_skipped_and_the_evidence_still_reproduces`
pins both halves, and fails if `include_rect=True` ever stops producing rectangles — otherwise a
matcher that quietly stopped finding them would look identical to a working skip.

**No null band was computed for these lifts.** CANDLE-0 flagged that gap; it is still open, and the
decision above does not rest on the lift figures.

## 7. What was NOT measured

1. **Whether any of this predicts anything.** Nothing here is a return study. Every number is a
   fire rate, an overlap or a recall. A pattern can be perfectly non-redundant and perfectly
   useless. This is the same gap `CandlePatternShortlist.md` §5 item 1 recorded.
2. **Parameter sensitivity.** Every figure is at one setting (`left=right=5, tol=0.03,
   max_wait=60`; cup `40/10/0.6/0.1`). No sweep was run. The overlap verdicts sit an order of
   magnitude below the ship line, so they are robust to this; the *counts* are indicative.
3. **Non-BIST behaviour.** All 91,197 bars are BIST daily. Hourly bars and US equities were not
   sampled, and pivot-based pattern rates move with bar interval.
4. **A null band for the ±3-bar lifts in §6.**
5. **Whether `dtdb` should have gained a touch-count parameter, or
   `liquidity_compression_box` a pivot-anchored boundary mode**, instead of two of these modules
   existing. `CandlePatternShortlist.md` §5 item 5 raised it; this document measures the modules
   side by side (triple-top × `dtdb` and rectangle × LCB, §6) and concludes they are separable
   populations, but it does not attempt the merged implementations that would settle it.
6. **The interaction of the six deleted columns with a MODEL.** They were deleted on a rank
   correlation. A tree can sometimes use two near-collinear features where a correlation says it
   cannot. No model was fit.

---

## 8. Reproduction

```sh
cd ../Backtesting
# Gates C and E, the internal overlap, and the 50-ticker rectangle delta
python scripts/analysis/measure_candle1_overlap_full.py --tickers 50 --out scripts/analysis/candle1_out

# the six deleted columns, re-derived, so §5's numbers stay reproducible
python scripts/analysis/measure_candle1_overlap_full.py --tickers 50 --out scripts/analysis/candle1_out --reverted

# THE RUN THAT SETTLED THE RECTANGLE (§6.4) -- 250 tickers / 343,638 bars.
# Skips IndicatorEngine entirely, so it is minutes rather than an hour.
python scripts/analysis/measure_candle1_overlap_full.py --rect-only 250 --out scripts/analysis/candle1_out
```

`--skip-sweep` reuses the cached pool and recomputes only the rectangle sections. It **refuses to
run** if `gate_e_max.csv` / `gate_e_top.csv` / `internal_overlap.csv` are missing or empty, because
an earlier revision of that flag emptied all three — leaving every figure in §4 and §5 true and
every citation pointing at nothing. The assert fails before any work is done.

Roughly 9 minutes to build the pool (cached per ticker under `candle1_out/_work/`) plus the
Spearman sweep. Writes:

| CSV | contents | backs |
|---|---|---|
| `pooled_meta.csv` | tickers, bars, engine column count | §0 |
| `reachability.csv` | per column: non-null, non-zero, fires, min/max/std | §2 |
| `gate_e_max.csv` | per column: max \|ρ\| over 485, the column, n, verdict | §4 |
| `gate_e_top.csv` | the 25 strongest pairings per column | §4 |
| `internal_overlap.csv` | every pair among the 22 shipped columns | §5 |
| `reverted_internal_overlap.csv` | the same with the six DELETED columns re-derived and put back (`--reverted`) | §5 |
| `rect_lcb.csv` | the rectangle trigger on 50 tickers, **both** masks (exact and round 1's proxy) | §6.2, §6.4 |
| `rect_lcb_large.csv` | the trigger on **250 tickers / 343,638 bars**, exact mask — the run that decided it | §6.4 |

Gates B, C and D are re-derived by `python -m pytest -q tests/test_candle1_patterns.py`.
