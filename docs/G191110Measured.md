# g191_110 — measured (issue #84)

> **Status: Gates A-F cleared on the port. Gate E ran on the committed module (2026-11-11,
> run `is84-g191_110-1dad5ee8`): max |ρ| **0.8860** vs `brar_BR_26`, per-frame max median
> **0.8819** → **DISCLOSE_GAP**, under the 0.90 strike line, so no column is struck and
> `G191_110_20` ships under the bands. Ledger row recorded.
> ⚠ RECOMMENDATION NEVERTHELESS: SKIP THIS COLUMN as question-redundancy — the owner has to
> make that call, because Gate E cannot. This column is `brar`'s `BR` at a different window
> length. Measured, not argued: at the SAME length the port and
> `brar(..., length=20)["BR_20"]` have Spearman **1.0** and differ by at most
> **5.684341886080802e-14** (one ulp), and the port's own expression re-spelled `brar`'s way
> is **bit-identical** to `BR_20` on all 1,480 shared bars. And the Gate E run's own
> `top25.csv` now settles what an earlier draft of this file could only infer: the 687
> comparators carry `brar` at its default 26 only, so the same-length duplication was
> structurally invisible to the measurement (see "What Gate E saw" below). The port ships
> under the bands; the revert list, should the owner take the recommendation, is at the end of
> "The recommendation".**

Prior-Close Pressure Ratio: Guotai Junan's (2017, "GTJA191", internal quant report) alpha
`#110`, per issue #84, which attributes its copy of the report to HKUDS/Vibe-Trading (MIT).
Module `pandas_ta/momentum/g191_110.py`, column `G191_110_20`. Tests:
`tests/test_g191_110.py` (37, all passing). Numbers below: `python docs/measure_g191_110.py`.
Environment: pandas 2.3.3 / numpy 1.26.4, printed by the measure script's last line. Measured
2026-11-11.

## Gate A: derivation from the published formula, not the prototype

Issue #84 states GTJA191 alpha `#110`:

    SUM(MAX(0,H-C1),20) / SUM(MAX(0,C1-L),20) * 100

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access are both
unavailable in this worktree, so the issue's own named copy -- HKUDS/Vibe-Trading (MIT) -- was
never read. Everything below is derived from the issue's own stated formula string, per the
issue's own rule ("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype (`docs/issues/screen/ind_screen.py:459-463`):

    @cand("g191_110", "high-over-prior-close vs prior-close-over-low (20)", G,
          "#110: SUM(MAX(0,H-C1),20) / SUM(MAX(0,C1-L),20) * 100")
    def _(o, h, l, c, v):
        c1 = delay(c, 1)
        return 100 * sdiv(tsum((h - c1).clip(lower=0), 20),
                          tsum((c1 - l).clip(lower=0), 20))

The string and the prototype agree on the window (20), on both `MAX(0, .)` arms and on the
`* 100`. Operators, each read directly off the prototype's own module source in this session:
`DELAY(C,1) = C.shift(1)` (`ind_screen.py:45`), a BACKWARD shift; `SUM(X,n) =
X.rolling(n).sum()` (`ind_screen.py:49`), a trailing sum at pandas' default `min_periods=n`,
which this port spells out explicitly as `rolling(length, min_periods=length)` -- the same
explicit spelling `g191_003` and `g191_129` use -- so the warm-up does not depend on a pandas
default; and the prototype's own `sdiv` (`ind_screen.py:41-42`, `_fin(a / b)`), which replaces
`+-inf` with `NaN` on the division, BEFORE the `* 100`. This port spells the `.replace()` in
the same position, so the two agree bar for bar. `H`, `L`, `C` are the current bar's high,
low and close; `OPEN` and `VOLUME` are not read.

The candidate's own `candidates.csv` row carries an EMPTY `conv` cell
(`docs/issues/screen/candidates.csv:47`): there is no extra scale-free conversion to apply,
because a ratio of two price-linear sums is already scale-free (derived under Gate D).

### The three ambiguities and the four decisions they forced, each measured rather than asserted

| # | ambiguity in the source string | shipped reading | the rejected reading, measured on the 1,500-bar walk |
|---|---|---|---|
| 1 | `MAX(0, X)` — pointwise floor, or GTJA191's windowed `TSMAX`? | pointwise, `.clip(lower=0)` — the screen defines `tsmax`/`tsmin` separately (`ind_screen.py:50-51`) and does not use them here | `TSMAX(H-C1,20)/TSMAX(C1-L,20)*100` is a MATERIALLY different column: Spearman **0.449365**, max \|diff\| **160.812927**, **0 of 1,480** bars bit-equal |
| 2 | `/ SUM(..) * 100` — does `*100` multiply the ratio or scale the denominator? | the ratio, `100 * (num/den)` — left-to-right precedence, and the prototype writes it (`ind_screen.py:463`) | `num / (den*100)` is this column divided by exactly 10,000 (ratio **9999.999999999996** to **10000.000000000002**), **Spearman 1.0**, **0 of 1,480** bit-equal: a pure constant rescale that reorders nothing |
| 2b | a THIRD parse exists, and the fork's own `brar` uses it | `100 * (num/den)` | `(100*num)/den` (`brar.py:32-33`): algebraically identical, NOT bit-identical — Spearman **1.0**, bit-equal on **927 of 1,480** bars, max \|diff\| **5.684341886080802e-14** |
| 3 | `MAX(0, .)` at bar 0, where `C1` is undefined | `.clip(lower=0)` PRESERVES the NaN, so the trailing sum's `min_periods` carries it through the first `length` outputs | `np.where(x > 0, x, 0.0)` maps the NaN to `0.0` (a NaN fails `> 0`): it fires on **1,481** bars against the port's **1,480**, starts at bar **19** instead of **20**, and differs on **0** of the bars where both fire — its entire effect is one invented output at the warm-up edge |

