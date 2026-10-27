# -*- coding: utf-8 -*-
"""The Gate E ledger (`docs/gate_e_ledger.csv`) is what CI checks instead of Gate E.

Gate E needs the private Backtesting engine and an 827 MB BIST frame cache, so
it cannot run in this public repo's CI. The owner runs it locally and records
each run with `python docs/gate_e_ledger.py record <run dir>`. These tests make
a merge impossible while that record is missing, stale or failing.

What is pinned, in order of how much it would hurt to lose:

* EVERY indicator in `Category` has a ledger row, except the 233 frozen in
  `docs/gate_e_grandfathered.txt` (Category at 82eda5c, the commit before
  `pfe`). `pfe`, `kalman_trend` and `range_compress_run` were all merged with
  Gate E owed; this is the test that would have stopped them.
* Each row still describes its module: the LF-normalised sha1 of the module
  file equals the one recorded. An edit after the run fails until Gate E is
  re-run and re-recorded. `record` itself refuses a run whose
  `candidate_source_sha1` is not this tree's file.
* No STRUCK row ships without a waiver, and the waivers are exactly the two
  the owner granted on 2026-10-28 for columns already merged when the ledger
  arrived: `pfe` `PFE_10_5` (#23; 0.9285 vs `rsx`) and `kalman_trend`
  `KFT_VEL_0.01_0.0001` (#22; 0.9938 vs `MACD_pct`). A new STRUCK column
  cannot pass without editing `ALLOWED_WAIVERS` here, in review's sight.
* The verdict column follows the `r3-perframe-0.90` bands from the recorded
  numbers, so a hand-edited verdict fails.
* The ledger's columns are exactly the indicator's output at its defaults,
  which is what `df.ta.strategy()` emits; a run taken with `--columns` would
  leave one out.
* Gate C on real data: every recorded column is non-zero on some of the
  89 frames' bars (`non_zero` is the harness's pooled count).
"""
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import pandas_ta as ta

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("gate_e_ledger", REPO / "docs" / "gate_e_ledger.py")
gl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gl)

ROWS = gl.read_ledger()
CATEGORY = {name for names in ta.Category.values() for name in names}
LIVE = [r for r in ROWS if r["indicator"] in CATEGORY]

# Owner, 2026-10-28: STRUCK columns already on dev when the ledger arrived. Shrink only.
ALLOWED_WAIVERS = {
    ("pfe", "PFE_10_5"): "#23",
    ("kalman_trend", "KFT_VEL_0.01_0.0001"): "#22",
}
GRANDFATHERED_COUNT = 233
GRANDFATHERED_SHA1 = "519a6efdfcbef670cb12c21c90cb5ad667e438fd"


def _row_id(row):
    return f"{row['indicator']}:{row['column']}"


def _ohlcv(n: int = 600, seed: int = 11) -> pd.DataFrame:
    """Tick-rounded GBM bars, long enough for every recorded indicator's warm-up."""
    rng = np.random.default_rng(seed)
    close = np.round(100 * np.exp(np.cumsum(rng.normal(0, 0.02, n))), 2)
    spread = np.round(np.abs(rng.normal(0, 0.01, n)) * close, 2)
    return pd.DataFrame({
        "open": np.round(close * (1 + rng.normal(0, 0.005, n)), 2),
        "high": close + spread, "low": close - spread, "close": close,
        "volume": rng.integers(1_000, 100_000, n).astype(float),
    })


def _default_columns(indicator: str) -> set:
    """The columns `indicator` returns at its defaults, fed the OHLCV its signature names."""
    fn = getattr(ta, indicator)
    df = _ohlcv()
    series = {"open_": df["open"], "high": df["high"], "low": df["low"],
              "close": df["close"], "volume": df["volume"]}
    args = [series[p] for p in inspect.signature(fn).parameters if p in series]
    out = fn(*args)
    return {out.name} if isinstance(out, pd.Series) else set(out.columns)


def test_grandfathered_list_is_frozen():
    names = gl.read_grandfathered()
    assert len(names) == GRANDFATHERED_COUNT
    assert names == sorted(set(names))
    assert hashlib.sha1("\n".join(names).encode()).hexdigest() == GRANDFATHERED_SHA1


