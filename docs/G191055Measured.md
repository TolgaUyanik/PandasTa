# g191_055 — measured (issue #80)

> **Status: Gates A–D cleared in this session, Gate E PENDING (run by
> issue-solver after this session, CLAUDE.md "Owed, not failed"), Gate F
> green in this repo with the parent repo's suite run by the launcher.
> The issue's prototype measured DISCLOSE_GAP (max |ρ| 0.8628 vs
> `Ret_21d_pct`) — but this port is NOT the prototype (see Gate A), so
> that number does not transfer and the port's own Gate E run decides
> whether `G191_055_20` ships, discloses, or is reverted.**

20-day Wilder swing-index sum: Guotai Junan's (2017, "GTJA191", internal
quant report) alpha `#55`, per issue #80, which attributes its copy of the
report to HKUDS/Vibe-Trading (MIT) — a copy **not read in this session**,
see the disclosure under Gate A. Module
`pandas_ta/momentum/g191_055.py`, column `G191_055_20`. Tests:
`tests/test_g191_055.py` (**26, all passing**). Numbers below:
`python docs/measure_g191_055.py` for Gates A–D and the synthetic frames.
Environment: this worktree's pinned pandas/numpy. Measured 2026-11-11.

## Gate A: derivation from the source formula, not the prototype — and the two disagree

Issue #80 quotes GTJA191 alpha `#55` with its middle **elided**:

    #55: SUM(16*(...)/R*MAX(|H-C1|,|L-C1|), 20)

**What this session could NOT do, disclosed up front.** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own named
copy — HKUDS/Vibe-Trading (MIT) — was never read, and the issue's own
quote hides both the numerator and `R`. Two sources were available here,
and they **disagree about `R`**.

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

### Source 2: the report's own `#55` string as this session RECALLS it — THREE branches

    R = (A>B & A>D) ? A + B/2 + E/4
      : (B>D & B>A) ? B + A/2 + E/4
      : D + E/4          with A=|H-C1|, B=|L-C1|, D=|H-L1|, E=|C1-O1|

**This is the weakest link in this Gate A and it is not dressed up as
anything else.** No copy of the GTJA191 report was readable here, so the
three-branch string is RECALLED, not transcribed.

### What this port ships, and why

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

**If the owner's copy turns out to carry the two-branch `R`,** the fix is
one line: replace the module's inner `np.where` with its
`b + a / 2 + e / 4` arm. That edit is exactly `TWO_BRANCH_MUTANT` in
`tests/test_g191_055.py` and `TWO_BRANCH_R` in `docs/measure_g191_055.py`,
and the next section is the size of the decision, measured.

**Not Wilder's own Swing Index either.** Wilder's first two cases
SUBTRACT half the smaller term (`R = A - B/2 + E/4`) and his constant is
`50/T` (`T` = the limit move) rather than `16`. GTJA191's string adds and
uses `16`; this port follows GTJA191, which is what the issue asks for
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
inequality is violated **0** times. The arm stays in the module because it
is in the source formula and because an inconsistent frame (bad vendor
data, `L > H`) can still reach it — but nothing in this port's claims
depends on it, and
`tests/test_g191_055.py::test_branch_one_is_unreachable_on_consistent_ohlc`
pins the census and both inequalities.

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
2–3 poisoned), valid from bar 4. **The synthetic walk never reaches it: 0
of 1,500 bars have `R == 0` and 0 have `H == L`**, so the fixture is this
session's only coverage, and the real-data cost is Gate E's to report.

### The numerator: in-repo provenance, kept in the source's written order

Unlike `R`, the numerator `N = C - C1 + (C - O)/2 + C1 - O1` is read
straight off the prototype (`ind_screen.py:404`,
`c - c1 + (c - o) / 2 + c1 - o1`), so it has an **in-repo** source, and
the recalled report string agrees with it term for term. The two sources
that disagree about `R` agree about `N`; nothing here rests on recall
alone.

