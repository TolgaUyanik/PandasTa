# Auto run — TS-PERMENT-20 (PandasTa issue #91)

`/brutally-honest-review --auto "TS-PERMENT-20: port the indicator of issue
#91 through Gates A-D, the wiring, the tests and docs/<Name>Measured.md, per
the issue and the rules in your system prompt (permutation entropy of close
(order 3, 20). Source: tsfresh feature_calculators (MIT) —
`permutation_entropy(tau=1, dimension=3) on 20 closes`.). Gate E and the
suites are run by the launcher afterwards."`

Mode C (batch task execution), one task, run 2026-11-12 on branch
`issue-91-ts-perment-20`. Mode C has no pre-gate: the argument is a task, not
a plan carrying load-bearing reasoning.

## Phase 1 — the task

| id | scope | source |
|---|---|---|
| `ts-perment-20` | Port *permutation entropy of close (order 3, 20)* — tsfresh `permutation_entropy(tau=1, dimension=3)` on 20 closes — through Gates A–D, the five wiring touch points, a test module and `docs/TsPerment20Measured.md`. Gate E and both repos' suites are the launcher's. | PandasTa issue #91, quoted verbatim in the session prompt |

Run folder: `docs/reviews/auto-2026-11-12-ts-perment-20/`.

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in this headless session, so every gap is
resolved by the most conservative reading (the smaller scope) and logged as an
ASSUMPTION here.

* **ASSUMPTION 1 — the SOURCE formula ships, not the screen prototype.** The
  prototype (`docs/issues/screen/ind_screen.py`, candidate `ts_perment_20`)
  sums over `for k in (0, 1, 3, 4, 6, 7)`; measured exhaustively, two of those
  codes (1 and 6) are unrealisable and two realisable ones (2 and 5) are
  missing, so the prototype is a FOUR-pattern sum that drops 25.90% of a
  walk's triples. `CLAUDE.md` says *"Gate A starts from the source formula, not the
  prototype"*, so the six-pattern Bandt-Pompe form ships. The divergence is
  measured on three frames (Spearman 0.5487 / 0.4817 / −0.0296) and disclosed
  in the module docstring, `docs/TsPerment20Measured.md` and
  `docs/MLCompanionContract.md`. **This invalidates issue #91's own Gate E
  figures for this port** — they were taken on the prototype.
* **ASSUMPTION 2 — dimension 3 and tau 1 are CONSTANTS, not parameters.** The
  issue fixes both ("order 3, 20", `tau=1, dimension=3`). A general dimension
  needs different pattern-counting machinery; fixing it is the smaller scope.
  The 3 is in the column name so a later order cannot silently reuse it.
* **ASSUMPTION 3 — the column name is `TS_PERMENT_{length}_3`.** The issue
  names the candidate and not the column. The fork's convention is that the
  name carries the effective parameters (`TS_C3_20_1`, `TS_BINENT_20_5`), so
  the default is `TS_PERMENT_20_3`.
* **ASSUMPTION 4 — entropy in nats, UNNORMALISED.** tsfresh's
  `permutation_entropy` does not divide by `log(d!)`; the prototype does.
  Dividing is a strict rescaling (Spearman exactly 1.000000, measured), so it
  changes nothing a rank miner sees; the unnormalised source form ships and
  the alternative is priced.
* **ASSUMPTION 5 — ties are broken by INDEX (`<=`).** That is what the
  installed numpy's `argsort(argsort(x))` does on a 3-element array —
  measured over all 27 triples, not assumed, since `argsort`'s default `kind`
  is not documented as stable — and therefore what tsfresh's `argsort`
  spelling does *if* that is its spelling: tsfresh is NOT importable in this
  worktree (`ModuleNotFoundError`, measured). The prototype folds ties the
  other way with a strict `<`. The cost is
  measured rather than assumed: free on a continuous path, decisive on a
  coarse grid (Spearman 0.0384 at a 46.33% tie rate).
* **ASSUMPTION 6 — a degenerate window reads 0.0, not NaN.** One ordering
  holds all the mass, and the entropy of a one-bin histogram is 0 — the
  source's reading. The cost (a flat window and a monotone one are the same
  number) is measured and disclosed rather than hidden.
* **ASSUMPTION 7 — Gate E is the launcher's.** The session prompt forbids
  running `gate_e_overlap.py` or reading `../Backtesting`, so
  `docs/TsPerment20Measured.md` carries *Gate E: pending, run by issue-solver
  after this session* and `tests/test_gate_e_ledger.py` fails here until a
  later receipt session records the row.

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| `ts-perment-20` | main thread | One indicator, five wiring touch points plus four docs files, all overlapping; every number in the receipt has to come from a run made in this context. No independent scope to parallelise. |

Gate per task: a fresh `/brutally-honest-review` Fletcher reviewer subagent,
read-only, every verdict quoted in `01-ts-perment-20.md`. Cap 3 REVISE rounds
per the skill, raised to 4 rounds total by the user's global review-loop rule.
