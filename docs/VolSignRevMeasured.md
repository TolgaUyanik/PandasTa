# vol_sign_rev — measured (issue #43)

> **Status: Gates A-D cleared; Gate E measured by the launcher 2026-11-08 — SHIP.**
> Ledger row recorded in `docs/gate_e_ledger.csv`. Gate F (both repos' suites) is run by
> the launcher in clean worktrees; `python -m pytest -q` in this worktree is reported
> below for the record.

Alpha#12 of Kakushadze's "101 Formulaic Alphas" (2016, Wilmott), as asked for by
issue #43 and `docs/issues/screen/candidates.csv` (candidate `a101_012`,
"volume-signed reversal"): `sign(delta(volume,1)) * -delta(close,1)`, with the
issue's own scale-free substitution `delta(close,1) -> one-bar return`. One bar's
price return, sign-flipped whenever volume rose over the same bar. Module
`pandas_ta/volume/vol_sign_rev.py`, column `VSR`. Tests: `tests/test_vol_sign_rev.py`
(15, all passing). Numbers below: `python docs/measure_vol_sign_rev.py`. Environment:
this worktree's pinned pandas/numpy. Measured 2026-11-08.

## Gate A: the Kakushadze (2016) paper and the vnpy `alpha101` repository are NOT consulted — read this before trusting the column

