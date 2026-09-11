# Candle / Chart-Pattern Shortlist — CANDLE-0

Status: decision document for **CANDLE-0** (round 2). It decides *what to build* and proves, by
measurement, that each "build" entry is not already shipped. **No pattern is implemented here** —
that is CANDLE-1.

> **CANDLE-1 has since run (2026-09-08).** The results — what shipped, what was measured and
> deleted, the full 485-column Gate E this document could not run, and the resolution of the
> rectangle flip trigger — are in **`docs/CandlePatternsMeasured.md`**. Read that alongside this
> one: several §3 verdicts here were confirmed and six proposed columns in §4 did not survive
> measurement.

Every number below comes from one script,
`../Backtesting/scripts/analysis/measure_chart_patterns_overlap_full.py`, whose CSV outputs are in
`../Backtesting/scripts/analysis/candle0_out/`. §6 gives the command.

**Status of that script: written to disk, `untracked` pending the owner's commit decision.** All
thirteen sibling `measure_*_overlap_full.py` harnesses in that directory are tracked and this one
should join them; committing was outside this session's authority, so nothing has been staged.

**Round-2 correction, stated up front.** Round 1 of that harness called
`ta.liquidity_compression_box` **positionally as `(open, high, low, close)`**. Its real signature is
`(high, low, close, open_)`, so the probe fed open→high, high→low, low→close and got all-zero,
all-NaN output — which round 1 then wrote up as a Gate C failure in shipped code. **It was not a Gate
C failure; it was a caller bug.** Called correctly, `LCB_FORMED_5` fires 7,872, `LCB_BREAKOUT_UP_5`
3,974, `LCB_BREAKOUT_DN_5` 3,871, and `LCB_HIGH_DIST_5`/`LCB_LOW_DIST_5` have 41,554 non-null each on
the same 91,197-bar pool. Those five columns are back in the sweep, `LCB_BREAKOUT_UP/DN` is now the
rectangle candidate's headline comparison (§3), and the harness now audits every call site's keywords
against the function's own signature before it runs.

---

## 0. The stale premise in `TODO.md`, and what CANDLE-2 still owes

`TODO.md` CANDLE-0 states: *"TA-Lib is not installed in this environment, so its ~60 patterns are
unreachable (the probe prints `[X] Please install TA-Lib to use <pattern>`)."*

**That is false as of this run.** Measured:

```sh
python -c "import talib; print(talib.__version__)"          # -> 0.7.1
python -c "import pandas_ta as ta; print(ta.version)"       # -> 0.2.67b1+tu.1
```

```python
ta.cdl_pattern(df.open, df.high, df.low, df.close, name="all").shape[1]   # -> 62
```

No `[X] Please install TA-Lib` line was printed.

**CANDLE-2 is NOT thereby closed.** `TODO.md:246-248`'s done-when is that
`docs/IndicatorDictionary.md` states which candle patterns are actually callable, and that file
currently says the opposite of the measurement:

- `docs/IndicatorDictionary.md:49` tags **23 of the 62** `cdl_pattern` columns `CONST`;
- `docs/IndicatorDictionary.md:308` repeats those same 23 in the *unregistered / defect* table;
- measured on 91,197 real BIST daily bars, **0 of 62 are constant** — every one fires at least once.

So CANDLE-2 remains open with three concrete items:

1. **Correct the dictionary against real data.** Regenerate or annotate so the 23 `CONST` tags at
   line 49 and the 23 rows at line 308 reflect that all 62 fire; if the generator's own probe frame
   is too small to fire the rare ones, say so in the file rather than tagging live columns dead.
2. **Decide TA-Lib's dependency status.** `setup.py:81` already lists `talib` — but inside
   `extras_require["dev"]`, alongside `matplotlib` and `vectorbt`. That is not "an optional-but-tested
   dependency"; it is a developer convenience. Decide whether it becomes its own extra
   (`extras_require["talib"]`) with a documented install path, or stays informal and the 62 columns
   are documented as environment-dependent.
3. **Add the test that pins the contract.** No test in `tests/` references `cdl_pattern` or the count
   62 (`grep -rn "cdl_pattern" tests/` → no hits). CANDLE-2 should add one asserting 62 columns when
   TA-Lib is importable, `pytest.skip` otherwise, plus the 0-dead reachability claim on a real frame.

None of that is a `TODO.md` edit. The `TODO.md` premise is stale and should be corrected, but the
task's own done-when is unmet.

This also makes CANDLE-0 *harder*: the non-duplication proof runs against 62 reachable pattern
columns, not zero.

---

## 1. Measured inventory of what is already reachable

### 1a. Environment and data

| item | value | how measured |
|---|---|---|
| talib | 0.7.1 | `import talib; talib.__version__` |
| pandas_ta (this fork) | 0.2.67b1+tu.1 | `ta.version` |
| `talib.CDL*` functions | **61** | `len([x for x in dir(talib) if x.startswith("CDL")])` |
| `ta.cdl_pattern(name="all")` columns | **62** | `.shape[1]` |
| data | BIST daily Parquet cache, `../Backtesting/datastore/cache/*_1d.parquet`, **578 files** | harness line 1 |
| pooled sample behind every number below | **50 tickers / 91,197 bars** (files in sorted order with ≥400 clean bars) | harness |

