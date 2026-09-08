# Lower-timeframe data: what the current source can actually feed

Companion note for **PINEBI-1d** — `up_and_down_volume` and `volume_delta`.
Both split a bar's volume into buying and selling pressure using INTRABAR data,
so both are only as good as the sub-bar history available. This note states
what exists, measured, so nobody has to discover it by getting an empty column.

## The short answer

**There is no sub-hourly data in this project today.** Not stale, not thin —
none. Measured 2026-09-08 against `../Backtesting/datastore/cache/`:

| interval | cached files |
|---|---|
| `_1d` | 578 |
| `_1h` | 362 |
| `_5m` / `_15m` / `_30m` | **0** |

```sh
ls Backtesting/datastore/cache/ | grep -oE '_(1h|1d|5m|15m|30m)' | sort | uniq -c
ls Backtesting/datastore/cache/*_5m.parquet 2>/dev/null | wc -l   # 0
```

So on today's cache the only usable pairing is **1h intrabar under a daily main
bar** — roughly 7–8 intrabars per BIST session. That is enough for a coarse
delta and far too few for the intrabar precision the Pine functions assume.

## What the 1h cache covers

Sampled 40 of the 362 `_1h` files (2026-09-08):

| | |
|---|---|
| median bars per ticker | 6,249 |
| earliest bar | 2023-08-31 06:30 UTC |
| latest bar | 2026-07-21 14:30 UTC |

Just under three years. Note the latest bar is **2026-07-21**, so the hourly
cache is itself ~7 weeks stale as of this writing — refresh before trusting any
recent window.

## Why there is no 5m data, and what it would cost

`yfinance` serves sub-hourly intervals for a **rolling ~60-day window only**.
That is an upstream limit, not a caching choice, and it has three consequences:

1. **No backtest depth.** A 60-day window on daily main bars is ~42 usable
   observations per ticker. Nothing in this repo's gate structure — Gate C
   reachability counts, Gate E overlap against ~200 columns — produces a
   meaningful number on 42 rows.
2. **It cannot be back-filled.** The history is not retrievable later, so the
   only way to build depth is to start capturing now and wait. A 5m capture
   started today yields a 2-year usable panel in 2028.
3. **It expires.** Any 5m panel must be appended to continuously or it decays
   back to 60 days.

## What this means for the two functions

Neither function fetches anything. Both take the lower-timeframe frame as an
argument and raise a named error when it is absent — deliberately, because the
caller is the only party that knows what history exists:

```python
lower = pd.read_parquet("…/GARAN_IS_1h.parquet")     # the caller's problem
ta.up_and_down_volume(lower, anchor="1D")            # daily main bars
ta.volume_delta(lower, anchor="1D", cumulative_period="1W")
```

`anchor` is required too, and is never guessed — a string offset alias floors a
`DatetimeIndex`, or a Series aligned to the lower frame names each row's main
bar.

⚠ **They are not exercised on real intraday data anywhere in the test suite**,
because none exists to exercise them on. `tests/test_pinebi_1d_lower_timeframe.py`
runs entirely on a synthetic 1h-from-5m fixture (12 five-minute bars per hour,
48 hours). The Pine semantics are pinned there — the `var bool isBuyVolume`
carry, the `VD_HIGH >= VD_OPEN >= VD_LOW` construction, the
`UDV_POS - UDV_NEG == total volume` identity — but the behaviour on real,
gappy, tick-rounded BIST intrabars is **unmeasured**.

⚠ For the same reason they are **not probed** by
`docs/gen_indicator_dictionary.py`: its harness builds a single daily OHLCV
frame and cannot synthesise a lower-timeframe one. The dictionary's *Known
breaks* section names them as unprobed rather than silently counting them
either way.

## If someone wants these to be useful

In rough order of cost:

1. **Use 1h under daily now.** Free, works today, coarse. Start here to find
   out whether the delta carries anything at all before paying for the rest.
2. **Start a 5m capture.** A cron appending `interval="5m"` for the BIST_100
   into a rolling parquet store. Cheap to run, but the panel only becomes
   backtest-grade after a year or more of accumulation.
3. **Buy intraday history.** The only route to a deep panel this decade.

Whichever path, the finding to record first is (1)'s: whether up/down volume
split at 1h-under-daily has any measurable edge. If it does not, (2) and (3)
are not worth starting.
