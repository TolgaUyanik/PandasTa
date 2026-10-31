# -*- coding: utf-8 -*-
"""The Gate E ledger (`docs/gate_e_ledger.csv`) is what CI checks instead of Gate E.

Gate E needs the private Backtesting engine and an 827 MB BIST frame cache, so it
cannot run in this public repo's CI. The owner runs it locally and records each
run with `python docs/gate_e_ledger.py record`. CI runs this file twice: as part
of the suite (`ci.yml`, job `tests`), and from the BASE branch's copy against
the PR's tree (`gate-e-guard.yml`, job `guard`), so a PR cannot loosen these
checks in the same change that needs them loosened. What CI checks is the
record, not the measurement: a hand-written row with invented numbers is caught
only in review.

What is pinned, in order of how much it would hurt to lose:

* EVERY indicator in `Category` has a ledger row, except those frozen in
  `docs/gate_e_grandfathered.json` (Category at 82eda5c, the commit before
  `pfe`: 233 indicators, 563 default columns) -- and a grandfathered indicator
  loses its exemption the moment its default columns grow. `pfe`,
  `kalman_trend` and `range_compress_run` were all merged with Gate E owed;
  this is the test that would have stopped them (reaching `main`; on the way
  to `dev` it reports them as owed, see below).
* Each row still describes its code: the LF-normalised sha1 of the module file,
  AND an output fingerprint of every column on a fixed synthetic frame, which
  catches an edit to a helper the module imports (`pfe` imports `ema`,
  `range_compress_run` imports `ml.companions`). `record` itself refuses a run
  unless the whole `pandas_ta` tree is the one the run imported.
* No STRUCK row ships without a waiver, and a waiver names the exact
  measurement it waives: issue, module sha1 and output fingerprint. The owner
  granted two on 2026-10-28, for columns already merged when the ledger
  arrived: `pfe` `PFE_10_5` (#23; 0.9285 vs `rsx`) and `kalman_trend`
  `KFT_VEL_0.01_0.0001` (#22; 0.9938 vs `MACD_pct`). Any edit that changes
  either column's code or output voids its waiver.
* The verdict column follows the `r3-perframe-0.90` bands from the recorded
  numbers, so a hand-edited verdict fails.
* The ledger's columns are exactly the indicator's output at its defaults,
  which is what `df.ta.strategy()` emits; a run taken with `--columns` would
  leave one out.
* Every new indicator has `tests/test_<name>.py` with a `mutant` test (Gate B)
  and a `scale` test (Gate D). That is a name check: it proves the tests exist,
  not that they are sound. Gate A is not checked here at all.
* Gate C on real data: every recorded column is non-zero on some of the
  89 frames' bars (`non_zero` is the harness's pooled count).

Each of these was broken on purpose on 2026-10-28 and failed; the breaks are
listed in PR #196.

Owed, not failed, on the way to `dev` (owner, 2026-11-01): contributors cannot run
Gate E, so ci.yml (PRs into `dev`, pushes to it, manual runs off `main`) and
gate-e-guard.yml (PRs into `dev`) set GATE_E_PENDING_OK=1. Then a
measurement that is OWED -- no row for an indicator that needs one, or a row whose
module, output or columns moved since its run -- is a skip whose reason starts
"Gate E owed", and the owner records it later. Toward `main` (a release PR, a push
to `main`) and on any local run the variable is not `1` and these fail as before, so
a release still needs every row. A deleted row counts as owed too (its indicator
then has no row). Strict everywhere: a waived STRUCK column (ALLOWED_WAIVERS)
whose code or output moved or whose row was deleted, a STRUCK row without its waiver, a hand-edited
verdict, missing Gate B/D tests. A manual CI run relaxes unless it is on `main`.
Until the owner records it, `dev` may carry an unmeasured column that Gate E would
strike; if its run is STRUCK, the column is reverted (or waived by the owner)
before the release, and the release PR into `main` fails until then.
"""
import hashlib
import importlib.util
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import NoReturn, Optional