The 62 vs 61 difference is not a discrepancy: `cdl_pattern` drops TA-Lib's `CDLDOJI` and substitutes
two pandas_ta-native columns, `CDL_DOJI_10_0.1` and `CDL_INSIDE`. Measured:

Measured off `cdl_pattern`'s own dispatch table rather than by munging column-name strings
(harness `talib_lookback_and_perturbation`, persisted to `talib_span.csv`):

```
cdl_pattern columns: 62 = 60 forwarded to talib + 2 pandas_ta-native ['doji', 'inside']
talib CDL* functions cdl_pattern never calls: ['CDLDOJI']
cdl_pattern names talib does not provide: []
```

`ALL_PATTERNS` in `pandas_ta/candles/cdl_pattern.py` has 62 entries; `doji` and `inside` are served
by the fork's own `cdl_doji` / `cdl_inside`, and the other 60 are forwarded as `CDL<NAME>`. TA-Lib's
`CDLDOJI` is therefore the one function the wrapper never calls. **Round 2 quoted this as a set
difference over normalised column names; that phrasing reached the right answer by an accident of
string handling and is replaced by the dispatch-table read above.**

### 1b. The 62 reachable candle-pattern columns

`CDL_2CROWS · CDL_3BLACKCROWS · CDL_3INSIDE · CDL_3LINESTRIKE · CDL_3OUTSIDE · CDL_3STARSINSOUTH ·
CDL_3WHITESOLDIERS · CDL_ABANDONEDBABY · CDL_ADVANCEBLOCK · CDL_BELTHOLD · CDL_BREAKAWAY ·
CDL_CLOSINGMARUBOZU · CDL_CONCEALBABYSWALL · CDL_COUNTERATTACK · CDL_DARKCLOUDCOVER · CDL_DOJISTAR ·
CDL_DOJI_10_0.1 · CDL_DRAGONFLYDOJI · CDL_ENGULFING · CDL_EVENINGDOJISTAR · CDL_EVENINGSTAR ·
CDL_GAPSIDESIDEWHITE · CDL_GRAVESTONEDOJI · CDL_HAMMER · CDL_HANGINGMAN · CDL_HARAMI ·
CDL_HARAMICROSS · CDL_HIGHWAVE · CDL_HIKKAKE · CDL_HIKKAKEMOD · CDL_HOMINGPIGEON ·
CDL_IDENTICAL3CROWS · CDL_INNECK · CDL_INSIDE · CDL_INVERTEDHAMMER · CDL_KICKING ·
CDL_KICKINGBYLENGTH · CDL_LADDERBOTTOM · CDL_LONGLEGGEDDOJI · CDL_LONGLINE · CDL_MARUBOZU ·
CDL_MATCHINGLOW · CDL_MATHOLD · CDL_MORNINGDOJISTAR · CDL_MORNINGSTAR · CDL_ONNECK · CDL_PIERCING ·
CDL_RICKSHAWMAN · CDL_RISEFALL3METHODS · CDL_SEPARATINGLINES · CDL_SHOOTINGSTAR · CDL_SHORTLINE ·
CDL_SPINNINGTOP · CDL_STALLEDPATTERN · CDL_STICKSANDWICH · CDL_TAKURI · CDL_TASUKIGAP ·
CDL_THRUSTING · CDL_TRISTAR · CDL_UNIQUE3RIVER · CDL_UPSIDEGAP2CROWS · CDL_XSIDEGAP3METHODS`

**Reachability (measured on the 91,197-bar pool):** **0 of 62 are dead.** 15 of 62 fire on fewer than
0.1% of bars; the rarest are `CDL_KICKING`, `CDL_KICKINGBYLENGTH`, `CDL_MATHOLD`,
`CDL_CONCEALBABYSWALL` at 1 firing each (0.0011%). The most frequent are `CDL_DOJI_10_0.1` 30.53%,
`CDL_LONGLEGGEDDOJI` 28.52%, `CDL_SPINNINGTOP` 20.02%.

**Why none of them can be a chart pattern.** TA-Lib's own declared lookback, read from the abstract
API (`talib.abstract.Function(name).lookback`), is **at most 14 bars** across all 61 functions
(distribution: 2→2, 3→1, 5→1, 6→1, 7→3, 8→1, 10→14, 11→17, 12→15, 13→2, 14→4). The four at 14 are
`CDLBREAKAWAY`, `CDLLADDERBOTTOM`, `CDLMATHOLD`, `CDLRISEFALL3METHODS`, and most of that budget is
TA-Lib's running body/shadow *average* normaliser (default period 10), not pattern shape.

The comparison span is measured, not asserted. Instrumenting the head-and-shoulders probe over its
360 firings (`candle0_out/hs_span.csv`), the distance from the pattern's **first pivot bar to its
confirmation bar** is:

| | n | min | p10 | median | p90 | max | mean |
|---|---|---|---|---|---|---|---|
| HS_BEAR | 180 | 20 | 26 | **41** | 69.1 | 135 | 45.4 |
| HS_BULL | 180 | 22 | 30 | **45** | 69.2 | 127 | 48.3 |

So a confirmed H&S spans a median of 41–45 bars, with a p10–p90 range of 26–69. Against a ≤14-bar
declared lookback, the 62 candle columns and the candidates in §3 cannot be reading the same window
*by construction*; §3 measures the overlap anyway.

### 1c. The 112 shipped columns swept, module by module

Read off `candle0_out/pooled_columns.csv`. **112 columns from 16 modules, 0 dropped** — every one has
≥1,000 non-null values and non-zero standard deviation on the pool.

| module | n | columns |
|---|---|---|
| `cdl_pattern` | 62 | the 62 listed in §1b |
| `equal_highs_lows` | 6 | `EQH_5_5` `EQL_5_5` `EQH_DIST_5_5` `EQL_DIST_5_5` `EQH_BROKEN_5_5` `EQL_BROKEN_5_5` |
| `sphinx_unicorn` | 6 | `SPHINX_ARM_BULL_2` `SPHINX_ARM_BEAR_2` `SPHINX_FIRE_BULL_2` `SPHINX_FIRE_BEAR_2` `SPHINX_DIST_BULL_2` `SPHINX_DIST_BEAR_2` |
| `dtdb` | 5 | `DTDB_CONF_BEAR_8_0.5_0.15` `DTDB_CONF_BULL_8_0.5_0.15` `DTDB_TGT_PCT_8_0.5_0.15` `DTDB_PEND_8_0.5_0.15` `DTDB_RES_8_0.5_0.15` |
| `liquidity_compression_box` | 5 | `LCB_FORMED_5` `LCB_HIGH_DIST_5` `LCB_LOW_DIST_5` `LCB_BREAKOUT_UP_5` `LCB_BREAKOUT_DN_5` |
| `bos` | 4 | `BOS_BULL` `BOS_BEAR` `HIGHER_HIGH` `LOWER_LOW` |
| `fvg` | 4 | `FVG_BULL` `FVG_BEAR` `IN_FVG_BULL` `IN_FVG_BEAR` |
| `flag_breakout` | 3 | `FLAG_CONF_BULL_12_0.85_0.15` `FLAG_CONF_BEAR_12_0.85_0.15` `FLAG_PEND_12_0.85_0.15` |
| `range_profile` | 3 | `RPO_VA_WIDTH_PCT_110_80` `RPO_BREAK_UP_110_80` `RPO_BREAK_DN_110_80` |
| `swing_equilibrium` | 3 | `SWINGEQ_5_5` `SWINGEQ_BOS_BULL_5_5` `SWINGEQ_BOS_BEAR_5_5` |
| `atr_push` | 2 | `APUSH_BULL_14_5_5` `APUSH_BEAR_14_5_5` |
| `choch` | 2 | `CHoCH_BULL` `CHoCH_BEAR` |
| `halftrend` | 2 | `HALFTREND` `HALFTREND_DIR` |
| `ob` | 2 | `OB_BULL` `OB_BEAR` |
| `zigzag_fib` | 2 | `ZZFIB_50_5` `ZZFIB_618_5` |
| `sr_corridor` | 1 | `SRCOR_WIDTH_ATR_8_5_0.6` |

`zigzag` itself is not in the sweep: its single column `ZIGZAG_5` is NaN on every non-pivot bar by
design and carries no information the confirmed-pivot stream does not already provide to the probes.

### 1d. Two shipped chart-pattern matchers the task brief did not list

The brief's "what coverage already exists" list is **incomplete**. Two of the patterns a naive
shortlist would propose are *already shipped*:

- **`pandas_ta/trend/dtdb.py` — Double Top / Double Bottom.** Its own docstring calls it *"the first
  CHART-PATTERN SHAPE MATCHER in this fork"*: confirmed-pivot zigzag → two-peak/two-trough template →
  carried forward to a neckline break. Measured firings on the pool: BEAR 140, BULL 196, PEND non-zero
  on 8,746 bars.
- **`pandas_ta/trend/flag_breakout.py` — Flag / pennant.** `FLAG_CONF_BULL_12_0.85_0.15` 47 firings,
  `FLAG_CONF_BEAR_12_0.85_0.15` 201, `FLAG_PEND_12_0.85_0.15` 37,169.

**Double top/bottom and flag/pennant are therefore struck off the shortlist as already built**, and
`dtdb` is the template CANDLE-1 must follow (event on the *break* bar, scale-free unsigned target,
signed pending count).

Grepped for the rest across the whole package:

```sh
grep -rilE --include='*.py' \
  "head.and.shoulders|triangle|wedge|pennant|cup.and.handle|rounding|double.top|rectangle" pandas_ta/
```

Without `--include` that pattern returns **21 paths** — 12 `.py` files plus 9 compiled `.pyc`
duplicates of them. With `--include='*.py'`: **12 source files**. Round 2 printed the unfiltered
command, reported "ten", and disposed of only ten, omitting `trend/dtdb.py` and
`volume/tri_dir_pressure.py`. All twelve, opened and disposed of:

| file | matched | what it actually is |
|---|---|---|
| `overlap/pwma.py:2,34`, `overlap/swma.py:2`, `utils/_math.py:118-119` | *triangle* | `pascals_triangle` — the weighting kernel |
| `momentum/macd_area_divergence.py:437`, `overlap/iama.py:211`, `trend/fvg.py:134` | *rounding* | floating-point rounding, in prose |
| `trend/inverse_fvg.py:381`, `trend/sd_zone_pro.py:89` | *rectangle* | the drawn zone box of the Pine source |
| `trend/swing_equilibrium.py:40`, `trend/zigzag_fib.py:16` | *double-top* | prose in the pivot tie-breaking comment |
| `volume/tri_dir_pressure.py:98,101` | *triangle* | "right-triangle CDF" — the triangular distribution used to place a bar's open within its range. Unrelated |
| **`trend/dtdb.py`** — 14 matches, incl. its own `Indicator: Double Top / Double Bottom (DTDB)` docstring | *double top* | **a real detector, not a false positive — the shipped double-top/bottom matcher, §1d** |

So: **no module implements head-and-shoulders, triple top/bottom, triangle, wedge, rectangle,
broadening or rounding/cup — `dtdb` covers double top/bottom and is struck off the shortlist in
§1d.** Round 2's flat "None implements any of these patterns" contradicted its own §1d twelve lines
earlier; this is the correction.

---

## 2. Method used for the non-duplication proof

Names prove nothing here — this repo has shipped wrong "already covered" verdicts on exactly that
mistake, and round 1 of this very document added another. So for every candidate a **causal detector
was actually built and run**, and its output was correlated against the shipped columns.

The detectors live in the harness as `proto_pivot_patterns` and `proto_rounding`. They are
**throwaway probes, not the CANDLE-1 implementation**: coarse, single-parameterisation, and
deliberately outside `pandas_ta/`.

- Pivot stream: `pandas_ta.trend.zigzag_fib._confirm_pivots` (the fork's own causal,
  rightmost-tie-wins confirmation), `left=right=5`, alternated with replace-if-more-extreme.
- A pattern is matched only from pivots **already confirmed** at bar `T`, and emits only on the bar
  the neckline/boundary breaks.
- **Call safety.** Every shipped indicator is invoked by keyword, and `audit_signatures()` re-derives
  each signature at run time and exits non-zero if a call site's keywords are not real parameters.
  Run output: `signature audit: 16/16 call sites match their function's parameters`. This guard
  exists because of the LCB bug; it catches a wrong *keyword*, and since every keyword here is bound
  to the identically-named series, that is sufficient — but it would **not** have caught a positional
  call, which is why there are none.
- Overlap is reported three ways, because a rare binary event is badly served by Spearman alone:
  1. **max |Spearman ρ|** against all 112 swept columns;
  2. **same-bar Jaccard** and raw co-fire counts, plus both conditional directions where they differ;
  3. **±3-bar windowed lift** — `P(some shipped event within ±3 bars | candidate fires) / base rate`,
     the measure that catches "same event, one bar off". Computed against the 35 swept columns that
     are event-like (fire rate in (0, 20%), values in {−3…3}).

**Gate D and prefix stability, with the actual output** (harness `gate_d_and_prefix_check()`):

```
Gate D (x8, atol=0): 754 bars x 29 cols = 21866 cells, mismatches = 0
prefix stability:    440 bars x 15 flag cols = 6600 cells, mismatches = 0
```

The Gate D comparison is `!=` on the raw arrays — **exact equality, no tolerance**, as Gate D
requires. Round 2's banner said `atol=0` while the code ran `np.isclose(..., atol=1e-9)`; the code
now matches the banner and all 21,866 cells still agree bit-for-bit, so the tolerance had been
carrying nothing.

**Prefix stability is NOT causality evidence.** Per `CLAUDE.md` Gate B, prefix truncation cannot see
back-dating; only a mutant test can. CANDLE-1 owes that test, and this document does not claim
causality has been proven.

---

## 3. Shortlist

Pooled sample for every number: **50 BIST tickers, 91,197 daily bars**, swept against **112 shipped
columns from 16 modules, 0 dropped**. Repo ship line: |ρ| ≥ 0.9 revert, 0.76–0.80 ship-with-disclosure,
< 0.76 ship.

**This is not Gate E.** Gate E requires the full production config (~204 registered indicators); this
sweep covers 112 columns from 16 modules chosen for collision risk. CANDLE-1 must re-run it in full.

