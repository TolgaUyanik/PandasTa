# g191_145 — measured (issue #78)

> **Status: Gates A–E cleared, wired, tests green. Gate E measured 2026-11-11 by the
> issue-solver launcher: `G191_145_9_26_12` max \|ρ\| **0.8359** vs `pvo_PVO_12_26_9`
> (compute_all, n = 396,588), per-frame max median **0.8432** over 89 frames →
> **DISCLOSE_GAP** — the column ships with disclosure, no strike, no waiver. Gate F: this repo
> green except the pre-existing breaks listed below; the parent repo is the launcher's run, not
> this session's.**

Volume oscillator 9/26 over 12: Guotai Junan's (2017, "GTJA191", internal quant report; the
issue cites the HKUDS/Vibe-Trading copy, MIT, which this session could not read — see Gate A)
alpha `#145`, per issue #78. Module `pandas_ta/volume/g191_145.py`, column
`G191_145_9_26_12`. Tests: `tests/test_g191_145.py` (23, all passing). Numbers below:
`python docs/measure_g191_145.py` and `python -m pytest -q`. Four exceptions, each named where
it appears and listed here so the sentence is not a blanket one: the Gate E numbers, which come
from the launcher's own run (`gatee/is78-g191_145-88681c5e`, `overlap_max.csv` and `meta.json`)
and not from this worktree; the **563**-line dictionary count, which is `python docs/gen_indicator_dictionary.py`'s
own output; the **5162** suite baseline, quoted from `docs/G191040Measured.md` and not re-run
here; and the prototype-screen figures (0.8359 / 0.8432 / 396,588 / 398,849 / 0.8165 / 0.7616),
quoted from issue #78. Environment: this worktree's pinned pandas/numpy (2.3.3 / 1.26.4).
Measured 2026-11-11.

## Gate A: derivation from the published formula, not the prototype

Issue #78 states GTJA191 alpha `#145`:

    #145: (MEAN(V,9)-MEAN(V,26))/MEAN(V,12)*100

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access are both
unavailable in this worktree, so the issue's own named copy — HKUDS/Vibe-Trading (MIT) — was
never read. Everything below is derived from the issue's own stated formula string, per the
issue's own instruction ("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype (`docs/issues/screen/ind_screen.py:494-495`):

    @cand("g191_145", "volume oscillator 9/26 over 12", G,
          "#145: (MEAN(V,9)-MEAN(V,26))/MEAN(V,12)*100")
    def _(o, h, l, c, v): return 100 * sdiv(mean(v, 9) - mean(v, 26), mean(v, 12))

Operator by operator, each spelling read off the prototype's own (unambiguous) module source:

| token | reading | where the reading comes from |
|---|---|---|
| `MEAN(X, n)` | `X.rolling(n).mean()`, a trailing SIMPLE moving average | `ind_screen.py:47` |
| `V` | volume; **no price input appears in the formula at all** | the formula string itself |
| `sdiv(a, b)` | `(a / b).replace([inf, -inf], nan)` | `ind_screen.py:41-42` |
| `/ … * 100` | left-to-right: `((A - B) / C) * 100` — divide first, scale second | `ind_screen.py:494-495`, whose `100 * sdiv(A-B, C)` fixes divide-first. C-family precedence gives the same reading, and the two spellings are measured bit-identical (table below). **The report's own precedence rules were not read** — nobody here could open it |

`MEAN` is **not** GTJA191's own `SMA(A,n,m)` recursion, which the report spells differently and
which `ind_screen.py:57-59` renders as `ewm(alpha=m/n)`. This is the whole difference against
the nearest shipped column — see **Non-redundancy** below.

**No disclosed interpretation choice is needed anywhere in this port**, and that is measured,
not asserted: the port and the prototype agree **bit-for-bit** on the whole 1,500-bar frame —
`mask-equal=True`, `n_both=1475`, `max|diff| = 0.0`, `bit-identical=True`
(`python docs/measure_g191_145.py`).

