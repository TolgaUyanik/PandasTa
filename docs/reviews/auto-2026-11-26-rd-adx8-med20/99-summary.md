# Run summary — RD-ADX8-MED20 (issue #178)

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| RD-ADX8-MED20 | PASS | 2 | `pandas_ta/trend/rd_adx8_med20.py`, `tests/test_rd_adx8_med20.py`, `docs/RdAdx8Med20Measured.md`, `docs/measure_rd_adx8_med20.py`, `docs/measure_rd_adx8_med20_cpu.py`, `pandas_ta/trend/__init__.py`, `pandas_ta/__init__.py`, `pandas_ta/core.py`, `README.md`, `docs/IndicatorDictionary.md`, `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py` | Gate E run owed (launcher); a later receipt session records the ledger row and measured Gate E numbers in `docs/RdAdx8Med20Measured.md` |

Round 1 found a CRITICAL (`min_bars` under-counted ADX's own warm-up, letting a 7-bar-wide range of
undersized inputs return an all-NaN Series instead of `None`, plus an overclaiming docstring
sentence) and a MAJOR (a loosened mutant-catch assertion reintroducing a majority-vs-minority
ambiguity the sibling port's own review history had already closed), plus a MINOR and a NIT. All
four were fixed on the main thread and re-measured; round 2 confirmed each fix by tracing the actual
ADX warm-up chain and re-running the target suite, and passed clean.

No project task-file convention detected for this repo's open-work tracking (`docs/issues/` is
gitignored and not writable from here per session rules) — no write-back attempted.

Full run folder: `docs/reviews/auto-2026-11-26-rd-adx8-med20/` (`00-manifest.md`,
`01-rd-adx8-med20.md`, this file).