Reading 1 is the only rejected reading that changes the column's ORDERING (Spearman 0.449365,
max \|diff\| 160.812927, 0 of 1,480 bit-equal). Reading 3's rejected spelling leaves ordering
and values alone and changes the SUPPORT: 1,481 fires against 1,480, first valid 19 instead of
20, and 0 differing bars where both fire. Reading 2 changes every value and no rank, by the
exact constant 10,000 (0 of 1,480 bit-equal). Reading 2b changes **553 of 1,480** values by at
most one ulp (bit-equal on the other **927**) and no rank. All four columns are built and
compared in
`docs/measure_g191_110.py` and pinned in `tests/test_g191_110.py` (one test each). Reading 2b
is pinned as a BAND (`0 < bit_equal < 1480`) rather than as the integer 927, because a
bit-equal count over float64 turns on last-bit rounding — the `g191_022` CI lesson, commit
`a56d873`.

### Agreement with the prototype

On the 1,500-bar synthetic walk (seed 11, `docs/measure_g191_110.py:_walk`):

| compared against | shared bars | max \|diff\| | bit-equal |
|---|---|---|---|
| the retyped prototype expression | 1,480 | `0.0` | 1,480 of 1,480 |
| the REAL `g191_110` candidate out of the owner's (gitignored) screen registry | 1,480 | `0.0` | 1,480 of 1,480 |

The prototype's `tsum` and this port's explicit `min_periods=length` are the same thing, so
unlike `g191_188` there is no warm-up convention of the fork's own riding in here: both fire
on 1,480 of 1,500 bars.

### Warm-up: a disclosed necessary condition

`C1` is undefined at bar 0, so `up` and `down` are NaN there, and `SUM(., length)` at
`min_periods=length` needs `length` CONSECUTIVE valid contributions ending at `t`, i.e.
`t >= length`. So `min_length = length + 1` = **21** bars, enforced by `verify_series`.
Measured: 20 bars of history return `None`; 21 bars fire exactly **once**, at bar **20**.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived from the issue's own stated formula, matching the issue's own prototype bit-for-bit | An 8-bar hand-derived example at `length=3` — `up = [nan,3,0,5,1,3,0,5]`, `down = [nan,0,3,0,1,0,3,0]`, bars 3-7 `[266.66666666666663, 150.0, 900.0, 100.0, 266.66666666666663]`, including an EXACT `100.0` balance bar and both floors firing — printed by `python docs/measure_g191_110.py`; an independent per-bar replay at the shipped default in plain Python scalars (no `.rolling()`, no `.clip()`, no `.replace()`) on a 900-bar frame at bars 300/600/899, agreeing to **exactly `0.0`** at all three; bit-equality with the owner's own screen candidate on all 1,480 shared bars (table above); and all three ambiguities with all four of their rejected readings measured, not dismissed (table above) |
| B Causality | pass | Future-perturbation sweep (high/low/close rewritten JOINTLY from `j` onward with a second walk, seed 97), 37 offsets past the 21-bar warm-up: real module **0 of 37** leaks. FOUR mutants (`importlib` source read, `exec`'d in memory), each first shown LIVE (its output differs from the real module's) then caught at **37 of 37** offsets: write-shift (final write index `length=20` bars into the future); forward `DELAY` (`close.shift(-1)`, so `C1` becomes TOMORROW's close — this formula's own most plausible sign error); and a `center=True` sum on EACH of the two rolling calls separately, the numerator's and the denominator's — the `bos` look-ahead bug class CLAUDE.md documents, one mutant per call so neither arm is proven by analogy. Separately, `offset` — a user-reachable way to make THIS column read the future — is pinned by `test_a_positive_offset_only_delays_and_is_the_forks_convention`: `offset=+2`/`-2` are exactly the default column shifted later/earlier, and the registry uses `offset=0`, which the sweep covers. No claim that `offset` is the package's only look-ahead: CLAUDE.md names `ichimoku`'s `ICS_26` (`close.shift(-kijun)` at defaults) as an accepted exception |
| C Reachability | pass, synthetic AND real | 1,500-bar OHLC walk (seed 11), shipped default: **1,480 of 1,500** bars non-NaN (98.67%), first valid at bar **20** (the structural boundary, `min_length - 1`), **1,480 distinct values**. Range `[27.612949, 328.461817]`, median `102.285783`, **774 bars above 100 / 706 below / 0 exactly on it / 0 negative / 0 exactly zero**. The issue's own prototype screen reports n = **396,399** pooled real bars for this candidate (2026-10-24), which is the real-data reachability number the porting session could not reproduce; the Gate E run of 2026-11-11 supersedes it with **396,927** non-NaN and **396,927** non-zero of 398,849 pooled bars (99.52%) over the 89 frames |
| D Scale-free | pass | `C1` carries no arithmetic; the `MAX(0,.)` floor is a comparison against zero and is scale-invariant for any `k > 0`; both sums are linear; so the ratio cancels `k` EXACTLY with no extra division needed (hence the empty `conv` cell). The `* 100` is a constant and commutes. Measured on the 1,500-bar walk: PRICE **x8 / x64 bit-identical** (`0.0` max \|diff\|, all 1,480 bars, NaN masks matching); **x10 / x3.7** max \|diff\| **1.3073986337985843e-12 / 1.4210854715202004e-12**, NaN masks matching. Because the floors are EXACT comparisons, the branch masks were measured too rather than assumed: **0** bars change branch in either floor at any of the four multipliers. `0 < 1480 fires < 1500` and **1,480 > 1** distinct values rule out a constant column |
| E Attribution | **DISCLOSE_GAP** — measured on the port, no column struck | `G191_110_20`: max \|ρ\| **0.8860294833052819** vs **`brar_BR_26`** (compute_all, n = **396,399**), per-frame max median **0.8818911915226397** (same comparator, 89 frames) -> **DISCLOSE_GAP** (0.80 ≤ ρ < 0.90, and the per-frame median is under 0.90 too). Full run facts in "Gate E: the measured run" below; ledger row `docs/gate_e_ledger.csv` (run `is84-g191_110-1dad5ee8`, measured 2026-11-11). ⚠ Read the redundancy section below BEFORE reading a DISCLOSE_GAP verdict as "this column earns its place" |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | See "Gate F: the suite run" below |

