# osap_mrrev — measured (issue #37)

> **Status: Gates A-E cleared. SHIP.** Gate F (both repos' suites) is run by the launcher
> in clean worktrees; `python -m pytest -q` in this worktree is reported below for the
> record.

A medium-run reversal effect, as asked for by issue #37: the issue names it `MRreversal`
in the Open Source Asset Pricing (OSAP) SignalDoc (Chen & Zimmermann) catalogue (t-stat
not given, per the issue's own measurement) and restates its formation window as months
t-18 through t-13 — a 6-month window ending 12 months before the current month. That
window description is the issue's own restatement (and `docs/issues/screen/
candidates.csv`'s), not independently checked against the primary SignalDoc text, which
this worktree cannot reach — see Gate A below. Module `pandas_ta/momentum/osap_mrrev.py`,
column `MRREV_252_378`. Tests: `tests/test_osap_mrrev.py` (14, all passing). Numbers
below: `python docs/measure_osap_mrrev.py`. Environment: this worktree's pinned
pandas/numpy. Measured 2026-11-02.

## Gate A: the primary SignalDoc text and the OSAP code are NOT consulted — read this before trusting the column

Per the issue's own instruction, OSAP's replication code is GPL-2.0 and must never be the
source of a port; this is ported from the paper's definition. This session also could not
reach the OSAP SignalDoc PDF/CSV itself (`docs/pine/` and web access are unavailable), so
the port rests on two things, disclosed rather than assumed away:

1. **An identity, not an assumption.** A cumulative return compounded over a window of
   daily returns telescopes exactly to the ratio of the window's two endpoint prices:
   `prod(1 + r_i)` for `i` across the window equals `P_end / P_start`, since every interior
   price cancels. So "the cumulative return from month t-18 to month t-13" reduces to a
   single price ratio, with no month-by-month compounding step needed — this holds
   regardless of what the trading-day-per-month constant is.
2. **ASSUMPTION — the issue's own stated conversion, taken as given, not independently
   re-derived from the primary SignalDoc, which this worktree cannot reach.**
   `docs/issues/screen/candidates.csv` (candidate `osap_mrrev`) and the issue text both
   state the scale-free form as "252/378 bars": 21 trading days/month (the number this
   repo's own `RATE["DAYS_PER_MONTH"]` constant also uses, cited here only as narrative
   corroboration of the literal 21, not an active code dependency on that constant),
   giving `near_length = 12 * 21 = 252` and `far_length = 18 * 21 = 378`. The near/far
   split (far bound = the window's literal month count, near bound = one month less) is
   not a one-off: the same prototype file carries two sibling `@cand` rows using the
   identical arithmetic — `osap_intmom` ("t-12..t-7" → `delay(c,126)/delay(c,252)`,
   126/21=6=7-1, 252/21=12) and `osap_lrrev` ("t-36..t-13" → `delay(c,252)/delay(c,756)`,
   252/21=12=13-1, 756/21=36) both match far-bound=literal-month-count,
   near-bound=one-month-less exactly. Two further rows, `osap_mom12_1`
   (`delay(c,21)/delay(c,252)`) and `osap_mom6_1` (`delay(c,21)/delay(c,126)`), follow a
   related but distinct convention (Jegadeesh-Titman "skip the last month": near bound
   fixed at 21 = 1 month, not one-less-than-the-window) — they corroborate that the
   prototype's month-to-21-trading-days conversion is used consistently, not that every
   row shares `osap_mrrev`'s exact near/far arithmetic. This is a real, checkable,
   internal cross-candidate pattern, not confirmation against the primary SignalDoc,
   which is unreachable here. The prototype (`docs/issues/screen/ind_screen.py:780`,
   `delay(c, 252) / delay(c, 378) - 1`) was read for this conversion only, confirming it
   matches the issue's own `conv` field — the formula itself (the identity above) was
   derived independently, per the issue's own instruction ("Gate A starts from the source
   formula, not the prototype"). This conversion remains unconfirmed against the primary
   SignalDoc text itself.

If a future session gets access to the OSAP SignalDoc PDF/CSV, treat the 252/378
conversion as unverified against the primary source until re-checked (it is currently
verified only against the issue's own restatement of it).

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | primary SignalDoc unavailable — see above. Self-consistent against the issue's own stated formula and the telescoping-return identity | Hand-derived 5-bar example (`near_length=1, far_length=2`, every term a plain shift): bars read exactly 0.10, -0.10, 17/33 = 0.515152, derived by hand from the formula, not by re-running the module. Matches an independent per-bar loop (written from the formula) at 4 spot-checked bars (400, 500, 700, 899) on a 900-bar synthetic walk at the shipped defaults, rel. tolerance 1e-9 |
| B Causality | pass | Future-perturbation sweep, 29 offsets past the 378-bar warm-up: real module **0 of 29** leaks. One look-ahead mutant (`importlib` source read, the near-bar reference shifted from `close.shift(252)` to `close.shift(-8)` — an 8-bar read into the future — `exec`'d in memory) is shown live (differs from the real module), then caught at **29 of 29** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,600-bar synthetic geometric walk (seed 17, σ=1.5%/bar), shipped defaults (`near_length=252, far_length=378`): **1,222 of 1,600** bars non-NaN (76.38%) — exactly `n - far_length`, i.e. only the combined 378-bar warm-up is excluded, no wider gap. 1,222 distinct values among the 1,222 (every fired bar distinct). Range [-0.372330, 0.526875], median 0.055086 |
| D Scale-free | pass | x8/x64: **bit-identical, 0.0 max\|diff\|** (a ratio of two identically-scaled prices). x10/x3.7: max\|diff\| 2.22e-16 — both well under the 1e-9 tolerance the test asserts, with matching NaN masks. `0 < 1,222 fires < 1,600` and 1,222 distinct values rule out a constant column |
| E Attribution | **SHIP** | `gate_e_overlap.py run --module pandas_ta.momentum.osap_mrrev`, 89 ALTPORT-1 frames, 398,849 pooled bars, 329 + 358 = 687 comparators. `MRREV_252_378` max \|ρ\| **0.5786** vs `Ret_252d_pct_Pctl` (manifest, n=365,207); per-frame max median \|ρ\| **0.5927** (0.0% of frames ≥ 0.90). Both well under the 0.76 ship line. Canary bit-equal (AKBNK, BIENY, AGHOL, SASA.IS). Run `is37-osap_mrrev-75531ea6`, measured 2026-11-02, recorded in `docs/gate_e_ledger.csv` |
| F Suites | this repo only; parent repo (`Backtesting`) and Gate E are run by the launcher in clean worktrees | `python -m pytest -q` (this session, pre-ledger-record): **3 failed, 4106 passed, 83 skipped** — the three failures are the known break (`test_pine_coverage_csv.py`, untracked `docs/pine/` corpus), the sibling-repo dependency (`test_altrepo_talib_csv.py`, needs `../AlternativeRepos`), and `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (resolved by a future receipt session's ledger record); all three are documented pre-existing/expected failures per `CLAUDE.md`, none caused by this port |

## Wiring

`Category` **269 → 270** (`momentum` **61 → 62**); `df.ta.<name>()` accessor count **277 →
278**. Touch points: `pandas_ta/momentum/osap_mrrev.py` (module), `pandas_ta/momentum/__init__.py`
(export), `pandas_ta/__init__.py` → `Category["momentum"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.osap_mrrev` (accessor), `tests/test_osap_mrrev.py` (tests). `README.md`'s
headline and `momentum (62)` row, and `docs/IndicatorDictionary.md` (regenerated; `osap_mrrev`
probes cleanly, column `MRREV_252_378` tagged `SF`, no disclosed-side-effect gap since
`far_length=378` is well inside the generator's 600-bar probe frame), both updated and checked
by `tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s running tagged-column count
updated **615 → 616** (`SF` **260 → 261**) and checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match.

## Receipt

Gate E SHIP (0.5786 < 0.76). Column kept, nothing reverted. Ledger row recorded
2026-11-02 (`is37-osap_mrrev-75531ea6`).