That comparison is run against the **real candidate**, not a retyped copy of it: the script
loads `docs/issues/screen/ind_screen.py` by path, pulls `REG["g191_145"]["fn"]` out of the
prototype's own registry and calls it. It prints the retyped copy's agreement with that
candidate too (`retyped copy vs REAL candidate: mask-equal=True bit-identical=True`), so a
transcription slip cannot masquerade as agreement, and it prints
`prototype file … ABSENT (gitignored): only the retyped copy was compared` on a machine that
does not have the screen. `tests/test_g191_145.py::test_matches_the_prototype_expression_bit_for_bit`
necessarily uses the retyped form — `docs/issues/` is gitignored, so a clone running the suite
has no screen to load — and checks it on a second frame (seed 29).

`g191_040`, the sibling port of the issue before this one, could not make the bit-for-bit
claim: its `C > C1` comparison has an undefined-direction boundary at bar 0 that forced a
documented departure. This formula has no comparison in it, so it has no such boundary.

**The one association that is NOT free.** `(A-B)/C*100` can be coded three ways, and they are
not all the same in float64. Measured on the 1,500-bar frame:

| spelling | bit-identical to the shipped code? | max\|diff\| |
|---|---|---|
| `100.0 * ((A-B)/C)` — the shipped code, and the prototype's order | — (this is the baseline) | — |
| `((A-B)/C) * 100.0` — the source string's own order | **yes** | 0.0 |
| `(100.0 * (A-B)) / C` — multiply before dividing | **no** | **7.11e-15** |

Multiplication is commutative in IEEE754, so the first two agree exactly; the third rounds
after a different operation and does not. The shipped code uses the order the source string and
the prototype agree on, which is why `pandas_ta/volume/g191_145.py` writes
`100.0 * ((fast_mean - slow_mean) / norm_mean)` with the inner parentheses rather than the more
usual `100.0 * x / y` one-liner that `g191_080` uses. The residual is ~1e-15 and would change
nothing downstream; it is recorded because the alternative was to call all three identical
without checking, which is this repo's documented dominant defect.

    fast_mean = MEAN(V, 9)
    slow_mean = MEAN(V, 26)
    norm_mean = MEAN(V, 12)
    G191_145  = 100 * (fast_mean - slow_mean) / norm_mean, inf -> NaN