## Wiring

`Category` **317 -> 318** (`momentum` **81 -> 82**); `df.ta.<name>()` accessor count **325 ->
326**. Touch points: `pandas_ta/momentum/g191_110.py` (module),
`pandas_ta/momentum/__init__.py` (export), `pandas_ta/__init__.py` -> `Category["momentum"]`
(discovery), `pandas_ta/core.py` -> `AnalysisIndicators.g191_110` (accessor),
`tests/test_g191_110.py` (tests). `README.md`'s headline (`317 -> 318` / `325 -> 326`) and its
`momentum (81 -> 82)` row updated and checked by `tests/test_readme_counts.py`;
`docs/IndicatorDictionary.md` regenerated (`320` probed, the new row tagged `G191_110_20`
**`SF`** with warm-up 20). ⚠ That generated row truncates the public `__doc__` at its first
sentence, so the dictionary — the document CLAUDE.md tells a reader to consult before judging
a column — does NOT carry the `brar` redundancy flag; the disclosure lives in the module
source docstring, the public `__doc__`, this file, `tests/test_g191_110.py`'s docstring and
`docs/MLCompanionContract.md`'s tag line. `docs/MLCompanionContract.md`'s running tag count updated **662 ->
663 / 305 -> 306 `SF`**, checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated (`317 -> 318`);
`CATEGORY_BUCKETS` has no `momentum` key, so it is unchanged.

`g191_110`'s row is in `docs/gate_e_ledger.csv`, recorded by
`python docs/gate_e_ledger.py record <run dir> --measured 2026-11-11` in the receipt session
(2026-11-11), which printed `g191_110:G191_110_20 DISCLOSE_GAP 0.8860 vs brar_BR_26`. The row
is not STRUCK, so it needs no waiver.

## Gate E: the measured run

Run by issue-solver on the committed module (this session may not read `../Backtesting` and
did not run the harness). Run directory `is84-g191_110-1dad5ee8`; the numbers below are copied
from its `overlap_max.csv`, `top25.csv`, `degenerate.csv` and `meta.json`.

| column | max \|ρ\| | against | set | n | per-frame max median | frames | verdict |
|---|---|---|---|---|---|---|---|
| `G191_110_20` | **0.8860294833052819** | `brar_BR_26` | compute_all | **396,399** | **0.8818911915226397** (`brar_BR_26`) | 89 | **DISCLOSE_GAP** |

Band arithmetic, both halves of the strike rule: pooled **0.8860** is in `0.80 ≤ ρ < 0.90`
(DISCLOSE_GAP), and the top-5 per-frame max median **0.8819** is under 0.90, so the
`r3-perframe-0.90` rule does not strike the column on either leg. `perframe_pct_frames_ge_090`
is **4.49438202247191%** of 89 frames, i.e. **4** frames whose per-frame \|ρ\| against
`brar_BR_26` reaches 0.90 — the band tests the MEDIAN, not the tail, and the median is 0.8819.

