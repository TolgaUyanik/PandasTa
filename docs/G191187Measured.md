# g191_187 — measured (issue #65)

> **Status: Gates A-E cleared (SHIP), this repo's suite green except the pre-existing/owed
> breaks below.**

20-day sum of open-up moves (DTM): Guotai Junan's (2017, "GTJA191", internal quant report, read
via the HKUDS/Vibe-Trading copy, MIT) alpha `#187`, per issue #65's own instruction. Module
`pandas_ta/momentum/g191_187.py`, column `G191_187_20`. Tests: `tests/test_g191_187.py` (16, all
passing). Numbers below: `python docs/measure_g191_187.py`. Environment: this worktree's pinned
pandas/numpy. Measured 2026-11-09.

## Gate A: derivation from the published formula, not the prototype

Issue #65 states GTJA191 alpha `#187`:

    SUM(O<=O1 ? 0 : MAX(H-O, O-O1), 20)

with the issue's own stated scale-free form: "`/close`".

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access are both
unavailable in this worktree, so the issue's own named copy -- HKUDS/Vibe-Trading (MIT) -- was
never read. Everything below is derived from the issue's own stated formula string plus its own
scale-free instruction, per the issue's own rule ("Gate A starts from the source formula, not the
prototype"), then cross-checked against the issue's own prototype
(`docs/issues/screen/ind_screen.py:554-557`):

    @cand("g191_187", "20-day sum of open-up moves (DTM)", G,
          "#187: SUM(O<=O1 ? 0 : MAX(H-O, O-O1), 20)", "/close")
    def _(o, h, l, c, v):
        o1 = delay(o, 1)
        return tsum(pd.Series(np.where(o <= o1, 0.0, np.maximum(h - o, o - o1)),
                               index=c.index).where(o1.notna()), 20) / c

No disclosed interpretation choice was needed -- the issue's own string and the prototype agree
exactly, including the window length and the scale-free conversion. `O1` is read as GTJA's own
`DELAY(O,1)` notation, the same convention the issue's sibling alpha `#93` (already shipped as
`g191_093`) uses for `DELAY(O,1)` identically. Operators, each read directly off the prototype's
own module source (`ind_screen.py:45` DELAY, `ind_screen.py:49` SUM): `DELAY(X,n) = X.shift(n)`,
`SUM(X,n) = X.rolling(n).sum()`, matching the convention every other `g191_*` port in this fork
already relies on. `MAX(a,b)` is read as the POINTWISE `np.maximum`, not the rolling-window
`TSMAX` the same registry also defines -- the issue's own formula names two plain series
arguments, not a series and a window length.

### A measured structural fact: `MAX(H-O, O-O1)` does NOT collapse, unlike its mirror `#93`

The mirror alpha `#93` (`g191_093`, open-DOWN moves) has a `MAX(O-L, O-O1)` that always collapses
to `O-L` under ordinary OHLC consistency, because its down-branch makes `O-O1` negative while
`O-L` stays nonnegative. `#187`'s up-branch has no such asymmetry: `H-O >= 0` always (a bar's
high is by definition `>= ` its open), and `O-O1 > 0` in the up-branch (`O > O1`) -- BOTH terms
are nonnegative, so the `MAX` is a genuine, data-dependent comparison. Measured, not assumed: on a
1,500-bar synthetic OHLC frame (`python docs/measure_g191_187.py`), of **753** up-branch bars,
`H-O` wins at **149**, `O-O1` wins at **604**, and **0** are ties. This matters for Gate B (below):
because the formula does not collapse, the `DELAY` direction changes the OUTPUT'S magnitude
directly through the `O-O1` term, not merely through a branch gate -- so, unlike `#93`'s
forward-DELAY mutant, no dedicated deterministic construction is needed to catch a flipped
`DELAY`.

### Warm-up: a disclosed necessary condition

