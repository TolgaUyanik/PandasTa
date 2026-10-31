# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A fork of [twopirllc/pandas-ta](https://github.com/twopirllc/pandas-ta) `0.2.67b`, published as
`github.com/TolgaUyanik/PandasTa`. Upstream shipped ~130 indicators; this fork registers **224** in `Category` — the count that
matters, since `Category` is what `df.ta.strategy()` sweeps — with the extras being
TradingView/Pine and SMC price-action ports. README's "Indicators by category" section
gives the two adjacent counts (232 callable on `df.ta`, plus `drawdown`/`ma` on the module)
and is checked against the package by `tests/test_readme_counts.py`. Do not retype any of
the three here.

Its only consumer is the parent repo, `d:/AwakenAnalytics/Backtesting/`, which pip-installs it from
GitHub and calls it from `backtesting_engine/indicator_engine.py`. Every indicator here is a candidate
**machine-learning feature**, not a chart drawing — that constraint drives the porting rules below.

## Commands

```sh
python -m pytest -q                     # full suite; the 21 skips are explained below; an owed Gate E row fails here (CI into `dev` skips it)
python -m pytest tests/test_tvstop.py -q            # one module
python -m pytest tests/test_tvstop.py::test_name -q # one test
python -m pytest -q -k "causal or scale"            # one concern across modules

pip install -e .                        # editable install into the active env
python docs/gen_indicator_dictionary.py # regenerate docs/IndicatorDictionary.md
```

The 21 skips are the whole upstream correlation suite: `tests/config.py` skips at import when
`data/SPY_D.csv` is absent, and that fixture is gitignored. Port tests are self-contained (synthetic
frames), so a green run does **not** mean the upstream category suites ran.

`Makefile` targets (`make test_ta`, `make test_ext`, …) are upstream leftovers driving `unittest` and
`make init` references a `requirements.txt` that does not exist. Use pytest.

**CI.** `.github/workflows/ci.yml` (job `tests`) runs the full suite on every PR and push to `dev`
and `main`, direct dependencies pinned (pandas 2.3.3 / numpy 1.26.4), with two tests deselected by
name: the one known break (#8) and `test_regenerating_reproduces_the_committed_rows`, which needs
the sibling `../AlternativeRepos` checkout. `.github/workflows/gate-e-guard.yml` (job `guard`, on
`pull_request_target`) runs the BASE branch's copy of `tests/test_gate_e_ledger.py` against the PR,
so a PR cannot loosen the ledger check it needs loosened. Branch protection on `dev` and `main`
requires the checks, **admins included**, with the branch up to date with its base: a direct push
to either branch is refused, so every change goes through a PR. `guard` can be required on a branch
only once the workflow file is on it, because `pull_request_target` reads the workflow from the base.
⚠ Measured 2026-10-31: no `pull_request_target` run has ever happened here, and `main` has no
workflows; per GitHub's current rule (not measured here) that event reads the workflow from the
default branch, `main`, so `guard` does not run for PRs until a release puts it on `main`.

**Merging into `dev`: the merge queue.** GitHub's native merge queue is not available on this
repository, so `.github/workflows/merge-queue.yml` (logic in `.github/scripts/merge-queue.sh`)
builds one from auto-merge. Queue a PR with `gh pr merge <N> --auto --merge`; PRs go roughly in the
order auto-merge was switched on. The queue takes the head of the line, reading only the `tests`
check: behind `dev`, it updates the branch and the update's `pull_request` CI follows; conflicting,
red, with CI waiting for approval, or with CI that never produces `tests`, it switches auto-merge
off with a comment and moves to the next. One PR is tested at a time. `merge-queue.yml` runs on each
push to `dev` and on `workflow_dispatch --ref dev`, which `auto-merge-guard.yml` sends when a PR is
queued; `ci.yml`'s `queue` job runs when a PR's CI finishes, has no owner token, takes red PRs out,
and dispatches `merge-queue.yml` when the next PR needs an update; either runner dispatches it when
a later PR still has no CI run. Branch updates use the owner's fine-grained token (Contents, Pull
requests, Workflows: read/write) as `MERGE_QUEUE_TOKEN` in the `merge-queue` environment, which only
`dev` may use, so a PR's workflows cannot read it. `dev` requires no approving review, so a merged
PR that edits the queue could still reach the token: read every change under `.github/` before
merging it. On #226 an update made with GITHUB_TOKEN started a pull_request run that waited for
approval, and the PR stayed blocked although a dispatched run passed `tests`. A rejected token fails
the step red and drops nothing (a refused update takes a PR out only when it conflicts): renew it.
`auto-merge-guard.yml` switches auto-merge off on any PR whose base is not `dev` (best effort: it
runs after the fact). A cancelled `queue` job on a CI run is expected: its concurrency group keeps
one waiting step and cancels older ones.

