# osap_intmom — measured (issue #40)

> **Status: Gates A-D cleared this session. Gate E: pending, run by issue-solver after
> this session.** Gate F (both repos' suites) is run by the launcher in clean worktrees;
> `python -m pytest -q` in this worktree is reported below for the record.

Intermediate momentum, as asked for by issue #40: the issue names it `IntMom` in the Open
Source Asset Pricing (OSAP) SignalDoc (Chen & Zimmermann) catalogue (Novy-Marx 2012, OSAP
t 5.79) and restates its formation window as months t-12 through t-7 — the most recent
six months (t-6 through t-1) are excluded entirely, leaving only the six months before
that. That window description is the issue's own restatement (and `docs/issues/screen/
candidates.csv`'s), not independently checked against the primary SignalDoc text, which
this worktree cannot reach — see Gate A below. Module
`pandas_ta/momentum/osap_intmom.py`, column `INTMOM_126_252`. Tests:
`tests/test_osap_intmom.py` (14, all passing). Numbers below: `python
docs/measure_osap_intmom.py`. Environment: this worktree's pinned pandas/numpy (pandas
2.3.3). Measured 2026-11-02.

The prototype (`docs/issues/screen/ind_screen.py:771-772`) screened the identical
scale-free formula on BIST data and recorded Gate E DISCLOSE (max |ρ| 0.7610 vs
`Mom_12_1_pct`, per `docs/issues/screen/candidates.csv`) — a measurement of the
*prototype*, not of this port's module, and over a different harness run. The issue's own
"Measured" section states it as motivation, not as this port's Gate E result; this port's
real Gate E (on `pandas_ta.momentum.osap_intmom`, via `gate_e_overlap.py`) is run by the
launcher after this session and recorded separately.

## Gate A: the primary SignalDoc text and the OSAP code are NOT consulted — read this before trusting the column

Per the issue's own instruction, OSAP's replication code is GPL-2.0 and must never be the
source of a port; this is ported from the paper's definition. This session also could not
reach the OSAP SignalDoc PDF/CSV itself (`docs/pine/` and web access are unavailable), so
the port rests on two things, disclosed rather than assumed away:

1. **An identity, not an assumption.** A cumulative return compounded over a window of
   daily returns telescopes exactly to the ratio of the window's two endpoint prices:
   `prod(1 + r_i)` for `i` across the window equals `P_end / P_start`, since every interior
   price cancels. So "the cumulative return from month t-12 to month t-7" reduces to a
   single price ratio, with no month-by-month compounding step needed — this holds
   regardless of what the trading-day-per-month constant is. Identical to the identity
   this fork's own `osap_mrrev` #37 already relies on.
2. **ASSUMPTION — the issue's own stated conversion, taken as given, not independently
   re-derived from the primary SignalDoc, which this worktree cannot reach.**
   `docs/issues/screen/candidates.csv` (candidate `osap_intmom`) and the issue text both
   state the scale-free form as "126/252 bars": 21 trading days/month (the number this
   repo's own `RATE["DAYS_PER_MONTH"]` constant also uses, cited here only as narrative
   corroboration of the literal 21, not an active code dependency on that constant),
   giving `near_length = 6 * 21 = 126` (the "t-7" boundary, one month less than the
   window's literal month count) and `far_length = 12 * 21 = 252` (the "t-12" boundary).
   This is not a fresh derivation invented for this port: `osap_mrrev` #37's own module
   docstring already derived this exact arithmetic as internal corroboration *before this
   port existed* — `docs/issues/screen/ind_screen.py`'s `osap_intmom` row,
   `delay(c,126)/delay(c,252)`, with 126/21=6=7-1 and 252/21=12 — and a sibling row,
   `osap_lrrev` ("t-36..t-13" → `delay(c,252)/delay(c,756)`, 252/21=12=13-1, 756/21=36),
   follows the identical far-bound=literal-month-count, near-bound=one-month-less pattern.
   This is a real, checkable, internal cross-candidate pattern, not confirmation against
   the primary SignalDoc, which is unreachable here. The prototype
   (`docs/issues/screen/ind_screen.py:771-772`, `delay(c, 126) / delay(c, 252) - 1`) was
   read for this conversion only, confirming it matches the issue's own stated scale-free
   form — the formula itself (the identity above) was derived independently, per the
   issue's own instruction ("Gate A starts from the source formula, not the prototype").
   This conversion remains unconfirmed against the primary SignalDoc text itself.

If a future session gets access to the OSAP SignalDoc PDF/CSV, treat the 126/252
conversion as unverified against the primary source until re-checked (it is currently
verified only against the issue's own restatement of it).

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | primary SignalDoc unavailable — see above. Self-consistent against the issue's own stated formula, the telescoping-return identity, and `osap_mrrev` #37's prior independent derivation of the identical 126/252 arithmetic | Hand-derived 5-bar example (`near_length=1, far_length=2`, every term a plain shift): bars read exactly `nan, nan, 0.10000000000000009, -0.09999999999999998, 0.5151515151515151`, derived by hand from the formula, not by re-running the module. Matches an independent per-bar loop (written from the formula) at 4 spot-checked bars (300, 500, 700, 899) on a 900-bar synthetic geometric walk at the shipped defaults, to 9 decimal places |
| B Causality | pass | Future-perturbation sweep, 33 offsets past the 252-bar warm-up: real module **0 of 33** leaks. One look-ahead mutant (`importlib` source read, the near-bar reference shifted from `close.shift(near_length)` to `close.shift(near_length - 134)` — an 8-bar read into the future — `exec`'d in memory) is shown live (differs from the real module), then caught at **33 of 33** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 900-bar synthetic geometric walk (seed 17, σ=1.5%/bar), shipped defaults (`near_length=126, far_length=252`): **648 of 900** bars non-NaN (72.00%) — exactly `n - far_length`, i.e. only the combined 252-bar warm-up is excluded, no wider gap. 648 distinct values among the 648 (every fired bar distinct). Range [-0.372330, 0.362135], median -0.051867 |
| D Scale-free | pass | x8/x64: **bit-identical, 0.0 max\|diff\|** (a ratio of two identically-scaled prices). x10/x3.7: max\|diff\| 2.22e-16 — both well under the 1e-9 tolerance the test asserts, with matching NaN masks. `0 < 648 fires < 900` and 648 distinct values rule out a constant column |
| E Attribution | **pending, run by issue-solver after this session** | `gate_e_overlap.py run --module pandas_ta.momentum.osap_intmom`. The *prototype's* screen (same scale-free formula, different harness run) measured DISCLOSE — pooled max \|ρ\| 0.7610 vs `Mom_12_1_pct` (manifest, n=376,421), top-5 per-frame max median 0.7536 (`docs/issues/screen/candidates.csv`) — but that number is not this port's Gate E result and must not be quoted as such |
| F Suites | this repo only; parent repo (`Backtesting`) and Gate E are run by the launcher in clean worktrees | `python -m pytest -q` (this session, pre-ledger-record): see below |

## Wiring

`Category` **272 → 273** (`momentum` **62 → 63**); `df.ta.<name>()` accessor count **280 →
281**. Touch points: `pandas_ta/momentum/osap_intmom.py` (module),
`pandas_ta/momentum/__init__.py` (export), `pandas_ta/__init__.py` →
`Category["momentum"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.osap_intmom` (accessor), `tests/test_osap_intmom.py` (tests).
`README.md`'s headline and `momentum (63)` row, and `docs/IndicatorDictionary.md`
(regenerated; `osap_intmom` probes cleanly, column `INTMOM_126_252` tagged `SF`), both
updated and checked by `tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s
running tagged-column count updated **618 → 619** (`SF` **262 → 263**) and checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match.

## Receipt

Gate E: pending, run by issue-solver after this session. A future receipt session records
the ledger row (`docs/gate_e_ledger.csv`) and fills in the measured number here, deciding
ship vs. revert per the 0.76/0.80/0.90 bands in `CLAUDE.md`. Until then this column ships
provisionally (per "Owed, not failed, on the way to `dev`"), and a STRUCK result would
mean a revert before any release into `main`.
