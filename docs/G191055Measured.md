# g191_055 — measured and reverted (issue #80)

> **Status: REVERTED on Gate E — STRUCK.** The launcher's Gate E run on the
> port (code at `acde1fe`): `G191_055_20` max |ρ| **0.8755888636643001** vs
> `Ret_21d_pct` (manifest), n = **396,065**; that comparator's **per-frame
> median |ρ| 0.9077841239412677** over **89** frames, with **62.92134831460674%**
> of frames ≥ 0.90. Schema `r3-perframe-0.90` → **STRUCK**; the pooled
> maximum alone would have been DISCLOSE_GAP. The module, its export, its
> `Category` entry, its accessor, its tests and its measurement script are
> gone, and `README.md`, `docs/IndicatorDictionary.md`,
> `docs/MLCompanionContract.md` and `tests/test_altport2_ports.py` are back
> at base `bafb803` (*Closed* below). This file and the
> `docs/gate_e_ledger.csv` row are the receipt; issue #80's "Done when"
> counts a measured revert as a close, exactly as well as a ship.

20-day Wilder swing-index sum: Guotai Junan's (2017, "GTJA191", internal
quant report) alpha `#55`, per issue #80, which attributes its copy of the
report to HKUDS/Vibe-Trading (MIT) — a copy **not read in the porting
session**, see the disclosure under Gate A.

Built and measured at `acde1fe`, now deleted:
`pandas_ta/momentum/g191_055.py` (module, one column `G191_055_20` at the
default `length=20`), `tests/test_g191_055.py` (**26 tests, from pytest**,
all passing at `acde1fe`), `docs/measure_g191_055.py` (the measurement
script behind every Gates A–D number below). Read any of them with
`git show acde1fe:<path>`.

Where the numbers come from: the Gate E numbers are read from the
launcher's output files (*Gate E* below); every Gates A–D number was
printed by `python docs/measure_g191_055.py` at `acde1fe`; the exceptions
are the suite counts in Gate F and the test count (pytest), the prototype
figures quoted from issue #80 (marked *quoted*), the wiring counts
(`git diff bafb803 acde1fe`), and quantities obtained by arithmetic from
printed ones (marked *derived*). Environment: this worktree's pinned
pandas 2.3.3 / numpy 1.26.4. Gates A–D and the port measured 2026-11-11;
Gate E and the revert 2026-11-11.

## Gate E: attribution — STRUCK (the launcher's run, 2026-11-11)

Run `is80-g191_055-da874979`:
`gate_e_overlap.py run --module pandas_ta.momentum.g191_055`, function
`g191_055` at its defaults (`kwargs {}`), on the code at `acde1fe`. Every
number in this section is read from the launcher's copy of the outputs,
`/home/tolga/.issue-solver/runs/20261111-054610-80/gatee/is80-g191_055-da874979/`
(`overlap_max.csv`, `top25.csv`, `perframe.csv`, `degenerate.csv`,
`meta.json`). That folder exists only on the owner's machine, so the rows
that decide the verdict are copied here.

Pooled (`overlap_max.csv`):

| | measured |
|---|---|
| max \|ρ\| | **0.8755888636643001** (ρ = +0.8755888636643001) vs `Ret_21d_pct`, manifest set |
| n | 396,065 |
| max \|ρ\| within the manifest | 0.8755888636643001 vs `Ret_21d_pct`, n 396,065 |
| max \|ρ\| within compute_all | 0.818202930886035 vs `QQE_RSIMA`, n 396,154 |
| comparators | 687, **1** of them degenerate (`squeeze_SQZ_NO`, constant; `degenerate.csv`) |
| verdict, schema `r3-perframe-0.90` | **STRUCK** |
| verdict, pooled only | DISCLOSE_GAP |

Per frame (`perframe.csv`: the five largest pooled comparators of
`top25.csv`, 89 frames each):

