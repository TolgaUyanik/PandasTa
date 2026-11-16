# `bos_causal` — measurement receipt (issue #332)

> **Issue #332 is NOT closed by this change.** It asks for an in-place fix of `bos` and `choch` under their
> own column names. This ships a sibling indicator instead (see "Departure from issue #332" below); `bos`
> and `choch` still look ahead. No owner approval of the sibling route is on record: it is owed.

Source: this repo (`trend/bos.py`, `trend/choch.py`, `trend/swing_equilibrium.py::_confirm_pivots`, MIT).
Not a Pine port. Script: `docs/measure_bos_causal.py`. Tests: `tests/test_bos_causal.py`.
All numbers below are SYNTHETIC tick-rounded frames (16 frames x 2,000 bars = 32,000 bars; 3,743 bars
whose high or low equals the previous bar's). **Gate E has not been run** — it is owed on the way to `dev`
(no row in `docs/gate_e_ledger.csv`).

## What it is
`bos` and `choch` flag swings with `rolling(L, center=True)`, so they read `(L-1)//2` bars ahead.
`bos_causal` registers a swing at bar `j + k` (`k = (L-1)//2`, `left = L-1-k`):
`high[j] == max(high[j-left..j+k])` and no `high[i] == high[j]` for `i` in `(j, j+k]` (rightmost tie wins;
lows mirror). `HH`/`LL` fire on that bar vs the previous confirmed swing; `BULL`/`BEAR` compare `close[t]` with
the last swing confirmed at or before `t`; `CHOCH_*` is `choch`'s trend machine on those swings.
Columns (new names, so `bos`/`choch` and their `BOS_*`/`CHoCH_*` are untouched):
`BOSC_BULL_5 BOSC_BEAR_5 BOSC_HH_5 BOSC_LL_5 BOSC_CHOCH_BULL_5 BOSC_CHOCH_BEAR_5`.

## Gate A — correctness
Bit-equal to an independent reference (`tests/test_bos_causal.py::_ref`) on 8 frames x `L` 4/5/7/9, all six columns.
Double top, triple top, double bottom: exactly one swing each (rightmost).

## Gate B — causality
Future-perturbation probe (rewrite bars after `T`, prefix must not move), first frame, `L` 4/5/7/9:

| L | `bos_causal` | `bos` | `choch` |
|---|---|---|---|
| 4 | 0 | 1 | 1 |
| 5 | 0 | 2 | 2 |
| 7 | 0 | 3 | 1 |
| 9 | 0 | 4 | 1 |

Reach in bars, 40 probe bars. `bos` matches the 1/2/3/4 pinned by `tests/test_bos_lookahead.py`. The `choch`
figures are "at least" values: its trend state resets after each break and its events are ~1-2% of bars, so a
sparse probe can miss a leak (the issue says its reach was unmeasured; this is a first, partial measurement).
`choch` has the same centred-window defect as `bos` (reach >= 1 at every L tried).
Mutant (source read through `importlib`, flag moved to `j`, `exec`'d in memory): live, caught; real module clean.

## Gate C — reachability (pooled 32,000 bars, all 16 frames fire)
BULL 6,258 (19.56%) · BEAR 6,658 (20.81%) · HH 1,995 (6.23%) · LL 1,956 (6.11%) · CHOCH_BULL 546 (1.71%) · CHOCH_BEAR 607 (1.90%).

## Gate D — scale
x8, x64: bit-identical on all 16 frames. x10, x3.7: 0 mismatching cells. `0 < fires < n` per column.

## Overlap on synthetic frames (printed by `docs/measure_bos_causal.py`; not Gate E)
Per-frame median Spearman vs today's centred columns (16 frames): BULL 0.7256 (vs `BOS_BULL`), BEAR 0.7332,
CHoCH_BULL 0.7043, CHoCH_BEAR 0.7062, HH -0.0689, LL -0.0669. The rising edge of `BOSC_BULL_5`/`BOSC_BEAR_5` equals
`SWINGEQ_BOS_BULL_2_2`/`SWINGEQ_BOS_BEAR_2_2` with 0 mismatching bars over the 16 frames (the 2_2 setting shares
k = 2 and the tie rule with L = 5). The earlier analysis figures (0.7361 etc.) came from different random frames.

How to reproduce: Gate A (bit-equal to an independent reference, 8 frames x L 4/5/7/9) and the mutant are
asserted by `python -m pytest tests/test_bos_causal.py`, not printed by the script.

## Gate E — owed
Not run. Per `CLAUDE.md`, a STRUCK result reverts the columns before the release into `main`.

## Not done here
Departure from issue #332, stated plainly: the issue asks to fix `bos`/`choch` in place under their own names.
This change instead ships `bos_causal` beside them (the orchestrating task asked for a new indicator with the five
wiring touch points), so `bos` and `choch` STILL read ahead. Consequently `tests/test_bos_lookahead.py` is kept
(it pins `bos`, which is still true) and `CLAUDE.md` still lists `bos` as open, now with a pointer to `bos_causal`
and a note that `choch` has the same defect. The in-place fix, which changes column values the parent repo's
mined rules match on, remains the owner's call.