## Architecture

**One indicator, one module.** `pandas_ta/<category>/<name>.py` defines a single function named after
the file. Categories: candles, cycles, momentum, overlap, performance, statistics, trend, utils,
volatility, volume.

**Three call styles, one implementation.** `ta.sma(df["close"], 10)` (standard) → `df.ta.sma(10)`
(extension method in `pandas_ta/core.py`, ~227 methods) → `df.ta.strategy(...)` (bulk, multiprocessed
via `Category` in `pandas_ta/__init__.py`). The last two are thin wrappers; fixes belong in the
indicator module.

**Five wiring touch points.** A port that misses one computes correctly and is invisible:

| # | File | Role |
|---|---|---|
| 1 | `pandas_ta/<category>/<name>.py` | the indicator |
| 2 | `pandas_ta/<category>/__init__.py` | package export |
| 3 | `pandas_ta/__init__.py` → `Category` | discovery / `df.ta.strategy` |
| 4 | `pandas_ta/core.py` | `df.ta.<name>()` accessor |
| 5 | `tests/test_<name>.py` | test suite |

Touch points 3 and 4 drifted apart once: 11 indicators (`wavetrend`, `ema_align`,
`ichimoku_ml`, `linreg_channel`, `bos`, `choch`, `fvg`, `halftrend`, `ob`, `zigzag`, `vol_delta`) sat
in `Category` with no accessor, so `df.ta.strategy()` and the affected category runs raised
`AttributeError`. Fixed 2026-09-07 (WIRING-1). `tests/test_wiring_accessors.py` is now the guard:
`test_every_registered_indicator_has_an_accessor` fails the moment a name enters `Category` without a
`core.py` method, and `test_the_eleven_forward_their_parameters_under_the_right_name` spies on the
call to catch a keyword forwarded under the wrong name — the `supertrend` failure mode, which
`hasattr` cannot see.

**Naming is API.** Column names encode parameters (`STOCHk_14_3_3`, `BBU_20_2.0`). Renaming a column
breaks mined strategy rules in the parent repo, which match on these strings.

## The ML feature contract

Read `docs/IndicatorDictionary.md` before adding or judging a column — it is generated by probing the
live package and lists every column's observed form.

