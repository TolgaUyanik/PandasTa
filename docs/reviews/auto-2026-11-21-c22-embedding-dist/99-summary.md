# Summary — auto-2026-11-21-c22-embedding-dist

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| port-132 | PASS (measured revert) | 4 | `docs/C22EmbeddingDistMeasured.md`, `docs/measure_c22_embedding_dist.py` | Gate E/F are the launcher's; nothing shipped so no ledger/wiring/README entry is owed |

PandasTa issue #132 (C22-EMBEDDING-DIST) could not clear Gate A on every
frame: 34 structural variants of catch22's
`CO_Embed2_Dist_tau_d_expfit_meandiff` (30 histogram-parameter readings + 4
alternative structures, plus a 21-point fine sweep, a 25-frame
generalisation cross-check of the closest fixed reading, and round 4's
data-driven bin-count family including numpy's own `bins='auto'`
convention), calibrated against `pycatch22` 1.0.2 used strictly as a
black-box oracle, got closest with that auto-bin convention: 30 of 33
frames reproduce the oracle to float precision, but 3 stay off by exactly
one bin — short of this fork's own Gate A bar (`c22_acf_first_min`'s "0 of
N disagree"). Closed as a **measured revert** per the issue's own terms
("a measured revert closes this exactly as well as a ship") — no
`pandas_ta` module, test or wiring was added. The receipt
(`docs/C22EmbeddingDistMeasured.md`) and its harness
(`docs/measure_c22_embedding_dist.py`) are the only committed artifacts.

No task file convention applies here (this run was driven by the
issue-solver's own system prompt, not a repo `TODO.md`), so there is no
task-file write-back.