Per CLAUDE.md, Gate A starts from the source formula, not the prototype. This session
has no web access and `docs/pine/` is unavailable, so neither the Kakushadze paper text
nor the vnpy `alpha101` repository it is read from could be reached. The port therefore
rests on the issue's own restatement of Alpha#12 — `sign(delta(volume,1)) *
-delta(close,1)` — which is also, independently, exactly the expression the local Gate E
screen prototype computes (`docs/issues/screen/ind_screen.py:214`, `return
np.sign(delta(v, 1)) * -ret(c)`, where `ret(c) = c / c.shift(1) - 1` at
`ind_screen.py:108`). This remains unconfirmed against the primary paper text itself.

Unlike the OSAP ports (`osap_lrrev`, `osap_mrrev`, `osap_intmom`), no derivation or
unit-conversion assumption is needed: both operators translate literally and the
translation is exact, not approximate:

1. `delta(x, 1)` is `x - x.shift(1)`, i.e. `x.diff(1)` — used for both `delta(volume,1)`
   (`volume.diff(1)`) and, before the scale-free substitution below, `delta(close,1)`.
2. `sign(x)` is `np.sign(x)` — applied to `volume.diff(1)`.
3. **ASSUMPTION, but the issue's own, not derived here**: the scale-free conversion
   `delta(close,1) -> one-bar return` is stated explicitly by the issue text and by
   `candidates.csv`'s own `conv` field for `a101_012`. The raw price difference
   `delta(close, 1)` (price-unit, not a feature per CLAUDE.md's ML feature contract) is
   replaced by the dimensionless return `close.pct_change(1)` (`close / close.shift(1) -
   1`), matching the issue's own prototype's `ret(c)` helper exactly. `sign(delta(volume,
   1))` needs no such substitution: a sign is already scale-free regardless of volume's
   units.

If a future session gets access to the Kakushadze paper or the vnpy repository, treat the
exact Alpha#12 wording (not just the issue's restatement of it) as unverified against the
primary source until re-checked.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | primary paper/vnpy source unavailable — see above. Self-consistent against the issue's own stated formula and the local screen prototype's identical expression | Hand-derived 5-bar example (`close=[100,110,99,150,200]`, `volume=[1000,1200,1100,1100,1300]`, every term a plain diff/shift): bars read exactly -0.10, -0.10, 0.0, -1/3 = -0.333333, derived by hand from the formula, not by re-running the module. Matches an independent per-bar loop (written from the formula) at 4 spot-checked bars (1, 50, 400, 899) on a 900-bar synthetic walk, rel. tolerance 1e-9 |
| B Causality | pass | Future-perturbation sweep, 45 offsets past the 1-bar warm-up: real module **0 of 45** leaks. One look-ahead mutant (`importlib` source read, the return term's `close.shift(1)` switched to `close.shift(-1)` — a 1-bar read into the future — `exec`'d in memory) is shown live (differs from the real module), then caught at **45 of 45** |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 900-bar synthetic geometric-walk close (seed 17, σ=1.5%/bar) with an independent uniform volume stream (seed 23): **899 of 900** bars non-NaN (99.89%) — only the single 1-bar warm-up is excluded. 899 distinct values among the 899 (every fired bar distinct). Range [-0.053186, 0.044516], median 0.000610, median absolute value 0.009586 |
| D Scale-free | pass | Price: x8/x64 **bit-identical, 0.0 max\|diff\|** (a ratio of two identically-scaled prices). x10/x3.7: max\|diff\| 2.22e-16 — well under the 1e-9 tolerance the test asserts, with matching NaN masks. Volume: x8/x64/x10/x3.7 **all bit-identical, 0.0 max\|diff\|** — `np.sign` of a scaled diff reads only the sign bit, so any positive scalar is exact, not just powers of two. `0 < 899 fires < 900` and 899 distinct values rule out a constant column |
| E Attribution | **SHIP** | `VSR`: max\|ρ\| **0.2314** vs `efi_norm` (manifest, n=397,771); per-frame max median \|ρ\| **0.2261** vs `efi_norm`, 0.0% of frames ≥0.90; pooled n=398,760, 687 comparators (329 compute_all + 358 manifest), 0 degenerate columns. Against `compute_all` only: max\|ρ\| 0.2008 vs `aobv_AOBV_SR_2`. Run `is43-vol_sign_rev-345f250e`, 89 ALTPORT-1 frames, 398,849 pooled bars, canary (AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS) bit-equal. Recorded in `docs/gate_e_ledger.csv`, measured 2026-11-08 |
| F Suites | this repo only; parent repo (`Backtesting`) and Gate E are run by the launcher in clean worktrees | `python -m pytest -q` (this session, pre-ledger-record): **3 failed, 4218 passed, 83 skipped** — the 3 failures are all pre-existing/expected: `test_pine_coverage_csv.py` (known break, untracked `docs/pine/` corpus — see CLAUDE.md "Known breaks"), `test_altrepo_talib_csv.py` (needs the sibling `../AlternativeRepos` checkout), `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (this port's row is owed — a future receipt session records it) |

## Wiring

`Category` **274 → 275** (`volume` **30 → 31**); `df.ta.<name>()` accessor count **282 →
283**. Touch points: `pandas_ta/volume/vol_sign_rev.py` (module),
`pandas_ta/volume/__init__.py` (export), `pandas_ta/__init__.py` → `Category["volume"]`
(discovery), `pandas_ta/core.py` → `AnalysisIndicators.vol_sign_rev` (accessor),
`tests/test_vol_sign_rev.py` (tests). `README.md`'s headline and `volume (31)` row, and
`docs/IndicatorDictionary.md` (regenerated), both updated and checked by
`tests/test_readme_counts.py`. `tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` and
`CATEGORY_BUCKETS["volume"]` updated to match (274 → 275, 30 → 31).

## Receipt

Gate E ran on the port at commit `04200f8` (`pandas_ta_src_sha1` `8b3a7d60a641f2d9bd388cac847eb034fd03cd1d`),
run `is43-vol_sign_rev-345f250e`, recorded in `docs/gate_e_ledger.csv` 2026-11-08. Column
`VSR`: max\|ρ\| **0.2314** vs `efi_norm` (manifest, n=397,771), per-frame max median \|ρ\|
**0.2261**, verdict **SHIP** (band `r3-perframe-0.90`: pooled and per-frame both well under
the 0.76 ship line, let alone the 0.90 struck line). This matches the prototype's own
measurement in the issue text (max |ρ| 0.2314 vs `efi_norm`, top-5 per-frame max median
0.2260) to 4 decimal places — the port reproduces the prototype's attribution, not just its
formula. Per the issue's "Done when" and CLAUDE.md's Gate E bands: **shipped**, no
column removed.
