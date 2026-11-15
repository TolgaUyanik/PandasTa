# g191_040 — measured (issue #77)

> **Status: Gates A-E cleared, wired, ships. Gate E measured by issue-solver on 2026-11-11 (run
> `is77-g191_040-b7322f17`): `G191_040_26` max \|ρ\| **0.8268** vs `OBV_Slope_norm`,
> verdict **DISCLOSE_GAP** — the column SHIPS with disclosure, no strike, no waiver. Gate F:
> this repo green except the pre-existing breaks listed below; the parent repo is the launcher's
> run, not this session's.**

Up-volume / down-volume ratio (VR): Guotai Junan's (2017, "GTJA191", internal quant report; the
issue cites the HKUDS/Vibe-Trading copy, MIT, which no session here could read -- see Gate A)
alpha `#40`, per issue #77's own instruction. Module
`pandas_ta/volume/g191_040.py`, column `G191_040_26`. Tests: `tests/test_g191_040.py` (25, all
passing). Numbers below: `python docs/measure_g191_040.py`, except the Gate E section and the
real-data half of Gate C, which are issue-solver's run. Environment: this worktree's pinned
pandas/numpy. First measured 2026-11-10; re-measured and extended 2026-11-11. The 2026-11-10
session stopped on a usage limit before it could commit, so a second session re-ran `python
docs/measure_g191_040.py`, `python -m pytest tests/test_g191_040.py -q`, `python -m pytest -q`
and `python docs/gen_indicator_dictionary.py`, reproduced every figure the first session had
quoted (the regenerated dictionary differed only in its own probe-run date), then ran three
further `/brutally-honest-review` rounds and added the measurements they demanded. Each round's
findings, and the gate section that now carries the measurement, are in **Review history** at the
end of this file.

## Gate A: derivation from the published formula, not the prototype

Issue #77 states GTJA191 alpha `#40`:

    #40: SUM(C>C1 ? V : 0, 26) / SUM(C<=C1 ? V : 0, 26) * 100

**What this session could NOT do, disclosed up front:** `docs/pine/` and web access are both
unavailable in this worktree, so the issue's own named copy -- HKUDS/Vibe-Trading (MIT) -- was
never read. Everything below is derived from the issue's own stated formula string, per the
issue's own instruction ("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype (`docs/issues/screen/ind_screen.py:350-354`):

    @cand("g191_040", "up-volume / down-volume ratio (VR)", G,
          "#40: SUM(C>C1 ? V : 0, 26) / SUM(C<=C1 ? V : 0, 26) * 100")
    def _(o, h, l, c, v):
        up = c > delay(c, 1)
        return 100 * sdiv(tsum(v.where(up, 0.0), 26), tsum(v.where(~up, 0.0), 26))

using the prototype's own unambiguous spellings `delay(x, n) = x.shift(n)` (`ind_screen.py:45`)
and `tsum(x, n) = x.rolling(n).sum()` (`ind_screen.py:49`).

**DISCLOSED INTERPRETATION CHOICE** -- the one place this port deviates from the prototype, not
from the issue's own string. The prototype's down bucket is `v.where(~up, 0.0)`, "whatever `up`
is not". At bar 0, `C1 = DELAY(C, 1)` is undefined (no prior bar), and a comparison against `NaN`
evaluates to `False` under pandas/numpy, never `NaN` -- so `up` is `False` at bar 0, and `~up` is
`True` there, meaning the prototype silently counts bar 0's ENTIRE volume as a DOWN bar even
though its direction is actually unknown. This port does not repeat that: both the up-bucket and
the down-bucket are made explicitly `NaN` wherever the one-bar direction is undefined (keyed off
`close_prior.isna() | close.isna()`), so such a bar contributes to NEITHER sum, and -- because
`rolling(length, min_periods=length).sum()` requires `length` genuinely valid observations in its
window -- every window touching it comes out `NaN` too. This is the same warm-up shape this
fork's `g191_043` already ships (`min_length = length + 1`).

