# WIRING-1 — add the 11 missing `core.py` accessors

Status: **PASS** (3 review rounds). Files: `pandas_ta/core.py`, `pandas_ta/overlap/mcgd.py`,
`tests/test_wiring_accessors.py`.

## Implementation

Eleven accessors inserted into their category blocks, each following the house shape
(`_get_column` per price input, named params forwarded, `_post_process(result, **kwargs)`):
`wavetrend` (momentum); `ema_align`, `ichimoku_ml`, `linreg_channel` (overlap); `bos`, `choch`,
`fvg`, `halftrend`, `ob`, `zigzag` (trend); `vol_delta` (volume).

`ob` and `vol_delta` resolve `open_` via `kwargs.pop("open", "open")`, as `cdl_doji` does.
`ichimoku_ml` is the one that needed judgment: its indicator declares no `offset` and its lengths
carry real defaults (9/26/52), so the accessor forwards only lengths the caller set, and applies
`get_offset` + `.shift()` + the fill block itself.

`mcgd`'s `Series.append` → `pd.concat` (WIRING-3) was authorised mid-run because the acceptance
criterion says "no `exclude` list", which `mcgd` made unreachable.

## Round 1 — REVISE

> **MAJOR** — no test passes a non-default parameter to any accessor, so the entire defect class
> the brief warns about — the `supertrend` precedent of silently discarded kwargs — is unpinned.
> Change `swing_length=swing_length` to `swing_len=swing_length`: `bos()` swallows the unknown name
> in `**kwargs`, returns default-length output, and all 18 tests stay green.

Applied: `test_the_eleven_forward_their_parameters_under_the_right_name` spies on the function
`core.py` calls and asserts each keyword arrived under the declared name and value, plus
`test_non_default_parameters_change_the_output`. **Mutation-verified**: the exact `swing_len`
rename now fails the suite; reverted after checking.

> **MINOR** — the "acceptance criterion" test calls `df.ta.strategy(cores=0)`, the serial branch;
> the default multiprocessing path is never executed.

Applied: docstring downgraded to "serial form"; added
`test_full_strategy_runs_on_the_default_multiprocessing_path` calling bare `df.ta.strategy()`.

> **MINOR** — `ichimoku_ml` silently discards `offset` and mutates the caller's kwargs.
> **NIT** — placement drift: `linreg_channel` after `ma_disparity`, `ichimoku_ml` ahead of `ichimoku`.

Applied: local `params` dict; both methods moved beside their siblings.

## Round 2 — REVISE

> **MAJOR** — the round-1 `offset` fix installed a `raise TypeError` inside a method a bulk runner
> calls. `df.ta.strategy("overlap", cores=0, offset=1)` now aborts the entire run. Every sibling
> whose indicator lacks `offset` swallows it and continues.

**A regression I introduced while fixing a nit.** Reproduced, then fixed properly: the accessor
declares `offset=None` and applies the shift itself, which is bit-identical to what the ten
siblings do internally. Round 3 confirmed the equivalence independently.

> **MINOR** — `offset`, the one keyword all eleven forward by hand, is never passed by any test.

Applied: `test_offset_is_honored_by_every_new_accessor` over all eleven. Mutation-verified
(`offset=offset` → `offsett=offset` in `bos` fails).

> **MINOR** — the shadow scan only flags a module whose function is re-exported at package top level.
> **NIT** — `mcgd` pinned only by a column-name prefix.

Applied: predicate now also interrogates the shadowing module; added
`test_mcgd_concat_preserves_the_series_shape_and_first_value` (length, index, no NaNs, seed value).

## Round 3 — REVISE

> **MAJOR** — the README still says eleven indicators have no accessor, that `df.ta.strategy()`
> raises `AttributeError`, and that `mcgd`/`aberration` break on every call. You fixed the docs in
> the two files a reviewer named and skipped the one a user opens first.

Applied: the "Standalone-only" section deleted, `exclude=[...]` examples cleaned, Known-breaks block
rewritten, indicator counts reconciled (199 in `Category`, 201 probed).

> **MINOR** — `ichimoku_ml` honours `offset` but not `fillna`/`fill_method`, unlike its siblings.
> **MINOR** — `test_strategy_accepts_offset_for_every_indicator` runs one category despite its name.
> **NIT** — fvg line references straddle only one branch.

Applied: fill block added; the offset check folded into the parametrized category test (four
categories) and the over-named test deleted; line references corrected to `:46` / `:54`.

**Found while applying:** running every category with `offset=1` exposed that `squeeze` and
`squeeze_pro` raise `ValueError: cannot convert float NaN to integer` under any non-zero offset —
upstream, untouched since the first commit. Registered as **SQZOFF**; excluded from that test with
the reason inline.

## Verification

- `python -m pytest -q` → **1137 passed, 21 skipped** (was 1085/21 before this task).
- `df.ta.strategy()` completes with no `exclude` on 600 bars, serial and multiprocessed.
- Mutation checks: `swing_len` rename fails; `offsett` rename fails.