| pattern | what it measures | might restate | measured evidence | verdict |
|---|---|---|---|---|
| **Head & shoulders (bear)** | 5-pivot P-T-**P**-T-P, dominant middle peak, level shoulders; neckline break. Median span 41 bars | `DTDB_CONF_BEAR`, `CHoCH_BEAR`, `EQH_5_5` | 180 firings (0.197%). **max \|ρ\| = 0.0650** vs `EQH_5_5`. vs `DTDB_CONF_BEAR`: ρ = 0.0046, **1 co-fire of 180 / 140**. vs `CHoCH_BEAR`: ρ = 0.0217, 11 co-fires. Best ±3-bar lift 5.75× vs `EQL_BROKEN_5_5` at recall 0.206 — **79% of H&S confirmations have no shipped event within ±3 bars** | **BUILD** |
| **Inverse H&S (bull)** | mirror. Median span 45 bars | `DTDB_CONF_BULL`, `CHoCH_BULL` | 180 firings. max \|ρ\| = 0.0542 vs `BOS_BULL`. vs `DTDB_CONF_BULL`: ρ = 0.0086, 2 co-fires. ±3-bar lift 5.55× vs `EQH_BROKEN_5_5`, recall 0.200 | **BUILD** |
| **Triple top** | 3 peaks within tolerance + 2 intervening troughs, neckline break | `dtdb` (2-peak), `EQH_5_5` | 187 firings. max \|ρ\| = 0.1028 vs `EQH_5_5`. vs `DTDB_CONF_BEAR`: ρ = 0.0044, **1 co-fire of 187 / 140**; ±3-bar lift 10.5× at recall **0.112** → 89% of triple tops are invisible to `dtdb`. `dtdb`'s `dbl_mode` is `("any","weaker")` — read the source: **there is no 3-peak option**, so this is not reachable by parameter | **BUILD** |
| **Triple bottom** | mirror | `dtdb`, `EQL_5_5` | 219 firings. max \|ρ\| = 0.0923 vs `EQL_5_5`. vs `DTDB_CONF_BULL`: ρ = 0.0509, 11 co-fires; ±3-bar lift 12.9× at recall 0.192 | **BUILD** |
| **Ascending / descending triangle** | one flat boundary + one converging boundary over 4 pivots; boundary break | `RPO_BREAK_*`, `FLAG_*`, `LCB_BREAKOUT_*`, `SRCOR_WIDTH_ATR` | UP 705 firings (0.773%), DN 703 (0.771%). max \|ρ\| 0.0861 / 0.1209 (`EQH_5_5` / `EQL_5_5`). vs `FLAG_CONF_BULL`: ρ = −0.0020, **0 co-fires of 705 / 47**; vs `FLAG_CONF_BEAR`: 2 co-fires. vs `LCB_BREAKOUT_UP/DN`: ρ = 0.0229 / 0.0181. Best ±3-bar lift 3.7× / 3.5× | **BUILD** |
| **Symmetrical triangle** | both boundaries converging, opposite slopes | same | **now measured in its own right** (round-1 gap closed): UP 427 firings (0.468%), DN 390 (0.428%). max \|ρ\| 0.0580 / 0.0699 vs `EQL_5_5` / `EQH_5_5`. ±3-bar lift 2.53× / 3.33× vs `SWINGEQ_BOS_*` at recall 0.50 / 0.57 — the *highest recalls* in the table, so this is the shape most shadowed by an existing column, though at ρ ≤ 0.07 it is not a restatement | **BUILD** (same matcher; disclose the SWINGEQ recall) |
| **Rising / falling wedge** | both boundaries same-sign slope, converging | `CHoCH_*`, `HALFTREND_DIR` | RISE 579 (0.635%), FALL 451 (0.495%). max \|ρ\| 0.0660 / 0.0673, both vs `HALFTREND_DIR`. vs `CHoCH_BEAR`/`CHoCH_BULL`: ρ = 0.0224 / 0.0138, 23 / 13 co-fires. ±3-bar lift 2.01× / 2.58×, recall 0.152 / 0.175 | **BUILD** |
| **Rectangle / range break** | two flat boundaries, width > 2%, break | **`LCB_BREAKOUT_UP/DN`**, `RPO_BREAK_*`, `dtdb`, `SWINGEQ_BOS_*` | UP 217, DN 208. **max \|ρ\| = 0.1452 / 0.1252** vs `SWINGEQ_BOS_BULL/BEAR` — the highest of any candidate. **vs `LCB_BREAKOUT_UP_5`: ρ = 0.0712, 74 same-bar co-fires; vs `LCB_BREAKOUT_DN_5`: ρ = 0.0811, 80 co-fires.** That is **34.1% / 38.5% of rectangle breaks** landing on an LCB breakout bar — but only **1.9% / 2.1% of LCB breakouts** (74/3,974, 80/3,871): LCB fires ~18× more often, so the overlap is one-directional, not a restatement. Windowed, and this is the loudest number against this row: **68.7% / 71.2% of rectangle breaks sit within ±3 bars of an `LCB_BREAKOUT_*` — the highest coverage of any candidate in the table**, next highest being H&S at 0.206. Dilated base 0.279 / 0.264, lift 2.46× / 2.69×; **no null band was computed, so the lift is not tested against chance**. Against `LCB_FORMED_5` the windowed lift is **0.71 / 0.88 — below 1**, so rectangle breaks are if anything *less* likely near a compression box than baseline. vs `DTDB_CONF_BULL/BEAR`: ρ = 0.0803 / 0.0568, ±3-bar lift 16.4× / 14.9× (recall 0.244 / 0.159) — the largest lift in the table | **BUILD, with disclosure and last in build order** — see §5 item 5 |
| **Broadening / megaphone** | boundaries diverging | `BOS_*`, `APUSH_*` | 2,093 firings (2.30%). max \|ρ\| = 0.0984 vs `APUSH_BULL`. vs `BOS_BULL`: ρ = 0.0843, 579 co-fires of 2,093 / 9,732. ±3-bar lift 2.57× vs `DTDB_RES_8_0.5_0.15` (recall 0.0578, dilated base 0.0225) | **DEFER** — measured **non-duplicative** (max \|ρ\| 0.0984, the same range as several BUILD rows). Deferred on judgement, not on the overlap statistic: at a 2.30% fire rate from the loosest tolerance in the probe (`w2 > w1 × 1.25`, no shape constraint beyond divergence) it is likely a noise feature. **No predictive evidence either way** — see the criterion note below |
| **Cup & handle / rounding bottom** | curvature-positive quadratic over 40 bars, symmetric rims, handle offset, rim break | `APUSH_BULL`, `dtdb`, `LCB_BREAKOUT_UP`, `RPO_BREAK_UP` | 406 firings (0.445%). **max \|ρ\| = 0.0598** vs `APUSH_BULL_14_5_5` over all 112 columns. vs `LCB_BREAKOUT_UP_5`: ρ = 0.0583, 90 co-fires. ±3-bar lift 2.65× | **BUILD** |
| **Rounding top** | mirror | `APUSH_BEAR` | 241 firings (0.264%). max \|ρ\| = 0.0597 vs `APUSH_BEAR_14_5_5`. vs `LCB_BREAKOUT_DN_5`: ρ = 0.0390, 47 co-fires. ±3-bar lift 2.98× vs `SPHINX_FIRE_BEAR_2` | **BUILD** |
| **Double top / double bottom** | two-peak template + neckline break | — | **already shipped as `dtdb`** (§1d) | **SKIP — built** |
| **Flag / pennant** | impulse pole + counter-sloping consolidation + break | — | **already shipped as `flag_breakout`** (§1d) | **SKIP — built** |
| **Any TA-Lib candlestick pattern** | 1–5 candle shapes | — | all 62 already reachable, 0 dead (§1b) | **SKIP — reachable today**; the remaining work is CANDLE-2 §0 items 1–3 |

