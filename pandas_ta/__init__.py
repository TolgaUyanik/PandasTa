name = "pandas_ta"
"""
.. moduleauthor:: Kevin Johnson
"""
from importlib.util import find_spec
from pkg_resources import get_distribution, DistributionNotFound
import os.path


_dist = get_distribution("pandas_ta")
try:
    # Normalize case for Windows systems
    dist_loc = os.path.normcase(_dist.location)
    here = os.path.normcase(__file__)
    if not here.startswith(os.path.join(dist_loc, "pandas_ta")):
        # not installed, but there is another version that *is*
        raise DistributionNotFound
except DistributionNotFound:
    __version__ = "Please install this project with setup.py"

version = __version__ = _dist.version


Imports = {
    "alphaVantage-api": find_spec("alphaVantageAPI") is not None,
    "matplotlib": find_spec("matplotlib") is not None,
    "mplfinance": find_spec("mplfinance") is not None,
    "scipy": find_spec("scipy") is not None,
    "sklearn": find_spec("sklearn") is not None,
    "statsmodels": find_spec("statsmodels") is not None,
    "stochastic": find_spec("stochastic") is not None,
    "talib": find_spec("talib") is not None,
    "tqdm": find_spec("tqdm") is not None,
    "vectorbt": find_spec("vectorbt") is not None,
    "yfinance": find_spec("yfinance") is not None,
}

# Not ideal and not dynamic but it works.
# Will find a dynamic solution later.
Category = {
    # Candles
    "candles": [
        "cdl_doji", "cdl_inside", "cdl_pattern", "cdl_z", "ha"
    ],
    # Cycles
    "cycles": ["dsp", "ebsw"],
    # Momentum
    "momentum": [
        "ao", "apo", "bias", "bop", "brar", "cci", "cdvo", "cfo", "cg", "cmo",
        "coppock", "cti", "dm", "er", "eri", "fisher", "inertia", "kalman_rsi", "kdj", "kst", "lrsi", "macd",
        "mom", "pgo", "po", "ppo", "psl", "pvo", "qqe", "roc", "rsi", "rsx", "rvgi",
        "slope", "smi", "squeeze", "squeeze_pro", "stc", "stoch", "stochrsi", "td_seq", "trix",
        "trixh", "tsi", "uo", "vwmacd", "wavetrend", "willr"
    ],
    # Overlap
    "overlap": [
        "alma", "dema", "ema", "ema_align", "fwma", "hilo", "hl2", "hlc3", "hma", "ichimoku", "ichimoku_ml",
        "jma", "kama", "linreg", "linreg_channel", "ma_disparity", "mcgd", "midpoint", "midprice", "mmar",
        "ohlc4", "pwma", "rainbow", "rma", "sinwma", "sma", "ssf", "supertrend", "swma",
        "t3", "tema", "trima", "vidya", "vwap", "vwma", "wcp", "wma", "zlma"
    ],
    # Performance
    "performance": ["log_return", "percent_return", "trend_return"],
    # Statistics
    "statistics": [
        "entropy", "kurtosis", "mad", "median", "quantile", "skew", "stdev",
        "variance", "zscore"
    ],
    # Trend
    "trend": [
        "adx", "amat", "aroon", "bos", "choch", "chop", "cksp", "decay", "decreasing",
        "dpo", "fvg", "halftrend", "increasing", "long_run", "nwog", "ob", "pmax", "priorday_fib",
        "priormonth_range", "psar", "qstick", "short_run", "swing_equilibrium", "tsignals", "ttm_trend",
        "vhf", "vortex", "xsignals", "zigzag", "zigzag_fib"
    ],
    # Volatility
    "volatility": [
        "aberration", "accbands", "atr", "atr_ma_multiple", "bbands", "donchian", "hwc", "kc", "massi",
        "natr", "pdist", "rvi", "thermo", "true_range", "ui"
    ],

    # Volume, "vp" or "Volume Profile" is unique
    "volume": [
        "ad", "adosc", "aobv", "cmf", "efi", "eom", "kvo", "mfi", "nvi", "obv", "pocket_pivot", "pvi",
        "pvol", "pvr", "pvt", "vfi", "vol_delta", "weis_wave"
    ],
}

CANGLE_AGG = {
    "open": "first",
    "high": "max",
    "low": "min",
    "close": "last",
    "volume": "sum"
}

# https://www.worldtimezone.com/markets24.php
EXCHANGE_TZ = {
    "NZSX": 12, "ASX": 11,
    "TSE": 9, "HKE": 8, "SSE": 8, "SGX": 8,
    "NSE": 5.5, "DIFX": 4, "RTS": 3,
    "JSE": 2, "FWB": 1, "LSE": 1,
    "BMF": -2, "NYSE": -4, "TSX": -4
}

RATE = {
    "DAYS_PER_MONTH": 21,
    "MINUTES_PER_HOUR": 60,
    "MONTHS_PER_YEAR": 12,
    "QUARTERS_PER_YEAR": 4,
    "TRADING_DAYS_PER_YEAR": 252,  # Keep even
    "TRADING_HOURS_PER_DAY": 6.5,
    "WEEKS_PER_YEAR": 52,
    "YEARLY": 1,
}

from pandas_ta.core import *
