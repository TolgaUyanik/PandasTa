# -*- coding: utf-8 -*-
"""Gate E ledger: the committed record of every Gate E verdict CI relies on.

Gate E needs the private Backtesting engine and the BIST frame cache, so it
cannot run in this public repo's CI. The owner runs it locally
(`gate_e_overlap.py run`, see CLAUDE.md) and records the result here:

    python docs/gate_e_ledger.py record <run dir> [--waiver "#23"]

`<run dir>` is the harness output folder (`meta.json` + `overlap_max.csv`).
`record` refuses a run that does not describe the module file in this tree
byte for byte, or one that was not taken at the defaults `df.ta.strategy()`
sweeps. `tests/test_gate_e_ledger.py` then fails CI when an indicator in
`Category` has no row, when its module changed after the run, or when a row
is STRUCK without one of the allowed waivers.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LEDGER = REPO / "docs" / "gate_e_ledger.csv"
GRANDFATHERED = REPO / "docs" / "gate_e_grandfathered.txt"
SCHEMA = "r3-perframe-0.90"

FIELDS = [
    "indicator", "module", "column", "verdict", "max_abs_rho", "against",
    "against_set", "n", "perframe_max_median_abs_rho", "perframe_max_against",
    "non_nan", "non_zero", "n_frames", "pooled_bars", "n_comparators",
    "verdict_schema", "module_sha1", "run", "measured", "waiver",
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


def expected_verdict(max_abs_rho: float, perframe_max_median: float) -> str:
    """The r3-perframe-0.90 bands (Backtesting docs/gate_e.md, CLAUDE.md Gate E)."""
    if max_abs_rho >= 0.90 or perframe_max_median >= 0.90:
        return "STRUCK"
    if max_abs_rho >= 0.80:
        return "DISCLOSE_GAP"
    if max_abs_rho >= 0.76:
        return "DISCLOSE"
    return "SHIP"


def read_ledger(path: Path = LEDGER) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if rows and list(rows[0]) != FIELDS:
        raise ValueError(f"{path}: header {list(rows[0])} != {FIELDS}")
    return rows


def read_grandfathered(path: Path = GRANDFATHERED) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]


def _matches_run(path: Path, run_sha1: str) -> bool:
    """True if the file, in its LF or CRLF form, is the one the harness hashed."""
    lf = path.read_bytes().replace(b"\r\n", b"\n")
    return run_sha1 in {hashlib.sha1(lf).hexdigest(),
                        hashlib.sha1(lf.replace(b"\n", b"\r\n")).hexdigest()}


def rows_from_run(run_dir: Path, waiver: str = "") -> list[dict]:
    meta = json.loads((run_dir / "meta.json").read_text(encoding="utf-8"))
    if meta.get("mode") != "run":
        raise ValueError(f"{run_dir}: mode {meta.get('mode')!r}, expected 'run'")
    # Category sweeps the defaults, so only a default-parameter, full-window, full-comparator run counts.
    for key, default in (("kwargs", {}), ("end", None), ("excluded", []), ("rename_prefix", None)):
        if meta.get(key) != default:
            raise ValueError(f"{run_dir}: {key}={meta.get(key)!r}; the ledger takes only {key}={default!r}")
    path = module_path(meta["module"])
    if not path.is_file():
        raise FileNotFoundError(f"{meta['module']} is not in this tree ({path})")
    if not _matches_run(path, meta["candidate_source_sha1"]):
        raise ValueError(f"{path.relative_to(REPO)} is not the file this run measured "
                         f"(run sha1 {meta['candidate_source_sha1']}); re-run Gate E")
    measured = dt.date.fromtimestamp((run_dir / "meta.json").stat().st_mtime).isoformat()
    with (run_dir / "overlap_max.csv").open(newline="", encoding="utf-8") as fh:
        overlap = list(csv.DictReader(fh))
    if not overlap:
        raise ValueError(f"{run_dir}: overlap_max.csv has no rows")
    if waiver and not any(o["verdict"] == "STRUCK" for o in overlap):
        raise ValueError(f"{run_dir}: --waiver given, but no column is STRUCK")
    rows = []
    for o in overlap:
        row = {k: o[k] for k in COPIED}
        # A waiver covers only the STRUCK columns; the module's other columns stand on their own verdict.
        row.update(indicator=meta["fn"], module=meta["module"], n_frames=meta["n_frames"],
                   pooled_bars=meta["pooled_bars"], module_sha1=lf_sha1(path),
                   run=run_dir.name, measured=measured,
                   waiver=waiver if o["verdict"] == "STRUCK" else "")
        rows.append({k: row[k] for k in FIELDS})
    return rows


def record(run_dir: Path, waiver: str = "") -> list[dict]:
    """Replace the ledger's rows for this run's indicator with the run's rows."""
    new = rows_from_run(run_dir, waiver)
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
    rec.add_argument("--waiver", default="", help='open issue for a STRUCK row, e.g. "#23"')
    args = parser.parse_args()
    for row in record(args.run_dir, args.waiver):
        print(f"{row['indicator']}:{row['column']} {row['verdict']} "
              f"{float(row['max_abs_rho']):.4f} vs {row['against']} -> {LEDGER.relative_to(REPO)}")


if __name__ == "__main__":
    main()