The mask covers BOTH closes of the comparison, not just the prior one (**round-2 review fix**). A
`NaN` at `C[t]` for `t > 0` makes `C > C1` and `C <= C1` BOTH `False` by the same pandas rule, so
without the `close.isna()` half the bar's volume would vanish from both buckets while the
`length` windows containing it kept firing over `length - 1` defined bars. `g191_043` does not
have that gap because its `signed_series(close)` is a `close.diff()` and propagates the `NaN`;
these two comparisons do not, so the mask does it explicitly. One `NaN` close blanks
`length + 1` output bars, not `length`, because it also leaves bar `t+1`'s direction undefined
(its `C1` is that `NaN`). Measured on the 1,500-bar frame with `close[700] = NaN` (`python
docs/measure_g191_040.py`): **27 newly-NaN output bars, 700..726**, **0** bars newly defined, and
of the **1,447** bars that stay defined the largest move is **5.68e-14** -- the same
rolling-accumulation-order rounding as the `[25]` comparison below, not a semantic change (they
are NOT bit-identical, and the script prints that explicitly: `bit-identical=False`). Pinned by
`tests/test_g191_040.py::test_a_nan_close_blanks_only_the_windows_that_contain_it`, which asserts
the NaN mask exactly and the surviving bars at `rtol=1e-9`.

**How the choice is pinned (round-2 review fix).** The round-1 test for this re-typed the
module's own two bucket expressions and asserted they agreed with themselves -- a mirror, not a
test: it would have passed with the indicator deleted. It is now asserted on the SHIPPED
function's own output, from both sides. At `length=3` the first full window is bar 2, and it
touches bar 0; the three readings of the same frame all differ (`python
docs/measure_g191_040.py`: `bar2 (window touches bar 0): prototype=50.0
mask-removal-mutant=66.66666666666667 shipped=nan`):