Run facts from `meta.json`: default parameters (`kwargs {}`, no exclusions, no rename prefix),
**89** frames, **398,849** pooled bars, **687** comparators (`n_compute_all` **329** +
`n_manifest` **358**), canary `AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS bit-equal`, pandas 2.3.3
/ numpy 1.26.4, data stamp `1be6495ef7095ff67ad8f59a2fc0311d74f02652`, module sha1
`a4942f1240b52afd07be67ad99d3a4ac9e73f90b`, tree sha1
`13ca59d9a3b71ce923b921a32d8d9296bfc7f52e`. Coverage of the column itself on the real tape:
`non_nan` **396,927** of 398,849 pooled bars (**99.52%**), `non_zero` **396,927** — which is
the real-data Gate C number the porting session could only owe. One comparator was dropped as
degenerate (`degenerate.csv`): `squeeze_SQZ_NO` (manifest), reason `constant`.

Next comparators after `brar_BR_26` (`top25.csv`): `Ret_21d_vol_adj` **0.8015**,
`Ret_21d_pct` **0.7947**, `SMA_20_Slope_pct` **0.7654**, `bias_ta` **0.7625**. The port
reproduces the prototype's screen to four decimals on its top three (prototype 2026-10-24:
0.8860 / 0.8015 / 0.7947, n = 396,399) — a prototype is still not a port, but here the two
agree.

**What the receipt session deliberately did NOT update.** `pandas_ta/momentum/g191_110.py`'s
docstring still reads "the issue's own prototype measured 0.8860 pooled on real data" (lines
~55-59) and still calls Gate E's verdict a prediction. That text is now stale in its framing —
the port's own run measured the same 0.8860 — but the module is left byte-identical on purpose:
`docs/gate_e_ledger.py record` stamped its sha1 `a4942f1240b52afd07be67ad99d3a4ac9e73f90b` and
the tree sha1 `13ca59d9a3b71ce923b921a32d8d9296bfc7f52e` into the ledger row, and
`tests/test_gate_e_ledger.py` fails if either moves after the run. Editing a docstring would
invalidate the measurement it describes. `tests/test_g191_110.py`'s docstring, which is not in
the stamp, was updated instead.

### What Gate E saw — and the one thing it could not see, now measured

The porting session INFERRED that the comparator set carries no 20-bar `BR`, and asked for
that inference to be replaced by a run. It is replaced here, from the run's own `top25.csv`:
the 25 strongest comparators out of 687 contain exactly **one** `brar` column, `brar_BR_26`,
and no `brar_BR_20`. That is decisive rather than suggestive, because the same-length identity
measured below is Spearman **1.0**: a `brar_BR_20` comparator would have ranked **first** at
ρ ≈ 1.0 and would have STRUCK the column outright. It did not appear, so the set does not
carry it.

So the DISCLOSE_GAP verdict is confirmation that this column does not restate any of the 687
comparators the engine actually computes — and it is NOT evidence that the column asks a
question `pandas_ta`'s own `brar(length=20)` cannot answer, because that column is not in the
comparator set. Gate E has done what it can; the keep-or-skip question below is the owner's.

## The redundancy, measured — and the recommendation

This is the part of the receipt that matters most, so it is not left to Gate E.

**`brar`'s `BR` column is this formula.** `pandas_ta/momentum/brar.py:23-33`:

    hcy = non_zero_range(high, close.shift(drift));  hcy[hcy < 0] = 0
    cyl = non_zero_range(close.shift(drift), low);   cyl[cyl < 0] = 0
    br  = scalar * hcy.rolling(length).sum();  br /= cyl.rolling(length).sum()

which is `MAX(0, H-C1)` and `MAX(0, C1-L)`, trailing sums, scalar 100 — GTJA191 `#110`.

The differences are enumerated as a measured list, not as a closed count. They matter because
the sentence "`df.ta.brar(length=20)` already produces this arithmetic" invites a reader to
swap one for the other, and (d) through (g) say what that would cost:

| # | difference | how it is known |
|---|---|---|
| a | `brar`'s default `length` is **26**, this alpha's is **20** | read in `brar.py:9` |
| b | `brar` puts the `100` on the NUMERATOR (`brar.py:32-33`) | read in code; measured as reading 2b above |
| c | `brar` spells `MAX(0,.)` as `non_zero_range` + a negative-clip, so it adds `sys.float_info.epsilon` to the whole difference series when ANY element is exactly 0 (`pandas_ta/utils/_core.py:non_zero_range`) | read in code; measured with planted ties below |
| d | **`brar` does NOT replace `+-inf` with NaN.** On the 40-bar all-gap-up frame its `BR_20` carries **20** `inf` values where this column reports NaN | measured, `docs/measure_g191_110.py` |
| e | `brar` guards history at `verify_series(.., length)`, this port at `length + 1`: with exactly 20 bars, `brar` returns a DataFrame whose `BR_20` is non-NaN on **0** bars, this port returns `None` | measured |
| f | `brar.py:38` reads `br = ar.shift(offset)`, so at a non-zero `offset` its `BR` column is its own `AR` column shifted TWICE. Measured at `offset=2`: `BR_20` equals `AR_20.shift(4)` on **1,477 of 1,477** shared bars, while this port's `offset=2` equals its own base shifted by 2 on **1,478 of 1,478** | measured |
| g | `brar` exposes `scalar` (default 100) and `drift` (default 1) as parameters (`brar.py:6, 10, 17`); this port hardcodes `100` and `close.shift(1)`. So "`df.ta.brar(length=20)` reproduces this arithmetic" holds only at `scalar=100, drift=1`, and `brar(length=20, drift=2)` has no equivalent here at all | read in `brar.py:6, 10, 17` |