def test_every_new_category_indicator_has_a_ledger_row():
    missing = CATEGORY - set(gl.read_grandfathered()) - {r["indicator"] for r in ROWS}
    assert not missing, (
        f"in Category with no Gate E ledger row: {sorted(missing)}. Run Gate E "
        "(CLAUDE.md, 'Gate E harness'), then `python docs/gate_e_ledger.py record <run dir>`")


def test_ledger_header_and_schema():
    assert ROWS, "the ledger is empty"
    assert {r["verdict_schema"] for r in ROWS} == {gl.SCHEMA}
    assert len({_row_id(r) for r in ROWS}) == len(ROWS), "duplicate indicator:column rows"


@pytest.mark.parametrize("row", LIVE, ids=_row_id)
def test_row_still_describes_its_module(row):
    path = gl.module_path(row["module"])
    assert gl.lf_sha1(path) == row["module_sha1"], (
        f"{path.relative_to(REPO)} changed after Gate E run {row['run']}; "
        "re-run Gate E and re-record it")


@pytest.mark.parametrize("row", ROWS, ids=_row_id)
def test_verdict_follows_the_bands(row):
    expected = gl.expected_verdict(float(row["max_abs_rho"]),
                                   float(row["perframe_max_median_abs_rho"]))
    assert row["verdict"] == expected


@pytest.mark.parametrize("row", LIVE, ids=_row_id)
def test_struck_rows_carry_an_allowed_waiver(row):
    key = (row["indicator"], row["column"])
    if row["verdict"] == "STRUCK":
        assert key in ALLOWED_WAIVERS, f"{_row_id(row)} is STRUCK: revert it, or ask the owner"
        assert row["waiver"] == ALLOWED_WAIVERS[key]
    else:
        assert row["waiver"] == "", f"{_row_id(row)} is {row['verdict']} but carries a waiver"


@pytest.mark.parametrize("indicator", sorted({r["indicator"] for r in LIVE}))
def test_ledger_columns_are_the_default_output(indicator):
    recorded = {r["column"] for r in LIVE if r["indicator"] == indicator}
    assert recorded == _default_columns(indicator)


@pytest.mark.parametrize("row", ROWS, ids=_row_id)
def test_every_column_fires_on_real_data(row):
    assert 0 < int(row["non_zero"]) <= int(row["non_nan"]) <= int(row["pooled_bars"])


def _fake_run(tmp_path, meta_overrides):
    """A one-column harness run for `range_compress_run`, matching this tree's file."""
    path = gl.module_path("pandas_ta.volatility.range_compress_run")
    meta = {"mode": "run", "module": "pandas_ta.volatility.range_compress_run",
            "fn": "range_compress_run", "kwargs": {}, "end": None, "excluded": [],
            "rename_prefix": None, "n_frames": 89, "pooled_bars": 1000,
            "candidate_source_sha1": gl.lf_sha1(path)}
    meta.update(meta_overrides)
    run = tmp_path / "run"
    run.mkdir()
    (run / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    header = ",".join(gl.COPIED)
    (run / "overlap_max.csv").write_text(
        f"{header}\nRCR_100,SHIP,0.5,x,manifest,900,0.5,x,900,450,687,{gl.SCHEMA}\n",
        encoding="utf-8")
    return run


def test_record_accepts_a_matching_default_run(tmp_path):
    rows = gl.rows_from_run(_fake_run(tmp_path, {}))
    assert [r["column"] for r in rows] == ["RCR_100"]


@pytest.mark.parametrize("override", [
    {"candidate_source_sha1": "0" * 40},
    {"kwargs": {"cap": 50}},
    {"end": "2026-08-27"},
    {"excluded": ["Range_ATR_Pctl"]},
    {"mode": "replay"},
], ids=lambda o: next(iter(o)))
def test_record_refuses_a_run_that_is_not_this_file_at_its_defaults(tmp_path, override):
    with pytest.raises(ValueError):
        gl.rows_from_run(_fake_run(tmp_path, override))
