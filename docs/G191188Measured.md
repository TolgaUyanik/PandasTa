# g191_188 — measured (issue #83)

> **Status: Gates A-D cleared and wired; Gate E pending, run by issue-solver after this
> session. A later receipt session records the ledger row and fills in the measured numbers.
> This repo's suite is green except the two PRE-EXISTING breaks and the EXPECTED owed-Gate-E
> ledger failure THIS port creates -- all three itemised under Gate F.**

Range vs its EMA: Guotai Junan's (2017, "GTJA191", internal quant report) alpha `#188`, per
issue #83, which attributes its copy of the report to HKUDS/Vibe-Trading (MIT). Module
`pandas_ta/volatility/g191_188.py`, column `G191_188_11_2`. Tests: `tests/test_g191_188.py`
(30, all passing). Numbers below: `python docs/measure_g191_188.py`. Environment: pandas
2.3.3 / numpy 1.26.4, printed by the measure script's last line. Measured 2026-11-11.

## Gate A: derivation from the published formula, not the prototype

Issue #83 states GTJA191 alpha `#188`:

    (H-L-SMA(H-L,11,2))/SMA(H-L,11,2)*100

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access are both
unavailable in this worktree, so the issue's own named copy -- HKUDS/Vibe-Trading (MIT) -- was
never read. Everything below is derived from the issue's own stated formula string, per the
issue's own rule ("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype (`docs/issues/screen/ind_screen.py:560-563`):

    @cand("g191_188", "range vs its EMA", G,
          "#188: (H-L-SMA(H-L,11,2))/SMA(H-L,11,2)*100")
    def _(o, h, l, c, v):
        e = sma(h - l, 11, 2)
        return 100 * sdiv(h - l - e, e)

The string and the prototype agree on both parameters (`n = 11`, `m = 2`) and on the shape of
the expression. Operators, each read directly off the prototype's own module source: `H`, `L`
= high, low (no other OHLCV field is read); `SMA(A,n,m)` -- NOT this fork's plain
simple-moving-average `sma` but GTJA's own recursive smoother, called out explicitly in the
prototype's own docstring (`ind_screen.py:57-59`): `Y[t] = (m*A[t] + (n-m)*Y[t-1])/n`, an EMA
with `alpha = m/n`, here `2/11`; and the prototype's own `sdiv` (`ind_screen.py:41-42`,
`_fin(a / b)`), which replaces `+-inf` with `NaN` on the division, BEFORE the `* 100`. This
port spells the `.replace()` in the same position, so the two agree bar for bar. The GTJA
`SMA` is implemented as `ewm(alpha=m/n, adjust=False, min_periods=n)` -- the spelling the
nearest sibling port in this same category writes for the identical operator
(`pandas_ta/volatility/g191_109.py:101`, read in this session). No fork-wide claim about the
other `g191_*` ports is made here, since none was measured.

A SECOND convention rides in with `adjust=False` and the source string does not state it: the
recursion `Y[t] = (m*A[t] + (n-m)*Y[t-1])/n` is undefined at its first bar, and `adjust=False`
seeds it with `Y[first] = A[first]`. `min_periods=11` masks the output but does not remove that
seed's influence -- its weight at the first REPORTED bar is `(9/11)**10`, about 0.15. The seed
is inherited from the prototype (which uses the same `ewm`) and from `g191_109`, not derived
from the formula, and nothing in this session can see a different initial condition: Gate A's
independent per-bar replay is seeded the SAME way
(`docs/measure_g191_188.py:_independent_loop`), so it validates the RECURSION, not the seed.
Disclosed here rather than left implicit.

The candidate's own `candidates.csv` row carries an EMPTY `conv` cell
(`docs/issues/screen/candidates.csv:65`): there is no extra scale-free conversion to apply,
because a quantity divided by its own EMA is already scale-free (derived under Gate D).

### The one reading that had to be fixed, and the measurement that settles it