`C - C1 + (C - O)/2 + C1 - O1` cancels algebraically to
`C + (C - O)/2 - O1` — `DELAY(C,1)` drops out of the numerator entirely,
surviving only inside `A`, `B`, `E`, `R`. The source's order is kept for
**fidelity** (CLAUDE.md's reason for summing TA-Lib's Hilbert taps in
TA-Lib's order), **not** because the two spellings were found to differ:
measured on the walk they agree bit-for-bit, **max |diff| 0.0, 0 of 1,499
bars differing**. Reported rather than assumed in either direction.

### What this is, next to what the fork already ships

This fork ships **no other Swing Index / ASI construction** — measured by
one case-insensitive content search for
`swing[ _-]?index|accum\w* swing|\bASI\b` over `pandas_ta/**/*.py`
(ripgrep, source files only), which matches **this file and nothing else**.

A looser search for bare `swing` matches **31 files**, one of which is the
port's own module. The count quoted here is deliberately the one over the
**other 30**, because any total includes the port's own docstring and
moves whenever that docstring is edited — which is exactly how an earlier
draft of this paragraph went stale by one. Ripgrep's count mode
(`rg -ic swing` over `pandas_ta/**/*.py`), summed over every file except
`pandas_ta/momentum/g191_055.py`, gives **349 matching LINES across the
other 30**. No whole-tree total is quoted here, deliberately — one was,
and editing the module docstring moved it by one. (Lines are not
occurrences either: several of the 349 carry the word twice.) The evidence
that none of those 30 is a Swing Index is
the index-pattern search above matching none of them — **not** a reading
of all 349 lines, which this session did not do. Those 30 are the SMC /
pivot-structure detectors (`trend/swing_equilibrium.py`,
`trend/bos.py`, `trend/choch.py`, `trend/sr_decay.py`,
`trend/zigzag_fib.py`, …), their package and accessor plumbing
(`pandas_ta/__init__.py:85`, `trend/__init__.py:50`, `core.py`'s `swing_*`
keyword arguments), and bare uses of the word for a price swing inside
modules that are something else entirely — `momentum/tsi.py:53`,
`overlap/kama.py:58`, `volatility/wvma.py:65`, `volume/volcv.py:39`.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived from the source formula with the prototype's two-branch `R` rejected, disclosed and measured against | A hand-derived 5-bar example (`length=2`) with every `A`, `B`, `D`, `E`, `R`, `N` and `SI` written out, branch 2 / branch 3 / an `A == B == D` triple tie all exercised: `R = [nan, 8.25, 13.5, 6.75, 2.0]`, SI `[nan, 23.272727272727273, -163.55555555555554, -28.444444444444443, 6.0]`, column `[nan, nan, -1.5248133509003072, -2.0425531914893615, -0.24264264264264263]`, bar by bar to `abs=1e-12`. An independent per-bar replay (plain Python loop over numpy scalars — no `.rolling()`, no `.shift()`, no `np.where`) at the shipped default on a 900-bar frame: `t=300 module=-2.6501557001261786 loop=-2.6501557001261786`, `t=600 0.17579471867618934 / 0.17579471867618915`, `t=899 -1.4155524946725604 / -1.41555249467256` (the last two agree to `rel=1e-9`, differing only in the summation's last bits). The three-way prototype comparison and the branch census are in the Gate A sections above |
| B Causality | pass | Future-perturbation sweep (open/high/low/close jointly rewritten from `j` onward), **36 offsets** past the 21-bar warm-up: real module **0 of 36** leaks. Two mutants (`importlib` source read, `exec`'d in memory), each shown live different from the real module, then caught **36 of 36**: the final write index shifted `length=20` bars into the future, and `rolling(length, center=True)` in place of the causal trailing window (the `bos` look-ahead bug class CLAUDE.md documents) |
| C Reachability | pass on synthetic; **real data owed with Gate E** | 1,500-bar synthetic OHLC walk (seed 11, `low <= open, close <= high` at every bar — **1,500 of 1,500** verified; see `docs/measure_g191_055.py:_walk`), shipped default: **1,480 of 1,500** bars non-NaN (98.67%) — exactly `n - length` — first valid at bar **20**, the structural warm-up boundary (`min_length - 1`). **1,480 distinct values.** Range `[-4.486048, 2.354767]`, median `-0.285670`, **588 positive / 892 negative / 0 zero**. The walk's `open` is the SAME bar's close times noise, so it carries no overnight-gap structure: the sign imbalance is the frame's, not a property of the formula, and nothing here claims otherwise. **The one real reachability risk is `R == 0`**, which this frame never reaches (0 of 1,500) and only real data can price |
| D Scale-free | pass | A positive rescale factors through `A`, `B`, `D`, `E`, `N`, `R` and `MAX(A,B)` and cancels against the `/close`; all three branch tests and the `R == 0` test are scale-invariant. Measured on the 1,500-bar walk with all four price series scaled: PRICE ×8/×64 **bit-identical, 0.0 max\|diff\|**; ×10/×3.7 within float64 rounding tolerance (**2.0872192862952943e-14 / 2.070565940925917e-14** absolute, **4.652690502521582e-15 / 4.6155679719163575e-15** relative to `max\|column\| = 4.486048`), NaN masks matching at all four. The SELECTED-BRANCH masks are measured too, and they are measured rather than argued: at a non-power-of-two `k` the module compares `fl(fl(k*H) - fl(k*C1))`-style differences of SEPARATELY rounded products, not `fl(k*A)`, so a strict `>` between two nearly equal branch quantities could in principle tie OR invert — monotonicity of `x -> k*x` does not cover it. Measured: **0 bars changed branch** at any of the four multipliers. `0 < 1480 fires < 1500` and `1480 > 1` distinct values rule out a constant column |
| E Attribution | **pending** | Gate E: pending, run by issue-solver after this session |
| F Suites | this repo green apart from three failures: the two CLAUDE.md "Known breaks" **plus this port's own OWED Gate E ledger row**, which fails by design (CLAUDE.md "Owed, not failed"); parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see run below |

## Gate E: attribution

**Gate E: pending, run by issue-solver after this session.**

This session may not read `../Backtesting`, so the harness
(`gate_e_overlap.py run --module pandas_ta.momentum.g191_055`,
Backtesting #107) is the launcher's to run, and
`docs/gate_e_ledger.csv` carries no `g191_055` row yet. Until it does,
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails here naming `['g191_055', 'mtd_ret']` — expected, per CLAUDE.md's
"Owed, not failed on the way to `dev`". A later receipt session records
the row and writes the measured numbers into this file.

**What the issue measured on the PROTOTYPE, and why it does not transfer.**
Issue #80 reports the prototype at max |ρ| **0.8628** vs `Ret_21d_pct`
(manifest, n = 395,533) with a top-5 per-frame max median of 0.8992 →
DISCLOSE_GAP, and a stage-2 fork overlap of 0.7886 vs `bias:BIAS_SMA_26`.
Those are measurements of the **two-branch** column. This port differs
from it at every non-NaN bar of the synthetic walk (ρ 0.967451 between the
two, max |diff| 2.3181), so the prototype's numbers are a **prior, not a
result**: ρ 0.9675 is high enough that the port will probably land in the
same neighbourhood, and nowhere near 1.0, so "probably" is all it is. The
per-frame max median of 0.8992 on the prototype sits **0.0008 under the
0.90 strike line**, so the port's own run could land either side of it.
**If the port's Gate E strikes `G191_055_20`, the column is reverted and
this file stays as the receipt** — issue #80's "Done when" counts a
measured revert as a close.

## Non-redundancy on a synthetic frame — NOT Gate E

Spearman ρ of `G191_055_20` against the nearest shipped columns, on the
900-bar seed-5 OHLC walk (`python docs/measure_g191_055.py`):

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

All eight sit under the 0.90 strike line and under the 0.80 DISCLOSE_GAP
line on this frame, in |ρ|. This is a synthetic stand-in and proves
nothing about Gate E, whose bands are defined over the 89 frozen
ALTPORT-1 BIST frames against 687 engine comparators (CLAUDE.md, Gate E).

The open-anchored directional GTJA191 ports already in this fork are
**three**, not one — `g191_069` (`#69`, the DTM-vs-DBM balance),
`g191_093` (`#93`, the DBM half) and `g191_187` (`#187`, the DTM half) —
and all three are measured above rather than reasoned about: 0.766786,
-0.677876 and 0.682709. `g191_069` leads, which is the expected shape (it
is the two-sided one), and the `g191_093` sign is negative because it sums
open-DOWN moves. The owner's own stage-2 fork overlap found
`bias:BIAS_SMA_26` at 0.7886 on 12 real frames against 0.753646 here,
which is the only comparator with a real-data cross-check available to
this session.

## Wiring

`Category` **314 → 315** (`momentum` **80 → 81**); `df.ta.<name>()`
accessor count **322 → 323**; dictionary probe **316 → 317** indicators.
Touch points: `pandas_ta/momentum/g191_055.py` (module),
`pandas_ta/momentum/__init__.py` (export), `pandas_ta/__init__.py` →
`Category["momentum"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.g191_055` (accessor), `tests/test_g191_055.py`
(tests). `README.md`'s headline, its `df.ta.<name>()` count and its
`momentum (81)` row, and `docs/IndicatorDictionary.md` (regenerated), all
updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated
**659 → 660 / 302 → 303 `SF`** (`G191_055_20` probes cleanly at the
dictionary's 600-bar synthetic frame with a 20-bar warm-up and takes many
distinct values, so the generator tags it `SF`), checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match
(314 → 315); no `CATEGORY_BUCKETS` entry needed (that dict tracks only
`trend`/`volatility`/`volume`, not `momentum`).

The accessor forwards `open`/`high`/`low`/`close` and the `length`
tunable; `tests/test_g191_055.py::test_name_registration_and_accessor`
asserts `df.ta.g191_055()` equals the direct call and that
`length=10` reaches the module under its own name (the `supertrend`
failure mode CLAUDE.md documents, which `hasattr` cannot see).

## Review rounds, including what was NOT re-reviewed

Four `/brutally-honest-review` rounds (the session's 4-round cap), run
folder `docs/reviews/auto-2026-11-11-g191-055/`:

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
re-derived from two runs in this session, it touches no code path, and the
full suite was re-run after it (same 3 failed / 5255 passed / 83 skipped)
— but a reader should know it carries one less pair of eyes than
everything above it.

## Suite run (this repo)

`python -m pytest -q -p no:warnings --tb=line -rf`, full suite, default
collection order: **3 failed, 5255 passed, 83 skipped** — run twice, before
and after the review rounds' edits (109s, then 106s), identical counts and
identical failures both times.

* `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  — "no Gate E ledger row for `['g191_055', 'mtd_ret']`". `g191_055`'s row
  is owed by design (Gate E is the launcher's); `mtd_ret` pre-dates this
  issue.
* `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
  — needs the sibling `../AlternativeRepos` checkout, absent in this
  worktree (CLAUDE.md "Known breaks"; CI deselects it).
* `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
  — the untracked `docs/pine/` corpus (CLAUDE.md "Known breaks").

No other test regresses, and the three failures are exactly the three the
previous session's receipt recorded, with `g191_055` now named alongside
`mtd_ret` in the first. The move from the previous session's **5,228**
passed to **5,255** is **+27**, and all 27 are measured, not inferred:
`python -m pytest --collect-only -q -k g191_055` collects exactly 27 ids —
the **26** in `tests/test_g191_055.py` (which also pass on their own:
`python -m pytest tests/test_g191_055.py -q` → 26 passed) plus
`tests/test_gate_e_ledger.py::test_every_new_indicator_has_gate_b_and_d_tests[g191_055]`,
which this port created by entering `Category`, since that test is
parametrized per indicator needing a row.
