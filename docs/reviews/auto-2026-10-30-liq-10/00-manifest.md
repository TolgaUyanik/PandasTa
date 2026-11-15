# Auto run liq-10 — 2026-10-30

## Tasks
| # | Task id | Source | One-line scope |
|---|---------|--------|----------------|
| 1 | LIQ | GitHub issue #10 (`docs/issues/012-LIQUIDITY.md`) | Port Corwin-Schultz spread, Roll spread and Amihud illiquidity from OHLCV through Gates A-D, wiring, tests and `docs/LiquidityMeasured.md`; Gate E and the parent-repo suite are run by the issue-solver launcher afterward. |

## Clarifications (asked ONCE, before execution)

`AskUserQuestion` is unavailable in this headless issue-solver session (session
rule). Per that session's own instruction, every point the issue leaves open was
resolved by the most conservative reading and logged as an ASSUMPTION in the task
log (`01-LIQ.md`), not asked:

- ASSUMPTION: one module per indicator (three files), not one module with three
  columns — `CLAUDE.md`'s "one indicator, one module" architecture rule and the
  session's own 3-new-file cap both point the same way, and the three formulas
  answer three distinct questions from three distinct papers.
- ASSUMPTION: Amihud normalised as a ratio to its own expanding median (not log,
  not rolling rank) — the only one of the three options that cancels exactly
  under the required ×8/×64 scale test on BOTH the price and volume axes, and the
  one with a direct precedent already in this repo (`maxvol_adv`'s peak/ADV
  ratio).
- ASSUMPTION: Roll's `cov >= 0` bars read NaN, not 0 — matches the repo's existing
  convention for an undefined ratio (`maxvol_adv`'s `NaN` where `ADV <= 0`) and a
  `0` would misstate "no cost" on a bar the model has no reading for at all.
- ASSUMPTION: Corwin-Schultz's negative alpha is clipped to 0, matching AFML's own
  `getAlpha` — not reverted to let negatives through, because the cost-MODEL use
  in `costs.py` can net a negative against a later positive bar in a backtest P&L
  and a bar-by-bar FEATURE column cannot.
- ASSUMPTION: the issue's "count how often [Corwin-Schultz clips] on real data" and
  "real-data counts" for Gate C cannot be done in this session — there is no real
  OHLCV data in this worktree (`data/SPY_D.csv` is gitignored and absent, and
  `../Backtesting` is off-limits per the session's own rules). Reported on a
  synthetic fixture instead, with that limitation stated, and left as Gate E's
  job via the issue-solver launcher.

## Execution map
| Task | Lane | Why |
|------|------|-----|
| LIQ | main thread | one task, five wiring touch points across shared files (`pandas_ta/__init__.py`, `core.py`, two category `__init__.py`s, `tests/test_altport2_ports.py`'s pinned `Category` counts, `README.md`, `docs/MLCompanionContract.md`) — not parallelisable, and needs judgement calls the issue deliberately leaves open. |