import pytest

import pandas_ta as ta

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("gate_e_ledger", REPO / "docs" / "gate_e_ledger.py")
gl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gl)

ROWS = gl.read_ledger()
CATEGORY = {name for names in ta.Category.values() for name in names}
LIVE = [r for r in ROWS if r["indicator"] in CATEGORY]
GRANDFATHERED = gl.read_grandfathered()

# Owner, 2026-10-28: STRUCK columns already on dev when the ledger arrived.
# (indicator, column) -> (issue, module_sha1, output_fp) of the waived measurement.
ALLOWED_WAIVERS = {
    ("pfe", "PFE_10_5"): (
        "#23", "2c772d89b16e36f45bc76511c65d5a1c130b253c",
        "590;3129.530309979087;1263586.9013363486;622627.9758610134"),
    ("kalman_trend", "KFT_VEL_0.01_0.0001"): (
        "#22", "b5423402e034863abdf482211bce39bef1927f9d",
        "387;12.73088580326977;19.772012464238024;1974.6266060299877"),
}
GRANDFATHERED_COUNT = 233
GRANDFATHERED_COLUMNS = 563
GRANDFATHERED_SHA1 = "1b16434916bc4fb85889e2b72bc0960afcedb3dc"
PENDING_OK = os.environ.get("GATE_E_PENDING_OK") == "1"


def _owed(message: str, row: Optional[dict] = None) -> NoReturn:
    """A measurement is owed: a skip under GATE_E_PENDING_OK=1 (see the docstring), else a failure.
    Never a skip for a waived STRUCK column: its waiver covers one exact measurement."""
    if PENDING_OK and not (row and (row["indicator"], row["column"]) in ALLOWED_WAIVERS):
        pytest.skip(f"Gate E owed (the owner records it later): {message}")
    pytest.fail(message)


def _row_id(row):
    return f"{row['indicator']}:{row['column']}"


@lru_cache(maxsize=None)
def _output(indicator: str):
    return gl.default_output(indicator)


def _columns(indicator: str) -> set:
    return set(map(str, _output(indicator).columns))


def _needs_a_row() -> set:
    """New indicators, plus grandfathered ones whose default columns grew."""
    new = CATEGORY - set(GRANDFATHERED)
    grew = {g for g in CATEGORY & set(GRANDFATHERED) if not _columns(g) <= set(GRANDFATHERED[g])}
    return new | grew


def test_grandfathered_list_is_frozen():
    canonical = json.dumps(GRANDFATHERED, sort_keys=True, separators=(",", ":"))
    assert len(GRANDFATHERED) == GRANDFATHERED_COUNT
    assert sum(map(len, GRANDFATHERED.values())) == GRANDFATHERED_COLUMNS
    assert hashlib.sha1(canonical.encode()).hexdigest() == GRANDFATHERED_SHA1


def test_every_indicator_that_needs_a_row_has_one():
    missing = _needs_a_row() - {r["indicator"] for r in ROWS}
    if missing:
        _owed(f"no Gate E ledger row for {sorted(missing)} (new to Category, or a grandfathered "
              "indicator whose default columns grew). Run Gate E (CLAUDE.md, 'Gate E harness'), "
              "then `python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD`")


def test_every_waived_column_keeps_its_row():
    """Strict in both modes: deleting a waived row would otherwise turn its edit into "owed"."""
    have = {(r["indicator"], r["column"]) for r in ROWS}
    gone = sorted(k for k in ALLOWED_WAIVERS if k not in have)
    assert not gone, f"waived STRUCK rows {gone} were removed from the ledger; restore them or ask the owner"


@pytest.mark.parametrize("indicator", sorted(CATEGORY - set(GRANDFATHERED)))
def test_every_new_indicator_has_gate_b_and_d_tests(indicator):
    path = REPO / "tests" / f"test_{indicator}.py"
    assert path.is_file(), f"{indicator} has no {path.relative_to(REPO)} (touch point 5)"
    names = re.findall(r"^def (test_\w+)", path.read_text(encoding="utf-8"), flags=re.M)
    assert any("mutant" in n for n in names), f"{path.name}: no Gate B mutant test"
    assert any("scale" in n for n in names), f"{path.name}: no Gate D scale test"


