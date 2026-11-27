# Run summary — RD-DIP-DEPTH-10-25 (issue #181)

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| RD-DIP-DEPTH-10-25 | PASS | 1 | `pandas_ta/momentum/rd_dip_depth_10_25.py`, `tests/test_rd_dip_depth_10_25.py`, `docs/RdDipDepth1025Measured.md`, `docs/measure_rd_dip_depth_10_25.py`, `docs/measure_rd_dip_depth_10_25_cpu.py`, `pandas_ta/momentum/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py` | Gate E run owed (launcher); a later receipt session records the ledger row and measured Gate E numbers in `docs/RdDipDepth1025Measured.md` |

Round 1 passed clean on the gate rule (no CRITICAL or MAJOR), with one MINOR: the module's
docstring and receipt named the issue's own prototype comparators (`kdj_J_9_3`, `willr`) without
arguing why `willr`'s structurally similar numerator doesn't make this a redundant restatement, the
same disclosure `rd_std_ratio_20_60` carries for its own borderline comparator. Applied voluntarily
on the main thread (a NON-REDUNDANCY paragraph in both the module docstring and the receipt) even
though a MINOR-only verdict does not require a re-review round; re-ran the target suite and the
measurement script afterward and confirmed every number held.

No project task-file convention detected for this repo's open-work tracking (`docs/issues/` is
gitignored and not writable from here per session rules) — no write-back attempted.

Full run folder: `docs/reviews/auto-2026-11-27-rd-dip-depth-10-25/` (`00-manifest.md`,
`01-rd-dip-depth-10-25.md`, this file).