The string's tail `/SMA(H-L,11,2)*100` admits a second parse, `/(SMA(H-L,11,2)*100)` -- the
`*100` scaling the DENOMINATOR instead of the finished ratio. Standard left-to-right
precedence for `/` and `*` gives the shipped reading, and the prototype writes it explicitly
(`100 * sdiv(h - l - e, e)`, `ind_screen.py:563`: it divides by `e` alone). The rejected
reading was measured rather than dismissed: over the **1,490** bars both define on the
1,500-bar walk, the ratio of the two columns is `10000.0` to within float64 (min
`9999.999999999996`, max `10000.000000000004`), **Spearman 1.0**, **0 bars change sign**, and
**0 of 1,490** bars are bit-equal. So it is a pure constant rescale: the two readings order
the bars identically and differ only in magnitude. Pinned by
`tests/test_g191_188.py::test_the_rejected_precedence_reading_is_a_constant_rescale`, which
asserts the bit-equal count equals the count of exact zeros (0 on this frame) so the test does
not pin a platform-dependent float count.

### Agreement with the prototype, measured three ways

On the 1,500-bar synthetic walk (seed 11, `docs/measure_g191_188.py:_walk`):

| compared against | shared bars | max \|diff\| | bit-equal |
|---|---|---|---|
| the retyped prototype expression with the fork's `min_periods=11` | 1,490 | `0.0` | 1,490 of 1,490 |
| the prototype's OWN smoother (no `min_periods`, `ind_screen.py:59`) | 1,490 | `0.0` | 1,490 of 1,490 |
| the REAL `g191_188` candidate out of the owner's (gitignored) screen registry | 1,490 | `0.0` | 1,490 of 1,490 |

The prototype's own `sma` omits `min_periods`, so it fires on **1,500 of 1,500** bars where
this port fires on **1,490** -- and it is bit-equal to the port on every bar they share. The
10-bar head of this port's warm-up is therefore this FORK's convention, not the source's, and
it is reported rather than claimed as the formula's.

### Warm-up: a disclosed necessary condition