**Headline, recomputed over the corrected 112-column set:** the **largest |Spearman ρ| observed
anywhere is 0.1452** (`P_RECT_UP` × `SWINGEQ_BOS_BULL_5_5`). Restoring the five LCB columns did **not**
change it — the strongest LCB pairing is ρ = 0.0811, below eight other pairings already in the table.
The repo's revert line is 0.9 and its disclosure band starts at 0.76. On this evidence the shortlist
is not a restatement of anything shipped, with the rectangle's one-directional LCB co-fire disclosed
above and carried into §5.

**Criterion note (why one row is DEFER and ten are BUILD).** Overlap decides *duplication* only:
every row here clears it, so overlap alone would BUILD all eleven. The second, separate criterion is
**whether the shape is specific enough to be a feature rather than noise**, proxied by fire rate and
by how much of the probe's tolerance budget the shape actually constrains. Applied to all eleven
rows: H&S 0.197%, triple 0.205/0.240%, triangles 0.428–0.773%, wedges 0.495/0.635%, rectangle
0.228/0.238%, cup/rounding 0.264/0.445% — all under 0.8% from constrained templates. Broadening is
2.30%, ~3× the next-loosest, from the one template with no constraint beyond "the boundaries
diverged". That is the criterion, stated and applied; it is a judgement about specificity, not a
measurement, and it is reversible the moment CANDLE-1 has predictive evidence.

### Why they are worth measuring even at low overlap

Low ρ proves *non-duplication*, not *value*. The positive case, one line each:

- **H&S / inverse H&S** — the only candidate that encodes *momentum failure at a new extreme* (a
  higher high the next rally cannot match). `bos`/`choch` fire on the break; neither knows the break
  was preceded by a failed retest. This is the pattern the user asked for by name.
- **Triple top/bottom** — `dtdb` stops at two touches; the third touch is a different conditional.
  Measured recall 0.112 / 0.192 against `dtdb` says the two populations are mostly disjoint events.
- **Triangles / wedges** — the fork has *no* converging-boundary feature. `range_profile` measures
  value-area width but not boundary slope; `SRCOR_WIDTH_ATR` measures a corridor's width, not its
  convergence rate; `LCB_*` measures compression against ATR over a fixed 5-bar window, not a
  pivot-anchored trendline pair. A tree cannot derive "the boundaries are closing at X%/bar" from
  anything shipped.
- **Rectangle** — worth building precisely *because* it is adjacent to `LCB_BREAKOUT_*` and `dtdb`.
  Its value proposition is **specificity**: 217 events where LCB gives 3,974. Whether that
  specificity survives a full Gate E is the measurable question CANDLE-1 answers.