def test_ledger_header_and_schema():
    assert ROWS, "the ledger is empty"
    assert {r["verdict_schema"] for r in ROWS} == {gl.SCHEMA}
    assert {r["n_frames"] for r in ROWS} == {str(gl.N_FRAMES)}
    assert {r["n_comparators"] for r in ROWS} == {str(gl.N_COMPARATORS)}
    assert len({_row_id(r) for r in ROWS}) == len(ROWS), "duplicate indicator:column rows"


@pytest.mark.parametrize("row", LIVE, ids=_row_id)
def test_row_names_the_module_that_defines_the_indicator(row):
    assert row["module"] == getattr(ta, row["indicator"]).__module__


@pytest.mark.parametrize("row", LIVE, ids=_row_id)
def test_row_still_describes_its_module(row):
    path = gl.module_path(row["module"])
    if gl.lf_sha1(path) != row["module_sha1"]:
        _owed(f"{path.relative_to(REPO)} changed after Gate E run {row['run']}; re-run Gate E and re-record it", row)


@pytest.mark.parametrize("row", LIVE, ids=_row_id)
def test_row_output_has_not_moved(row):
    out = _output(row["indicator"])
    if row["column"] not in out.columns:
        _owed(f"{_row_id(row)} is no longer in the default output; re-run Gate E and re-record it", row)
    now = gl.fingerprint(out[row["column"]])
    if not gl.fingerprints_match(now, row["output_fp"]):
        _owed(f"{_row_id(row)} output moved since Gate E run {row['run']} ({row['output_fp']} -> {now}); "
              "a helper it imports may have changed. Re-run Gate E and re-record it", row)


@pytest.mark.parametrize("row", ROWS, ids=_row_id)
def test_verdict_follows_the_bands(row):
    expected = gl.expected_verdict(gl.to_float(row["max_abs_rho"]),
                                   gl.to_float(row["perframe_max_median_abs_rho"]))
    assert row["verdict"] == expected


@pytest.mark.parametrize("row", LIVE, ids=_row_id)
def test_struck_rows_carry_the_waiver_for_this_exact_measurement(row):
    key = (row["indicator"], row["column"])
    if row["verdict"] == "STRUCK":
        assert key in ALLOWED_WAIVERS, f"{_row_id(row)} is STRUCK: revert it, or ask the owner"
        issue, sha1, fp = ALLOWED_WAIVERS[key]
        assert (row["waiver"], row["module_sha1"], row["output_fp"]) == (issue, sha1, fp), (
            f"{_row_id(row)}'s waiver {issue} covers a different measurement; this one is not waived")
    else:
        assert row["waiver"] == "", f"{_row_id(row)} is {row['verdict']} but carries a waiver"


@pytest.mark.parametrize("indicator", sorted({r["indicator"] for r in LIVE}))
def test_ledger_columns_are_the_default_output(indicator):
    recorded = {r["column"] for r in LIVE if r["indicator"] == indicator}
    if recorded != _columns(indicator):
        _owed(f"{indicator}'s ledger columns {sorted(recorded)} are not its default output "
              f"{sorted(_columns(indicator))}; re-run Gate E and re-record it")


@pytest.mark.parametrize("row", ROWS, ids=_row_id)
def test_every_column_fires_on_real_data(row):
    assert 0 < int(row["non_zero"]) <= int(row["non_nan"]) <= int(row["pooled_bars"])


def test_fingerprint_tolerates_ulps_but_not_a_change():
    s = _output("range_compress_run")["RCR_100"].astype(float)
    fp = gl.fingerprint(s)
    assert gl.fingerprints_match(gl.fingerprint(s * (1 + 4e-16)), fp)
    assert not gl.fingerprints_match(gl.fingerprint(s * (1 + 1e-6)), fp)
    moved = s.copy()
    moved.iloc[-1] += 1
    assert not gl.fingerprints_match(gl.fingerprint(moved), fp)


