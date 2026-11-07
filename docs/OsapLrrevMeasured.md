# osap_lrrev — measured (issue #35)

> **Status: Gates A-D cleared this session.** Gate E: pending, run by issue-solver
> after this session. Gate F (both repos' suites) is run by the launcher in clean
> worktrees; `python -m pytest -q` in this worktree is reported below for the record.

De Bondt & Thaler's (1985) long-run reversal/overreaction effect, as asked for by issue
#35: the issue names it `LRreversal` in the Open Source Asset Pricing (OSAP) SignalDoc
(Chen & Zimmermann) catalogue (reported t-stat 3.29) and restates its formation window as
months t-36 through t-13 — a 24-month window ending 12 months before the current month.
That window description is the issue's own restatement (and `docs/issues/screen/
candidates.csv`'s), not independently checked against the primary SignalDoc text, which
this worktree cannot reach — see Gate A below. Module `pandas_ta/momentum/osap_lrrev.py`,
column `LRREV_252_756`. Tests: `tests/test_osap_lrrev.py` (12, all passing). Numbers
below: `python docs/measure_osap_lrrev.py`. Environment: this worktree's pinned
pandas/numpy. Measured 2026-11-07.

## Gate A: the primary SignalDoc text and the OSAP code are NOT consulted — read this before trusting the column

Per the issue's own instruction, OSAP's replication code is GPL-2.0 and must never be the
source of a port; this is ported from the paper's definition. This session also could not
reach the OSAP SignalDoc PDF/CSV itself (`docs/pine/` and web access are unavailable), so
the port rests on two things, disclosed rather than assumed away:

1. **An identity, not an assumption.** A cumulative return compounded over a window of
   daily returns telescopes exactly to the ratio of the window's two endpoint prices:
   `prod(1 + r_i)` for `i` across the window equals `P_end / P_start`, since every interior
   price cancels. So "the cumulative return from month t-36 to month t-13" reduces to a
   single price ratio, with no month-by-month compounding step needed — this holds
   regardless of what the trading-day-per-month constant is.
2. **ASSUMPTION — the issue's own stated conversion, taken as given, not independently
   re-derived from the primary SignalDoc, which this worktree cannot reach.**
   `docs/issues/screen/candidates.csv` (candidate `osap_lrrev`) and the issue text both
   state the scale-free form as "252/756 bars": 21 trading days/month (the number this
   repo's own `RATE["DAYS_PER_MONTH"]` constant also uses, cited here only as narrative
   corroboration of the literal 21, not an active code dependency on that constant),
   giving `near_length = 12 * 21 = 252` and `far_length = 36 * 21 = 756`. The near/far
   split (far bound = the window's literal month count, near bound = one month less) is
   not a one-off: the same prototype file carries two sibling `@cand` rows using the
   identical arithmetic — `osap_intmom` ("t-12..t-7" → `delay(c,126)/delay(c,252)`,
   126/21=6=7-1, 252/21=12) and `osap_mrrev` ("t-18..t-13" → `delay(c,252)/delay(c,378)`,
   252/21=12=13-1, 378/21=18) both match far-bound=literal-month-count,
   near-bound=one-month-less exactly. Two further rows, `osap_mom12_1`
   (`delay(c,21)/delay(c,252)`) and `osap_mom6_1` (`delay(c,21)/delay(c,126)`), follow a
   related but distinct convention (Jegadeesh-Titman "skip the last month": near bound
   fixed at 21 = 1 month, not one-less-than-the-window) — they corroborate that the
   prototype's month-to-21-trading-days conversion is used consistently, not that every
   row shares `osap_lrrev`'s exact near/far arithmetic. This is a real, checkable,
   internal cross-candidate pattern, not confirmation against the primary SignalDoc,
   which is unreachable here. The prototype (`docs/issues/screen/ind_screen.py:775-776`,
   `delay(c, 252) / delay(c, 756) - 1`) was read for this conversion only, confirming it
   matches the issue's own `conv` field — the formula itself (the identity above) was
   derived independently, per the issue's own instruction ("Gate A starts from the source
   formula, not the prototype"). This conversion remains unconfirmed against the primary
   SignalDoc text itself.

If a future session gets access to the OSAP SignalDoc PDF/CSV, treat the 252/756
conversion as unverified against the primary source until re-checked (it is currently
verified only against the issue's own restatement of it).

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | primary SignalDoc unavailable — see above. Self-consistent against the issue's own stated formula and the telescoping-return identity | Hand-derived 5-bar example (`near_length=1, far_length=2`, every term a plain shift): bars read exactly 0.10, -0.10, 17/33 = 0.515152, derived by hand from the formula, not by re-running the module. Matches an independent per-bar loop (written from the formula) at 4 spot-checked bars (760, 800, 850, 899) on a 900-bar synthetic walk at the shipped defaults, rel. tolerance 1e-9 |
| B Causality | pass | Future-perturbation sweep, 29 offsets past the 756-bar warm-up: real module **0 of 29** leaks. One look-ahead mutant (`importlib` source read, the near-bar reference shifted from `close.shift(252)` to `close.shift(-8)` — an 8-bar read into the future — `exec`'d in memory) is shown live (differs from the real module), then caught at **29 of 29** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,600-bar synthetic geometric walk (seed 17, σ=1.5%/bar), shipped defaults (`near_length=252, far_length=756`): **844 of 1,600** bars non-NaN (52.75%) — exactly `n - far_length`, i.e. only the combined 756-bar warm-up is excluded, no wider gap. 844 distinct values among the 844 (every fired bar distinct). Range [-0.324912, 1.322480], median 0.484309 |
| D Scale-free | pass | x8/x64: **bit-identical, 0.0 max\|diff\|** (a ratio of two identically-scaled prices). x10/x3.7: max\|diff\| 4.44e-16 — both well under the 1e-9 tolerance the test asserts, with matching NaN masks. `0 < 844 fires < 1,600` and 844 distinct values rule out a constant column |
| E Attribution | pending, run by issue-solver after this session | — |
| F Suites | this repo only; parent repo (`Backtesting`) and Gate E are run by the launcher in clean worktrees | `python -m pytest -q` (this session, pre-ledger-record): **3 failed, 4195 passed, 83 skipped** — the 3 failures are all pre-existing/expected: `test_pine_coverage_csv.py` (known break, untracked `docs/pine/` corpus — see CLAUDE.md "Known breaks"), `test_altrepo_talib_csv.py` (needs the sibling `../AlternativeRepos` checkout), `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (this port's row is owed — a future receipt session records it) |

## Disclosed side effect: `docs/IndicatorDictionary.md`'s probe harness

`docs/gen_indicator_dictionary.py` builds a single 600-row synthetic OHLCV frame to probe
every registered indicator at its defaults (`N = 600` in that script, which this session
did not and may not edit — it is an existing helper module). `osap_lrrev`'s default
`far_length=756` needs 757 bars to produce even one non-NaN value, so the probe returns
`None` and the generator records it as a "Known break" (`no frame/series returned`) —
this is the probe harness being too short for this indicator's deliberately long,
issue-specified window, not a defect in the indicator itself (see Gate C above, measured
on a 1,600-bar frame). A real BIST frame clears this trivially; Gate E's own pooled bar
count (hundreds of thousands of bars per the ledger's other rows) will confirm it fires
there too. One side effect of this: because the generator's "Known breaks" section branches
on whether any probe error exists at all, this row's presence suppressed the two
previously-printed items in that section (the `up_and_down_volume`/`volume_delta`
"not probed" note and the 2026-09-07 WIRING fix history) — both still true, just not
re-printable without hand-editing the generated file, which this session does not do
(same effect already observed on `osap_intmom`/`osap_mrrev`, the other two long-window
OSAP ports already shipped). A future session that either widens the probe frame or
special-cases long-window indicators in the (unmodifiable-this-session) generator would
restore them.

## Wiring

`Category` **273 → 274** (`momentum` **63 → 64**); `df.ta.<name>()` accessor count **281 →
282**. Touch points: `pandas_ta/momentum/osap_lrrev.py` (module), `pandas_ta/momentum/__init__.py`
(export), `pandas_ta/__init__.py` → `Category["momentum"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.osap_lrrev` (accessor), `tests/test_osap_lrrev.py` (tests). `README.md`'s
headline and `momentum (64)` row, and `docs/IndicatorDictionary.md` (regenerated), both
updated and checked by `tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s running
tag count is unchanged because `LRREV_252_756` was not probed into a tagged row — see the
disclosed side effect above; `tests/test_ml_companions.py::
test_the_contract_quotes_the_dictionarys_actual_ml_form_counts` still passes against the
unchanged `Counter`. `tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match
(273 → 274).

## Receipt (pending)

Gate E has not run yet. A future receipt session records the launcher's run in
`docs/gate_e_ledger.csv` and fills in this section with the measured verdict, max\|ρ\| and
comparator, deciding ship vs. revert per CLAUDE.md's bands.
