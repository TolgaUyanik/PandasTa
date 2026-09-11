# -*- coding: utf-8 -*-
"""Packaging for the AwakenAnalytics fork of pandas-ta.

⚠ **The version is load-bearing, and it was wrong until 2026-09-07.** This file
still declared upstream's `0.2.67b` with upstream's author and URL, so the sole
consumer -- `Backtesting/`, which installs with
`pip install -U git+https://github.com/TolgaUyanik/PandasTa` -- resolved it as
`pandas_ta==0.2.67b0`, found that already satisfied, and **skipped the install**.
A whole session of fixes (11 missing accessors, the `mcgd` pandas-2 break, three
module-shadowing imports, the `squeeze`/`squeeze_pro` offset crash, the `fvg`
zone repair) would never have reached the engine.

**Bump `__version__` on every merge**, or the same thing happens silently again.
The local suffix (`+tu.N`) marks this as the fork build: PEP 440 orders
`0.2.67b1+tu.1 > 0.2.67b0`, so `pip install -U` upgrades an existing upstream
install rather than shrugging at it.
"""
from setuptools import setup

__version__ = "0.2.67b1+tu.1"

long_description = (
    "AwakenAnalytics fork of pandas-ta: a Python 3 Pandas extension with ~200 "
    "technical analysis indicators, oriented toward machine-learning feature "
    "generation. Adds TradingView/Pine and SMC price-action ports on top of "
    "upstream, plus a generated indicator dictionary recording every column's "
    "ML form (scale-free / price-level / binary), warm-up and causality. "
    "Callable from a Pandas DataFrame or standalone like TA-Lib."
)

setup(
    name="pandas_ta",
    packages=[
        "pandas_ta",
        "pandas_ta.candles",
        "pandas_ta.cycles",
        "pandas_ta.momentum",
        "pandas_ta.overlap",
        "pandas_ta.performance",
        "pandas_ta.statistics",
        "pandas_ta.trend",
        "pandas_ta.utils",
        "pandas_ta.volatility",
        "pandas_ta.volume"
    ],
    version=__version__,
    description=long_description,
    long_description=long_description,
    author="Tolga Uyanik",
    maintainer="Tolga Uyanik",
    url="https://github.com/TolgaUyanik/PandasTa",
    download_url="https://github.com/TolgaUyanik/PandasTa.git",
    keywords=["technical analysis", "trading", "python3", "pandas",
              "machine learning", "feature engineering"],
    license="The MIT License (MIT)",
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: Science/Research",
        "Topic :: Office/Business :: Financial",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    # NOTE: no `package_data`. The old entry declared `{"data": ["data/*.csv"]}`
    # for a `data` package that does not exist in this tree.
    install_requires=["pandas", "numpy"],
    extras_require={
        "dev": [
            "alphaVantage-api", "matplotlib", "mplfinance", "scipy",
            "scikit-learn", "statsmodels", "stochastic",
            "talib", "tqdm", "vectorbt", "yfinance",
        ],
        # CANDLE-2: `talib` gets its own extra as well as sitting in `dev`.
        # It is the ONLY optional dependency that changes what the package
        # COMPUTES rather than what it can plot or test: without it
        # `cdl_pattern` reaches 2 native patterns, with it 62. Burying that
        # beside matplotlib and vectorbt made it read as a dev convenience.
        # `pip install pandas-ta[talib]` is now the documented way to get them.
        "talib": ["talib"],
        "test": ["pytest"],
    },
)