| reading | bar 2 | why |
|---|---|---|
| prototype (`v.where(~up, 0.0)`) | `50.0` = `100*20/40` | bar 0's 10 units fabricated into the DOWN bucket |
| this module with `.mask(undefined, np.nan)` deleted (a live mutant, `importlib` source read, `exec`'d in memory) | `66.66666666666667` = `100*20/30` | `C<=C1` is `False` at bar 0 exactly as `C>C1` is, so bar 0 contributes 0 to BOTH buckets and the window fires on an effectively 2-bar sample |
| shipped | `nan` | bar 0 excluded from both buckets AND from every window reading it |

Pinned by `tests/test_g191_040.py::test_bar_zero_is_excluded_from_both_buckets_unlike_the_prototype`
(prototype finite at bar 2, shipped NaN, the two equal at bars 3-5) and
`::test_mask_removal_mutant_fabricates_the_bar_zero_window` (the mutant finite at bar 2, so the
shipped NaN comes from that mask and nothing else).

**Full-series departure from the prototype, measured (round-2 review fix).** Round 1 claimed "no
column value changes for any bar whose window excludes bar 0" from two compared scalars. Measured
on the whole 1,500-bar frame (`python docs/measure_g191_040.py`): the two series' NaN masks
disagree at **exactly one index, `[25]`** -- the single full `length`-bar window that touches bar
0 -- and where both are defined, `max|diff| = 2.84e-14`. That residual is float64 rounding, not a
semantic gap: pandas' rolling sum accumulates in a different order once a `NaN` sits at bar 0 of
the summed series.

    C1          = DELAY(C, 1)
    up_volume   = V where C  > C1, else 0; NaN where C or C1 is NaN
    down_volume = V where C <= C1, else 0; NaN where C or C1 is NaN
    G191_040    = 100 * SUM(up_volume, 26) / SUM(down_volume, 26)

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived directly from the issue's own stated formula, using the prototype's own (unambiguous) `delay`/`tsum` spellings; one disclosed interpretation choice at the bar-0 boundary (see above), which the prototype gets wrong and this port does not | 9-bar hand-derived example at `length=3` (`tests/test_g191_040.py::test_hand_derived_nine_bars`), including a flat-day (`C==C1`) boundary bar landing in the down-bucket per the issue's own `C<=C1` string: `result[3..8] = [28.571429, 71.428571, 50.000000, 200.000000, 50.000000, 200.000000]`, matching the module's float64 output exactly (`python docs/measure_g191_040.py`: `hand-derived bars 0..8`). Matches an independent per-bar loop built from plain numpy slicing (not the module's own `.rolling()` calls) at the shipped default (`length=26`), 3 spot-checked bars (300, 600, 899) on a 900-bar synthetic frame -- agreeing to `rel=1e-9`, not bit-identically, because the loop's summation order differs from `.rolling()`'s; the script's own full reprs are `module=58.87191163347931 loop=58.871911633479286`, `module=158.84866985261976 loop=158.84866985261982`, `module=79.41246298120792 loop=79.4124629812079` (relative agreement ~1e-15). The disclosed bar-0 choice is pinned on the shipped function's own output from both sides, and the departure from the prototype is measured over the whole 1,500-bar frame (one disagreeing index, `[25]`; `max|diff| = 2.84e-14` elsewhere) -- see the Gate A section above |
| B Causality | pass | Future-perturbation sweep (close AND volume rewritten from `j` onward, another synthetic pair), 34 offsets past the 26-bar warm-up: real module **0 of 34** leaks (`python docs/measure_g191_040.py`). One mutant (`importlib` source read, `exec`'d in memory, the final write index shifted `length=26` bars into the future), shown live (differs from the real module) then caught at **34 of 34** |
| C Reachability | pass -- real data (Gate E's pooled count) plus synthetic | Real data, from Gate E's run `is77-g191_040-b7322f17` over the 89 ALTPORT-1 frames (**398,849** pooled bars): `G191_040_26` is **396,531** non-NaN and **396,506** non-zero, so the NaN count is **2,318** against a pure warm-up of 89 x 26 = **2,314** -- four bars wider, which this session does not attribute to a cause (the per-frame NaN positions are not in the run's outputs; a NaN close would do it, see Gate A). Zero is not a degenerate value here: 25 non-zero-gap bars out of 396,531 defined. `tests/test_gate_e_ledger.py::test_every_column_fires_on_real_data[g191_040:G191_040_26]` passes on those counts. Synthetic: 1,500-bar synthetic frame (seed 11 close, seed 97 volume, `docs/measure_g191_040.py:_walk`/`_volume`), shipped default: **1,474 of 1,500** bars non-NaN (98.27%) -- exactly `n - 26`, the `length = 26`-bar warm-up, no wider gap. **1,474 distinct values** observed on this frame (not a constant column), range `[20.023556, 734.696808]`, median `107.977780` |
| D Scale-free | pass | Algebraically, for ANY `k > 0`, scaling volume (`V -> k*V`) scales both the up-bucket sum and the down-bucket sum linearly (the bucket split depends only on the SIGN of `C-C1`, which does not change), so `k` cancels in the ratio exactly; scaling price (`C -> k*C`) changes nothing in exact arithmetic, since only `SIGN(C-C1)` is read. What the code actually computes is independently-rounded float64 comparisons, which the algebra alone does not guarantee immune to a near-tied flip -- measured, not merely asserted: on the 1,500-bar frame, VOLUME x8/x64 **bit-identical, 0.0 max\|diff\|**; VOLUME x10/x3.7: max\|diff\| **1.42e-13** / **1.14e-13**, float64 rounding from the scalar multiply itself, well under the test's tolerance. PRICE x8/x64/x10/x3.7 **ALL bit-identical, 0.0 max\|diff\|** on this frame (no comparison flip observed). `0 < 1,474 fires < 1,500` and `1,474 > 1` distinct values rule out a constant column. **Zero-down-volume** (round-1 and round-2 review fixes): the denominator is zero exactly when the down-bucket SUM is zero, which has TWO causes, not one -- every bar in the window an up-day, OR every non-up bar in the window carrying zero volume (the one a halted / zero-turnover session produces: a flat close lands in the `C<=C1` bucket with `V = 0`). Round 1 stated only the first and called it "a real, reachable condition ... not an edge case", which was unmeasured; measured now: the longest consecutive up-run on the 1,500-bar frame is **16 bars**, short of the 26 a rally would need, so neither of the two frames whose fire counts are pinned reaches the branch -- the 1,500-bar frame here (`fires = 1474 = 1500 - 26`, no interior gap) and the 900-bar frame of `tests/test_g191_040.py::test_fires_and_is_not_constant` (`fires = 874 = 900 - 26`). The other synthetic frames in these two files are not checked for it, and how often either cause occurs on real data is **not isolated by any run** -- Gate E's counts bound it instead: at most **4** bars over the 398,849 pooled bars (see Gate C above), and those 4 could equally be NaN closes. Both causes are therefore pinned on dedicated small fixtures: `all-up-window bars 0..4 = [nan, nan, nan, nan, nan]` (`close=[100,105,110,115,120]`, `length=3`; bars 3 and 4 are the two full all-up windows) and `zero-volume-down-bar bars 0..4 = [nan, nan, nan, nan, nan]` (`close=[100,101,100,101,102]`, `volume=[10,20,0,30,40]`, `length=3`; bar 2 IS a non-up bar inside both windows, and its volume is 0, so the down-bucket sum is `0.0` rather than NaN). Both resolve `inf -> NaN`, not a raised error. (The `+inf` step needs a non-zero up-bucket sum, which both fixtures have; a window whose up-sum is also zero divides `0/0` and is already NaN before the `.replace`. The column is NaN either way.) |
| E Attribution | **DISCLOSE_GAP — ships with disclosure** | `G191_040_26`: max \|ρ\| **0.8268** vs `OBV_Slope_norm` (manifest), n = **396,525**; top-5 per-frame max median **0.8323** (same comparator, 89 frames, **0.0%** of frames ≥ 0.90). Measured by issue-solver 2026-11-11, run `is77-g191_040-b7322f17`; ledger row in `docs/gate_e_ledger.csv`. Full numbers in the Gate E section below |
| F Suites | this repo only; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Gate E: measured (issue-solver, 2026-11-11)

Run by issue-solver, not by this worktree's sessions:
`gate_e_overlap.py run --module pandas_ta.volume.g191_040`. Outputs
`gatee/is77-g191_040-b7322f17/` (`overlap_max.csv`, `meta.json`), recorded into
`docs/gate_e_ledger.csv` with `python docs/gate_e_ledger.py record <run dir> --measured
2026-11-11`.

| column | max \|ρ\| | against | set | n | per-frame max median \|ρ\| | per-frame comparator | frames | % frames ≥ 0.90 | verdict |
|---|---|---|---|---|---|---|---|---|---|
| `G191_040_26` | **0.8268** | `OBV_Slope_norm` | manifest | 396,525 | **0.8323** | `OBV_Slope_norm` | 89 | 0.0% | **DISCLOSE_GAP** |

Split by comparator set, from the same row of `overlap_max.csv`: against the engine's
`compute_all` the max is **0.6665** vs `tsi` (n = 396,531); against the `ml_features` manifest
`1d` it is **0.8268** vs `OBV_Slope_norm` (n = 396,525). The pooled-only verdict is
**DISCLOSE_GAP** as well, so the per-frame leg does not change the band.

Run facts (`meta.json`): bands `r3-perframe-0.90`; **89** frames, **398,849** pooled bars; **687**
comparators (**329** `compute_all` + **358** manifest), **1** degenerate; defaults only
(`kwargs: {}`); canary `AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS bit-equal`; data stamp
`1be6495e`; `pandas 2.3.3 numpy 1.26.4`; module sha1 `d91b2099`, tree sha1 `0274b94e`. Column
coverage on the pooled set: **396,531** non-NaN, **396,506** non-zero.

**Verdict applied.** `CLAUDE.md`'s Gate E bands (`r3-perframe-0.90`): STRUCK needs pooled
\|ρ\| ≥ 0.90 or a top-5 comparator's per-frame median ≥ 0.90. Measured 0.8268 pooled and 0.8323
per-frame, both under 0.90 and both at or above 0.80, which is **DISCLOSE_GAP**: the column ships
with this disclosure, no column is removed, and no waiver is needed (waivers are for STRUCK rows).

The prototype's own screen figure (0.8268 vs `OBV_Slope_norm`, n = 396,614, per-frame max median
0.8323, DISCLOSE_GAP) is reproduced by the port to four decimals on both legs, against the same
comparator; the pooled `n` differs by 89 bars (396,525 vs 396,614), one bar per frame, which is the
port's extra warm-up bar — the disclosed bar-0 exclusion documented in Gate A above, where the
prototype counts bar 0's whole volume as a down bar and the port does not.

**Why the module docstring still says Gate E is the launcher's.** `pandas_ta/volume/g191_040.py`
is deliberately NOT edited in this receipt session: the ledger pins the module's LF-normalised
sha1 (`d91b2099`, `tests/test_gate_e_ledger.py::test_row_still_describes_its_module`), so any
docstring edit -- a comment included -- would make the recorded row stop describing its code and
owe a re-run (`_owed(f"{path} changed after Gate E run {row['run']}; re-run Gate E and re-record
it")`, read in `tests/test_gate_e_ledger.py:174-177`, not provoked by a run here: this session
started such an edit, then reverted it with `git restore` before running anything). The Gate E
numbers therefore live here and in the ledger, not in the module. `tests/test_g191_040.py` and
`docs/measure_g191_040.py` are not sha1-pinned; their remaining "Gate E is the real-data run"
statements stay true, and the test file's one stale sentence -- that Gate E is pending -- is
corrected to point here.

**What this column is correlated with, in words.** `OBV_Slope_norm` is the engine's normalized
signed-volume slope: the same two up/down volume buckets this column divides, differenced instead
of ratioed. The disclosure is that a tree offered both gets one signal twice at ρ ≈ 0.83 — strong,
but under this fork's 0.90 restatement line.

## Non-redundancy against the nearest already-shipped sibling (round-2 review fix)

Not a numbered gate, but one of the three pillars of `CLAUDE.md`'s ML feature contract, and the
2026-10-24 screen could not have covered it: the screen's stage-2 fork-overlap run (max \|ρ\|
**0.7012** vs `vzo:VZO_14`, 12 frames) predates this fork's own `g191_043` port -- issue #69, a
candidate of that very same screen, merged in `ed2d7ee` on 2026-11-10 (`git log -1 --format=%ci
ed2d7ee`) -- so the nearest in-package comparator was not in `Category` when this candidate was
screened.

`g191_043` is `SUM(SIGN(C-C1)*V, 6) / SUM(V, 6)` over the SAME two buckets. Write `U` for the
up-bucket sum, `D` for the strictly-down sum and `F` for the flat-day sum over one window:

    G191_043 = (U - D) / (U + D + F)        G191_040 = 100 * U / (D + F)

With no flat bars (`F = 0`) both are strictly increasing functions of the single ratio
`r = U/D` (`100r` and `(r-1)/(r+1)`), hence **rank-identical** at equal `length`. Measured on the
1,500-bar frame, which has **0 flat bars** so `F = 0` holds exactly (`python
docs/measure_g191_040.py`):

| pair | Spearman ρ | n |
|---|---|---|
| `G191_040_26` vs `G191_043_26` (equal length) | **1.000000** | 1,474 |
| `G191_040_26` vs `G191_043_6` (the SHIPPED defaults) | **0.451774** | 1,474 |

So the shipped pair is not a restatement — the differing default windows (26 vs 6) break the rank
identity, and real data prints flat closes (`F > 0`), which breaks the single-ratio form as well.
But the equal-length identity is exact, and the launcher's Gate E comparator set (the engine's
`compute_all` plus the `ml_features` manifest, 687 columns) need not contain `G191_043_6` at all,
so this is recorded here as the expected-leading in-package comparator to read the Gate E row
against. The real-data figure is Gate E's, not this session's.

**The engine-side form of the same kinship already has a real-data number, and it is the strongest
prior for the band the launcher's run will land in.** Issue #77's own prototype screen measured
max \|ρ\| **0.8268** vs `OBV_Slope_norm` (manifest, n = 396,614), top-5 per-frame max median
**0.8323**, verdict **DISCLOSE_GAP** — run `screen_20261024`, 89 ALTPORT-1 frames, 398,849 bars,
329 + 358 comparators, canary bit-equal; next comparators `OBV_Slope_norm_Pctl` 0.7274 and
`OBV_Slope_norm_State` 0.6857. `OBV_Slope_norm` is the engine's own normalized signed-volume
slope, i.e. the same construct as `g191_043` and the same two buckets this column divides. So
**DISCLOSE_GAP (0.80 ≤ \|ρ\| < 0.90) was the band to expect** from the launcher's Gate E run, which
ships the column with disclosure rather than striking it. That figure was the PROTOTYPE's, not this
port's: a prototype is not a port (the issue says so itself), and the port differs from the
prototype at the undefined-direction boundary documented above. **The port's own run has now
replaced it and landed in that band** — same comparator, same four decimals on both legs; see the
Gate E section above.

## Wiring

`Category` **311 -> 312** (`volume` **40 -> 41**); `df.ta.<name>()` accessor count **319 ->
320**. Touch points: `pandas_ta/volume/g191_040.py` (module), `pandas_ta/volume/__init__.py`
(export), `pandas_ta/__init__.py` -> `Category["volume"]` (discovery), `pandas_ta/core.py` ->
`AnalysisIndicators.g191_040` (accessor), `tests/test_g191_040.py` (tests). README.md's headline
and `volume (41)` row, and `docs/IndicatorDictionary.md` (regenerated), both updated and checked
by `tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s running tag count updated
**656 -> 657 / 299 -> 300 `SF`** (`G191_040_26` probes cleanly at the dictionary's 600-bar
synthetic frame and takes many distinct values, so the generator tags it `SF`).
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match (311 -> 312) and
`CATEGORY_BUCKETS["volume"]` (40 -> 41).

`g191_040`'s Gate E ledger row was owed until the launcher's run; it is now recorded
(`docs/gate_e_ledger.csv`, run `is77-g191_040-b7322f17`, measured 2026-11-11), so
`tests/test_gate_e_ledger.py` no longer reports it as owed -- see the suite run below.

## Suite run (this repo)

**Receipt session, 2026-11-11, after the ledger row landed.** `python -m pytest -q`, full suite,
default collection order: **3 failed, 5162 passed, 83 skipped** (107s). `g191_040`'s own tests
(`tests/test_g191_040.py`): **25 passed**, unchanged. The passing count moved **5155 -> 5162**
because the ledger row is itself parametrized over: `pytest tests/test_gate_e_ledger.py -k
g191_040 --collect-only` lists **8** tests, **7** of them keyed `g191_040:G191_040_26` (the row's
module-sha1, output-fingerprint, verdict-band, waiver, default-columns, defining-module and
real-data-fires checks) and one (`test_every_new_indicator_has_gate_b_and_d_tests[g191_040]`)
already present before the row; all 8 pass.

The 3 failures are the two pre-existing breaks plus one indicator that is not this port:

- `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows` -- needs the
  sibling `../AlternativeRepos` checkout, absent in this worktree (CI deselects it by name).
- `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence` -- the untracked
  `docs/pine/` corpus, `8d8f705` (CLAUDE.md "Known breaks").
- `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` -- now owed for
  **`mtd_ret` only**: the failure message this session read is `no Gate E ledger row for
  ['mtd_ret']`. `g191_040` is no longer in that list. `mtd_ret` pre-dates this issue (same note in
  `docs/G191109Measured.md`) and is the owner's to record; under `GATE_E_PENDING_OK=1` the CI path
  into `dev` turns it into a skip.

No other test regresses.

**Earlier (port session, before the Gate E row):** the same 3 failures with **5155 passed, 83
skipped** -- and that run's ledger failure named both `g191_040` and `mtd_ret`.

## Review history

`/brutally-honest-review` rounds (Mode C, one Fletcher reviewer subagent per round, each reading
the files cold). None was a mathematics error. All but one were a claim standing in front of its
measurement, or a test standing in front of a mirror — this fork's documented dominant defect.
The exception is round 2's `undefined` finding, a real behaviour gap in the shipped module (a
`NaN` close dropped out of both buckets while its windows kept firing), fixed in
`pandas_ta/volume/g191_040.py`'s `undefined = close_prior.isna() | close.isna()` and pinned by
`tests/test_g191_040.py::test_a_nan_close_blanks_only_the_windows_that_contain_it`. Every
measurement these rounds demanded now lives in the gate section named beside it; this list is the
audit trail, not the evidence. Run folder: `docs/reviews/auto-2026-11-10-g191-040/`
(`00-manifest.md`, `01-g191-040.md` with each round's verdict verbatim, `99-summary.md`).

| round | date | findings | what they were | where the fix lives now |
|---|---|---|---|---|
| 1 | 2026-11-10 | 2 (0 MAJOR) | the zero-denominator `inf -> NaN` branch shipped with no test or measurement reaching it; the scale-free wording claimed an algebraic exactness the independently-rounded float64 comparisons do not guarantee | Gate D row (`all-up-window` fixture), SCALE-FREE paragraph of the module docstring |
| 2 | 2026-11-11 | 6 (1 MAJOR, 4 MINOR, 1 NIT; the zero-denominator MINOR named two separate defects) | MAJOR: the bar-0 test never called `g191_040` — it re-typed the module's own two bucket expressions and asserted they agreed with themselves, so it would have passed with the indicator deleted, while three documents cited it as the pin for the port's only judgement call. Also: `undefined` missed `close.isna()`, a real behaviour gap; the zero-denominator trigger was stated as one cause when it has two; "a real, reachable condition … not an edge case" had no run behind it; "no column value changes for any bar whose window excludes bar 0" rested on two compared scalars; nothing noted the kinship with the shipped `g191_043`; NIT: `rel=1e-9` loop agreement rounded to six decimals read as exact | Gate A section (three-reading table, full-series departure), module `undefined` expression + its paragraph, Gate D row (two causes, longest up-run), non-redundancy section, Gate A row (full reprs) |
| 3 | 2026-11-11 | 5 (1 MAJOR, 3 MINOR, 1 NIT) | MAJOR: round 2 answered a claim-before-measurement finding with a NEW one — "27 newly-NaN output bars … **and no other bar moves**", cited to a script that printed only the count and the two endpoints. Measured, the unqualified form was false: `max|diff| = 5.68e-14`, `bit-identical=False`. Also: the struck "real, reachable condition" sentence was still standing in the test file; both zero-denominator tests had grown NEW mirrors labelled "confirms"; the non-redundancy section omitted the screen's own real-data Gate E figure on this prototype; NIT: one mirror still carried the pre-fix `undefined` expression | Gate A section (NaN-close paragraph), test-file docstrings, `INF_REPLACE_MUTANT` in `tests/test_g191_040.py`, non-redundancy section's DISCLOSE_GAP paragraph |
| 4 | 2026-11-11 | 6 (1 MAJOR, 4 MINOR, 1 NIT) | MAJOR: the round-3 retraction was applied in two files out of three — "and moves nothing else" survived in the test-file header, measured false by this session's own script. Also: the same struck sentence and a stale re-typed bucket block (on the PRE-fix `undefined` line) were still in `docs/measure_g191_040.py`; "neither random-walk frame" was a count no run produces — the two files build many `_walk(...)` frames (19 call sites, `grep -c "_walk("` giving 17 + 4 lines including the two definitions) and exactly two have a pinned fire count; 28% of this file was review stenography placed before the first gate; NIT: a headline count did not match the list it headed | test-file header bullet, `docs/measure_g191_040.py` (mirror block deleted, comment restated), the scoped two-frames wording in both the module and the test file, and this section — which is where the stenography went |

Round-4 finding 1's lesson, recorded because it recurred three times: a retraction is not done when
the sentence is gone from the file you were looking at. Grep all four files
(`pandas_ta/volume/g191_040.py`, `tests/test_g191_040.py`, `docs/measure_g191_040.py`,
`docs/G191040Measured.md`) for the struck phrase before calling it fixed.