| comparator | set | pooled \|ρ\| | per-frame median | mean | min | max | frames ≥ 0.90 | frames ≥ 0.80 |
|---|---|---|---|---|---|---|---|---|
| `Ret_21d_pct` | manifest | 0.8756 | **0.9077841239412677** | 0.8952 | 0.6778 | 0.9646 | **62.92134831460674%** (56 of 89, *derived*) | 91.01123595505618% (81 of 89, *derived*) |
| `Ret_21d_vol_adj` | manifest | 0.8679 | 0.8958 | 0.8853 | 0.7073 | 0.9558 | 41.57303370786517% (37 of 89, *derived*) | 91.01123595505618% (81 of 89, *derived*) |
| `SMA_20_Slope_pct` | manifest | 0.8452 | 0.8751 | 0.8638 | 0.6596 | 0.9387 | 20.224719101123593% (18 of 89, *derived*) | 91.01123595505618% (81 of 89, *derived*) |
| `bias_ta` | manifest | 0.8361 | 0.8662 | 0.8545 | 0.6360 | 0.9283 | 14.606741573033707% (13 of 89, *derived*) | 89.8876404494382% (80 of 89, *derived*) |
| `smi_SMI_5_20_5` | manifest | 0.8223 | 0.8467 | 0.8382 | 0.6549 | 0.9151 | 4.49438202247191% (4 of 89, *derived*) | 89.8876404494382% (80 of 89, *derived*) |

**Why STRUCK.** The pooled maximum sits **0.0244111363356999** *under* the
0.90 line (*derived*: 0.90 − 0.8755888636643001), so pooled-only this
column is DISCLOSE_GAP. But `r3-perframe-0.90` also strikes a column whose
top-5 comparator has a per-frame median ≥ 0.90, and `Ret_21d_pct`'s is
**0.0077841239412677** *over* it (*derived*: 0.9077841239412677 − 0.90) on
**56 of 89** frames (*derived* from 62.92134831460674%). The second
comparator, `Ret_21d_vol_adj`, is itself at 0.8958 per-frame — 0.0042 under
the line — so the strike is not carried by one comparator's tail: the
column restates the 21-day forward-looking-window return family on most
BIST frames. The pooled figure is the one that understates it, not the
per-frame one.