- **Cup / rounding** — the only candidate that is a *curvature* statement rather than a pivot-sequence
  statement, and it measured among the lowest overlaps of the set (0.0598 / 0.0597).

---

## 4. Proposed columns for each "build" entry (CANDLE-1 input)

Shape follows `dtdb`: event on the break bar, unsigned scale-free target, signed pending count,
nothing emitted at the pattern's own pivots.

**Suffix ordering rule** (one rule, applied to every module below): `_{left}_{right}_{tol}_{max_wait}`
— structural parameters first in the order they appear in the signature, then tolerances, then the
bar budget; floats written as given, not reformatted. This matches the existing convention where the
suffix is the parameter tuple in signature order (`DTDB_CONF_BEAR_8_0.5_0.15` =
`pivots_tolatr_bufatr`; `FLAG_CONF_BULL_12_0.85_0.15`).

**Common to every pattern module** (`X` = the prefix; defaults `left=5, right=5, tol=0.03,
max_wait=60`, i.e. suffix `_5_5_0.03_60`):

| column | ML form | definition |
|---|---|---|
| `X_CONF_BULL` / `X_CONF_BEAR` | BIN | 1 on the bar the neckline / boundary breaks by the ATR buffer, 0 elsewhere, NaN before the first bar at which a pattern could have confirmed. Saturating on simultaneity. |
| `X_TGT_PCT` | SF | `abs(measured_target - close) / close` on a confirmation bar, 0.0 elsewhere. **Unsigned** — direction lives in the two flags; `dtdb` already measured that shipping it signed alongside a signed flag hits ρ = 0.938 and gets reverted. |
| `X_PEND` | ORD | net live-pattern count at the close: `+1` per pending bullish, `−1` per pending bearish. |
| `X_AGE` | SF | bars since the most recent confirmation **divided by `max_wait`**, clipped to 1.0 — the "bars-since" the task asks for, made scale-free in *time*. 1.0 when nothing has confirmed. |

**Per module — one fully-suffixed example each, at the defaults above:**

| module | example column | extra pattern-specific columns |
|---|---|---|
| `head_shoulders` | `HS_CONF_BEAR_5_5_0.03_60` | `HS_SYM_5_5_0.03_60` — shoulder asymmetry `abs(p_left − p_right) / max(p_left, p_right)`; `HS_HEAD_EXC_5_5_0.03_60` — head excess over the taller shoulder as a fraction of it |
| `triple_top_bottom` | `TRPL_CONF_BEAR_5_5_0.03_60` | `TRPL_SPREAD_…` — `(max touch − min touch) / max touch`; `TRPL_TOUCHES_…` ORD |
| `triangle_wedge` | `TRIW_CONF_BULL_5_5_0.03_60` | `TRIW_CONV_…` — `(width_at_second_pivot_pair − width_at_first) / width_at_first`, negative = converging; `TRIW_SLOPE_UP_…`, `TRIW_SLOPE_DN_…` — each boundary's slope per bar as a fraction of its own level; `TRIW_WIDTH_…` — boundary separation `/ close`. Ascending / descending / symmetrical / rising wedge / falling wedge / rectangle are then a *tree-derivable function of these four*, so ship the measurements and at most one categorical — **not six one-hot flags** |
| rectangle | — | no separate module: `TRIW_CONV ≈ 0` with both slopes flat |
| `rounding_cup` | `CUP_CONF_BULL_40_10_0.6_0.10` (`N=40, handle=10, curv_min=0.6, sym_tol=0.10`) | `CUP_CURV_…` — the fitted quadratic's leading coefficient on rim-normalised prices (already unitless); `CUP_R2_…` 0–1; `CUP_DEPTH_…` — `(rim − low) / rim`; `CUP_SYM_…` — `abs(left_rim − right_rim) / rim` |

**Causality rule:** every value at bar `T` reads confirmed pivots only — pivots whose confirmation bar
is ≤ `T`. The probe was checked by prefix stability (0 mismatches over 6,600 cells), which per Gate B
**is not causality evidence**; CANDLE-1 owes the mutant test, and a pivot-based pattern is exactly the
defect class where back-dating hides.

**Explicitly forbidden columns:** any neckline / boundary / rim *price*; any pattern width in points;
any raw bar index; any signed target beside a signed flag.

---

## 5. What I could NOT measure, and why

1. **Whether these patterns predict anything.** Nothing here is a return study. Every number is an
   overlap or a fire rate. A pattern can be perfectly non-redundant and perfectly useless.
