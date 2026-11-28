# PandasTa — technical indicators as machine-learning features

[![tests](https://github.com/TolgaUyanik/PandasTa/actions/workflows/ci.yml/badge.svg?branch=dev)](https://github.com/TolgaUyanik/PandasTa/actions/workflows/ci.yml)
![licence](https://img.shields.io/badge/licence-MIT%20%2B%20MPL--2.0%20files-blue)

A pandas extension with **400+ technical-analysis indicators**, built so that every column can be
fed to a model: causal (no bar reads the future), scale-free where it matters, and documented
column by column. A fork of pandas-ta `0.2.67b` (twopirllc), written mostly by AI coding
agents: a human owner approves the work queue and rules on judgement calls, and changes merge
on automated tests (and, for queue work, an automated reviewer), not on a human code review
([how](#how-this-repository-is-built)).

> **Not financial advice. No warranty.** This is software for computing indicators, not a
> trading recommendation. Read the [disclaimer](DISCLAIMER.md) before using it.

---

## Why this fork

- **400+ indicators registered for bulk computation** (`df.ta.strategy()`), across 9 categories:
  upstream's set, plus TradingView/Pine ports, SMC price-action structure, TA-Lib ports, and
  time-series features from catch22, Kats and tsfresh-style definitions.
- **Built for ML, not charts.** Every column's observed form (scale-free, price level, binary,
  ordinal) and warm-up is generated into [`docs/IndicatorDictionary.md`](docs/IndicatorDictionary.md).
  Look-ahead bugs are fixed and pinned by tests (`ssf`, `bos`, `choch`) or made causal by
  default (`dpo`).
- **Gated, not just added.** A new indicator ships with correctness evidence against its source,
  plus causality (*mutant*), reachability and scale-invariance tests that CI runs with the full
  suite (about 17,000 tests) before the PR merges into `dev`. Its redundancy against a fixed set of several hundred reference
  features (Gate E) is recorded in `docs/gate_e_ledger.csv`; a release to `main` fails until
  every new indicator has its row.
- **Actively maintained.** 215 pull requests merged since 2026-09-11 (measured 2026-11-28). The
  original upstream GitHub repository is no longer available.

**How it compares** (counted 2026-11-28 by the method in the last column; libraries count
differently, so read the unit):

| library | version | indicators | how counted |
|---|---|---|---|
| **PandasTa (this fork)** | dev | **400+** | names in `Category` |
| pandas-ta-classic | 0.9.0 | 284 | indicator modules in the wheel (their README's own number): 65 candle modules counted one by one, and a 31-module math package (253 without it) |
| pandas-ta-openbb | 0.4.25 | 156 | names in `Category` |
| pandas-ta (PyPI) | 0.4.71b0 | 151 | names in `Category` |
| TA-Lib (Python wrapper) | 0.7.1 | 161 | `talib.get_functions()` |

The units favour the others: this fork counts all TA-Lib candle patterns as one name
(`cdl_pattern`). Even so it is larger than every other open-source technical-analysis library
we measured. Time-series feature libraries (tsfresh, hctsa) count parameterised features, a
different unit, so they are not compared here.

---

## Install

```sh
pip install -U "git+https://github.com/TolgaUyanik/PandasTa@dev"   # latest, what this page describes
pip install -U git+https://github.com/TolgaUyanik/PandasTa         # last release (main), fewer indicators
```

Requires `pandas`, `numpy`. Optional: `scipy`, `sklearn`, `statsmodels`, `talib`, `yfinance`, `mplfinance`, `tqdm`.

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
df.ta.bbands(length=20, append=True)          # writes the columns into df

# 3. Strategy — named group, multiprocessed, always appends
feat = ta.Strategy(name="ml_v1", ta=[
    {"kind": "natr"},
    {"kind": "stoch"},
    {"kind": "zscore", "length": 20},
])
df.ta.strategy(feat)
df.ta.strategy("overlap", length=42)          # a category, with a shared kwarg override

# Any indicator also works standalone, joined on your own terms:
df = df.join(ta.ichimoku_ml(df["high"], df["low"], df["close"]))
```

Discovery:

```python
df.ta.indicators()                 # print every indicator + utility
df.ta.indicators(as_list=True)     # same, as a list
df.ta.categories                   # category names
help(ta.bbands)                    # signature, params, output columns, sources
sum(map(len, ta.Category.values()))   # the exact count today
```

---

## Using it for machine learning

### 1. Causality is the contract

The value at bar `T` uses only data at `<= T`. One upstream column leaks at default parameters
([tracked in the leak watchlist](docs/IndicatorDictionary.md#leak-watchlist)), and one upstream
option leaks when you turn it on:

| Column | Problem | What to do |
|---|---|---|
| `ichimoku` → `ICS_26` | Chikou span is `close.shift(-kijun)`, the future | drop the column, or use `ichimoku_ml` |
| `dpo` → `DPO_20` | `centered=True` reads `length // 2 + 1` bars ahead; the default here is `False` (upstream's is `True`) | leave `centered` at its default |

Ported indicators state their causality in the module docstring (`help(ta.<name>)`).

### 2. Trees cannot read absolute price

An indicator returning a price level (`SMA_50 = 41.72`) is a dead feature: the model cannot
compare it to `close`, and the level moves with the ticker and the year. Feed relations.

```python
# bad: absolute level                    # good: scale-free relation
df.ta.sma(length=50, append=True)        (df["close"] - ta.sma(df["close"], 50)) / df["close"]
df.ta.atr(append=True)                   df.ta.natr(append=True)    # ATR normalised by price
```

`ichimoku_ml` is the worked example: the 5 Ichimoku price lines become 8 scale-free causal
features. Prefer a `*_ml` variant wherever one exists. Properties to prefer in a feature:
scale-free (a ratio, or percent of price), bounded or distribution-stable across tickers, and
stationary enough that a threshold learned in one period still means the same in the next.

### 3. Warm-up NaNs are real

Rolling indicators emit `NaN` for their first `length` (often more) bars. Drop the warm-up
**per ticker**, before concatenating tickers. Never `fillna(0)`: it invents signal at the start
of each series.

```python
feats = feats.iloc[max_lookback:]     # per ticker, then concat
```

### 4. Naming is stable, so parse it

Column names encode the parameters: `STOCHk_14_3_3`, `BBU_20_2.0`, `MACDh_12_26_9`. Pass
`col_names=(...)` to pin fixed names (it disables multiprocessing for that Strategy).

### 5. Signals are labels, not features

`tsignals` / `xsignals` turn a trend or a crossover into entry / exit columns (`asbool=True`
for boolean). Use them to build labels; feeding them back as features is how a target leaks in.

---

## Indicators

Every registered indicator, by category, with its output columns, ML form, warm-up and
parameters: **[docs/IndicatorDictionary.md](docs/IndicatorDictionary.md)**, generated from the
package (`python docs/gen_indicator_dictionary.py`). Per-indicator reference pages live under
[`docs/indicators/`](docs/indicators/).

Present but outside `Category`, so skipped by `df.ta.strategy()`: `beta`, `drawdown`,
`hwma`, `vp`, `ma` (moving-average selector — `help(ta.ma)`), the two lower-timeframe
functions `up_and_down_volume` / `volume_delta`, and the three TA-Lib ports
`ht_trendline`, `mama` and `sarext`. `beta`, `ht_trendline`, `hwma`, `mama`, `sarext`, `vp`,
`up_and_down_volume` and `volume_delta` are reachable as `df.ta.<name>()`; `drawdown` and
`ma` only as `ta.drawdown()` / `ta.ma()`. `beta` needs a benchmark series and the two volume
functions need a second, lower-timeframe frame, which a single-frame sweep cannot supply
(see `docs/LowerTimeframeData.md`). `ht_trendline`, `mama` and `sarext` return TA-Lib's raw
price levels; their distance forms restated existing columns, so a sweep would only add dead
price-level columns.

Utilities: `above` `above_value` `below` `below_value` `cross`. Performance metrics (return a
`float`, called standalone — `ta.cagr(df.close)`): `cagr` `calmar_ratio` `downside_deviation`
`jensens_alpha` `log_max_drawdown` `max_drawdown` `pure_profit_score` `sharpe_ratio`
`sortino_ratio` `volatility`.

## DataFrame extension reference

```python
df.ta.adjusted = "adj_close"   # use adj_close instead of close; None resets
df.ta.cores = 4                # strategy multiprocessing; 0 disables it
df.ta.datetime_ordered         # True if DatetimeIndex and ascending
df.ta.reverse                  # df in reverse order
df.ta.to_utc                   # index -> UTC
df.ta.hl2(prefix="pre", suffix="post")   # -> "pre_HL2_post"
df.ta.ticker("aapl", period="1y")        # yfinance download (optional dep)

df.ta.strategy()                            # everything (large)
df.ta.strategy("momentum")                  # one category
df.ta.strategy(exclude=["vp"], verbose=True, timed=True)
```

`vwap` requires a `DatetimeIndex`. Known breaks, if any, are listed in the dictionary's
generated [Known breaks](docs/IndicatorDictionary.md#known-breaks) section.

---

## How this repository is built

About nine in ten merged pull requests (190 of 215, measured 2026-11-28) were written by AI coding
agents (Claude Code), most of them from a GitHub issue queue. A human owner decides what gets
built and rules on judgement calls; `dev` requires no human approving review, so what merges
is gated by the automated checks below. The pipeline:

1. **issue-writer** (an agent skill) turns an idea, a formula or a script into a
   self-contained GitHub issue: source, formula, parameters, gates owed, a "done when" line.
   It checks for duplicates and lints the issue with the solver's own parser. The owner
   approves it and labels it `agent`.
2. **issue-solver** (a headless launcher) takes the oldest eligible issue and runs it with no
   human in the loop: an isolated worktree, a work session, then code checks (allowed paths,
   the full test suite in a clean worktree, a CPU-feature variant, and the redundancy
   measurement, run on the owner's machine).
3. **An independent reviewer gate.** A fresh agent with no memory of the work reviews the
   result against the issue and the repository's rules and returns PASS or REVISE with concrete
   fixes; up to three rounds, each REVISE answered by a fix session.
4. **CI and a merge queue.** The PR runs the full suite on GitHub Actions; a home-built merge
   queue (GitHub's native one is not available on this repository) updates and merges PRs into `dev`
   one at a time.
5. **The owner** takes over whatever the pipeline cannot settle: attended ports, licence
   questions, failed reviews, and anything that changes existing column values.

Measured on GitHub on 2026-11-28: 172 of 211 issues were labelled for the agent queue, and
170 automated review runs are kept in [`docs/reviews/`](docs/reviews/). Human contributors work
in the same issue queue; their PRs go through the same CI and are queued by the owner (see the
[contributors graph](https://github.com/TolgaUyanik/PandasTa/graphs/contributors)). The agent
skills live in a separate repository.

Agent authorship is not a warranty: no line here is warranted, and every indicator's evidence is
a set of measurements, not a claim of predictive value.

---

## Contributing an indicator

Follow [`docs/ImplementingAnIndicator.md`](docs/ImplementingAnIndicator.md). Scaffold the five
wiring files with `python docs/new_indicator.py <category> <name>`, which also writes the
causality, scale and reachability tests that must pass.

## Licence and credits

MIT ([LICENSE](LICENSE)), except the files listed in [NOTICE](NOTICE): modules translated from
TradingView Pine scripts that are MPL-2.0 (by the script's header or, where the script states
none, by the owner's stated assumption) stay MPL-2.0 file by file, and a few modules' source
licence is still being verified. See also the [disclaimer](DISCLAIMER.md).

Upstream: pandas-ta by Kevin Johnson (twopirllc) and its contributors
([PyPI](https://pypi.org/project/pandas-ta/)). Indicator authors are credited in each module's
docstring. Formula references: [TA-Lib](http://ta-lib.org/) ·
[TradingView](http://www.tradingview.com) · [catch22](https://github.com/DynamicsAndNeuralSystems/catch22) ·
[Sierra Chart](https://search.sierrachart.com/?Query=indicators&submitted=true) ·
[MQL5](https://www.mql5.com) · [FM Labs](https://www.fmlabs.com/reference/default.htm) ·
[ProRealCode](https://www.prorealcode.com/prorealtime-indicators).