(f) is a pre-existing `brar` bug, not something this port introduces or may fix — the
launcher's rules forbid editing an existing helper module here. It is recorded because it is
one of the ways "just call `brar(length=20)`" silently does not reproduce this column; (d), (e)
and (g) are the others.

Measured on the 1,500-bar walk, at the SAME length 20 and `offset=0`:

| comparison | result |
|---|---|
| port vs `brar(..., length=20)["BR_20"]` | Spearman **1.0**, max \|diff\| **5.684341886080802e-14** — ONE ulp at this column's 328.46 maximum (`2**-44`) — bit-equal **927 of 1,480** (a last-bit-dependent count; the test pins `0 < bit_equal < 1480` and a 4-ulp tolerance, not these integers) |
| the port's own expression re-spelled `brar`'s way, `(100*num)/den`, vs `BR_20` | bit-equal **1,480 of 1,480**, max \|diff\| **exactly 0.0** |
| exact ties on this frame (the only condition under which `non_zero_range`'s epsilon changes anything) | `H == C1` on **0** bars, `C1 == L` on **0** bars |
| with ties planted at index 500 (`H == C1`) and 600 (`C1 == L`) | max \|diff\| **1.1368683772161603e-13**, bit-equal **683 of 1,480** |

So on a tie-free frame the entire float gap between this port and `brar` at the same length is
the `100`'s placement, measured rather than assumed. `df.ta.brar(length=20)` already produces
this arithmetic today.

**What Gate E can and cannot see.** ⚠ This subsection is the porting session's text, written
BEFORE the run, and its central claim was an inference. It is now MEASURED — see "What Gate E
saw" above: the run's `top25.csv` carries `brar_BR_26` and no `brar_BR_20`, and since the
same-length identity is Spearman 1.0 a `brar_BR_20` comparator would have ranked first and
struck the column. The paragraphs below are kept as written, with that correction standing
over them. The engine's comparator set
contains `brar_BR_26`, and that much is measured from ONE COMMITTED file:
`docs/gate_e_ledger.csv:73` records `ovn_split`'s run hitting `brar_BR_26` (compute_all,
n = 396,399, `n_comparators` 687) at 0.5789. It is corroborated by the issue's own screen
output, which names `brar_BR_26` as this candidate's top comparator at 0.8860 — but that file
(`docs/issues/083-g191-110.md`) is in the gitignored tracker and `git ls-files docs/issues/`
returns zero paths, so a clone does not carry it and nobody else can check it. CLAUDE.md's
Gate E section is where the 687 = 329 + 358 split is written down.

What is NOT measured: that the set has no `brar_BR_20`. CLAUDE.md defines the set as
`compute_all` ∪ the `ml_features` `1d` manifest and says nothing about parameters. The
pattern in `docs/gate_e_ledger.csv`'s `against` column is narrower than an earlier draft of
this paragraph claimed: those comparator names that DO carry parameters carry their
indicator's defaults (`brar_BR_26`, `rvgi_RVGIs_14_4`, `smi_SMIo_5_20_5`,
`eri_BEARP_13_pct`, `pvo_PVO_12_26_9`), but many carry no parameter suffix at all — `natr`,
`ADX`, `psl`, `stdev`, `rsx`, `ui`, `pvi`, `log_return`, `ZIGZAG`, and `Range_ATR` itself. No
`brar_BR_20` occurs as a comparator name in `docs/gate_e_ledger.csv`, in
`docs/indicators/brar.md` or in any committed screen artifact; the only occurrences of that
string in this repo are this section's own and the review log's.
So the pattern constrains only the parameterised pandas_ta comparators, and a bare-named
engine comparator computed at a 20-bar window would leave no "20" for a grep to find.

From that weakened pattern — not from a written rule, not from reading the catalogue — I
INFER that the 687-comparator set has no 20-bar `BR`, and therefore that the near-exact
duplication at length 20 is structurally invisible to Gate E, which would make a DISCLOSE_GAP
verdict on this port no evidence at all that the column asks a new question.

**Resolved, 2026-11-11 (receipt session).** The run's `top25.csv` was read instead of grepped
for: one `brar` comparator, `brar_BR_26`, at rank 1 with 0.8860, and no `brar_BR_20` anywhere
in the top 25 of 687. Because the same-length identity below is Spearman 1.0, a `brar_BR_20`
in the set would have been rank 1 at ρ ≈ 1.0 and STRUCK the column. The inference held: the
set has no 20-bar `BR`, so the DISCLOSE_GAP verdict is silent on the only open question.

**How much of the 0.886 is just "20 bars resembles 26 bars".** The same formula at other
lengths, on the same frame (Spearman against the shipped `length=20`):

