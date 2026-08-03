import os
from pathlib import Path

import pytest
from pandas import DatetimeIndex, read_csv

VERBOSE = True

ALERT = f"[!]"
INFO = f"[i]"

CORRELATION = "corr"  # "sem"
CORRELATION_THRESHOLD = 0.99  # Less than 0.99 is undesirable

# Resolve the fixture relative to the repo root, not the cwd: the old
# bare "data/SPY_D.csv" only worked when pytest ran from the repo root.
SAMPLE_DATA_CSV = Path(__file__).resolve().parents[1] / "data" / "SPY_D.csv"

if not SAMPLE_DATA_CSV.is_file():
    # The fixture is not in the repo. Skip the suites that need it instead of
    # raising FileNotFoundError at import time, which aborted collection for
    # every test module in this directory.
    pytest.skip(
        f"sample data fixture missing: {SAMPLE_DATA_CSV}",
        allow_module_level=True,
    )

sample_data = read_csv(
    SAMPLE_DATA_CSV,
    index_col=0,
    parse_dates=True,
    infer_datetime_format=True,
    keep_date_col=True,
)
sample_data.set_index(DatetimeIndex(sample_data["date"]), inplace=True, drop=True)
sample_data.drop("date", axis=1, inplace=True)


def error_analysis(df, kind, msg, icon=INFO, newline=True):
    if VERBOSE:
        s = f"{icon} {df.name}['{kind}']: {msg}"
        if newline:
            s = f"\n{s}"
        print(s)
