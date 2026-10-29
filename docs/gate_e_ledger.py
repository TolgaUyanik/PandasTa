# -*- coding: utf-8 -*-
"""Gate E ledger: the committed record of every Gate E verdict CI relies on.

Gate E needs the private Backtesting engine and the BIST frame cache, so it
cannot run in this public repo's CI. The owner runs it locally
(`gate_e_overlap.py run`, see CLAUDE.md) and records the result here:

    python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD [--waiver "#23"]

`<run dir>` is the harness output folder (`meta.json` + `overlap_max.csv`).
`record` refuses a run unless the whole `pandas_ta` tree here is the tree the
run imported, the run was taken at the defaults `df.ta.strategy()` sweeps, and
it used the frozen 89-frame / 687-comparator set with a bit-equal canary.
Each row also stores an output fingerprint on a fixed synthetic frame, so a
later edit to a helper module the indicator imports is caught.
`tests/test_gate_e_ledger.py` is the check CI runs against this file.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:  # `python docs/gate_e_ledger.py` must import THIS tree's pandas_ta
    sys.path.insert(0, str(REPO))
import pandas_ta  # noqa: E402  (registers the df.ta accessor)

LEDGER = REPO / "docs" / "gate_e_ledger.csv"
GRANDFATHERED = REPO / "docs" / "gate_e_grandfathered.json"
SCHEMA = "r3-perframe-0.90"
N_FRAMES = 89          # ALTPORT-1's frozen BIST daily universe (owner, 2026-10-23)
N_COMPARATORS = 687    # compute_all 329 + ml_features manifest 1d 358

FIELDS = [
    "indicator", "module", "column", "verdict", "max_abs_rho", "against",
    "against_set", "n", "perframe_max_median_abs_rho", "perframe_max_against",
    "non_nan", "non_zero", "n_frames", "pooled_bars", "n_comparators",
    "verdict_schema", "module_sha1", "output_fp", "pandas_ta_src_sha1",
    "stamp_data", "run", "measured", "waiver",
]
# Copied verbatim from the harness's overlap_max.csv, so the ledger keeps its full precision.
COPIED = [
    "column", "verdict", "max_abs_rho", "against", "against_set", "n",
    "perframe_max_median_abs_rho", "perframe_max_against", "non_nan",
    "non_zero", "n_comparators", "verdict_schema",
]


def module_path(module: str) -> Path:
    """`pandas_ta.overlap.kalman_trend` -> <repo>/pandas_ta/overlap/kalman_trend.py"""
    return REPO.joinpath(*module.split(".")).with_suffix(".py")


def lf_sha1(path: Path) -> str:
    """sha1 of the file with CRLF folded to LF, so Windows and Linux checkouts agree."""
    return hashlib.sha1(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _line_ending_variants(data: bytes) -> set:
    """The raw bytes plus their all-LF and all-CRLF forms."""
    lf = data.replace(b"\r\n", b"\n")
    return {data, lf, lf.replace(b"\n", b"\r\n")}


def _matches_run(path: Path, run_sha1: str) -> bool:
    """True if the file, raw or in its LF or CRLF form, is the one the harness hashed."""
    return run_sha1 in {hashlib.sha1(v).hexdigest() for v in _line_ending_variants(path.read_bytes())}


def src_tree_sha1s() -> set:
    """`gate_e_overlap.pandas_ta_src_sha1` of this tree, raw and line-ending-normalised.

    Same recipe as the harness: every `*.py` under the package, sorted, name then bytes.
    """
    paths = sorted((REPO / "pandas_ta").rglob("*.py"))
    out = set()
    for mode in ("raw", "lf", "crlf"):
        h = hashlib.sha1()
        for p in paths:
            data = p.read_bytes()
            if mode != "raw":
                data = data.replace(b"\r\n", b"\n")
            if mode == "crlf":
                data = data.replace(b"\n", b"\r\n")
            h.update(p.name.encode())
            h.update(data)
        out.add(h.hexdigest())
    return out


def ohlcv(n: int = 600, seed: int = 11) -> pd.DataFrame:
    """Tick-rounded GBM daily bars: the fixed frame for column sets and fingerprints."""
    rng = np.random.default_rng(seed)
    close = np.round(100 * np.exp(np.cumsum(rng.normal(0, 0.02, n))), 2)
    spread = np.round(np.abs(rng.normal(0, 0.01, n)) * close, 2)
    return pd.DataFrame({
        "open": np.round(close * (1 + rng.normal(0, 0.005, n)), 2),
        "high": close + spread, "low": close - spread, "close": close,
        "volume": rng.integers(1_000, 100_000, n).astype(float),
    }, index=pd.date_range("2020-01-01", periods=n, freq="D"))


def default_output(indicator: str, df: pd.DataFrame = None) -> pd.DataFrame:
    """`df.ta.<indicator>()` at its defaults: the call `df.ta.strategy()` makes."""
    df = ohlcv() if df is None else df
    out = getattr(df.ta, indicator)()
    if isinstance(out, tuple):  # ichimoku: the accessor appends only the first frame (core.py)
        out = out[0]
    if isinstance(out, pd.Series):
        out = out.to_frame()
    if not isinstance(out, pd.DataFrame):
        raise TypeError(f"df.ta.{indicator}() returned {type(out).__name__}")
    return out


def fingerprint(s: pd.Series) -> str:
    """finite count; sum; sum of squares; index-weighted sum -- robust to a few ulps of platform noise."""
    v = s.to_numpy(dtype=float)
    fin = np.isfinite(v)
    x, i = v[fin], np.flatnonzero(fin).astype(float)
    return f"{int(fin.sum())};{float(x.sum())!r};{float((x * x).sum())!r};{float((i * x).sum())!r}"


def fingerprints_match(a: str, b: str) -> bool:
    """Counts equal, sums within rel 1e-9 (CI's Linux runner differs from Windows by a few ulps)."""
    (ca, *fa), (cb, *fb) = a.split(";"), b.split(";")
    return ca == cb and all(math.isclose(float(x), float(y), rel_tol=1e-9, abs_tol=1e-9)
                            for x, y in zip(fa, fb))


def to_float(field: str) -> float:
    """CSV field -> float; pandas writes a NaN per-frame median as an empty string."""
    return float(field) if field.strip() else math.nan


def expected_verdict(max_abs_rho: float, perframe_max_median: float) -> str:
    """The r3-perframe-0.90 bands (Backtesting docs/gate_e.md, CLAUDE.md Gate E). NaN compares False."""
    if max_abs_rho >= 0.90 or perframe_max_median >= 0.90:
        return "STRUCK"
    if max_abs_rho >= 0.80:
        return "DISCLOSE_GAP"
    if max_abs_rho >= 0.76:
        return "DISCLOSE"
    return "SHIP"


def read_ledger(path: Path = LEDGER) -> list:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if rows and list(rows[0]) != FIELDS:
        raise ValueError(f"{path}: header {list(rows[0])} != {FIELDS}")
    return rows


def read_grandfathered(path: Path = GRANDFATHERED) -> dict:
    """{indicator: [default output columns]} frozen at 82eda5c."""
    return json.loads(path.read_text(encoding="utf-8"))["indicators"]


def _check_run(run_dir: Path, meta: dict, overlap: list) -> Path:
    """Raise unless the run is a default-parameter, frozen-universe run of this exact tree."""
    if meta.get("mode") != "run":
        raise ValueError(f"{run_dir}: mode {meta.get('mode')!r}, expected 'run'")
    # Category sweeps the defaults, so only a default-parameter, full-window, full-comparator run counts.
    for key, default in (("kwargs", {}), ("end", None), ("excluded", []), ("rename_prefix", None)):
        if meta.get(key) != default:
            raise ValueError(f"{run_dir}: {key}={meta.get(key)!r}; the ledger takes only {key}={default!r}")
    if meta.get("n_frames") != N_FRAMES:
        raise ValueError(f"{run_dir}: n_frames={meta.get('n_frames')}, expected {N_FRAMES}")
    if not str(meta.get("canary", "")).endswith("bit-equal"):
        raise ValueError(f"{run_dir}: canary {meta.get('canary')!r} is not bit-equal")
    bad = [o["column"] for o in overlap if o["n_comparators"] != str(N_COMPARATORS)]
    if bad:
        raise ValueError(f"{run_dir}: n_comparators != {N_COMPARATORS} for {bad}")
    path = module_path(meta["module"])
    if not path.is_file():
        raise FileNotFoundError(f"{meta['module']} is not in this tree ({path})")
    if not _matches_run(path, meta["candidate_source_sha1"]):
        raise ValueError(f"{path.relative_to(REPO)} is not the file this run measured "
                         f"(run sha1 {meta['candidate_source_sha1']}); re-run Gate E")
    if meta.get("pandas_ta_src_sha1") not in src_tree_sha1s():
        raise ValueError(f"{run_dir}: pandas_ta_src_sha1 {meta.get('pandas_ta_src_sha1')} is not this "
                         "tree's pandas_ta; the run imported other code (helpers included). Re-run Gate E")
    here = Path(pandas_ta.__file__).resolve().parent
    if here != (REPO / "pandas_ta").resolve():
        raise RuntimeError(f"imported pandas_ta from {here}, not from {REPO}")
    return path


def rows_from_run(run_dir: Path, measured: str, waiver: str = "") -> list:
    dt.date.fromisoformat(measured)  # fail fast on a malformed date
    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
    with (run_dir / "overlap_max.csv").open(newline="", encoding="utf-8") as fh:
        overlap = list(csv.DictReader(fh))
    if not overlap:
        raise ValueError(f"{run_dir}: overlap_max.csv has no rows")
    path = _check_run(run_dir, meta, overlap)
    if waiver and not any(o["verdict"] == "STRUCK" for o in overlap):
        raise ValueError(f"{run_dir}: --waiver given, but no column is STRUCK")
    out = default_output(meta["fn"])
    rows = []
    for o in overlap:
        row = {k: o[k] for k in COPIED}
        # A waiver covers only the STRUCK columns; the module's other columns stand on their own verdict.
        row.update(indicator=meta["fn"], module=meta["module"], n_frames=meta["n_frames"],
                   pooled_bars=meta["pooled_bars"], module_sha1=lf_sha1(path),
                   output_fp=fingerprint(out[o["column"]]),
                   pandas_ta_src_sha1=meta["pandas_ta_src_sha1"], stamp_data=meta["stamp"]["data"],
                   run=run_dir.name, measured=measured,
                   waiver=waiver if o["verdict"] == "STRUCK" else "")
        rows.append({k: row[k] for k in FIELDS})
    return rows


def record(run_dir: Path, measured: str, waiver: str = "") -> list:
    """Replace the ledger's rows for this run's indicator with the run's rows."""
    new = rows_from_run(run_dir, measured, waiver)
    indicator = new[0]["indicator"]
    old = read_ledger() if LEDGER.exists() else []
    rows = [r for r in old if r["indicator"] != indicator] + new
    rows.sort(key=lambda r: (r["indicator"], r["column"]))
    with LEDGER.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return new


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    rec = sub.add_parser("record", help="write one Gate E run into docs/gate_e_ledger.csv")
    rec.add_argument("run_dir", type=Path)
    rec.add_argument("--measured", required=True, help="date the Gate E run was taken, YYYY-MM-DD")
    rec.add_argument("--waiver", default="", help='open issue for a STRUCK row, e.g. "#23"')
    args = parser.parse_args()
    for row in record(args.run_dir, args.measured, args.waiver):
        print(f"{row['indicator']}:{row['column']} {row['verdict']} "
              f"{float(row['max_abs_rho']):.4f} vs {row['against']} -> {LEDGER.relative_to(REPO)}")


if __name__ == "__main__":
    main()
