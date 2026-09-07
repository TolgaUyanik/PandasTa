# Run summary — 2026-09-07 — `/brutally-honest-review --auto WIRING-1 WIRING-2`

Mode C, Fletcher gate, 3-round cap. Both tasks implemented on the main thread.

| task | status | rounds | files touched | follow-ups |
|---|---|---|---|---|
| WIRING-1 | PASS (fixes applied through round 3) | 3 | `pandas_ta/core.py`, `pandas_ta/overlap/mcgd.py`, `tests/test_wiring_accessors.py`, `README.md`, `CLAUDE.md`, `docs/gen_indicator_dictionary.py`, `docs/IndicatorDictionary.md` | SQZOFF |
| WIRING-2 | PASS (fixes applied through round 3) | 3 | `pandas_ta/volatility/aberration.py`, `pandas_ta/overlap/zlma.py`, `pandas_ta/volatility/ui.py`, `tests/test_wiring_accessors.py` | — |
| WIRING-3 (`mcgd`, user-authorised mid-run) | PASS | with -1 | `pandas_ta/overlap/mcgd.py` | closes TVPTA-7b in the parent repo |

⚠ **The round-3 fixes were not themselves re-gated** — the 3-round cap was reached. Round 3's two
MAJORs (stale README, dictionary recommending dead columns as feed-ready) were applied and verified
by running the suite and re-reading the generated output, but no fourth reviewer saw the result.

## What the reviews changed that the author would not have

1. **Round 1 found the defect class.** WIRING-2 as written fixed `aberration`; `zlma` (every
   `mamode`) and `ui` (`everget=True`) carried the identical module-shadowing bug and still raised.
   Without the review, two indicators stay broken and the task closes as done.
2. **Round 1 found the tests flattered the code.** 18 green tests, not one passing a parameter
   through an accessor. Renaming `swing_length` to `swing_len` in `bos` left the suite green.
3. **Round 2 caught a regression the author introduced in round 1** — a `raise TypeError` on
   `offset` inside a method `strategy()` calls, which broke `df.ta.strategy("overlap", offset=1)`.
4. **Round 3 caught the docs half-fixed** — the README, the file a user opens first, still described
   all three fixed defects as live, and the regenerated dictionary tagged two provably dead `fvg`
   columns `BIN — feed to a model? yes` and listed them as feed-ready.

## Defects found and NOT fixed (registered instead)

| task | defect | why deferred |
|---|---|---|
| **FVGDEAD** | `fvg`'s `IN_FVG_BULL`/`IN_FVG_BEAR` are constant zero by construction — the zone is evicted on the bar that creates it (`trend/fvg.py:46`, `:54`). 0 fires in 12,000 bars over 6 seeds. | Repairing it changes shipped column semantics that mined rules in the parent repo match on; the port protocol gates that behind Gates C/D/E. Round 3 was asked to rule on this scope call and agreed it is correct engineering, not a dodge — conditional on telling downstream, which the dictionary's new *Never fires on the probe* section now does. |
| **SQZOFF** | `squeeze`/`squeeze_pro` raise `ValueError` under any non-zero `offset` (`int` cast over shifted NaNs). Untouched since the fork's first commit. | Upstream defect, unrelated to accessor wiring; found only because the round-3 offset test swept every category. |

The `CONST` classification added to the dictionary generator also surfaced **9 indicators** with
columns that never fire on the synthetic probe. `fvg` is proven structural; the other eight
(`macd_area_divergence`, `rsi_divergence`, `band_cross_retest`, `flag_breakout`, `fvg_sweep_magnet`,
and others) are event-driven columns that may simply need real data — they are listed with
"unregistered, file one" rather than assumed dead.

## Verification

`python -m pytest -q` → **1137 passed, 21 skipped** (before: 1085 / 21).
Two mutation checks confirm the new guards bite: `swing_length`→`swing_len` fails; `offset`→`offsett`
fails.
