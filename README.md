# Pandas TA — Tolga Uyanik's fork

Technical analysis indicators as a pandas extension. Fork of
[twopirllc/pandas-ta](https://github.com/twopirllc/pandas-ta) `0.2.67b`, extended with
price-action / SMC indicators and oriented toward **machine-learning feature generation**.

**224 indicators** registered in `Category`, across 9 categories — that is the number
that matters, because `Category` is exactly what `df.ta.strategy()` sweeps. Two other
counts are true of the same package and are easy to confuse with it: **232** are callable
as `df.ta.<name>()` (`Category` plus `beta`, `hwma` and `vp`), and `drawdown` and `ma` are
importable as `ta.<name>()` without being either. All of them are in the dictionary; the
three counts are emitted by its generator, and `tests/test_readme_counts.py` fails if this
section drifts from the package. Every indicator returns a `Series` or `DataFrame`
with `UPPERCASE_UNDERSCORE_PARAM` column names.

---

## Install

```sh
pip install -U git+https://github.com/TolgaUyanik/PandasTa
```

Requires `pandas`, `numpy`. Optional: `scipy`, `sklearn`, `statsmodels`, `talib`, `yfinance`, `mplfinance`, `tqdm`.

---

## Quick start

```python
import pandas as pd
import pandas_ta as ta

df = pd.read_csv("ohlcv.csv", parse_dates=["datetime"], index_col="datetime")
# columns: open, high, low, close, volume  (df.ta lowercases OHLCVA for you)

# 1. Standard — explicit in, explicit out
sma10 = ta.sma(df["close"], length=10)        # Series "SMA_10"
bb    = ta.bbands(df["close"], length=20)     # DataFrame: BBL_/BBM_/BBU_/BBB_20_2.0

# 2. DataFrame extension — infers the ohlcv columns
sma10 = df.ta.sma(length=10)
df.ta.bbands(length=20, append=True)          # writes the columns into df

# 3. Strategy — named group, multiprocessed, always appends
feat = ta.Strategy(name="ml_v1", ta=[
    {"kind": "natr"},
    {"kind": "stoch"},
    {"kind": "zscore", "length": 20},
])
df.ta.strategy(feat)

# Every registered indicator also works standalone -- useful when you want one
# result joined on your own terms rather than appended by a strategy run:
df = df.join(ta.ichimoku_ml(df["high"], df["low"], df["close"]))
```

Discovery:

```python
df.ta.indicators()                 # print every indicator + utility
df.ta.indicators(as_list=True)     # same, as a list
df.ta.categories                   # category names
help(ta.bbands)                    # signature, params, output columns, sources
```

---

## Using this for machine learning

Fork rules. Read before feeding any column to a model.

### 1. Causality is the contract

Indicators added in this fork are **causal**: the value at bar `T` uses only data at `<= T`.
Two upstream columns are not, and they are the whole exception list —
[docs/IndicatorDictionary.md](docs/IndicatorDictionary.md#leak-watchlist) tracks them:

| Column | Problem | What to do |
|---|---|---|
| `ichimoku` → `ICS_26` | Chikou span is `close.shift(-kijun)` — the future | drop the column, or use `ichimoku_ml` |
| `dpo` → `DPO_20` | `centered=True` by default | pass `centered=False` |

Non-repainting is enforced elsewhere: `nadaraya_watson_envelope`, for example, weights a
trailing window only. Ported price-action indicators state causality in their module
docstring — `help(ta.<name>)` and read the leak note.

### 2. Trees cannot read absolute price

An indicator returning a *price level* (`SMA_50 = 41.72`) is a dead feature — the model
cannot compare it to `close`, and the level moves with the ticker and the year. Feed
**relations**, not levels.

```python
# bad: absolute level                    # good: scale-free relation
df.ta.sma(length=50, append=True)        (df["close"] - ta.sma(df["close"], 50)) / df["close"]
df.ta.atr(append=True)                   df.ta.natr(append=True)    # ATR normalized by price
```

`ichimoku_ml` is the worked example: the 5 Ichimoku price lines become 8 scale-free causal
features (`ICHI_PRICE_VS_CLOUD`, `ICHI_PRICE_VS_KIJUN`, `ICHI_TK_DIST`, `ICHI_TK_CROSS_AGE`,
`ICHI_CLOUD_COLOR`, `ICHI_CLOUD_THICK`, `ICHI_FUTURE_CLOUD_COLOR`, `ICHI_CHIKOU_VS_CLOUD`).
Prefer a `*_ml` variant wherever one exists.

Properties to prefer in a feature: scale-free (ratio, or percent of price), bounded or
distribution-stable across tickers, and stationary enough that a threshold learned in one
period still means the same thing in the next.

### 3. Warm-up NaNs are real

Every rolling indicator emits `NaN` for its first `length` (often more) bars. Drop the
warm-up window **per ticker**, before concatenating tickers. Never `fillna(0)` — that
invents signal at the start of each series.

```python
feats = feats.iloc[max_lookback:]     # per ticker, then concat
```

### 4. Naming is stable, so parse it

Column names encode the parameters: `STOCHk_14_3_3`, `BBU_20_2.0`, `MACDh_12_26_9`.
Pass `col_names=(...)` to pin fixed names — note it disables multiprocessing for that
Strategy.

### 5. Signals are labels, not features

`tsignals` / `xsignals` turn a trend or a crossover into entry / exit / trend columns
(`asbool=True` for boolean). Use them to build **labels**; feeding them back as features
is how a target leaks in.

---

## Indicators by category

Full reference — every output column, its ML form (scale-free / price-level / binary),
warm-up bars, and parameters: **[docs/IndicatorDictionary.md](docs/IndicatorDictionary.md)**
(generated by `python docs/gen_indicator_dictionary.py`).

`help(ta.<name>)` for the same per indicator.

**candles (5)** — `cdl_doji` `cdl_inside` `cdl_pattern` `cdl_z` `ha`

**cycles (7)** — `dsp` `ebsw` `ht_dcperiod` `ht_dcphase` `ht_phasor` `ht_sine` `ht_trendmode`

**momentum (52)** — `ao` `apo` `bias` `bop` `brar` `cci` `cdvo` `cfo` `cg` `cmo` `coppock`
`cti` `dm` `er` `eri` `fisher` `imi` `inertia` `kalman_rsi` `kdj` `kst` `lrsi` `macd`
`macd_area_divergence` `mom` `pgo` `po` `ppo` `pressure_pulse` `psl` `pvo` `qqe` `roc`
`rsi` `rsi_divergence` `rsx` `rvgi` `slope` `smi` `squeeze` `squeeze_pro` `stc` `stoch`
`stochrsi` `td_seq` `trix` `trixh` `tsi` `uo` `vwmacd` `wavetrend` `willr`

**overlap (48)** — `alma` `bpress` `dema` `dema2` `ema` `ema2` `ema_align` `fwma` `hilo` `hl2`
`hlc3` `hma` `iama` `ichimoku` `ichimoku_ml` `jma` `kama` `linreg` `linreg_channel`
`ma_disparity` `mcgd` `midpoint` `midprice` `mmar` `nadaraya_watson_envelope` `ohlc4` `pwma`
`rainbow` `rma` `rma2` `sinwma` `sma` `ssf` `supertrend` `supertrend2` `swma` `t3` `t3_tv`
`tema` `tema2` `trima` `vidya` `vwap` `vwma` `wcp` `wilder_rma` `wma` `zlma`

**performance (3)** — `log_return` `percent_return` `trend_return` (`cumulative=True` for cumulative)

**statistics (12)** — `covariance` `entropy` `kurtosis` `mad` `median` `normalize` `quantile` `rolling_sum` `skew` `stdev` `variance` `zscore`

**trend (56)** — `adx` `amat` `aroon` `atr_push` `band_cross_retest` `bdi4kewl` `bos` `choch`
`chop` `cksp` `decay` `decreasing` `dpo` `dtdb` `equal_highs_lows` `flag_breakout` `fvg`
`fvg_sweep_magnet` `halftrend` `head_shoulders` `increasing` `inverse_fvg`
`liquidity_compression_box`
`liquidity_sweep` `long_run` `nwog` `ob` `pivot` `pmax` `priorday_fib` `priormonth_range` `psar`
`qstick` `rejection_blocks` `renko_trend` `ribbon_concordance` `rounding_cup` `sd_zone_pro`
`short_run` `smc_sweep`
`sphinx_unicorn` `sr_corridor` `sr_decay` `sr_force` `swing_equilibrium` `triangle_wedge`
`triple_top_bottom` `tsignals`
`ttm_trend` `tvstop` `vhf` `volume_sr_zones` `vortex` `xsignals` `zigzag` `zigzag_fib`

**volatility (19)** — `aberration` `accbands` `atr` `atr2` `atr_ma_multiple` `bbands` `cvi` `donchian`
`har_park` `hwc` `kc` `massi` `natr` `pdist` `range_profile` `rvi` `thermo` `true_range` `ui`

**volume (22)** — `ad` `adosc` `aobv` `avwap_z` `bw_mfi` `cmf` `efi` `eom` `kvo` `mfi` `nvi` `obv`
`pocket_pivot` `pvi` `pvol` `pvr` `pvt` `tod_profile` `tri_dir_pressure` `vfi` `vol_delta`
`weis_wave`

Present but outside `Category`, so skipped by `df.ta.strategy()`: `beta`, `drawdown`,
`hwma`, `vp`, `ma` (moving-average selector — `help(ta.ma)`), and the two lower-timeframe
functions `up_and_down_volume` / `volume_delta`, and the four TA-Lib ports
`beta`, `ht_trendline`, `mama` and `sarext`. `beta`, `hwma`, `vp`,
`up_and_down_volume` and `volume_delta` are reachable as `df.ta.<name>()`; `drawdown` and
`ma` only as `ta.drawdown()` / `ta.ma()`. `beta` is a TALIB-1 port and needs a BENCHMARK
series a single-frame sweep cannot supply, which is the same reason as the two volume
functions below; it is absent from the dictionary for the same reason they are.

`ht_trendline`, `mama` and `sarext` return TA-Lib's raw PRICE LEVELS, and their
scale-free distance forms were measured into the Gate E revert band against columns
the engine already ships — `bias` 0.9576, `QQE_RSIMA` 0.9408, `dist_to_psar_pct`
0.9850. They stay callable (`emit_dist=True` restores the deleted columns for
re-measurement) but a strategy sweep would only emit dead `PX` columns. `beta`
needs a second series a sweep cannot supply.

The two volume functions are excluded **deliberately**: they require a second
(lower-timeframe) frame, which a strategy sweep cannot supply, so registering them took
the whole multiprocessing path down with a `ValueError`. See `docs/LowerTimeframeData.md`. `drawdown` was previously counted under
**performance** above AND listed here as outside `Category` — it is the latter.

Utilities: `above` `above_value` `below` `below_value` `cross`.

Performance metrics (return a `float`, called standalone — `ta.cagr(df.close)`): `cagr`
`calmar_ratio` `downside_deviation` `jensens_alpha` `log_max_drawdown` `max_drawdown`
`pure_profit_score` `sharpe_ratio` `sortino_ratio` `volatility`.

---

## DataFrame extension reference

```python
df.ta.adjusted = "adj_close"   # use adj_close instead of close; None resets
df.ta.cores = 4                # strategy multiprocessing; 0 disables it
df.ta.categories               # category list
df.ta.datetime_ordered         # True if DatetimeIndex and ascending
df.ta.exchange = "LSE"         # exchange used by last_run
df.ta.last_run                 # last run timestamp
df.ta.reverse                  # df in reverse order
df.ta.time_range               # index span, default "years"
df.ta.to_utc                   # index -> UTC

df.ta.hl2(prefix="pre", suffix="post")   # -> "pre_HL2_post"
df.ta.constants(True, [1])               # add / remove constant columns
df.ta.ticker("aapl", period="1y")        # yfinance download (optional dep)
```

Strategy shortcuts:

```python
df.ta.strategy()                            # everything (large)
df.ta.strategy("momentum")                  # one category
df.ta.strategy("overlap", length=42)        # override a shared kwarg
df.ta.strategy(exclude=["vp"], verbose=True, timed=True)   # skip what you do not want
```

`vwap` requires a `DatetimeIndex`.

Known breaks: **none** — every registered indicator calls cleanly on pandas 2.3.3, and every
name in `Category` has a `df.ta.<name>()` accessor. The dictionary's
[Known breaks](docs/IndicatorDictionary.md#known-breaks) section is generated from a live
probe, so it is the authority rather than this line.

`fvg`'s `IN_FVG_BULL`/`IN_FVG_BEAR` were **repaired 2026-09-07** and are safe to feed. They
had been driven by tick rounding: a zone was evicted on the bar that created it, so it
survived only when the close tied the bar's extreme. They now fire at **22.17% / 19.85%**
over 89 BIST_100 frames and 408,253 daily bars, with Gates C/D/E cleared (max |ρ| 0.6390 /
0.5962, under the 0.76 ship line). Evidence:
`../Backtesting/scripts/analysis/measure_fvg_overlap_full.py` and its four CSVs.

⚠ The **live trading container** still runs an unrepaired private copy of the same loop
(`FVGENG-2` in `TODO.md`), so research and live currently compute different `IN_FVG_*`
values. Account for that before comparing them.

---

## Adding an indicator (fork conventions)

1. One module per indicator in `pandas_ta/<category>/`; function name == file name.
2. Docstring states source, formula, **causality** (which bars each output reads), and any
   column deliberately dropped for leaking or for duplicating an existing one.
3. Register in `pandas_ta/<category>/__init__.py` and in `Category` in `pandas_ta/__init__.py`.
4. Add the DataFrame extension method in `pandas_ta/core.py`.
5. Tests in `tests/`. Measure a new column against the existing set first — columns that
   overlap an existing one get deleted, not shipped.

---

## Sources

[TA-Lib](http://ta-lib.org/) · [TradingView](http://www.tradingview.com) ·
[Sierra Chart](https://search.sierrachart.com/?Query=indicators&submitted=true) ·
[MQL5](https://www.mql5.com) · [FM Labs](https://www.fmlabs.com/reference/default.htm) ·
[Pro Real Code](https://www.prorealcode.com/prorealtime-indicators)

MIT. Upstream author: Kevin Johnson ([twopirllc](https://github.com/twopirllc)) and
[contributors](https://github.com/twopirllc/pandas-ta#contributors-).