- **Causal.** Value at bar `T` reads only bars `<= T`. One upstream column is an ACCEPTED
  exception, by design: `ichimoku` → `ICS_26` (Chikou, `close.shift(-kijun)`).
  `dpo` at `centered=True` also reads `int(0.5 * length) + 1` bars ahead, but since 2026-10-26
  (owner's decision, issue #5) `centered` **defaults to `False`**, so `ta.dpo(close)` and
  `df.ta.strategy()` get the causal form; the look-ahead form is opt-in only. This diverges from
  upstream, whose default is `True` — do not "restore" it. Pinned by `tests/test_dpo_causality.py`.
  ⚠ **This list was described as "complete" until 2026-09-11 and was not.** `ssf` was a third,
  undocumented, and it was a BUG rather than a design choice: its recursion ran `for i in
  range(0, m)`, so at `i = 0` it read `ssf.iloc[-1]` — Python negative indexing, the LAST bar of
  the series — and the recursion propagated that forward. Perturbing only bars ≥ 300 of a 400-bar
  frame moved **bar 0** by 31.4. Fixed and pinned by `tests/test_ssf_causality.py`.
  🔴 **`bos` is a fourth, and it is still OPEN** — all four columns. It flags swings with
  `rolling(swing_length, center=True)`, so it reads exactly `(swing_length - 1) // 2` bars ahead
  (measured: 1 / 2 / 3 / 4 at `swing_length` 4 / 5 / 7 / 9). A bug, not a design choice; fixing it
  changes column values, so **owner's call**. `swing_equilibrium` is the causal model for a fix.
  Pinned by `tests/test_bos_lookahead.py`, which fails if the reach changes in either direction.
  **Do not trust this list as a substitute for measuring.** `ssf` was found by a per-parent
  perturbation probe in MLCOL-1's companion screen, not by reading it; a hand-maintained list
  contains only the cases someone already thought of.
- **Scale-free.** A column that scales with price (`SMA_10`, `MACD_12_26_9`) is not a feature; a tree
  cannot compare it to `close`. Ship ratios and distances. `ichimoku_ml` is the reference conversion:
  5 price lines → 8 scale-free causal columns.
- **Non-redundant.** A column that restates a shipped column double-weights one signal in the miner.

## Porting a Pine indicator

Full protocol: `../Backtesting/docs/TVPTA6-Indicator-Porting-Process.md`. Source corpus:
`docs/pine/` — 2,211 `.pine` files, 46MB, **untracked on purpose** (`.gitignore`). 912 of them
carry `Mozilla Public License 2.0` / `© TradingView` and the rest state no licence at all, so
committing them under this repo's root MIT `LICENSE` would misstate their terms. They were tracked
until 2026-09-07; if you re-add them, add a `NOTICE` first. Summary of the gates a port must
clear:

| Gate | Requirement |
|---|---|
| A Correctness | line-by-line against the Pine source, citing its line numbers. `int/int` is fractional in Pine v6; `ta.stdev(biased=true)` is `ddof=0`. |
| B Causality | a **mutant** test: `importlib`-read the module source, shift a write index earlier, `exec` it in memory, show the real module clean and the mutant caught. Prefix truncation alone proves nothing — it cannot see back-dating. |
| C Reachability | every shipped column fires on real data, with counts stated. |
| D Scale-free | invariant under ×8/×64 (bit-identical) and ×10/×3.7 (tolerance, NaN masks matching), plus `0 < fires < n` so a constant column cannot pass. |
| E Attribution | Spearman ρ of each new column against the engine's `compute_all` ∪ the `ml_features` manifest `1d` (329 + 358 = 687 comparators), over the 89 frozen ALTPORT-1 BIST frames (owner's rules, 2026-10-23). Report the measured max with its sample size. Bands (`r3-perframe-0.90`): STRUCK if pooled \|ρ\| ≥ 0.90 or a top-5 comparator's per-frame median ≥ 0.90 · DISCLOSE_GAP 0.80 ≤ ρ < 0.90 · DISCLOSE 0.76 ≤ ρ < 0.80 · SHIP < 0.76. |
| F Suites | both repos green. |

**Gate E harness:** `../Backtesting/Backtesting/scripts/analysis/gate_e_overlap.py` (Backtesting #107,
merged 2026-10-23; reference `../Backtesting/Backtesting/docs/gate_e.md` on Backtesting `main`).
From `../Backtesting/Backtesting`: `python scripts/analysis/gate_e_overlap.py build` once, then
`run --module pandas_ta.<category>.<name> --name <name>`; outputs land in
`../Backtesting/backtest_results/gatee/<name>/`. `run` refuses a stale cache, but **pandas_ta's
source is not in the stamp**: after editing a function the engine or `ml_features` calls, run
`build --rebuild`. The old `measure_<name>_overlap_full.py` scripts were never committed; only
their outputs survive under `../Backtesting/backtest_results/` (`talib1/`, `altport1/`, `tvpta6/`),
measured against a 492-column engine that no longer exists.

**Gate E ledger — what CI checks instead (2026-10-28).** CI cannot run Gate E (private engine,
827 MB BIST cache, public repo), so each run is recorded in `docs/gate_e_ledger.csv`:
`python docs/gate_e_ledger.py record <run dir> --measured YYYY-MM-DD [--waiver "#N"]`. The harness
must import a `pandas_ta` tree byte-identical to the one you record into: `record` compares the run's
`pandas_ta_src_sha1` with this tree, and refuses non-default parameters, a universe other than the
89 frames, a comparator set other than 687, or a canary that is not bit-equal.
`tests/test_gate_e_ledger.py` fails when a `Category` indicator needs a row and has none (anything
outside the 233 frozen with their columns in `docs/gate_e_grandfathered.json`, or a frozen one
whose columns grew), when a row's module sha1 or output fingerprint moved after the run, when a new
indicator has no `tests/test_<name>.py` with a `mutant` and a `scale` test, or when a STRUCK row
lacks its waiver. A waiver in `ALLOWED_WAIVERS` names the exact measurement (issue, module sha1,
output fingerprint); today only `pfe` #23 and `kalman_trend`'s `KFT_VEL` #22 (owner, 2026-10-28).

