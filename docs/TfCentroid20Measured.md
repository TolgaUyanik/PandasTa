# Temporal Centroid of Squared Returns — measured (`tf_centroid_20`)

> **Status: Gates A, B, D, E measured (pass — SHIP). Gate C synthetic + real-data fire count
> from the Gate E run. Gate F: this repo's suite has 3 failures, 2 pre-existing and unrelated
> plus 1 new and expected — caused by this port, not a regression (see below); Backtesting not
> run here.**

`TFCENTROID_20 = sum(t * ret^2) / sum(ret^2)` over the last 20 bars, `ret` = simple returns,
`t = 0..19` rescaled to `0..1` (oldest bar = 0, current bar = 1). Issue
[#116](https://github.com/TolgaUyanik/PandasTa/issues/116). Module
`pandas_ta/statistics/tf_centroid_20.py`, tests `tests/test_tf_centroid_20.py` (14).
Found by the 2026-10-24 library catalog screen, round 2.

## Source

TSFEL (Fraunhofer Portugal AICOS, BSD-3-Clause),
https://github.com/fraunhoferportugal/tsfel, `tsfel/feature_extraction/features.py`
`calc_centroid`:

```python
time = np.arange(0, len(signal))
energy = np.sum(np.power(signal, 2))
t_energy = np.dot(time, np.power(signal, 2))
return t_energy / energy if energy != 0 else 0
```

Existence, not evidence (per the issue's framing of the library catalog screen): this
is a library function name and formula, not a published, evaluated trading signal.
Prototyped, scale-free, at `docs/issues/screen/ind_screen_r2.py:209-213` (candidate
`tf_centroid_20`, local to the owner's machine, `docs/issues/` is gitignored):

```python
t = np.arange(20) / 19
roll(ret(c), 20, lambda W: (W ** 2 @ t) / sum(W ** 2))
```

where `ret(c) = c / c.shift(1) - 1` and `roll` applies the lambda to causal,
oldest-first, 20-bar windows.

## What differs from TSFEL

| | TSFEL `calc_centroid` | `tf_centroid_20` |
|---|---|---|
| `t` | `0..len(signal)-1`, raw bar index | `0..length-1` rescaled to `0..1` |
| `signal` | any 1-D array the caller passes | `length`-bar simple returns of `close` |
| zero-energy fallback | returns `0` | returns `NaN` |
| scale-free | no — grows with `length` and with the signal's own units | yes — a bounded `[0, 1]` ratio |

The rescaled `t` is what the prototype calls "scale-free form" and is the reason this
column does not need a `length`-dependent interpretation: `0.5` always means "energy
evenly spread across the window," regardless of `length`.

**The zero-energy fallback is deliberately not carried.** TSFEL returns a literal `0`
for a silent signal, which is indistinguishable from "all the energy sits at the oldest
bar" (`t=0`). This fork's convention (`maxvol_adv`'s zero ADV, `entropy`'s `sdiv`) is to
never emit a magic number for an undefined ratio: `tf_centroid_20` returns `NaN`
instead. Reaching it needs `length` consecutive identical closes (all-zero returns),
which `test_zero_energy_window_is_nan_not_zero` exercises directly.

## A bug Gate D's own environment caught, not the column itself

The first draft used `close.pct_change()` with pandas' default `fill_method="pad"`,
which **forward-fills a NaN close before differencing** — a real data gap would have
been silently padded over instead of propagating as `NaN`, with no FutureWarning read
before it was caught (pandas 2.3.3 has already deprecated the default, but it is still
the default). Fixed to `close.pct_change(fill_method=None)`, matching the "a NaN bar
blanks itself and the warm-up that follows" convention every other port in this fork
uses. `test_warmup_and_nan_propagation` pins the gap-blanking shape directly: a single
NaN close at bar 500 blanks `[500, 520]` (21 bars: the bar itself, the `length-1` windows
still containing it, and the one extra from the tainted return at 501) and bar 521
onward is clean.

## Gates

Environment: Python 3.11.2, pandas 2.3.3, numpy (pandas-ta's pinned version), no TA-Lib
needed for this module. Synthetic numbers are from `tests/test_tf_centroid_20.py`'s
`_walk()`: 1,200 bars, GBM-like log-returns `N(0, 0.02)`, seed 11, tick-rounded to 2dp,
`s0=100`.

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass — checked against the TSFEL source formula (not the prototype) and an independent loop | `test_hand_computed` (hand-computed 4-bar window, length=4); `test_matches_an_independent_loop`, a bar-by-bar Python loop reproducing `sum(t*ret^2)/sum(ret^2)` directly from the formula, `rtol=1e-12` against the vectorized module over 1,180 bars; `test_bounded_0_1`, every finite value in `[0, 1]` (true by construction: a convex combination of `t` values, which live in `[0, 1]`) |
| B Causality | pass | Future-perturbation at 31 offsets (`j = 60..1094` step 34), two futures per offset (an independent walk, and the same walk ×1000): real module leaks at **0 of 31**. One one-bar look-ahead mutant (`close.shift(-1)` feeding the return calc, via `importlib`-read source + `exec`) is shown live (differs from the real module) then caught at **31 of 31** |
| C Reachability | synthetic + real | Synthetic, 1,200-bar walk: 1,180 of 1,180 post-warm-up bars finite (20-bar warm-up, matching `length`), **1,180 distinct values**, range **0.2270 .. 0.7640**, mean **0.5007**, median **0.5015**. Real, from the Gate E run below: **397,069 of 398,849 pooled bars finite** (non-zero on all of those), 89 frames |
| D Scale-free | pass | Price ×8 / ×64: **bit-identical** (measured exactly, not assumed — the returns ratio cancels the uniform price scale before squaring). Price ×10 / ×3.7: max relative error **6.633e-15** / **6.076e-15** (test asserts `<= 1e-13`, two orders of margin above the measured value). NaN masks match in all four. `0 < fires < n`: 1,180 of 1,200 (not constant: 1,180 distinct values, see Gate C) |
| E Attribution | **measured, 2026-10-30, SHIP** — run via `gate_e_overlap.py run --module pandas_ta.statistics.tf_centroid_20`, recorded in `docs/gate_e_ledger.csv`. `TFCENTROID_20`: max \|ρ\| **0.5943** vs `ATR_Ratio_5_20_Pctl` (manifest comparator set, n = 391,818 pooled bars), per-frame max median \|ρ\| **0.5946** (89 frames, 0% of frames ≥ 0.90) → verdict **SHIP** (bands: SHIP < 0.76 pooled and per-frame-median). 687 comparators (329 `compute_all` + 358 manifest), 398,849 pooled bars across 89 ALTPORT-1 frames, canary bit-equal on AKBNK.IS/BIENY.IS/AGHOL.IS/SASA.IS. Against `compute_all` alone: max \|ρ\| 0.4919 vs `CHOP`, n = 396,311. This matches the issue's prototype-stage number (0.5943) almost exactly — the port reproduces the prototype's measured overlap |
| F Suites | this repo: 3 failed / 3,272 passed / 83 skipped at this branch's head. **Two are pre-existing, unrelated to this port**: `test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` (needs the sibling `../AlternativeRepos` checkout) and `test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` (CLAUDE.md's documented known break, `docs/pine/` untracked) — both fail identically on a clean checkout of this branch's base, before this port. **The third is new and expected, caused directly by this port, not a regression**: `test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` fails because `tf_centroid_20` just entered `Category` with no ledger row — it has none because Gate E is deferred to the launcher; the ledger row is added by the Gate E receipt session once that run exists. Before this port, that test is green. Backtesting's suite not run from this session (no access to that worktree) |

## Wiring

`pandas_ta/statistics/tf_centroid_20.py` (module), `pandas_ta/statistics/__init__.py`
(export), `pandas_ta/__init__.py` → `Category["statistics"]` (discovery), `pandas_ta/core.py`
→ `AnalysisIndicators.tf_centroid_20` (accessor), `tests/test_tf_centroid_20.py` (tests).
`README.md` and `docs/IndicatorDictionary.md` regenerated/updated: `Category` 237 → 238,
`df.ta.<name>()` 245 → 246, `statistics (12)` → `statistics (13)`.
`docs/MLCompanionContract.md`'s dictionary-derived counts: 570 → 571 tagged columns,
216 → 217 `SF`. `tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` 237 → 238 (its own
per-bucket counts, `trend`/`volatility`/`volume`, are untouched by this port).

## Closed

Gate E measured 2026-10-30 on the port itself (not the prototype): max \|ρ\| 0.5943,
well inside SHIP (< 0.76 pooled and per-frame-median). Shipped as-is; no revert needed.
