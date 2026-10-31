# -*- coding: utf-8 -*-
"""Recomputes the Gate E ledger fingerprints for `crsi` after the Gate E revert
(CRSI_3_2_100 and CRSI_PCTRANK_100 struck and deleted; only CRSI_STREAK_2
ships). `docs/gate_e_ledger.py record` cannot be re-run here: it refuses
unless the current tree matches the harness run's `candidate_source_sha1`,
and that run measured the pre-revert, three-column module. This prints the
same two numbers `record` would have written for the surviving column --
the module's LF-normalised sha1 and `CRSI_STREAK_2`'s output fingerprint --
so `docs/gate_e_ledger.csv`'s surviving row can be hand-trimmed to describe
the post-revert code honestly, without inventing a new measurement.

    python docs/measure_crsi_ledger_fix.py
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
import docs.gate_e_ledger as gl  # noqa: E402

path = gl.module_path("pandas_ta.momentum.crsi")
print("module_sha1:", gl.lf_sha1(path))
out = gl.default_output("crsi")
print("columns:", list(out.columns))
print("output_fp CRSI_STREAK_2:", gl.fingerprint(out["CRSI_STREAK_2"]))
