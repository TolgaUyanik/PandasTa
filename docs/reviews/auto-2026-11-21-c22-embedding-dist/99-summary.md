# Summary — auto-2026-11-21-c22-embedding-dist

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| port-132 | PASS (measured revert) | 3 | `docs/C22EmbeddingDistMeasured.md`, `docs/measure_c22_embedding_dist.py` | Gate E/F are the launcher's; nothing shipped so no ledger/wiring/README entry is owed |

PandasTa issue #132 (C22-EMBEDDING-DIST) could not clear Gate A: 35
structural variants of catch22's `CO_Embed2_Dist_tau_d_expfit_meandiff`
(plus a 21-point fine sweep and a 25-frame generalisation cross-check of
the closest one), calibrated against `pycatch22` 1.0.2 used strictly as a
black-box oracle, never reproduced the reference's output to within
anything near its own float precision. Closed as a **measured revert**
per the issue's own terms ("a measured revert closes this exactly as well
as a ship") — no `pandas_ta` module, test or wiring was added. The receipt
(`docs/C22EmbeddingDistMeasured.md`) and its harness
(`docs/measure_c22_embedding_dist.py`) are the only committed artifacts.

No task file convention applies here (this run was driven by the
issue-solver's own system prompt, not a repo `TODO.md`), so there is no
task-file write-back.