**Owed, not failed, on the way to `dev` (owner, 2026-11-01).** Contributors cannot run Gate E, so
`ci.yml` (PRs into `dev`, pushes to it, manual runs off `main`) and `gate-e-guard.yml` (PRs into
`dev`) set `GATE_E_PENDING_OK=1`: a measurement that is owed (no row for an indicator that needs
one, a deleted row, or a row whose module, output or columns moved since its run) is a skip whose
reason starts "Gate E owed", listed in the run summary under "Gate E owed"; the owner runs Gate E
and records the row later. Toward `main` (a release PR, a push to `main`) and on every local run the
variable is not `1` and these fail, so a release needs every row. Strict everywhere: a waived STRUCK
column whose code or output moved or whose row was deleted, a STRUCK row without its waiver, a
hand-edited verdict, and missing Gate B/D tests. Until the owner records it, `dev` may carry an
unmeasured column that Gate E would strike; if its run is STRUCK, the column is reverted (or waived)
before the release, whose PR into `main` fails until then.

The dominant historical defect is **a claim written before it was measured** — 17 of 18 candidates
failed first review, almost none on the mathematics. Every sentence containing *only, never, always,
every, all, identical* or a specific count must correspond to a run. Deleting an over-correlated
column you just built is the expected outcome, not a failure (`tvstop`'s `TVS_DIST`,
`flag_breakout`'s `FLAG_POLE_ATR`, `range_profile`'s `RPO_OSC` were all built, measured, deleted).

Port test modules carry an unusually heavy docstring: what is pinned, in order of how much it would
hurt to lose, with the measured numbers. Match that when adding one — see `tests/test_tvstop.py`.

## Known breaks

🔴 **One test fails on a clean checkout, and it is not flaky.**
`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` asserts that every
`<path>:<n>` citation in `docs/pine_builtin_coverage.csv`'s audit evidence resolves to a real
file. It does not: the first failing row is `supertrend`, citing `RA2vGpkA-ta.pine`. **The cause
is `8d8f705`, which untracked the 2,211-file `docs/pine/` corpus for licensing reasons** — 912 of
those files are MPL-2.0 under a root MIT `LICENSE`. The citations were never updated, so the
guard now demands files this repo deliberately does not carry, and it will fail for every person
who clones it.

Full suite as of 2026-09-12: **1 failed, 3197 passed, 24 skipped**.

Neither fix is small, which is why this is recorded rather than patched: re-adding the corpus
reverses a licensing decision, and rewriting the guard to accept unresolvable citations removes
the only thing standing between "audited" and "asserted". **Owner's call.**

Separately, two indicators (`up_and_down_volume`, `volume_delta`) are **not probed** —
they need a lower-timeframe frame the single-frame harness cannot synthesise — and the generated
*Known breaks* section says so rather than counting them either way. Verify with
`python docs/gen_indicator_dictionary.py`, whose *Known breaks* section is generated from a live
probe, not hand-maintained.

Fixed 2026-09-07 (WIRING), kept here because the second one is a trap worth recognising:

- `mcgd` — used `Series.append`, removed in pandas 2.0. Now `pd.concat`.
- `aberration`, `zlma` (every `mamode`), `ui` (`everget=True`) — all wrote
  `from pandas_ta.overlap import sma`, which binds the **submodule** while pandas_ta is still
  importing itself, so the call raised `TypeError: 'module' object is not callable`. **Import a
  helper from its own module** (`from pandas_ta.overlap.sma import sma`), never from the package.
  `test_no_module_shadows_a_function_name_anywhere_in_the_package` scans for the whole class.