That is the whole verdict. No waiver was sought: `ALLOWED_WAIVERS` in
`tests/test_gate_e_ledger.py` is the owner's, it names two columns
(`pfe` #23, `kalman_trend` #22), and CLAUDE.md's Gate E row says a STRUCK
column is reverted unless the owner waives it.

Run stamp (`meta.json`): engine_code
`d4b78314a2ef494d6e36f77afc13a3178536f249`, ladders
`a1575177ee31e5ee7cee9cf0d5c576671c7d9254`, cache_code
`d583ded2f94301e5d559dc7d3ba103f77b9b79e0`, data
`1be6495ef7095ff67ad8f59a2fc0311d74f02652`, universe
`fa3060e68acef410cbc04573ac39450bd210d81d`, pandas 2.3.3 / numpy 1.26.4;
canary "AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS bit-equal"; **89** frames,
**398,849** pooled bars, **329** compute_all + **358** manifest = 687
comparators; candidate_source_sha1
`5fcfaf6f5213bb46603d6d068742d0df79196c7e`, pandas_ta_src_sha1
`014f5fcdcb3e08a41accf5e22d0b9679366f4530`.

Ledger: recorded by `python docs/gate_e_ledger.py record <run dir>
--measured 2026-11-11`, which accepted the run (defaults, 89 frames, 687
comparators, canary bit-equal, tree sha1 matching) and wrote the STRUCK
row to `docs/gate_e_ledger.csv`. **The row is kept** after the revert: with
`g191_055` out of `Category` it is no longer in the ledger test's `LIVE`
set, so the waiver check does not apply to it (read in
`tests/test_gate_e_ledger.py:82,198-205`), and only
`test_verdict_follows_the_bands` still reads it — which it passes, STRUCK
being the band these numbers imply. Keeping it is a deliberate departure
from the `ewmac` / `crsi` / `rank` reverts, which deleted their STRUCK rows
because those indicators **stayed** in `Category` and the rows would then
have failed the waiver check; here the row costs nothing and is the second
copy of the measurement.

### Against the prototype prior (*quoted* from issue #80)

Issue #80 measured the **two-branch prototype**, not this port. Side by
side:

| | prototype (*quoted*) | port (measured) | move (*derived*) |
|---|---|---|---|
| pooled max \|ρ\| | 0.8628 | 0.8755888636643001 | +0.0127888636643001 |
| its comparator | `Ret_21d_pct` | `Ret_21d_pct` | same |
| n | 395,533 | 396,065 | +532 |
| top-5 per-frame max median | 0.8992 | 0.9077841239412677 | +0.0085841239412677 |
| next comparator | `Ret_21d_vol_adj` 0.8469 | `Ret_21d_vol_adj` 0.8678809902328485 | +0.0209809902328485 |
| third comparator | `SMA_20_Slope_pct` 0.8386 | `SMA_20_Slope_pct` 0.8452090176846332 | +0.0066090176846332 |
| verdict | DISCLOSE_GAP | **STRUCK** | crossed the line |

The porting session wrote, before this run, that the prototype's per-frame
max median of 0.8992 sat 0.0008 under the strike line and that "the port's
own run could land either side of it". It landed over it. The port is
**not** the prototype — they differ at every non-NaN bar of the synthetic
walk, ρ 0.967451 between them (Gate A below) — and the port's three-branch
`R` measures 0.0086 *more* correlated with the 21-day return than the
prototype's two-branch form, on the same universe and the same comparator.
Which of the two forms the owner's copy of GTJA191 actually carries is
still open (Gate A), and it no longer changes the outcome here: the
prototype's own screen number was DISCLOSE_GAP with a 0.8992 per-frame
median, so a re-port of the two-branch form would be a near-miss, not a
clear ship. That is a reading of the screen's numbers, not a measurement of
the two-branch column over the 89 frames, which this session did not run.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived from the source formula with the prototype's two-branch `R` rejected, disclosed and measured against — **and the source string itself is RECALLED, never read here**, so this is not a clean pass; see *Gate A* below | A hand-derived 5-bar example (`length=2`) with every `A`, `B`, `D`, `E`, `R`, `N` and `SI` written out, branch 2 / branch 3 / an `A == B == D` triple tie all exercised: `R = [nan, 8.25, 13.5, 6.75, 2.0]`, SI `[nan, 23.272727272727273, -163.55555555555554, -28.444444444444443, 6.0]`, column `[nan, nan, -1.5248133509003072, -2.0425531914893615, -0.24264264264264263]`, bar by bar to `abs=1e-12`. An independent per-bar replay (plain Python loop over numpy scalars — no `.rolling()`, no `.shift()`, no `np.where`) at the shipped default on a 900-bar frame: `t=300 module=-2.6501557001261786 loop=-2.6501557001261786`, `t=600 0.17579471867618934 / 0.17579471867618915`, `t=899 -1.4155524946725604 / -1.41555249467256` (the last two agree to `rel=1e-9`, differing only in the summation's last bits). The three-way prototype comparison and the branch census are in the Gate A sections below |
| B Causality | cleared at `acde1fe` (module and tests since deleted) | Future-perturbation sweep (open/high/low/close jointly rewritten from `j` onward), **36 offsets** past the 21-bar warm-up: real module **0 of 36** leaks. Two mutants (`importlib` source read, `exec`'d in memory), each shown live different from the real module, then caught **36 of 36**: the final write index shifted `length=20` bars into the future, and `rolling(length, center=True)` in place of the causal trailing window (the `bos` look-ahead bug class CLAUDE.md documents) |
| C Reachability | **synthetic at `acde1fe`, plus Gate E's own real-data pooled counts** | Real data, from Gate E's `overlap_max.csv` for the column: **396,154 non-NaN** (`non_nan`) and **396,154 non-zero** (`non_zero`) of **398,849** pooled bars over 89 frames — so every emitted bar on real data is non-zero, and `0 < 396,154 < 398,849`. The **2,695** NaN bars (*derived*: 398,849 − 396,154) are **not** fully attributed: the 20-bar structural warm-up accounts for 89 × 20 = **1,780** of them (*derived*), leaving **915** (*derived*) whose cause — short frames, missing OHLC bars, or the `R == 0` poisoning below — was **not measured**, since this session may not touch the frames. The per-bar sign split on real data was not measured either. Synthetic, at `acde1fe`: 1,500-bar OHLC walk (seed 11, `low <= open, close <= high` at every bar — **1,500 of 1,500** verified), shipped default: **1,480 of 1,500** bars non-NaN (98.67%) — exactly `n - length` — first valid at bar **20**, the structural warm-up boundary. **1,480 distinct values.** Range `[-4.486048, 2.354767]`, median `-0.285670`, **588 positive / 892 negative / 0 zero**. The walk's `open` is the SAME bar's close times noise, so it carries no overnight-gap structure: the sign imbalance is the frame's, not a property of the formula |
| D Scale-free | cleared at `acde1fe`, synthetic | A positive rescale factors through `A`, `B`, `D`, `E`, `N`, `R` and `MAX(A,B)` and cancels against the `/close`; all three branch tests and the `R == 0` test are scale-invariant. Measured on the 1,500-bar walk with all four price series scaled: PRICE ×8/×64 **bit-identical, 0.0 max\|diff\|**; ×10/×3.7 within float64 rounding tolerance (**2.0872192862952943e-14 / 2.070565940925917e-14** absolute, **4.652690502521582e-15 / 4.6155679719163575e-15** relative to `max\|column\| = 4.486048`), NaN masks matching at all four. The SELECTED-BRANCH masks are measured too, and they are measured rather than argued: at a non-power-of-two `k` the module compares `fl(fl(k*H) - fl(k*C1))`-style differences of SEPARATELY rounded products, not `fl(k*A)`, so a strict `>` between two nearly equal branch quantities could in principle tie OR invert — monotonicity of `x -> k*x` does not cover it. Measured: **0 bars changed branch** at any of the four multipliers. `0 < 1480 fires < 1500` and `1480 > 1` distinct values rule out a constant column |
| E Attribution | **STRUCK** (*Gate E* above) | max \|ρ\| 0.8755888636643001 vs `Ret_21d_pct` (manifest), n 396,065; its per-frame median 0.9077841239412677 over 89 frames, 62.92134831460674% of frames ≥ 0.90; compute_all max 0.818202930886035 vs `QQE_RSIMA`; pooled-only verdict DISCLOSE_GAP |
| F Suites | **after the revert**, this repo: 3 failed / 5,230 passed / 83 skipped, and all three failures pre-date this issue (*Suite run* below) | `python -m pytest -q` (this session, post-revert) |

## Gate A: derivation from the source formula, not the prototype — and the two disagree

*Everything in this section was measured at `acde1fe`, before the revert.
The module and the scripts it names are deleted; read them with
`git show acde1fe:<path>`.*

Issue #80 quotes GTJA191 alpha `#55` with its middle **elided**:

    #55: SUM(16*(...)/R*MAX(|H-C1|,|L-C1|), 20)

**What the porting session could NOT do, disclosed up front.**
`docs/pine/` and web access are both unavailable in this worktree, so the
issue's own named copy — HKUDS/Vibe-Trading (MIT) — was never read, and the
issue's own quote hides both the numerator and `R`. Two sources were
available here, and they **disagree about `R`**.

### Source 1: the issue's prototype — TWO branches

`docs/issues/screen/ind_screen.py:398-405`, the only machine-readable copy
in this worktree:

    @cand("g191_055", "20-day Wilder swing-index sum", G,
          "#55: SUM(16*(...)/R*MAX(|H-C1|,|L-C1|), 20)", "/close")
    def _(o, h, l, c, v):
        c1, o1, l1 = delay(c, 1), delay(o, 1), delay(l, 1)
        a, b, d = (h - c1).abs(), (l - c1).abs(), (h - l1).abs()
        e = (c1 - o1).abs()
        r = pd.Series(np.where((a > b) & (a > d), a + b / 2 + e / 4, b + a / 2 + e / 4), index=c.index)
        si = 16 * sdiv(c - c1 + (c - o) / 2 + c1 - o1, r) * np.maximum(a, b)
        return tsum(si, 20) / c

with `delay`/`tsum`/`sdiv` read off the same module source
(`ind_screen.py:45`, `:49`, `:41`): `delay(x, n) = x.shift(n)`,
`tsum(x, n) = x.rolling(n).sum()`, `sdiv(a, b) = a / b` with `±inf`
replaced by NaN. The scale-free conversion is the issue's own field,
`conv="/close"`, and the window its own `20`.

### Source 2: the report's own `#55` string as the porting session RECALLED it — THREE branches

    R = (A>B & A>D) ? A + B/2 + E/4
      : (B>D & B>A) ? B + A/2 + E/4
      : D + E/4          with A=|H-C1|, B=|L-C1|, D=|H-L1|, E=|C1-O1|

**This is the weakest link in this Gate A and it is not dressed up as
anything else.** No copy of the GTJA191 report was readable here, so the
three-branch string is RECALLED, not transcribed.

### What the port shipped, and why

**The THREE-branch `R`.** Issue #80's own Gates-owed line says "Gate A
starts from the source formula, not the prototype". **Two** pieces of
evidence inside this worktree, plus **one recalled fact** about Wilder's
own construction (labelled as such, like source 2), say the source has a
third branch that the prototype collapsed:

1. The prototype computes `d = |H - L1|` and uses it in **nothing but the
   first branch's test**. A two-branch `R` has no reason to know `d`: the
   only construction where `d` belongs in a test is one where `d` can also
   be the selected term.
2. That first test **can never pass on OHLC-consistent data** — proved and
   measured below — so under the two-branch reading the prototype's `R` is
   the single expression `B + A/2 + E/4`, a "swing index" whose range
   denominator ignores `|H - L1|` entirely. That is not Wilder's
   construction under any reading.
3. The issue names the thing "**Wilder** swing-index sum" and names the
   denominator `R` — that much is in the worktree. **RECALLED, not in this
   worktree:** Wilder's Swing Index defines `R` by three cases on which of
   `|H-C1|`, `|L-C1|`, `|H-L1|` is largest, the same three quantities the
   prototype computes. Nothing here can check that, so it carries exactly
   the weight of source 2 and no more.

**If the owner's copy turns out to carry the two-branch `R`,** the port's
fix was one line: replace the module's inner `np.where` with its
`b + a / 2 + e / 4` arm. That edit is exactly `TWO_BRANCH_MUTANT` in
`git show acde1fe:tests/test_g191_055.py` and `TWO_BRANCH_R` in
`git show acde1fe:docs/measure_g191_055.py`, and the next section is the
size of the decision, measured. **Gate E makes it moot for the ship
decision** — see *Against the prototype prior* above.

**Not Wilder's own Swing Index either.** Wilder's first two cases
SUBTRACT half the smaller term (`R = A - B/2 + E/4`) and his constant is
`50/T` (`T` = the limit move) rather than `16`. GTJA191's string adds and
uses `16`; the port followed GTJA191, which is what the issue asks for
("Source: GTJA191"). The `+` is corroborated in-repo by the prototype; the
claim about Wilder's own signs is RECALLED like source 2 and nothing here
can check it.

### How big the three-branch decision is (measured, 1,500-bar walk)

| measurement | value |
|---|---|
| bars taking branch 1 (`A>B & A>D`) | **0** of 1,499 |
| bars taking branch 2 (`B>D & B>A`) | **537** of 1,499 |
| bars taking branch 3 (`else`) | **962** of 1,499 (64.2%) |
| per-bar SI, branch-2 bars identical to the prototype's | **537 of 537** (bit-for-bit) |
| per-bar SI, branch-3 bars identical to the prototype's | **0 of 962** |
| column: non-NaN bars where port ≠ prototype | **1,480 of 1,480** |
| column: max \|diff\| port vs prototype | **2.3180569702483527** |
| column: Spearman ρ port vs prototype | **0.967451** |
| longest run of consecutive branch-2 bars | **6** (a 20-bar window needs 20 to make the columns agree) |

So the two forms are **not** a corner-case apart: they agree on every
branch-2 bar's SI and differ on every branch-3 bar's, and since no 20-bar
window on this walk is all-branch-2, every single output differs. ρ 0.9675
between them says they are the same shape, not the same column.

The comparison was run three ways and all three agree:

* against the **retyped** prototype expression (in both the test file and
  the measure script, because `docs/issues/` is gitignored and a clone
  cannot import it);
* against a **live `exec`'d mutant** of the shipped module with the third
  branch collapsed — which is **bit-equal to the retyped prototype**, so
  the retyping is a faithful stand-in;
* against the **REAL candidate** loaded out of
  `docs/issues/screen/ind_screen.py` through its own registry (present in
  this worktree, gitignored, so no test may depend on it): port vs
  candidate `max|diff| = 2.3180569702483527`, ρ 0.967451; retyped vs
  candidate `max|diff| = 0.0`.

### Branch 1 is unreachable on OHLC-consistent data

A derivation, then a measurement. Branch 1 needs `A > B` **and** `A > D`:

* `H >= C1`: `A = H - C1`, and `L1 <= C1` (a bar's low cannot exceed its
  close) gives `D = H - L1 >= H - C1 = A`. So `A > D` fails.
* `H <= C1`: `A = C1 - H`, and `L <= H` gives `B = C1 - L >= C1 - H = A`.
  So `A > B` fails.

The two cases cover every bar. Measured on the 1,500-bar walk (**1,500 of
1,500 bars OHLC-consistent**): branch 1 fires **0** times, and each
inequality is violated **0** times. The arm stayed in the module because it
is in the source formula and because an inconsistent frame (bad vendor
data, `L > H`) can still reach it — but nothing in this port's claims
depends on it, and
`git show acde1fe:tests/test_g191_055.py`'s
`test_branch_one_is_unreachable_on_consistent_ohlc` pinned the census and
both inequalities.

### `R == 0` is reachable, and one such bar NaNs a whole window

`R` is a sum of non-negative terms, so `R == 0` needs every term of the
**selected** branch to vanish. Branch 1 is selected only when `A > B >= 0`
(so `A > 0`) and branch 2 only when `B > D >= 0` (so `B > 0`); neither can
be zero. Branch 3's value `D + E/4` is zero iff `D == 0` and `E == 0`, and
branch 3 is selected given `D == 0` only when `A == B`. The solutions of
`|H-C1| == |L-C1|` are `H == L` and `H + L == 2*C1`; the second needs
`C1 = (H+L)/2 >= H = L1`, i.e. `L >= H`, which contradicts `H > L`. One
bar shape is left:

> bar `t-1` opened and closed at the same price (`O1 == C1`), and bar `t`
> is **zero-range** (`H == L`, hence `C == H == L`) printing exactly at
> bar `t-1`'s low (`H == L1`).

A halt, a limit-locked print, or an untraded day carried forward, after a
doji. `C == C1` is **not** required. There `N/R` is `x/0` (the numerator
collapses to `C - C1`, non-zero when the frozen print is below the prior
close) or `0/0`; `sdiv`'s `inf -> NaN` makes both NaN, and
`min_periods=length` carries that into the `length` outputs whose window
holds the bar. Pinned on a 7-bar fixture at `length=2`
(`test_zero_r_bar_nans_its_whole_window`): `R = [nan, 3.0, 0.0, 2.0,
2.625, 3.125, 3.125]`, column `[nan, nan, nan, nan, 0.44221105527638194,
0.2929353233830846, 0.26482758620689656]` — NaN at bars 0–3 (0–1 warm-up,
2–3 poisoned), valid from bar 4. **The synthetic walk never reached it: 0
of 1,500 bars have `R == 0` and 0 have `H == L`**, so the fixture was the
porting session's only coverage. Gate E's real-data counts bound it but do
not isolate it: 915 of the 2,695 real NaN bars are unexplained by the
warm-up (Gate C above), and whether any of them is an `R == 0` window was
not measured.

### The numerator: in-repo provenance, kept in the source's written order

Unlike `R`, the numerator `N = C - C1 + (C - O)/2 + C1 - O1` is read
straight off the prototype (`ind_screen.py:404`,
`c - c1 + (c - o) / 2 + c1 - o1`), so it has an **in-repo** source, and
the recalled report string agrees with it term for term. The two sources
that disagree about `R` agree about `N`; nothing here rests on recall
alone.

`C - C1 + (C - O)/2 + C1 - O1` cancels algebraically to
`C + (C - O)/2 - O1` — `DELAY(C,1)` drops out of the numerator entirely,
surviving only inside `A`, `B`, `E`, `R`. The source's order was kept for
**fidelity** (CLAUDE.md's reason for summing TA-Lib's Hilbert taps in
TA-Lib's order), **not** because the two spellings were found to differ:
measured on the walk they agree bit-for-bit, **max |diff| 0.0, 0 of 1,499
bars differing**. Reported rather than assumed in either direction.

### What this was, next to what the fork already ships

Measured at `acde1fe`, when the module was present: this fork shipped **no
other Swing Index / ASI construction** — one case-insensitive content
search for `swing[ _-]?index|accum\w* swing|\bASI\b` over
`pandas_ta/**/*.py` (ripgrep, source files only) matched **the port's own
file and nothing else**. With the port reverted, that search's match count
over the tree is **0**; that follow-up was not re-run in this session, it
is arithmetic on the previous result (*derived*).

A looser search for bare `swing` matched **31 files** at `acde1fe`, one of
which was the port's own module. The count quoted here is deliberately the
one over the **other 30**, because any total includes the port's own
docstring and moves whenever that docstring is edited — which is exactly
how an earlier draft of this paragraph went stale by one. Ripgrep's count
mode (`rg -ic swing` over `pandas_ta/**/*.py`), summed over every file
except `pandas_ta/momentum/g191_055.py`, gave **349 matching LINES across
the other 30**. No whole-tree total is quoted here, deliberately — one was,
and editing the module docstring moved it by one. (Lines are not
occurrences either: several of the 349 carry the word twice.) The evidence
that none of those 30 is a Swing Index is the index-pattern search above
matching none of them — **not** a reading of all 349 lines, which was never
done. Those 30 are the SMC / pivot-structure detectors
(`trend/swing_equilibrium.py`, `trend/bos.py`, `trend/choch.py`,
`trend/sr_decay.py`, `trend/zigzag_fib.py`, …), their package and accessor
plumbing (`pandas_ta/__init__.py:85`, `trend/__init__.py:50`, `core.py`'s
`swing_*` keyword arguments), and bare uses of the word for a price swing
inside modules that are something else entirely — `momentum/tsi.py:53`,
`overlap/kama.py:58`, `volatility/wvma.py:65`, `volume/volcv.py:39`.

## Non-redundancy on a synthetic frame — NOT Gate E, and it undershot

Spearman ρ of `G191_055_20` against the nearest shipped columns, on the
900-bar seed-5 OHLC walk (`docs/measure_g191_055.py` at `acde1fe`):

| comparator | ρ | n |
|---|---|---|
| `G191_069_20` | 0.766786 | 880 |
| `BIAS_SMA_26` | 0.753646 | 875 |
| `G191_187_20` | 0.682709 | 880 |
| `G191_093_20` | -0.677876 | 880 |
| `ROC_10` | 0.592150 | 880 |
| `CCI_14_0.015` | 0.539315 | 880 |
| `G191_003_6` | 0.452111 | 880 |
| `BOP` | 0.062834 | 880 |

All eight sat under the 0.90 strike line and under the 0.80 DISCLOSE_GAP
line on that frame, in |ρ|. **Gate E then struck the column at 0.9078
per-frame against a comparator this table does not contain**
(`Ret_21d_pct`, a manifest forward-window return): the synthetic proxy was
not merely low, it was pointed at the wrong family. Worth remembering the
next time a synthetic non-redundancy table reads reassuring — it was
labelled "proves nothing about Gate E" and that label was the accurate part.

The open-anchored directional GTJA191 ports already in this fork are
**three**, not one — `g191_069` (`#69`, the DTM-vs-DBM balance),
`g191_093` (`#93`, the DBM half) and `g191_187` (`#187`, the DTM half) —
and all three are measured above rather than reasoned about: 0.766786,
-0.677876 and 0.682709. `g191_069` led, which is the expected shape (it is
the two-sided one), and the `g191_093` sign is negative because it sums
open-DOWN moves. The owner's own stage-2 fork overlap found
`bias:BIAS_SMA_26` at 0.7886 on 12 real frames against 0.753646 here; Gate
E's own real-data `bias_ta` is 0.8361 pooled / 0.8662 per-frame, above both.

## Closed: measured revert (2026-11-11)

What the revert did, each path restored with
`git restore --source=bafb803 --staged --worktree`:

- **deleted** `pandas_ta/momentum/g191_055.py`, `tests/test_g191_055.py`,
  `docs/measure_g191_055.py`;
- **restored to base `bafb803`**: `pandas_ta/momentum/__init__.py`
  (export), `pandas_ta/__init__.py` (`Category["momentum"]`),
  `pandas_ta/core.py` (accessor), `tests/test_altport2_ports.py`
  (`CATEGORY_TOTAL` back to 314), `README.md` (its headline counts and the
  `momentum (80)` row), `docs/IndicatorDictionary.md` (the `g191_055` row,
  the counts, the feed-ready list entry), `docs/MLCompanionContract.md`
  (back to 659 tagged / 302 `SF`, the issue-#80 parenthetical gone);
- **kept**: this file, `docs/reviews/auto-2026-11-11-g191-055/` (the
  porting session's review run) and the `g191_055` row in
  `docs/gate_e_ledger.csv` (see *Gate E* for why).

ASSUMPTION, logged because the receipt instruction named only "the module,
its wiring and its tests": `docs/measure_g191_055.py` was deleted too. It
imports `pandas_ta.momentum.g191_055` and cannot run with the module gone,
and the `dickson_ma` measured revert (5a7b463) deleted its measurement
script the same way. Its numbers survive in this file, and the script
itself in `git show acde1fe:docs/measure_g191_055.py`.

Checked after the revert: `git diff --name-status bafb803` lists exactly
the kept paths above — `docs/G191055Measured.md`, the three files of
`docs/reviews/auto-2026-11-11-g191-055/`, and the one-line
`docs/gate_e_ledger.csv` change. No file under `pandas_ta/` or `tests/`,
and no other doc, differs from base.

The wiring the port had added, for the record (*from*
`git diff bafb803 acde1fe`): `Category` 314 → 315 (`momentum` 80 → 81),
accessor count 322 → 323, dictionary probe 316 → 317 indicators,
`docs/MLCompanionContract.md` 659 → 660 tagged / 302 → 303 `SF`. All four
are back at the left-hand number.

## If this is ever un-reverted

In order, before any un-revert:

0. **Settle Gate A against the source.** Read the owner's copy of GTJA191
   `#55` (HKUDS/Vibe-Trading, MIT) and decide whether `R` has two branches
   or three. The port shipped three on the evidence above; the recalled
   string is the weak link. The one-line two-branch edit is
   `TWO_BRANCH_MUTANT` in `git show acde1fe:tests/test_g191_055.py`.
1. **Expect a strike anyway.** The three-branch column measured STRUCK at
   0.9078 per-frame vs `Ret_21d_pct`, and the two-branch prototype the
   owner's screen measured sat at 0.8992 per-frame against the SAME
   comparator — 0.0008 under the line, which is a near-miss, not a ship.
   Either form needs a new Gate E run on the 89 frames whose verdict is not
   STRUCK, or the owner's waiver. Nothing short of a change that moves the
   column off the 21-day-return family is likely to clear it.
2. **Gate C on real data, properly.** Gate E's pooled counts gave 396,154
   non-NaN / non-zero of 398,849; the 915 NaN bars the 20-bar warm-up does
   not explain were never attributed, and neither was the real-data sign
   split. Both need the frames.

## Review rounds of the port, including what was NOT re-reviewed

Four `/brutally-honest-review` rounds in the porting session (its 4-round
cap), run folder `docs/reviews/auto-2026-11-11-g191-055/`:

| round | verdict | findings |
|---|---|---|
| 1 | PASS | 4 MINOR, 1 NIT |
| 2 | PASS | 3 MINOR, 1 NIT |
| 3 | PASS | 3 MINOR |
| 4 | **REVISE** | 1 CRITICAL |

**13 findings in total, 0 MAJOR.** Not one was a mathematics error: every
finding was prose running ahead of the measurement — an unattributed test
count, a recalled fact filed as in-repo evidence, a Gate F cell disowning
its own owed row, a numerator without provenance, a "relative" tolerance
that was a no-op, an unmeasured uniqueness claim about the fork's
open-anchored ports, a float caveat guaranteeing the wrong object, and a
code comment contradicting its own script's stdout.

**The round-4 CRITICAL, and the disclosure that goes with it.** Round 4
found that the bare-`swing` count (then "370 occurrences") was
self-referential: it counted the module docstring quoting it, and round
3's own fix to that paragraph had moved it to 371. The fix landed —
re-measured twice (`rg -ic` over `pandas_ta/**/*.py`: whole-tree 371, then
372 after the next docstring edit, with the sum over the other 30 files
holding at **349** both times) and rewritten to quote only the
non-self-referential 349, with no whole-tree total anywhere. **That fix
was NOT re-reviewed: the 4-round cap was spent.** It is a prose number
re-derived from two runs in that session, it touches no code path, and the
full suite was re-run after it. The receipt instruction for this session
says not to start a new review loop, so **this revert was not reviewed
either** — it is a `git restore` of seven paths to base plus two file
deletions, verified by the `git diff --name-status bafb803` check above and
the suite run below.

## Suite run (this repo, after the revert)

`python -m pytest -q`, full suite, default collection order:
**3 failed, 5,230 passed, 83 skipped** (106.06 s). The three failures:

* `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
  — needs the sibling `../AlternativeRepos` checkout, absent in this
  worktree (CLAUDE.md "Known breaks"; CI deselects it).
* `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
  — the untracked `docs/pine/` corpus (CLAUDE.md "Known breaks").
* `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  — measured message: "no Gate E ledger row for `['mtd_ret']`".
  `g191_055` is **no longer in it** (it was, at `acde1fe`): it is out of
  `Category`, so it needs no row, and `mtd_ret` pre-dates this issue.

All three pre-date this issue; none is this revert's. The porting session's
run at `acde1fe` was **3 failed / 5,255 passed / 83 skipped** with the same
three test ids.

The post-revert count is **5,230**, not the previous receipt session's
**5,228** at base `bafb803`: +2, and both are measured, not inferred.
`python -m pytest --collect-only -q -k g191_055` collects exactly two ids,
`tests/test_gate_e_ledger.py::test_verdict_follows_the_bands[g191_055:G191_055_20]`
and
`tests/test_gate_e_ledger.py::test_every_column_fires_on_real_data[g191_055:G191_055_20]`
— the two tests the kept STRUCK ledger row adds, both parametrized over the
whole ledger rather than over `Category`, and both passing (a STRUCK verdict
is what these ρ's imply, and the row's `non_zero` is 396,154 > 0). The 27
tests the port had added (26 in `tests/test_g191_055.py` plus the ledger's
Gate B/D name check) are gone with it: 5,255 − 27 = 5,228, +2 = 5,230
(*derived*, and it matches the run).

`python -m pytest tests/test_gate_e_ledger.py -q` on its own: 1 failed /
746 passed, the one failure being the `mtd_ret` owed row above.