| length | 5 | 10 | 15 | 19 | 21 | 26 | 40 | 60 |
|---|---|---|---|---|---|---|---|---|
| Spearman | 0.449792 | 0.651217 | 0.839252 | **0.968446** | **0.970599** | **0.858897** | 0.661417 | 0.535950 |

The decay with length is smooth and the source's `20` is not a special point on it — 19 and 21
are near-duplicates of 20, and the fork's existing `BR_26` sits at 0.858897 here against 0.886
on the real tape. Nothing in the formula distinguishes 20 as the right window; it is the GTJA
report's choice.

**A second restatement, this one of a SCALE rather than a column.** `100 * up / (up + down)`
— the RSI-shaped reparametrisation of the SAME two sums — measures Spearman **`1.0` at full
precision** (the script prints the `repr`, not a rounded `:.6f`) against this column, because
`x/(x+y)` is strictly increasing in `x/y` for `x, y >= 0`. The test allows 1e-12 of slack
anyway, since a Spearman is a Pearson of ranks and `sqrt(x*x) == x` is not an IEEE guarantee. The ratio form (unbounded above, skewed: a 2x imbalance up reads 200 and a 2x
imbalance down reads 50) and the bounded `[0, 100]` form are rank-identical, so any
rank-based miner is indifferent between them. That is a property of the source formula, not a
defect of the port, and it is disclosed because the skew is the kind of thing a tree split
sees and a Spearman does not.

### Other neighbours on the same frame (NOT Gate E)

| comparator | Spearman | shared bars |
|---|---|---|
| `brar:BR_26` (this formula at length 26) | **0.858897** | 1,474 |
| `rsi:RSI_14` | 0.860097 | 1,480 |
| `cmo:CMO_14` | 0.860097 | 1,480 |
| `100*g191_167/g191_129` (the close-to-close cousins' own ratio) | 0.708189 | 1,475 |
| `psl:PSL_12` | 0.648262 | 1,480 |
| `g191_129:G191_129_12` (`SUM(MAX(C1-C,0),12)/C`) | -0.621055 | 1,480 |
| `g191_167:G191_167_12` (`SUM(MAX(C-C1,0),12)/C`) | 0.569560 | 1,480 |
| `imi:IMI_14` | 0.037103 | 1,480 |
| `brar:AR_26` (`SUM(H-O)/SUM(O-L)`, the open-based sibling) | 0.003205 | 1,475 |

`RSI_14` and `CMO_14` land identically to six decimals, which is expected (`CMO = 2*RSI - 100`
is a monotone transform) and is a PRE-EXISTING property of those two shipped columns rather
than anything this port changes. This is not a claim to be every related column in the
package: these are the momentum hits a grep for `clip(lower=0)` and for `close.shift` returned
and that were read in this session.

### The recommendation

**RECOMMENDED: SKIP `G191_110_20` as question-redundancy.** Ranked, not hedged, and the
reasons are the repo's own written rules plus the owner's own precedent:

* **The owner has already dropped a sibling of this exact formula shape, against this exact
  comparator.** `docs/issues/screen/candidates.csv:36` (gitignored tracker, read in this
  session): `g191_052`, "CR energy index (26)",
  `SUM(MAX(0,H-DELAY(TP,1)),26) / SUM(MAX(0,DELAY(TP,1)-L),26) * 100` — this formula with the
  typical price `(H+L+C)/3` in place of `C` — Gate E **0.9063** pooled / **0.9173** per-frame
  vs `brar_BR_26`, fork overlap **0.9208** vs `brar:BR_26`, `fork_verdict` **FORKDUP**,
  `status` "dropped: Gate E STRUCK". `cand_pairs.csv:54` puts `g191_052` at 0.8126 against `g191_110`.
  Read honestly in BOTH directions: the band is what dropped `g191_052` (0.9063 ≥ 0.90) and
  the band is also what let `g191_110` through (0.8860 < 0.90), and the owner filed #84 with
  that 0.8860-vs-`brar_BR_26` number in its own text. The same `fork_verdict` column reads
  **`new`** for `g191_110` (`candidates.csv:47`, whose `status` is "issue 083"), and the
  issue's own text concludes "max \|ρ\| 0.8810
  vs `brar:BR_26`, per-frame max median 0.8787 → **not a restatement at the 0.90 line**" —
  the owner's only written finding about THIS candidate, and it is adverse to this
  recommendation. It is adverse on a comparison this section does not make, though: the
  screen compared the shipped DEFAULT 26 against this 20, and the same-length identity
  measured above was never in its view. So the owner's process already distinguished the two
  — which is exactly why this is a judgement call and not a gate verdict. But the shape the
  screen called a `brar:BR` duplicate is this shape.
* **The engine's own ML register already marks the column this port restates REDUNDANT.**
  `docs/indicators/brar.md:58-59` (committed; the verdict column is copied verbatim from
  `../Backtesting/Backtesting/docs/IndicatorMLRegister.md`): `AR_26` → "REDUNDANT (as
  `brar_AR_26`)", `BR_26` → "REDUNDANT (as `brar_BR_26`)". The keep case therefore asks the
  owner to add a second copy of a column the engine has already down-weighted.