**FVGDEAD is closed (2026-09-07).** `fvg`'s `IN_FVG_BULL`/`IN_FVG_BEAR` are repaired and fire at
22.17% / 19.85% on real data. The original "constant zero by construction" diagnosis was measured on
synthetic continuous-float frames and was wrong on real prices: the old loop retained a zone only
while `close <= zone_high`, true on an exact tie, and 86,415 of 408,253 BIST daily bars (21.17%)
close exactly at an extreme — so the columns fired at 4.63% / 3.51%, driven by tick rounding rather
than by structure. Gates C/D/E cleared (Gate E max |ρ| 0.6390 / 0.5962, under the 0.76 ship line);
evidence in the four `fvg_*` CSVs under `../Backtesting/backtest_results/tvpta6/`. The script
that produced them was never committed; GATEE-3 re-ran the four columns on the new harness and
they stay SHIP (Backtesting #107).

What is still open is **FVGENG**, tracked in the Backtesting repo since 2026-09-07: the engine kept three private copies of the same
loop. ⚠ The delegation of two of them to `pandas_ta.fvg` lived in an engine version that was
never committed (Backtesting #107): today `indicator_engine._calculate_fvg` (`indicator_engine.py:398`)
is its own loop again. Measured in #107 (`gate_e_acceptance.py fvg`): its `FVG_BULL`/`FVG_BEAR`
match the module bit-for-bit on every frame, its `IN_FVG_*` do not (ρ 0.061 / 0.019 on AKBNK).
`speedy_indicators` was not re-checked. The third copy — `deploy/app/paper_trading/paper_trading.py:~804`,
inside the live container — is unchanged behind the TRADING FREEZE. **Do not add a fourth copy: import the
function.**

## Porting a TA-Lib indicator

Done once, as **TALIB-1** (2026-09-08): the ten `port` rows of
`../AlternativeRepos/altrepo_talib.csv`. Same five touch points, same Gates A-F; Gate A's
citation becomes the TA-Lib C function name instead of a Pine line number. Measurements,
per indicator: `docs/TalibPortsMeasured.md`. Tests: `tests/test_talib1_ports.py`.
Overlap outputs: `../Backtesting/backtest_results/talib1/`. The harness script was never committed;
GATEE-3 re-ran 8 of its 14 columns on the new harness (Backtesting #107; see Gate E above).

Four things worth knowing before touching any of it:

* **`talib` is a DEV-ONLY dependency** (`setup.py`, `extras_require["dev"]`). It is the
  Gate A oracle and must never be imported by shipped code -- the fork's only consumer
  pip-installs it without TA-Lib. `test_no_shipped_module_imports_talib` pins the
  complete set of modules that do import it, which is two UPSTREAM files
  (`candles/cdl_pattern.py`, `momentum/dm.py`) behind `if Imports["talib"]`.
* **Seven of the ten are one state machine**, in `pandas_ta/cycles/_hilbert.py`, not
  seven algorithms. It has TWO warm-ups -- 12 bars for the lookback-32 read-outs
  (`HT_DCPERIOD`, `HT_PHASOR`, `MAMA`) and 37 for the lookback-63 ones (`HT_DCPHASE`,
  `HT_SINE`, `HT_TRENDLINE`, `HT_TRENDMODE`). Using 12 everywhere reproduces
  `HT_DCPERIOD` EXACTLY and leaves `HT_TRENDLINE` wrong by 0.18 as a transient that
  decays to zero by bar ~700, so it passes any check run on the tail.
* **The Hilbert taps are summed in TA-Lib's order on purpose.** The algebraically
  identical one-expression form is wrong by 1.1e-2 on MAMA, because MAMA's clamped alpha
  amplifies a 1-ulp difference in an ill-conditioned `atan`.
* **TA-Lib's price-level outputs are not features.** `HT_TRENDLINE`, `MAMA`, `FAMA` and
  `SAREXT` ship as percent distances; the levels are behind `raw=True` and are registered
  nowhere. `BETA` needs a benchmark series, so it is out of `Category` AND in
  `strategy`'s exclusion list.

## Open work

Local tracker: `docs/issues/` — **gitignored, so it exists only on the owner's machine**; a clone
does not have it. One file per issue, index and status conventions in `docs/issues/README.md`. `TODO.md` was removed 2026-10-20 after its open sections were copied into
issues; finished work is in `docs/CompletedWork.md`, which is also where the PINEBI verdict-count
table now lives (`tests/test_pine_coverage_csv.py` asserts it there).

## Commit conventions

`<type>(<scope>): <what and why>` — e.g. `feat(trend): port 7YXrxMjV Flag Pattern Breakout as
flag_breakout`, `fix(trend): tvstop -- delete TVS_DIST on the overlap measurement`,
`docs(range_profile): round 2 -- name DI-5b, state the floor/range-guard interaction`. Scope is the
category or the indicator. Review rounds are numbered in the subject.