`r = H - L` needs no history, and an `H == L` tie is a valid `0.0`, not a NaN, so `r` is
defined on every bar. `e = SMA(r, 11, 2)` carries `min_periods=11`, so it needs 11 valid `r`
values and is defined from `t >= 10`. The final expression is pointwise, so `G191_188` is
defined from `t >= 10`: `min_length = smooth_length` = **11** bars, enforced by
`verify_series`. Measured first valid index: **10**, exactly the structural boundary.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived from the issue's own stated formula, matching the issue's own prototype bit-for-bit | An 8-bar hand-derived example at `smooth_length=3, smooth_weight=1` (`alpha=1/3`), bars 2-7 `[-18.181818181818187, 34.99999999999999, -6.896551724137921, 34.679334916864626, -16.638078902229843, 36.38914873713752]`, printed by `python docs/measure_g191_188.py` alongside the intermediate `r` and `e` series; an independent per-bar replay at the shipped defaults in plain Python scalars (no `.ewm()`, no `.replace()`) on a 900-bar frame at bars 300/600/899, agreeing to `1.243e-14 / 0.0 / 0.0`; bit-equality with the owner's own screen candidate on all 1,490 shared bars (table above); and the rejected `*100` precedence reading measured, not dismissed |
| B Causality | pass | Future-perturbation sweep (high/low rewritten from `j` onward with a second walk, seed 97), 37 offsets past the 11-bar warm-up: real module **0 of 37** leaks. Three mutants (`importlib` source read, `exec`'d in memory), each first shown LIVE (its output differs from the real module's) then caught at **37 of 37** offsets: write-shift (final write index `smooth_length=11` bars into the future); look-ahead range (`r = high.shift(-1) - low.shift(-1)`, one bar folded in before the smoothing -- the `bos` look-ahead bug class CLAUDE.md documents); look-ahead EMA (`e.shift(-1)`, so both the subtraction and the division see tomorrow's EMA) |
| C Reachability | synthetic only (real-data reachability comes from Gate E's pooled count, not re-derived here) | 1,500-bar synthetic high/low walk (seed 11), shipped defaults: **1,490 of 1,500** bars non-NaN (99.33%), first valid at bar **10** (the structural boundary, `min_length - 1`). **1,490 distinct values**. Range `[-76.875814, 122.890814]`, median `-3.149360`, **697 positive / 793 negative / 0 exactly zero**. No bar reaches the `-100` floor on this frame (it has no `H == L` ties); the floor is exercised by a planted dead bar, below |
| D Scale-free | pass | `r = H - L` is linear in a positive price rescale and the GTJA `SMA` recursion is linear in a positive scalar multiple of its input, so `r -> k*r` and `e -> k*e`, and `(r-e)/e` cancels `k` EXACTLY for any `k > 0`, with no extra division needed (hence the empty `conv` cell). The `* 100` is a constant and commutes. Measured on the 1,500-bar walk: PRICE **x8 / x64 bit-identical** (`0.0` max\|diff\|, NaN masks matching, 0 sign changes); **x10 / x3.7** max\|diff\| **1.471e-12 / 1.101e-12**, NaN masks matching, 0 sign changes. `0 < 1490 fires < 1500` and **1,490 > 1** distinct values rule out a constant column |
| E Attribution | **Gate E: pending, run by issue-solver after this session** | Not run in this session: this session may not execute `gate_e_overlap.py` or read `../Backtesting`. The issue's own PROTOTYPE measured max \|rho\| **0.8846** vs `Range_ATR` (manifest, n = 397,603), top-5 per-frame max median **0.8878** -> **DISCLOSE_GAP**, next comparators `Range_ATR_Pctl` 0.8817 and `Range_ATR_State` 0.8241; fork overlap (stage 2, 12 frames, not Gate E) max \|rho\| **0.3338** vs `fvg_sweep_magnet:FSME_CE_SCORE_BULL_5`. **A prototype is not a port**, and those numbers do not transfer -- they are recorded here only as what the issue already knew. See "What Gate E has to decide" below |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): **3 failed, 5332 passed, 83 skipped**; `tests/test_g191_188.py`: **30 passed**. The three failures, all pre-existing or expected, are itemised below |

## Wiring

`Category` **316 -> 317** (`volatility` **33 -> 34**); `df.ta.<name>()` accessor count **324 ->
325**. Touch points: `pandas_ta/volatility/g191_188.py` (module),
`pandas_ta/volatility/__init__.py` (export), `pandas_ta/__init__.py` -> `Category["volatility"]`
(discovery), `pandas_ta/core.py` -> `AnalysisIndicators.g191_188` (accessor),
`tests/test_g191_188.py` (tests). `README.md`'s headline (`316 -> 317` / `324 -> 325`) and its
`volatility (33 -> 34)` row updated and checked by `tests/test_readme_counts.py`;
`docs/IndicatorDictionary.md` regenerated (`319` probed, the new row tagged `G191_188_11_2`
**`SF`** with warm-up 10). `docs/MLCompanionContract.md`'s running tag count updated **661 ->
662 / 304 -> 305 `SF`**, checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated (`316 -> 317`) and
`CATEGORY_BUCKETS["volatility"]` updated (`33 -> 34`).

`g191_188`'s Gate E row is NOT in `docs/gate_e_ledger.csv`, per this session's override rules
(issue-solver runs Gate E after this session; a later receipt session records the ledger row
and fills in the measured numbers above). That is why
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` fails on this
tree, reporting `['g191_188', 'mtd_ret']`. The indicator is wired into `Category` as usual and
was NOT held out to silence the test.

## What this column is, and what Gate E has to decide

`e` is an EMA of the daily range at `alpha = 2/11`, i.e. the range's own recent typical size.
The column is today's range as a PERCENT DEVIATION from it: `0` when today's range equals its
EMA, `+100` at twice the EMA, floored at `-100` on a dead bar. It is a range-expansion gauge
with no direction in it -- the sign of the bar's move and the close's position inside the bar
are both invisible to it.

### The fork's other range columns, and the one that measured 0.95

Grepping the package for `high - low` and reading the volatility hits in this session found
FOUR shipped volatility modules that divide one smoothing of `H - L` by another:

* `g191_109` (`pandas_ta/volatility/g191_109.py:157-159`) -- `SMA(H-L,10,2) /
  SMA(SMA(H-L,10,2),10,2)`, the ONCE-smoothed range over its TWICE-smoothed self, where this
  column is the RAW range over its once-smoothed self, less one, times 100;
* `massi` (`pandas_ta/volatility/massi.py:22-27`) -- `g191_109`'s ratio built from arithmetic
  EMAs, then summed over 25 bars;
* `cvi` (`pandas_ta/volatility/cvi.py:28-32`) -- `100 * (EMA(H-L,10) - EMA(H-L,10)[-10]) /
  EMA(H-L,10)[-10]`, this port's own `100*(a-b)/b` spelling on the same `H - L`, but comparing
  the EMA against ITSELF TEN BARS AGO rather than against today's range;
* this one.

No claim is made that those four are all of them: the grep hit 38 files across the package and
only the volatility hits were read. The nearest shape of all is not in that list and was
measured anyway: `g191_158` (`(H-L)/close`), ported on 2026-11-11 under issue #81
(`git log` on `pandas_ta/volatility/g191_158.py`) -- i.e. AFTER the 2026-10-24 screen whose
fork-overlap number the issue quotes, so that screen's 0.3338 could not have seen it.

Synthetic Spearman on the same 1,500-bar walk. Five shipped fork columns, one PROXY for the
engine column the prototype actually collided with, and six variants of this port's own
spelling -- four of them moving exactly ONE thing (the denominator's smoother; its length at
this port's own weight `m = 2`, long and short; or the numerator) and two kept as two-variable
controls. **This is not Gate E** -- one synthetic frame, twelve comparators, against Gate E's
89 real frames and 687 comparators:

| comparator | what it changes vs this port | Spearman | shared bars |
|---|---|---|---|
| `range / ewm(range, alpha=2/14)` = `SMA(14,2)` | the LENGTH only (14, not 11) | **0.998608** | 1,487 |
| `range / MEAN(range, 11)` | the SMOOTHER only (mean, not the GTJA EMA) | **0.988577** | 1,490 |
| `range / ewm(range, alpha=1/14)` = `SMA(14,1)` | length AND weight (a Wilder RMA; centre of mass 13 bars vs this port's 4.5) | **0.986242** | 1,487 |
| `range / MEAN(range, 14)` | length AND smoother | **0.984046** | 1,487 |
| `range / ewm(range, alpha=2/5)` = `SMA(5,2)` | the LENGTH only (5, not 11) | **0.973981** | 1,490 |
| **`g191_158:G191_158`** | **shipped; divides `H-L` by CLOSE instead of by an EMA of `H-L`** | **0.951954** | 1,490 |
| `g191_109:G191_109_10_2_10_2` | shipped; smooths the NUMERATOR too | **0.641397** | 1,482 |
| `true_range / ewm(true_range, alpha=2/11)` | the NUMERATOR only (`true_range`, not `H-L`) | **0.573258** | 1,489 |
| `true_range / Wilder RMA(true_range, 14)` -- proxy for the engine's `Range_ATR`, NOT the engine's column | numerator, length and weight | **0.569340** | 1,486 |
| `true_range:TRUERANGE_1` | shipped; no normalisation at all | **0.541550** | 1,490 |
| `cvi:CVI_10_10` | shipped; same `100*(a-b)/b` shape, but against the EMA of 10 bars ago | **0.266088** | 1,481 |
| `natr:NATR_14` | shipped; normalises ATR by CLOSE, not range by range | **0.113425** | 1,487 |
| `massi:MASSI_9_25` | shipped; `g191_109`'s ratio summed over 25 bars | **-0.066067** | 1,468 |

### The 0.951954 against `g191_158` is an artefact of the frame, and that was measured too

`g191_158` is `(H-L)/close`; this column is `(H-L)/EMA(H-L) - 1`, times 100. They are not the
same quantity, and on THIS frame they nearly are -- because of how the frame is built, not
because of the formulas. `_walk` draws each bar's spread as `close * uniform(0.005, 0.02)`
(`docs/measure_g191_188.py:_walk`), so `EMA(H-L)` comes out nearly PROPORTIONAL to close and
the two denominators become the same denominator up to a constant. Measured: `e / close` on
that frame has mean 0.016316, std 0.002278, **coefficient of variation 0.1396**.

So the frame was rebuilt with volatility clustering -- same lognormal close path, but the
spread's log following an AR(1) (`docs/measure_g191_188.py:_walk_clustered`, rho 0.95) -- which
breaks that proportionality: `e / close` there has mean 0.016730, std 0.015696, **CV 0.9382**,
nearly seven times as dispersed. On that frame:

| comparator | i.i.d.-spread walk | clustered-spread walk |
|---|---|---|
| `g191_158:G191_158` | 0.951954 | **0.451513** |
| `g191_109:G191_109_10_2_10_2` | 0.641397 | **0.729682** |
| `range / MEAN(range, 11)` | 0.988577 | **0.971270** |

The `g191_158` overlap falls by half once ranges persist, while the two genuinely
range-normalised comparators hold or rise. Real tapes cluster, so the 0.95 is most likely the
i.i.d. construction and not the column. That is a measurement of the frame, not of real data --
nothing here says what Gate E will find against `g191_158`, which is not even one of Gate E's
687 engine comparators. It is written down because a 0.95 against a shipped `Category` column
is the kind of number that must not first appear in somebody else's review.

What the one-variable rows say, and it is the opposite of what a first pass guessed. On this
frame the DENOMINATOR barely matters: with the numerator held at `H - L`, five different
denominators -- lengths 5, 11 and 14, as an arithmetic mean or as a GTJA EMA at two different
weights -- all land in **0.974 to 0.999**. What moves the column is the NUMERATOR: swapping
`H - L` for `true_range` while holding the denominator at this port's own `alpha = 2/11` drops
it to **0.573258**, and `true_range` exceeds `H - L` on **884 of 1,499** bars (58.97%) of this
walk. So the `Range_ATR` proxy's 0.569340 is explained by its numerator substitution, not by
its 14-bar Wilder denominator: holding the numerator at `H - L` and swapping in the proxy's own
Wilder `alpha = 1/14` denominator costs 0.0138 (to 0.986242), not 0.43.

Consequence, stated rather than buried: on this frame, the five denominators measured above all
leave the column intact, so a shipped column dividing `H - L` by any of them would restate it.
Nothing broader than those five was measured -- no median, no length past 14, no weight past
`m = 2` -- so this is not a claim about every possible smoothing. None of the five is a shipped
fork column, so none of them strikes anything on the fork side. Whether any of them is an
ENGINE column is UNKNOWN here: this session can see 3 of the 687 comparator names
(`Range_ATR`, `Range_ATR_Pctl`, `Range_ATR_State`, from the issue text) and may not read the
engine at all. If one of the 687 is a range-over-smoothed-range column, the 0.974-0.999 band is
what to expect from it.

The prototype's top Gate E comparator, `Range_ATR` at **0.8846** pooled over 89 real frames, is
an ENGINE column this fork does not contain. Its construction is reachable, and was measured
rather than declared out of reach: range normalised by ATR, i.e. a range-like numerator over a
Wilder RMA of true range at `alpha = 1/14`. The nearest build of that here lands at 0.569340,
far below 0.8846 -- and the one-variable rows locate the discrepancy in the numerator. An
INTERPRETATION follows, labelled as such because nothing in this session can test it: on a real
tape `true_range` equals `H - L` far more often than on this walk, whose bar spreads are drawn
i.i.d. (`docs/measure_g191_188.py:_walk`, `rng2.uniform`) so that a 1.5%-sigma close move gaps
out of a sub-1% spread on 59% of bars. If the engine's `Range_ATR` numerator is closer to
`H - L` than to `true_range`, the rows that predict its behaviour are the 0.974-0.999 band, not
the 0.569340 proxy. **The honest position is that the prototype's 0.8846 / DISCLOSE_GAP is the
better prior for this port than any number in the table above.**

This fork's own synthetic-vs-real precedents go BOTH ways, so the table above bounds nothing in
either direction. Four pairs were read out of committed receipts in this session:

| port | synthetic | real | direction |
|---|---|---|---|
| `g191_003` vs `kdj:J_9_3` | 0.906078 (`docs/G191003Measured.md:223`) | 0.8310 pooled (`:188`) | synthetic OVER |
| `g191_022` vs `smi:SMIo_5_20_5` | 0.9116 | 0.8842 pooled (`docs/G191022Measured.md:176-179`) | synthetic OVER |
| `g191_158` vs `pdist` | 0.706474 (`docs/G191158Measured.md:310`) | 0.8834 pooled vs `pdist_pct` (`:201`) | synthetic UNDER |
| `g191_055` vs `bias` | 0.753646 (`docs/G191055Measured.md:380`) | 0.8361 pooled / 0.8662 per-frame vs `bias_ta` (`:404`) | synthetic UNDER |

`g191_158` is the closest precedent to this port -- same category, same source family, also
range-based. Its `pdist` pair UNDER-read by 0.18, and its table's own MAXIMUM (0.734603 against
`g191_109`, `docs/G191158Measured.md:309`) under-read the real 0.8834 by 0.15. `g191_055` carries the
warning that matters more than the direction: its heading is "Non-redundancy on a synthetic
frame — NOT Gate E, and it undershot" (`docs/G191055Measured.md:372`), all eight of its
synthetic comparators sat under 0.80, and **Gate E then struck the column at 0.9078 against a
comparator that table did not contain** (`docs/G191055Measured.md:389-391`). A reassuring
synthetic table is not evidence of anything, including about which family the real collision
will come from. **If the launcher's Gate E run comes back STRUCK, the
column is reverted (or waived) and this file stays as the receipt — which closes issue #83
exactly as well as a ship.**

## Edge cases, measured rather than claimed

| case | measured |
|---|---|
| one dead bar (`H == L`) planted at index 700 | value exactly **`-100.0`**, the floor; fire count unchanged at **1,490**. `r = 0` is a valid float, so nothing empties |
| every bar dead (`H == L` on all 1,500) | fires on **0 of 1,500**. `e` is `0` too, so the division is `0/0` -- NaN DIRECTLY, which means the `.replace([inf, -inf], nan)` is not what carries this case |
| one NaN planted in `high` at index 700 | exactly **1** output bar emptied (that bar's own `r` is NaN); **167** later bars displaced, from bar **701** to bar **867**; first valid bar still **10**. pandas' `ewm` SKIPS a NaN input (carrying its previous value forward) rather than emptying its output, so `e` stays defined while its level moves. Nothing before bar 700 changes. The test pins the emptied bar, the start and a lower bound of 100, NOT the 167 -- where a displacement falls below float64 resolution is platform float detail (the lesson of `g191_022`'s CI failure, commit `a56d873`) |
| `smooth_weight` outside `0 < m/n <= 1` | `m = 0.5` truncates to `0` (`alpha = 0`) and `m >= 12` gives `alpha > 1`; pandas' `ewm` raises `ValueError` on both |
| `smooth_weight = 11` (`alpha = 1.0` exactly) | pandas ACCEPTS it. The smoother returns its own input, so `e == r`, the numerator is identically zero, and the column is a **CONSTANT `0.0`** wherever it fires. Nothing raises. Pinned by `test_a_weight_of_alpha_one_collapses_the_column_to_zero`, and the public docstring's parameter note says so |
| `smooth_length` off-nominal | three bands, none guarded: `0 < n < 1` truncates to `0` and `alpha = m/n` raises `ZeroDivisionError` before pandas is reached; `n < m` gives `alpha > 1` and pandas' `ewm` raises `ValueError`; **`n == m` gives `alpha = 1.0` exactly, which pandas ACCEPTS** -- so `smooth_length=2, smooth_weight=2` raises nothing and ships a constant `0.0` column. Round 4 of review caught the public docstring claiming `n <= m` raises; it does not at `n == m`. Pinned by `test_a_length_that_breaks_the_alpha_raises` and `test_a_length_equal_to_the_weight_collapses_the_column_to_zero` |

## Review, and what in this file is unreviewed

Four `/brutally-honest-review` rounds (REVISE x4, the cap), **26 findings: 9 MAJOR, 11 MINOR,
6 NIT, 0 CRITICAL** — recounted from the four verdict blocks quoted verbatim in
`docs/reviews/auto-2026-11-11-g191-188/01-g191-188.md`. Not one was a mathematics error. Every
round reproduced every number in this file and then failed the prose around it: a script that
printed the first VALID bar under the label `first_displaced`; a declaration that the
prototype's top comparator "cannot" be measured here; a causal verdict drawn from a
three-variable proxy; a "length only" row that moved two parameters; a `two precedents` and a
`no port was found` that two receipts in this same directory refute; a public docstring
claiming a raise where the column silently goes constant; and "the fork ships ONE adjacent
construction" when it ships several.

Round 4's fixes landed with the cap spent and were **NOT re-reviewed**. In this file that is:
the "fork's other range columns" subsection, the twelve-row table, the whole "0.951954 ... is
an artefact of the frame" subsection, the engine-column UNKNOWN sentence, the 0.0138 and
0.18/0.15 corrections, the Gate A `adjust=False` seed paragraph, and the `smooth_length` row of
the edge-case table. `docs/reviews/auto-2026-11-11-g191-188/99-summary.md` lists the unreviewed
text in the other files too. Every number in it comes from a run made after the edit, and the
suite was re-run after it; what is missing is an independent reader, not a run.

## Gate F: the suite run, in full

`python -m pytest -q`, full suite, default collection order: **3 failed, 5332 passed, 83
skipped** (105.5s). `tests/test_g191_188.py`: **30 passed**. The three failures:

1. `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` -- EXPECTED on
   this tree, per this session's override rules: `no Gate E ledger row for ['g191_188',
   'mtd_ret']`. `mtd_ret` is pre-existing and unrelated (issue #206).
2. `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` --
   pre-existing, needs the sibling `../AlternativeRepos` checkout, absent here (CI deselects
   it by name).
3. `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` -- pre-existing,
   CLAUDE.md "Known breaks" (the untracked `docs/pine/` corpus).

No other test regresses. The 83 skips were not broken down in this session; CLAUDE.md records
that 21 of them are the upstream correlation suite, which skips at import when the gitignored
`data/SPY_D.csv` fixture is absent.

One ordering note, pre-existing and unrelated to this port. Measured in this session:
`python -m pytest tests/test_readme_counts.py tests/test_wiring_accessors.py
tests/test_altport2_ports.py -q` fails
`test_the_category_count_moved_by_exactly_three` with `Category total 314, expected 317` --
3 short -- while `python -m pytest tests/test_altport2_ports.py -q -k category` passes and the
full suite (where alphabetical order puts `test_altport2_ports.py` first) passes. So the total
depends on what ran before it in the same process. Isolated during this issue's review rounds:
`tests/test_wiring_accessors.py` is the module that drops the three entries, and the mechanism
is in shipped code that this port does not touch --
`pandas_ta/core.py:451-453` (`_indicators_by_category` returns the LIVE `Category[name]` list,
not a copy) feeding `pandas_ta/core.py:691-692`
(`ta = self._indicators_by_category(...)` then `[ta.remove(x) for x in excluded if x in ta]`),
so every `df.ta.strategy("<category>")` call permanently deletes the excluded names from the
global registry for the rest of the process. The arithmetic here is unaffected: the pinned
`CATEGORY_TOTAL` is recounted from `pandas_ta/__init__.py`, and the live total read before any
`strategy()` call in the process is 317. Not fixed: changing what `strategy()` does to the
global `Category` is outside this issue's scope and is the owner's call.