* CLAUDE.md's ML contract: "Non-redundant. A column that restates a shipped column
  double-weights one signal in the miner." This column does not merely correlate with a
  shipped column — at the same length it IS one, to Spearman 1.0 and one ulp.
* CLAUDE.md again: "Deleting an over-correlated column you just built is the expected
  outcome, not a failure."
* The owner's own precedent is a *weaker* case than this one. `tests/test_altport2_ports.py`
  records three ALTPORT-1 question-redundancy skips at **0.834724** (`C_HVOL_20` vs `natr`),
  **0.874411** (`C_PB_WIDTH_PCT` vs `natr`) and **0.889416** (`C_WAD_BAR_SF` vs
  `percent_return`) — all DIFFERENT formulas that merely correlated. This candidate is
  **0.8860** against `brar_BR_26` *and* algebraically the same formula. It sits inside that
  band on strictly stronger grounds.
* The keep case cannot name the new QUESTION. `brar`'s `BR` already IS "did buyers push
  further past yesterday's close than sellers did"; what `G191_110_20` adds is a 20-bar
  window instead of 26, and the length sweep above shows 19/20/21 are mutual near-duplicates
  with a smooth decay, so 20 is not a distinguished point. The port's other differences from
  `brar` — (d) `inf → NaN`, (e) the `length + 1` history guard, (f) a working `offset`,
  (g) no `scalar`/`drift` — are better BEHAVIOUR on the same question, not a different
  question, and (d)-(f) are arguments for fixing `brar`.

**Why the port is nevertheless shipped rather than reverted.** Two reasons, neither of them
evidence about redundancy. First, the bands decide what a session may remove: Gate E measured
**DISCLOSE_GAP**, not STRUCK, so the column is not removable on a gate verdict, and the
receipt session's rule is that only a STRUCK column is removed. Second, the skip case is a
question-redundancy judgement against `brar(length=20)` — a column that is NOT in the
comparator set, as the run now shows — so it is the owner's call, not a gate's. The port
therefore ships with the recommendation standing, and the revert list is below. (An
earlier draft of this file also argued that reverting would "discard the Gate E measurement
the issue asks for" as if that were a reason to KEEP the column — it is not, and the section
above explains why: if the inference about the comparator set holds, Gate E's verdict is
uninformative on the only open question. The claim was removed in review round 1.)

The counter-case, stated so the owner is not reading a one-sided file: it is the source
formula, correctly ported, at the length the GTJA191 report states; Gate E's bands say
DISCLOSE_GAP, not STRUCK; the shipped `BR_26` is a different window; and the port, unlike
`brar`, replaces `+-inf` with NaN, guards its history correctly and has a working `offset`.
If the owner wants a 20-bar `BR` in the miner, this module is the better-behaved way to get
one — but that is an argument for fixing `brar`, which this session may not touch, and it has
to be weighed against `docs/indicators/brar.md:59`: the engine's register already calls
`brar_BR_26` REDUNDANT, so "a better-behaved second copy" of it is still a second copy.

This session could not ask (the issue-solver run is headless and `AskUserQuestion` is
unavailable); the ruling is logged as ASSUMPTION 2 in
`docs/reviews/auto-2026-11-11-g191-110/00-manifest.md`. **The revert, if the owner takes the
recommendation:** delete `pandas_ta/momentum/g191_110.py`, its line in
`pandas_ta/momentum/__init__.py`, its `Category["momentum"]` entry in `pandas_ta/__init__.py`,
its accessor in `pandas_ta/core.py` and `tests/test_g191_110.py`; revert the four count edits
(`README.md`'s headline and `momentum` row, `docs/IndicatorDictionary.md` by regenerating,
`docs/MLCompanionContract.md`'s tag count, `tests/test_altport2_ports.py`'s `CATEGORY_TOTAL`);
keep THIS file and `docs/measure_g191_110.py` as the receipt. The issue's own "Done when"
says a measured revert closes #84 exactly as well as a ship.

## Edge cases, measured rather than claimed