`O1 = DELAY(O,1)` is undefined at bar 0 (no prior bar). `contribution` (the per-bar ternary
output) is therefore only meaningful from `t >= 1`, masked to `NaN` at bar 0 rather than silently
read as "no up move". `DTM`, a trailing `length`-bar sum, needs `length` CONSECUTIVE meaningful
`contribution` values ending at `t`: true warm-up `min_length = length + 1` -- **21** at the
shipped default (`length=20`), enforced by `verify_series`.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula plus its own scale-free conversion, matching the issue's own prototype line-for-line | A hand-derived 7-bar example (`length=3`) matching the module to float precision (`8/103`, `6/104`, `16/105`, `10/106` at bars 3-6), plus an independent per-bar computation (plain numpy array slicing, not the module's own `.rolling()` calls) spot-checked at the shipped default on a 900-bar frame: `t=300 module=0.09718154613800689 independent=0.09718154613800689`, `t=600` and `t=899` identical to float precision (`python docs/measure_g191_187.py`) |
| B Causality | pass | Future-perturbation sweep (OHLC series jointly rewritten from `j` onward), 34 offsets past the 21-bar warm-up: real module **0 of 34** leaks. Write-shift mutant (final rolling-sum write index `length=20` bars into the future): caught **34 of 34**. Forward-DELAY mutant (`open_.shift(1)` to `open_.shift(-1)`): caught **34 of 34** by the ordinary random sweep -- no dedicated deterministic construction needed, because `MAX(H-O, O-O1)` does not collapse here (above) |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic OHLC series (seed 11, see `docs/measure_g191_187.py:_ohlc`), shipped default: **1,480 of 1,500** bars non-NaN (98.67%), first valid at bar 20 (exactly the structural warm-up boundary, `min_length - 1`). **1,480 distinct values**. Range `[0.050541, 0.243783]`, median `0.141075` |
| D Scale-free | pass | `O1` is linear in `open` (a shift carries no arithmetic); the `open <= O1` comparison is unchanged by a positive rescale; `H-O` and `O-O1` each scale linearly, so their `MAX` scales by the same positive factor; `DTM`, a plain sum, scales linearly; dividing by `close` (scaled by the same factor) cancels it exactly. Measured on the 1,500-bar series: PRICE x8/x64 **bit-identical, 0.0 max\|diff\|** (power-of-two multiplication is exact in IEEE754); x10/x3.7 **within float64 rounding tolerance** (max\|diff\| 8.19e-16 / 5.27e-16). `0 < 1480 fires < 1500` and `1480 > 1` distinct values rule out a constant column |
| E Attribution | SHIP | `gate_e_overlap.py run --module pandas_ta.momentum.g191_187`, run `is65-g191_187-76ca6bdb`, 89 ALTPORT-1 frames, 397,069 pooled bars, 687 comparators (329 compute_all + 358 manifest). `G191_187_20`: max\|rho\| **0.6950** vs `natr` (compute_all, n=397,069); per-frame max median \|rho\| **0.6821** (also vs `natr`); 0.0% of frames >= 0.90. Below the 0.76 ship line -> **SHIP**. Canary (AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS) bit-equal. Ledger: `docs/gate_e_ledger.csv`, measured 2026-11-09. |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Wiring

`Category` **299 -> 300** (`momentum` **74 -> 75**); `df.ta.<name>()` accessor count **307 ->
308**. Touch points: `pandas_ta/momentum/g191_187.py` (module),
`pandas_ta/momentum/__init__.py` (export), `pandas_ta/__init__.py` -> `Category["momentum"]`
(discovery), `pandas_ta/core.py` -> `AnalysisIndicators.g191_187` (accessor),
`tests/test_g191_187.py` (tests). `README.md`'s headline and `momentum (75)` row, and
`docs/IndicatorDictionary.md` (regenerated, `301 -> 302` probed), both updated and checked by
`tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s running tag count updated **644 ->
645 / 287 -> 288 `SF`** (`G191_187_20` probes cleanly at the dictionary's 600-bar synthetic frame
and takes many distinct values, so the generator tags it `SF`), checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match (299 -> 300); no
`CATEGORY_BUCKETS` entry needed (that dict only tracks `trend`/`volatility`/`volume`, not
`momentum`).

`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` -- `g191_187`'s row
is now recorded (`docs/gate_e_ledger.csv`, measured 2026-11-09, run `is65-g191_187-76ca6bdb`).
`mtd_ret` remains owed in the same assertion, pre-existing and unrelated to this port (carried
over from issue #206, per `docs/G191146Measured.md`'s identical note).

## Suite run (this repo, this session)

`python -m pytest -q` (receipt session, after the ledger row was recorded), full suite, default
collection order: **3 failed, 4849 passed, 83 skipped**. `g191_187`'s own tests
(`tests/test_g191_187.py`): **16 passed**. Remaining failures, all pre-existing and unrelated to
this port (CLAUDE.md "Known breaks" plus the owed Gate E ledger row):
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` (now owed only for
`['mtd_ret']` -- `g191_187`'s own row is recorded, see "Gate E" above; `mtd_ret` pre-dates this
session), `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
(needs the sibling `../AlternativeRepos` checkout, absent in this worktree) and
`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` (untracked
`docs/pine/` corpus). No other test regresses.