# ------------------------------------------------------------------ record()

def _fake_run(tmp_path, meta_overrides, n_comparators=None):
    """A one-column harness run for `range_compress_run`, matching this tree."""
    path = gl.module_path("pandas_ta.volatility.range_compress_run")
    meta = {"mode": "run", "module": "pandas_ta.volatility.range_compress_run",
            "fn": "range_compress_run", "kwargs": {}, "end": None, "excluded": [],
            "rename_prefix": None, "n_frames": gl.N_FRAMES, "pooled_bars": 1000,
            "canary": "AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS bit-equal",
            "candidate_source_sha1": gl.lf_sha1(path),
            "pandas_ta_src_sha1": sorted(gl.src_tree_sha1s())[0],
            "stamp": {"data": "d" * 40}}
    meta.update(meta_overrides)
    run = tmp_path / "run"
    run.mkdir()
    (run / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    header = ",".join(gl.COPIED)
    n_cmp = gl.N_COMPARATORS if n_comparators is None else n_comparators
    (run / "overlap_max.csv").write_text(
        f"{header}\nRCR_100,SHIP,0.5,x,manifest,900,0.5,x,900,450,{n_cmp},{gl.SCHEMA}\n",
        encoding="utf-8")
    return run


def test_record_accepts_a_matching_default_run(tmp_path):
    rows = gl.rows_from_run(_fake_run(tmp_path, {}), "2026-10-28")
    assert [r["column"] for r in rows] == ["RCR_100"]
    assert gl.fingerprints_match(rows[0]["output_fp"], gl.fingerprint(_output("range_compress_run")["RCR_100"]))


@pytest.mark.parametrize("override", [
    {"candidate_source_sha1": "0" * 40},
    {"pandas_ta_src_sha1": "0" * 40},
    {"kwargs": {"cap": 50}},
    {"end": "2026-08-27"},
    {"excluded": ["Range_ATR_Pctl"]},
    {"mode": "replay"},
    {"n_frames": 88},
    {"canary": "AKBNK.IS mismatch"},
], ids=lambda o: next(iter(o)))
def test_record_refuses_a_run_that_is_not_this_tree_at_its_defaults(tmp_path, override):
    with pytest.raises(ValueError):
        gl.rows_from_run(_fake_run(tmp_path, override), "2026-10-28")


def test_record_refuses_another_comparator_set(tmp_path):
    with pytest.raises(ValueError):
        gl.rows_from_run(_fake_run(tmp_path, {}, n_comparators=686), "2026-10-28")


def test_record_refuses_a_waiver_on_a_run_with_nothing_struck(tmp_path):
    with pytest.raises(ValueError):
        gl.rows_from_run(_fake_run(tmp_path, {}), "2026-10-28", waiver="#190")


def test_a_nan_per_frame_median_is_read_not_raised():
    assert gl.expected_verdict(gl.to_float("0.5"), gl.to_float("")) == "SHIP"
    assert gl.expected_verdict(gl.to_float("0.95"), gl.to_float("")) == "STRUCK"


def test_owed_fails_unless_pending_ok(monkeypatch):
    """The switch itself: owed is a failure without GATE_E_PENDING_OK=1, a skip with it, and a
    failure for a waived STRUCK column either way."""
    plain = {"indicator": "x", "column": "X_1"}
    waived = {"indicator": "pfe", "column": "PFE_10_5"}
    monkeypatch.setitem(globals(), "PENDING_OK", False)
    with pytest.raises(pytest.fail.Exception):
        _owed("owed", plain)
    monkeypatch.setitem(globals(), "PENDING_OK", True)
    with pytest.raises(pytest.skip.Exception):
        _owed("owed", plain)
    with pytest.raises(pytest.fail.Exception):
        _owed("owed", waived)