| case | measured |
|---|---|
| an unbroken 20-bar run of gap-ups (every low above its prior close) | the denominator is exactly 0, the raw ratio is `inf` on **20 of 40** bars, and the column fires on **0 of 40**: an EXTREME reported as MISSING, indistinguishable downstream from a short history. This is where the column's `sdiv` throws information away, and the spelling comes from the prototype's `sdiv`; the frozen-frame row below is the other NaN-for-a-determinate-state case. `brar`'s `BR_20` on the same frame leaves the **20** `inf` values in place instead — measured, the two modules genuinely differ here |
| the same frame with ONE bar dipping below its prior close (index 30) | **10 of 40** bars fire, the first at **30** and the last at **39** — exactly the windows containing the rescuing bar |
| an all-gap-DOWN frame (no high clears its prior close, every low breaks it) | the numerator is exactly 0, so the column is exactly **`0.0`** on all **20 of 40** fired bars — its floor, and CONSTANT on such a frame, which the ML contract says is not a feature |
| a frozen frame (`H == L == C`, constant) | numerator and denominator are both 0, so the division is `0/0` — NaN directly, with **0** `inf` values to replace and **40 of 40** bars NaN. The `.replace()` is not what carries this case |
| one NaN planted in `high` at index 700 of the 1,500-bar walk | exactly **20** bars emptied and **0** displaced — a trailing `rolling().sum()` propagates a NaN and carries no state past its own window, unlike an `ewm`-based port, whose state outlives it — measured on the sibling `g191_188`, where one NaN at 700 displaced 167 later bars (`docs/G191188Measured.md`); no survey of the other `ewm`-based ports was run |
| one NaN planted in `close` at index 700 | exactly **20** bars emptied — that close is read only as bar 701's `C1` |
| the `length` guard's spelling | `int(length) if length and length > 0 else 20`. Two greps over the fork's `g191_*` modules, counting the assignment form only (not docstring mentions): `…length > 0 else` appears **31** times in **16** OTHER modules, `…length > 1 else` **24** times in **18**, **5** modules use BOTH (`g191_023`, `g191_044`, `g191_160`, `g191_174`, `g191_191`) and `g191_098` uses a third spelling (`>= 1`) — so `> 0` is the fork's commonest window guard, NOT a departure from it. Narrowed to the parameter spelled exactly `length` the split reverses: **3 of 15** others use `> 0` (`g191_002`, `g191_003`, `g191_080`), **12** use `> 1`. `> 0` is kept because `length=1` is legal and defined for this formula, where a `> 1` guard would silently substitute 20 for a caller who asked for 1; the cost is the open `0 < length < 1` band two rows below, which `> 1` would have closed |
| `length=0` or any negative | falls back to the default 20 (the value is falsy or fails `> 0`), bit-identical to the default call |
| `0 < length < 1` | **nothing raises**: the guard passes, `int()` truncates to `0`, and a zero-width `rolling(0, min_periods=0).sum()` is not NaN but `0.0` — measured, `0.0` on all 1,500 bars with 0 NaN — so the ratio is `0/0` and an ALL-NaN column ships under the name `G191_110_0`. Unguarded, disclosed, pinned |
| `length=1` | legal and degenerate rather than empty: **1,045 of 1,500** bars fire (those whose single bar's low broke its prior close) and **430** of them are exactly `0.0` (the bar's high never cleared it) |
| misaligned `high`/`low`/`close` indexes | raises `ValueError` — a pressure ratio read off misaligned series is a silent nonsense number |

## Gate F: the suite run

`python -m pytest -q --tb=no -p no:warnings -rf` in this worktree, the receipt session's run
after the ledger row landed (2026-11-11): **3 failed, 5384 passed, 83 skipped** (107.95s). The
porting session's run, before the row, read **3 failed, 5377 passed, 83 skipped** (108.35s) —
INFERRED, not measured: the 7 extra passes are `tests/test_gate_e_ledger.py`'s per-row
parametrised checks for the new row, since the ledger row is the only change between the two
runs that a test reads, and that module parametrises over the ledger's rows. Measured:
`tests/test_gate_e_ledger.py` on its own is **1 failed, 778 passed**.
`tests/test_g191_110.py`: **37 passed**. The three failures, none caused by this port:

1. `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` — the known break
   CLAUDE.md documents (commit `8d8f705` untracked the `docs/pine/` corpus the citations point
   at). Fails on a clean checkout, deselected in CI.
2. `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` —
   PRE-EXISTING: it needs the sibling `../AlternativeRepos` checkout, which this worktree does
   not have. Deselected by name in CI (CLAUDE.md, "CI").
3. `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` — now fails
   with `no Gate E ledger row for ['mtd_ret']` only: the PRE-EXISTING `mtd_ret` (issue #206).
   `g191_110` is off that list since the row landed; the porting session's run read
   `['g191_110', 'mtd_ret']`. `GATE_E_PENDING_OK=1` turns the remaining one into a skip on the
   way to `dev`.

The parent repo (`Backtesting`) suite is run by the launcher in a clean worktree; this session
may not read `../Backtesting` at all.

## Review

Reviewed by `/brutally-honest-review --auto` (Mode C, one task, Fletcher gate), **four rounds,
all four REVISE** — the cap. The run folder is `docs/reviews/auto-2026-11-11-g191-110/`:
`00-manifest.md` (task, assumptions, execution map), `01-g191-110.md` (every review round
verbatim and the fixes applied) and `99-summary.md` (the run table and what is left open).
**Round 4's fixes landed with the cap spent and were NOT re-reviewed**; `99-summary.md` says
exactly which text that is. Across all four rounds not one finding was a mathematics error:
every round reproduced every number and failed the prose around it — four rounds of punished
absolutes, each one introduced by the previous round's own replacement text.

Provenance of the numbers in this file: each is either printed by
`python docs/measure_g191_110.py` / `python -m pytest -q` in this session, or cited to the
committed file it was read from (`docs/gate_e_ledger.csv`, `CLAUDE.md`,
`tests/test_altport2_ports.py`, `docs/indicators/brar.md`, `pandas_ta/momentum/brar.py`), or
labelled a PRIOR from the issue's own 2026-10-24 screen (whose artifacts are in the gitignored
tracker and are not in a clone). The `length`-guard split in the edge-case table comes from the
two greps quoted there.
