# `bos` and `choch` made causal — measured (#332)

Issue #332 (BOS-CAUSAL), parent #7 (owner chose: fix). A bug fix to two shipped modules, not a
new indicator: column names are unchanged, column values change.

**Status:** Gates A-F measured, SHIPPED as a bug fix. Gate E says `BOS_BULL` / `BOS_BEAR` are
STRUCK as near-duplicates of the downstream engine's own causal BOS columns; the owner chose to
ship anyway (2026-11-28), because the alternative is keeping a look-ahead bug in published
columns. `bos` and `choch` predate the Gate E ledger, so no ledger row is added.

| module | columns (unchanged names) | form |
|---|---|---|
| `pandas_ta/trend/bos.py` | `BOS_BULL`, `BOS_BEAR`, `HIGHER_HIGH`, `LOWER_LOW` (`BOS_<swing_length>`) | 0/1 flags |
| `pandas_ta/trend/choch.py` | `CHoCH_BULL`, `CHoCH_BEAR` (`CHoCH_<swing_length>`) | 0/1 flags |

Tests: `tests/test_bos_causal.py` (69 tests); `tests/test_bos_lookahead.py` is deleted (it pinned
the defect). Environment: Python 3.11.2, pandas 2.3.3, numpy 1.26.4. Measured 2026-11-27/28.

## The defect

Both modules flagged swings with `high == high.rolling(swing_length, center=True).max()` (and the
`low` mirror) and wrote the flag on the pivot bar `j`. A centred window at `j` contains bars after
`j`, so every column read `(swing_length - 1) // 2` bars ahead: 1 / 2 / 3 / 4 at `swing_length`
4 / 5 / 7 / 9. Measured for `bos` by the deleted test; for `choch` by the mutant test below
(it used the same two lines; its reach had not been measured before).

## The fix

Source: this repo, `pandas_ta/trend/swing_equilibrium.py` `_confirm_pivots` (MIT), rightmost tie
wins. With `L = swing_length`, `k = (L - 1) // 2`, `left = L - 1 - k`:

```
swing_high[j] is confirmed on bar t = j + k  iff
    high[j] == max(high[j-left .. j+k])  and  high[i] != high[j] for every i in (j, j+k]
swing_low: min, same tie rule
```

`pandas_ta.trend.bos._confirmed_swings` implements it with the same window as before
(`rolling(L)` ending at `t`, candidate `shift(k)`, plus a `rolling(k)` strict check on the bars
after the candidate). `choch` imports the helper. Then, per bar `t`:

- `HIGHER_HIGH` / `LOWER_LOW` fire on the confirmation bar `j + k`, comparing the new swing with
  the previous confirmed one.
- `BOS_BULL` = `close[t] > last swing high confirmed at or before t`; `BOS_BEAR` mirrors it.
- `CHoCH_*`: the same trend state as before (lower high sets down, higher low sets up), updated
  only on confirmation bars; a BOS against the trend fires and resets the trend.

## Gate A — correctness

`test_matches_an_independent_loop_over_the_formula`: a plain per-bar loop over the formula above,
sharing no code with the module, matches the swing series and all six columns exactly, for
`swing_length` 1-9 and seeds 0-4 (45 cases, 400 bars each). Prices are rounded to whole numbers
so ties occur and the tie rule is exercised.

`test_same_swings_as_the_old_centred_window_only_k_bars_later`: on a frame with no tied highs or
lows, the new confirmed swings equal the old centred swings shifted exactly `k` bars later
(`swing_length` 4 / 5 / 7 / 9). `test_a_double_top_confirms_one_swing_on_the_right_hand_bar`:
tops at bars 3 and 5 (`swing_length` 5) confirm one swing, on bar 7; the old window flagged both.

## Gate B — causality

`test_no_column_reads_a_later_bar`: every cut from bar 40 to 149 of a 160-bar frame, bars >= cut
scaled by x1.4 and separately by x0.6, seeds 0-3, `swing_length` 4 / 5 / 7 / 9, each module on
its own. Measured reach: **0** bars on all six columns.

`test_mutant_with_the_old_centred_placement_is_caught`: the module source with the swing written
back on its pivot bar (`.shift(-k)`, exactly the old placement) is exec'd in memory; `choch` gets
the mutant helper injected. Measured reach: **k** = 1 / 2 / 3 / 4 for each module, so the probe
sees the old defect in both.

## Gate C — reachability

89 frames, 398,849 daily bars (the Gate E universe below), default `swing_length` 5, new vs old
module:

| column | new fires | old fires | bars with the same value | frames firing (new) |
|---|---|---|---|---|
| `BOS_BULL` | 77,826 (19.51%) | 44,583 (11.18%) | 91.44% | 89 / 89 |
| `BOS_BEAR` | 61,975 (15.54%) | 33,577 (8.42%) | 92.52% | 89 / 89 |
| `HIGHER_HIGH` | 27,178 (6.81%) | 28,064 (7.04%) | 86.15% | 89 / 89 |
| `LOWER_LOW` | 23,073 (5.78%) | 24,036 (6.03%) | 88.19% | 89 / 89 |
| `CHoCH_BULL` | 6,170 (1.55%) | 3,895 (0.98%) | 99.24% | 89 / 89 |
| `CHoCH_BEAR` | 6,722 (1.69%) | 4,220 (1.06%) | 99.13% | 89 / 89 |

BOS fires about 1.75x (bull) / 1.85x (bear) as often as before. Why is not measured here; the
old rates came from a version that read future bars, so they are not a baseline to match.

## Gate D — scale-free

`test_scale_free`: 1,200-bar frame, x8 / x64 / x10 / x3.7 on all prices give identical frames for
both modules (0/1 flags of price comparisons; max, min and `>` commute with a positive scale).
Every column fires on some bars and not on all (`0 < fires < 1,200`).

## Gate E — attribution

`gate_e_overlap.py run --module pandas_ta.trend.bos|choch --rename-prefix NEW_` (the prefix
keeps the unchanged names from matching themselves). 89 ALTPORT-1 frames, 398,849 pooled bars,
687 comparators (329 `compute_all` + 358 manifest), canary bit-equal on
AKBNK.IS/BIENY.IS/AGHOL.IS/SASA.IS, `degenerate.csv` empty. Candidate sha1: `bos.py`
`6ecd443b348362063832570c206278e9f5a90cf8`, `choch.py` `f5f46002bf5644cebffe92de0162ff5214e7ca0e`.

| column | max \|rho\| | against | n | per-frame max median \|rho\| | verdict |
|---|---|---|---|---|---|
| `NEW_BOS_BULL` | 0.9831038608551811 | `BOS_BULL` | 398,849 | 0.9890445752600676 | STRUCK |
| `NEW_BOS_BEAR` | 0.9749301914143812 | `BOS_BEAR` | 398,849 | 0.9838757793920792 | STRUCK |
| `NEW_HIGHER_HIGH` | 0.6793628317106005 | `FRACTAL_UP` | 398,849 | 0.6795144153774948 | SHIP |
| `NEW_LOWER_LOW` | 0.6262865173763766 | `FRACTAL_DN` | 398,849 | 0.6301500349285093 | SHIP |
| `NEW_CHoCH_BULL` | 0.8493639168429895 | `CHoCH_BULL` | 398,849 | 0.8574156088026604 | DISCLOSE_GAP |
| `NEW_CHoCH_BEAR` | 0.8513465743815888 | `CHoCH_BEAR` | 398,849 | 0.8677186571888174 | DISCLOSE_GAP |

The `against` columns are the downstream engine's own computations, not this repo's modules.
Its `BOS_BULL` / `BOS_BEAR` already use confirmed (causal) 5-bar swings, so the fixed `bos`
nearly restates them. PR #347 (an earlier attempt at this issue, closed unmerged) measured the
same verdicts.

**Decision (owner, 2026-11-28): ship.** Gate E judges whether a NEW column adds information. Here
the columns already exist and are published; the choice is between a look-ahead column and a
causal one under the same name, not between adding a column or not.

## Gate F — suites

Both whole suites, run 2026-11-28 on this branch rebased onto `origin/dev` (c8a3c71):

- PandasTa (`python -m pytest -q`, no `GATE_E_PENDING_OK`, so the ledger check is strict):
  **17,283 passed, 1 failed, 93 skipped.** The one failure is
  `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`, which needs
  the sibling `../AlternativeRepos` checkout and is deselected by name in CI.
- Backtesting (`python -m pytest -q tests/`, the Gate E checkout, `PYTHONPATH` = PandasTa):
  base (`origin/dev`) **2,211 passed, 32 failed, 4 errors, 17 skipped**; this branch
  **2,211 passed, 32 failed, 4 errors, 17 skipped**. Same counts; the failures and errors are
  pre-existing in that checkout and not caused by this change.

Targeted: `tests/test_bos_causal.py` 69 passed.

## Counters touched

None: no module added or removed. `docs/IndicatorDictionary.md` and `docs/indicators/bos.md` /
`choch.md` regenerated (docstring and module length only); `CLAUDE.md`'s look-ahead list updated.