2. **The true dependency window of the TA-Lib patterns.** A perturbation probe (replace bar `T−k`
   with a flat doji, check whether the signal at `T` changes) **saturates at whatever `KMAX` is set**:
   the harness prints `perturbation probe KMAX=25: 14 of 61 functions report 25 -- AT THE CEILING`,
   and at `KMAX=60`, `CDLLONGLINE` / `CDLENGULFING` / `CDLHIKKAKE` all report 60 while `CDLDOJI`
   reports 0. **The count at the ceiling is itself sample-dependent** — a round-2 variant of this
   probe pooled 60 tickers and put 42 of 61 at the ceiling, where the harness's single-ticker run
   puts 14. That instability is the point: the probe measures how often a disturbance happened to
   flip a rare signal, not how far back the function reads. That is TA-Lib's running body-average normaliser, which has effectively
   unbounded reach, not the pattern's shape. `talib.set_candle_settings` does not exist in the 0.7.1
   Python binding (`[x for x in dir(talib) if "candle" in x.lower()]` → `[]`), so the averaging period
   could not be set to 1 to separate the two. **The ≤14-bar figure in §1b is TA-Lib's declared
   `lookback`, not my measurement of the shape span.** The conclusion rests on that declared lookback,
   the measured 41–45-bar median H&S span, and the 62 measured ρ values.
3. **Overlap against the entire shipped column set.** Gate E requires all ~204 registered indicators
   of the engine's production config. This sweep is 112 columns from 16 modules chosen for collision
   risk; the oscillator, volume and overlap families were not swept. **CANDLE-1 must run the full
   Gate E** via a `measure_<name>_overlap_full.py` per pattern.
4. **The probes' parameter sensitivity.** Every fire rate is at one setting (`left=right=5`,
   `tol=0.03`, `max_wait=60`; cup `N=40`, handle 10, R² > 0.6). No sweep was run, so the *counts* are
   indicative; the *overlap verdicts*, which sit an order of magnitude below the ship line, are what
   the decision rests on. The DEFER on broadening is the one verdict that depends on a count, and it
   is flagged as reversible for that reason.
5. **Whether rectangle and triple-top should be new modules or parameters on existing ones.** Two
   unresolved adjacencies. First and larger: **rectangle × `LCB_BREAKOUT_*` at ±3-bar recall
   0.687 / 0.712** — roughly seven in ten rectangle breaks already have an LCB breakout beside them,
   the highest coverage in the table (same-bar it is 34–38%, and only 1.9–2.1% the other way).
   Second: rectangle / triple-top × `dtdb` (±3-bar lift 16.4× / 10.5×). Both could
   be answered by giving `dtdb` a touch-count parameter, or by giving `liquidity_compression_box` a
   pivot-anchored boundary mode, instead of shipping new columns. **Deciding that needs the modules
   built and measured side by side — it is CANDLE-1 work and is recorded here so it is not silently
   decided.** **Flip trigger, stated on recall rather than on ρ or lift:** if the real module's ±3-bar
   recall against `LCB_BREAKOUT_*` stays at or above ~0.69 at production parameters, rectangle becomes
   SKIP — covered, whatever ρ says; ρ is depressed here purely by the 18× base-rate asymmetry. A
   full-Gate-E |ρ| above 0.76 against any LCB column flips it as well.
6. **Non-BIST behaviour.** All 91,197 bars are BIST daily. Hourly bars and US equities were not
   sampled; pivot-based pattern rates move with bar interval.
7. **A causality proof.** Prefix stability is not it (see §2 / §4).

### Ergonomics note (not a defect)

`liquidity_compression_box(high, low, close, open_, …)` puts `open_` **last**, where almost every
other OHLC indicator in the fork puts it first (`atr_push`, `ob`, `cdl_pattern`) or omits it. A
positional call in the conventional order silently produces all-zero, all-NaN output rather than
raising — which is exactly what happened in round 1 of this harness. The function is correct and its
own test (`tests/test_liquidity_compression_box.py:31`) calls it correctly; the risk is to callers.
Worth a docstring line warning against positional use, or a keyword-only marker. **Not a Gate C
failure and not filed as a defect.**

---

## 6. Reproduction

```sh
cd ../Backtesting
python scripts/analysis/measure_chart_patterns_overlap_full.py --tickers 50 --out candle0_out
```

Prints every measured figure in this document. The only things it does not produce are file reads
rather than measurements: the `TODO.md` / `IndicatorDictionary.md` / `setup.py` line references in
§0, and the `grep` disposal table in §1d. It writes:

| CSV | contents | backs |
|---|---|---|
| `pooled_columns.csv` | all 112 swept columns: module, name, non-null, non-zero, std | §1c |
| `overlap_max.csv` | per prototype: max \|ρ\|, max Jaccard, co-fire counts | §3 headline |
| `targeted_pairs.csv` | the 23 named suspect pairs, incl. rectangle × LCB | §3 |
| `windowed_lift.csv` | ±3-bar lift of each prototype vs the 35 event-like columns | §3 |
| `rect_lcb_windowed.csv` | rectangle × `LCB_BREAKOUT_*` and `LCB_FORMED_5`: recall, dilated base, lift | §3 rectangle row, §5 item 5 |
| `hs_span.csv` | the 360 head-and-shoulders spans | §1b span table |
| `talib_span.csv` | the 62-vs-61 dispatch decomposition, the declared-lookback distribution, the four functions at the max, and the perturbation probe's per-function ceilings | §1a, §1b, §5 item 2 |

The one environment fact not in a CSV is the version pair:

```sh
python -c "import talib, pandas_ta as ta; print(talib.__version__, ta.version)"
```