**Three parameters, no silent reordering** (manifest ASSUMPTION A1/A2 in
`docs/reviews/auto-2026-11-11-g191-145/00-manifest.md`). The three windows are exposed as
`fast=9`, `slow=26`, `norm=12`, defaulting to the source's own numbers, and the column name
carries all three: `G191_145_9_26_12`. Unlike `pvo`, this port does **not** swap `fast` and
`slow` when a caller inverts them — the source formula has no such rule, and a swap would
return the negation of what the caller asked for. Pinned by
`::test_the_three_windows_are_not_silently_reordered`, which asserts that inverting the two
windows negates the column exactly, bar for bar, on 300 bars.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | pass — derived from the issue's own stated formula, using the prototype's own `mean`/`sdiv` spellings; **no** disclosed interpretation choice, because the port reproduces the prototype's own expression bit-for-bit | 7-bar hand-derived example at `fast=2, slow=4, norm=3` with the arithmetic written out per bar (`tests/test_g191_145.py::test_hand_derived_seven_bars`): `result[3..6] = [33.33333333333333, 25.0, 20.0, -12.5]`, matching the module's float64 output exactly (`python docs/measure_g191_145.py`: `hand-derived bars 0..6`). Bar 6 exercises the negative branch. Matches an independent per-bar computation built from plain numpy slicing (not the module's own `.rolling()` calls) at the shipped defaults, 3 spot-checked bars (300, 600, 899) on a 900-bar synthetic volume frame, asserted at `rel=1e-9` because they do **not** all agree bit-for-bit — the slice-sum order differs from pandas' rolling mean. Per bar, from the script: bar 300 `bit-identical=True`, `\|diff\| = 0.0`; bar 600 `bit-identical=False`, `\|diff\| = 1.15e-14`; bar 899 `bit-identical=False`, `\|diff\| = 1.42e-14` (~2e-15 relative). Full reprs: `module=11.78486842895055 loop=11.78486842895055`, `module=5.819758045630176 loop=5.819758045630188`, `module=7.084239310949412 loop=7.084239310949426`. Against the REAL prototype candidate loaded out of `ind_screen.py` on the full 1,500-bar frame: `max\|diff\| = 0.0`, NaN masks equal, 1,475 overlapping bars, `bit-identical=True` |
| B Causality | pass | Future-perturbation sweep (volume rewritten from `j` onward with another synthetic series, seed 59), 34 offsets past the 25-bar warm-up: real module **0 of 34** leaks (`python docs/measure_g191_145.py`; the test file re-runs the same sweep on a 900-bar frame over `range(50, 900, 25)`). One mutant (`importlib` source read, `exec`'d in memory, the final write index shifted `slow = 26` bars into the future), shown live (differs from the real module) then caught at **34 of 34** |
| C Reachability | pass on synthetic **and** on real data: Gate E's run reports `non_nan = 396,588` and `non_zero = 396,588` of the **398,849** pooled bars over 89 BIST frames — the 2,261-bar shortfall is the per-frame 25-bar warm-up (89 × 25 = 2,225) plus 36 bars, and no bar is a non-NaN zero (`overlap_max.csv`, run `is78-g191_145-88681c5e`) | 1,500-bar synthetic volume frame (seed 97, `rng.uniform(1e4, 1e6)`, `docs/measure_g191_145.py:_volume`), shipped defaults: **1,475 of 1,500** bars non-NaN (98.33%) — exactly `n - 25`, the `max(fast, slow, norm) - 1 = 25`-bar warm-up, with **0** interior NaN bars after the first fire. **1,475 distinct values** (not a constant column), range `[-71.518821, 41.346734]`, median `0.273379`. Both signs occur, pinned by `::test_both_signs_occur` — a one-sided column would have a dead sign half. The 900-bar frame of `::test_fires_and_is_not_constant` gives `fires == 875 == 900 - 25`, likewise with no interior gap. Real data: the Gate E run's own counts, quoted in the Result column, and `tests/test_gate_e_ledger.py::test_every_column_fires_on_real_data[g191_145:G191_145_9_26_12]` re-checks them off the recorded row — **passing** in this session's suite run |
| D Scale-free | pass | Algebraically, for ANY `k > 0`: `MEAN(k*V, n) = k * MEAN(V, n)`, so `100 * (k·fast − k·slow) / (k·norm) = 100 * (fast − slow) / norm` — the `k` cancels inside the division itself, not merely at powers of two. There is **no comparison operator anywhere in the chain**, so unlike `g191_040` there is no near-tie a rescale could flip; the only residual is float64 rounding from the scalar multiply. Measured on the 1,500-bar frame: volume **×8 and ×64 bit-identical, 0.0 max\|diff\|**, NaN masks equal; **×10 and ×3.7 max\|diff\| 7.11e-14** each (`bit-identical=False`, which the script prints), well under the test's `1e-6` tolerance. **No price rescale is measured, because there is none to measure**: the function's signature is `('volume', 'fast', 'slow', 'norm', 'offset')` — the script prints it — so a price column cannot reach the result. `::test_no_price_input_so_a_price_scale_cannot_reach_the_column` asserts that signature AND drives the `df.ta` accessor on a frame whose OHLC columns are all multiplied by 7.3, where the output stays bit-identical. `0 < 1,475 fires < 1,500` and `1,475 > 1` distinct values rule out a constant column. **Zero-denominator**: see the section below |
| E Attribution | **DISCLOSE_GAP** — ships with disclosure, no strike | `G191_145_9_26_12`: pooled max \|ρ\| **0.835858534426807** vs `pvo_PVO_12_26_9` (compute_all), n = **396,588**; per-frame max median **0.8432316009538046** vs the same comparator over **89** frames, **0.0%** of frames at \|ρ\| ≥ 0.90. Manifest leg: **0.8164992072362767** vs `pvo_PVO_12_26_9_Pctl`, n = 391,337. Both the pooled and the per-frame leg land in `0.80 ≤ \|ρ\| < 0.90`, so the band is DISCLOSE_GAP under `r3-perframe-0.90`. Run `is78-g191_145-88681c5e`, measured 2026-11-11 by the launcher; ledger row in `docs/gate_e_ledger.csv`. Section below |
| F Suites | this repo only; the parent repo (`Backtesting`) is the launcher's clean-worktree run | `python -m pytest -q` (this session): see **Suite run** below |

## Zero-denominator: three cases, all pinned, none reached by the measured frames

For a **non-negative** volume series — the only input this column is defined for, and not
something the function enforces — `MEAN(V, norm)` is zero exactly when every one of the `norm`
bars in its window has `V = 0`, since no cancellation can produce a zero mean any other way.
That is a halted or zero-turnover stretch at least `norm` bars long. (Hand it a **signed**
volume series instead — this fork ships `vol_delta` and `vsumd`, which a caller could pass —
and both that statement and the first case's sign argument stop holding. The `inf -> NaN`
guard still fires; the three cases below are simply no longer the only ones.) It splits into
three cases with **different arithmetic**, which is why there are three fixtures and not one:

| case | fixture | what the shipped code returns | with the `.replace([inf,-inf], nan)` deleted (a live mutant) |
|---|---|---|---|
| `fast <= norm`, the `slow` window still carries volume → `negative / 0 = -inf` | `fast=2, slow=4, norm=3`, `volume = [10, 20, 0, 0, 0]`, bar 4 | `nan` | `-inf` |
| every window all-zero → `0 / 0` | `fast=2, slow=4, norm=3`, `volume = [0, 0, 0, 0, 0]`, bars 3–4 | `nan` | `nan` (never `±inf`) |
| `fast > norm`, so the numerator can be **positive** → `+inf` | `fast=4, slow=6, norm=2`, `volume = [0, 0, 0, 1000, 1000, 0, 0]`, bar 6 | `nan` | `inf` |

**The third case is a consequence of making the three windows caller-settable, and it is
unreachable at the shipped defaults** (`fast = 9 <= norm = 12`, so a zero `norm` window forces a
zero `fast` window and the numerator cannot be positive). It is measured anyway rather than
reasoned about: at `fast=4, slow=6, norm=2` on `[0,0,0,1000,1000,0,0]`, bar 6's norm window is
`[0,0]` while its fast mean (500) exceeds its slow mean (333.33), and the script prints
`fast>norm positive-numerator bars 0..6: [nan, nan, nan, nan, nan, 33.333333333333336, nan] |
with the replace deleted: [… , inf]`.

In the first and third cases a neighbouring bar stays **finite** — `-112.5` at bar 3 and
`33.333333333333336` at bar 5 respectively — which is what makes the NaN attributable to the
branch rather than to a warm-up gap. The mutant column is how all three are shown: an
`importlib` source read `exec`'d in memory, not a re-typed copy of the module's own arithmetic,
which would prove nothing. Pinned by `::test_zero_volume_window_divides_to_nan`,
`::test_all_zero_volume_divides_zero_by_zero_to_nan` and
`::test_fast_above_norm_can_divide_a_positive_numerator_by_zero`; all three also printed by
`docs/measure_g191_145.py`.

**Neither measured frame reaches the branch, and this is measured rather than assumed:** both
draw volume from `rng.uniform(1e4, 1e6)`, and the script prints `zero_volume_bars=0` on the
1,500-bar frame while `::test_fires_and_is_not_constant` asserts `(volume == 0).sum() == 0` on
the 900-bar one. The other synthetic frames in those two files are not checked for it. **How
often this happens on real data is not isolated by anything this session ran** — that waits on
Gate E, the only real-data run in this protocol.

## NaN propagation

A single NaN volume at bar `t` blanks the output over `t … t + slow − 1`:
`rolling(n, min_periods=n)` refuses any window containing it, and the slow window is the
widest, so it is the last to stop reading bar `t`. That span is `max(fast, slow, norm) = 26`
bars **in the interior** and shorter near either end, where it runs off the frame or overlaps
the warm-up. All three measured on the 1,500-bar frame
(`python docs/measure_g191_145.py`):

| hole at | newly-NaN output bars | span | why not 26 |
|---|---|---|---|
| 700 (interior) | **26** | `700..725` | — |
| 1495 (near the end) | **5** | `1495..1499` | the rest of the span runs off the frame |
| 10 (inside the warm-up) | **11** | `25..35` | bars `10..24` were already NaN |

For the interior hole the script also reports **0** bars newly defined and, of the **1,449**
bars that stay defined, a largest move of **4.97e-14** — `bit-identical=False`, which it prints
explicitly. That residual is pandas' rolling mean accumulating in a different order once a NaN
sits in the series, not a semantic change. Pinned by
`::test_a_nan_volume_blanks_only_the_windows_that_contain_it`, which uses an interior hole (bar
150 of 300), asserts the NaN mask exactly and checks the surviving bars at `rtol=1e-9` rather
than at equality.

No explicit mask is needed in the module for this, unlike `g191_040`: that port's two
comparisons silently evaluate `False` against a NaN, so it had to mask by hand. Three rolling
means propagate NaN by construction.

## Non-redundancy against the nearest already-shipped column

Not a numbered gate, but one of the three pillars of `CLAUDE.md`'s ML feature contract. The
nearest shipped column is `pvo`'s `PVO_12_26_9` — the same *shape* (a fast/slow volume-average
spread, scaled to a percentage), built three ways differently:

| | `G191_145_9_26_12` | `PVO_12_26_9` |
|---|---|---|
| averaging kernel | simple moving average | exponential moving average |
| fast window | 9 | 12 |
| denominator | `MEAN(V, 12)`, a **third independent window** | the slow EMA itself, `EMA(V, 26)` |

The third row is structural, not just a parameter difference. `PVO` is
`100 * (fast − slow) / slow`, a self-normalised spread bounded below by `−100`; this column
divides by an independent 12-bar mean, so it is unbounded below and its denominator can be zero
while its numerator is not (the first zero-denominator case above), which `PVO`'s cannot —
`EMA(V,26) = 0` forces every input to zero.

Measured on the 900-bar synthetic volume frame (seed 13, 875 overlapping bars,
`python docs/measure_g191_145.py`), against three neighbours that isolate one difference at a
time:

| pair | Spearman ρ | n |
|---|---|---|
| `G191_145_9_26_12` vs `PVO_12_26_9` (the shipped column) | **0.743004** | 875 |
| `G191_145_9_26_12` vs `PVO_9_26_9` (same windows, EMA, self-normalised) | **0.686191** | 875 |
| `G191_145_9_26_12` vs the same three windows built from EMAs | **0.682165** | 875 |

So on this frame neither the averaging kernel nor the denominator choice alone accounts for the
gap. **These are synthetic numbers on one frame and they decide nothing** — real-data overlap
against the engine's 687 comparators is Gate E's.

**The real-data figure is now measured, and it confirms the prototype prior.** Issue #78
recorded, for the `g191_145` prototype: max \|ρ\| 0.8359 vs `pvo_PVO_12_26_9` (compute_all,
n = 396,588), top-5 per-frame max median 0.8432 → DISCLOSE_GAP; next comparators
`pvo_PVO_12_26_9_Pctl` 0.8165 and `pvo_PVO_12_26_9_State` 0.7616; run `screen_20261024`, 89
ALTPORT-1 frames, 398,849 bars, 329 + 358 comparators, canary bit-equal. The launcher's run on
the port lands on the same comparator with the same pooled and per-frame figures and the same
band — see the Gate E section. A prototype is not a port, but here the port reproduces the
prototype's expression bit-for-bit (Gate A above), and the two measurements agree.

## Gate E: measured — DISCLOSE_GAP, the column ships with disclosure

Run by the issue-solver launcher, not by the session that wrote the port:
`gate_e_overlap.py run --module pandas_ta.volume.g191_145`, outputs
`gatee/is78-g191_145-88681c5e`. Every figure in this section is read off that run's
`overlap_max.csv` and `meta.json`; nothing here was computed in this worktree.

| column | max \|ρ\| | against | set | n | per-frame max median | per-frame comparator | frames | % frames ≥ 0.90 | verdict |
|---|---|---|---|---|---|---|---|---|---|
| `G191_145_9_26_12` | **0.835858534426807** | `pvo_PVO_12_26_9` | compute_all | **396,588** | **0.8432316009538046** | `pvo_PVO_12_26_9` | **89** | **0.0** | **DISCLOSE_GAP** |

Per leg, from the same row: compute_all **0.835858534426807** vs `pvo_PVO_12_26_9`
(n = 396,588); manifest **0.8164992072362767** vs `pvo_PVO_12_26_9_Pctl` (n = 391,337). The
pooled-only verdict is DISCLOSE_GAP as well, so the per-frame leg did not change the band.

**Band, applied to the measured numbers** (`CLAUDE.md`, Gate E row, bands `r3-perframe-0.90`):
STRUCK needs pooled \|ρ\| ≥ 0.90 **or** a top-5 comparator's per-frame median ≥ 0.90. Measured:
pooled 0.8359 < 0.90 and the per-frame max median 0.8432 < 0.90, with 0.0% of the 89 frames at
or above 0.90. Both land in `0.80 ≤ \|ρ\| < 0.90`, so the verdict is **DISCLOSE_GAP**: the
column ships with this disclosure, it is **not** struck, and it needs **no waiver**.

Run facts, from `meta.json`: **89** frames, **398,849** pooled bars, **329** compute_all +
**358** manifest = **687** comparators, canary `AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS bit-equal`,
no excluded comparators, default parameters (`kwargs: {}`), data stamp
`1be6495ef7095ff67ad8f59a2fc0311d74f02652`, pandas 2.3.3 / numpy 1.26.4, module sha1
`6a4a91351de17b1965b5579d70d7c4301eaf68ab`, tree sha1
`a08796e688f5bc5093163b515c79899fc60b5253`. One comparator was degenerate on this column
(`n_degenerate = 1`) and is excluded from the maximum by the harness.

**Against the prototype prior.** Issue #78's prototype screen recorded max \|ρ\| 0.8359 vs
`pvo_PVO_12_26_9` at n = 396,588 with a top-5 per-frame max median of 0.8432 — the port's
measured numbers above match that prior to every digit the issue quoted, which is what Gate A's
bit-for-bit agreement with the prototype expression predicted.

The ledger row is recorded with
`python docs/gate_e_ledger.py record /home/tolga/.issue-solver/runs/20261111-020111-78/gatee/is78-g191_145-88681c5e --measured 2026-11-11`
(`docs/gate_e_ledger.csv`), which printed
`g191_145:G191_145_9_26_12 DISCLOSE_GAP 0.8359 vs pvo_PVO_12_26_9 -> docs/gate_e_ledger.csv`.
`record` compares the run's `pandas_ta_src_sha1` against this tree and refuses a non-default
parameter set, a universe other than the 89 frames, a comparator set other than 687, or a canary
that is not bit-equal; it did not refuse.

## Wiring

`Category` **312 → 313** (`volume` **41 → 42**); `df.ta.<name>()` accessor count **320 → 321**.
Touch points, all five: `pandas_ta/volume/g191_145.py` (module), `pandas_ta/volume/__init__.py`
(export), `pandas_ta/__init__.py` → `Category["volume"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.g191_145` (accessor), `tests/test_g191_145.py` (tests). `README.md`'s
headline counts and its `volume (42)` row are updated and checked by
`tests/test_readme_counts.py`. `docs/IndicatorDictionary.md` is regenerated with
`python docs/gen_indicator_dictionary.py` (563 lines; the new row probes as
`G191_145_9_26_12 SF`, warm-up 25, inputs `V`). `docs/MLCompanionContract.md`'s running tag
count is updated **657 → 658 / 300 → 301 `SF`**, which
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`
re-derives from the dictionary. `tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` goes
**312 → 313** and `CATEGORY_BUCKETS["volume"]` **41 → 42**.

## Suite run (this repo)

`python -m pytest -q`, full suite, default collection order, re-run in the receipt session after
the Gate E row was recorded: **3 failed, 5193 passed, 83 skipped** (106.57s).
`g191_145`'s own tests (`tests/test_g191_145.py`): **23 passed**. The three failures:

- `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` — needs
  the sibling `../AlternativeRepos` checkout, absent in this worktree (CI deselects it by
  name). Pre-existing.
- `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` — the untracked
  `docs/pine/` corpus, `8d8f705` (`CLAUDE.md`, "Known breaks"). Pre-existing.
- `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` — now owed for
  `['mtd_ret']` only, quoted verbatim from this session's run:
  `no Gate E ledger row for ['mtd_ret']`. `mtd_ret` pre-dates this issue and is the owner's to
  record; `g191_145` dropped out of that list when its row was recorded. Pre-existing.

No other test regresses. The passing count is **31** above the **5162** the `g191_040` session
recorded in `docs/G191040Measured.md` for the same suite (that baseline is quoted from that
file, not re-run here). The 31 decompose as the **23** tests of `tests/test_g191_145.py` plus
the **8** parametrized ledger tests the recorded row switches on —
`python -m pytest tests/test_gate_e_ledger.py -k g191_145 --collect-only -q` lists exactly
those 8, among them `test_verdict_follows_the_bands[g191_145:G191_145_9_26_12]` (the band
arithmetic re-derived from the row) and
`test_every_column_fires_on_real_data[g191_145:G191_145_9_26_12]`, both passing. Before the row
existed the same command listed **1**
(`test_every_new_indicator_has_gate_b_and_d_tests[g191_145]`), which is the **5186** the port
session recorded.

## Review history

`/brutally-honest-review` rounds (Mode C, one Fletcher reviewer subagent per round, each
reading the files cold, each re-running `docs/measure_g191_145.py` and the suites itself). Run
folder: `docs/reviews/auto-2026-11-11-g191-145/` — `00-manifest.md` (tasks, the five
ASSUMPTIONs taken because `AskUserQuestion` is unavailable here, the execution map),
`01-g191-145.md` (each round's verdict verbatim plus the fixes applied), `99-summary.md`. Four
rounds, all four PASS, 14 findings, **0 CRITICAL and 0 MAJOR**. No round found a mathematics
error; every finding was prose standing in front of, or wider than, its measurement. This
table is the audit trail, not the evidence — each fix now lives in the gate section named
beside it.

| round | date | findings | what they were | where the fix lives now |
|---|---|---|---|---|
| 1 | 2026-11-11 | 6 (0 CRITICAL, 0 MAJOR, 5 MINOR, 1 NIT) | a test-file header crediting itself with a 1,500-bar frame it never builds; "NOT bit-identically" stated flatly where the script's own reprs show bar 300 agreeing exactly; a blanket "every number comes from the script" with three undeclared exceptions under it; a precedence rule attributed to the GTJA191 report, which nobody here could read; Gate A's strongest claim resting on a **retyped** copy of the prototype while the real `ind_screen.py` sat on disk; NIT: the zero-denominator claim stated an input-domain assumption (non-negative volume) as a property of the code | test-file header and `test_matches_an_independent_loop_at_defaults`; the Gate A row's per-bar `bit-identical` / `\|diff\|` figures; this file's provenance sentence; the Gate A operator table's precedence row; `_screen_prototype()` in `docs/measure_g191_145.py` plus the Gate A section above; the ZERO-DENOMINATOR paragraph of the module docstring and the section below Gate D |
| 2 | 2026-11-11 | 3 (0 CRITICAL, 0 MAJOR, 1 MINOR, 2 NIT) | MINOR: this very **Review history** table still said no round had happened while the run log beside it recorded one, and it listed a `99-summary.md` that did not exist — the same cross-file drift that bled `g191_040` for four rounds; NIT: "a NaN blanks exactly 26 bars" is true only in the interior, false at both ends; NIT: "TWO cases" of a zero denominator is exhaustive only while `fast <= norm`, and a third `+inf` route exists once a caller sets `fast > norm` | this table and `99-summary.md`; the NaN-propagation section's three-row measured table (holes at 700 / 1495 / 10) and the module's WARM-UP paragraph; the three-row zero-denominator table, the module's ZERO-DENOMINATOR paragraph, and the new `tests/test_g191_145.py::test_fast_above_norm_can_divide_a_positive_numerator_by_zero` |
| 3 | 2026-11-11 | 2 (0 CRITICAL, 0 MAJOR, 1 MINOR, 1 NIT) | MINOR: round 2's own fix never re-counted its own enumeration — the zero-denominator section heading still said "**two** cases, **both** pinned, **neither** reached" directly above a three-row table, and two test docstrings still said "two" while the module said three; NIT: the new third-case test's closing line read as if the SHIPPED code returns `+inf` when it returns NaN | the zero-denominator heading and its introducing sentence here; `::test_zero_volume_window_divides_to_nan`'s "First of the three", `INF_REPLACE_MUTANT`'s comment, and `::test_all_zero_volume_divides_zero_by_zero_to_nan`'s "two different routes" (a fourth site the finding did not list, found by running its own suggested grep over the four files carrying the change's claims); `::test_fast_above_norm_can_divide_a_positive_numerator_by_zero`'s closing sentence |
| 4 | 2026-11-11 | 3 (0 CRITICAL, 0 MAJOR, 2 MINOR, 1 NIT) | MINOR: rounds 1's and 2's retractions reached the module's prose docstring and this file but stopped at the public `g191_145.__doc__`, 150 lines below them in the same module — the one string `help()` and the dictionary generator read still said a flat 26 NaN bars and glossed a zero `norm` mean as a halt with no non-negativity qualifier; MINOR: the run log claimed a grep "over all seven files" two paragraphs above the record of that grep, which names four; NIT: five lines of this file restated the review harness's own round-cadence rule, already in `00-manifest.md` | the "Returns:" block of `pandas_ta/volume/g191_145.py` (and `docs/IndicatorDictionary.md`, regenerated from it); `01-g191-145.md`'s wording, plus the owed sweep of the three review files, now run and recorded there; the five lines deleted from this section |

Round 4 is the cap (one round plus three re-runs). Its three findings were applied rather than
left standing, because all three were documentation strings measured to be wrong; no code was
touched. The **Suite run** section above is the run made after those edits.

**Receipt session (2026-11-11), after the launcher's Gate E run.** No review round: the session's
only changes are the recorded ledger row (`docs/gate_e_ledger.csv`) and this file's Gate C / Gate
E / suite-count sections, rewritten from the run's `overlap_max.csv` and `meta.json`. No module,
test or wiring file was touched — the ledger pins the module sha1
`6a4a91351de17b1965b5579d70d7c4301eaf68ab` and the output fingerprint of the measured code, so
editing either would fail `test_row_still_describes_its_module` / `test_row_output_has_not_moved`
(both passing here).
