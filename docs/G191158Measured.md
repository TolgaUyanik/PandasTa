# g191_158 — measured (issue #81)

> **Status: Gates A–D cleared in this session; Gate E pending, run by
> issue-solver after this session; Gate F in this repo: 3 failures — the 2
> CLAUDE.md "Known breaks" plus the Gate E ledger row this port owes
> (expected, "Owed, not failed"), all three named below — the parent repo's
> suite run by the launcher. The
> issue's prototype measured DISCLOSE_GAP (max |ρ| 0.8834 vs `pdist_pct`),
> which is a PRIOR for this port and not a result.**

Range over close: Guotai Junan's (2017, "GTJA191", internal quant report)
alpha `#158`, per issue #81, which attributes its copy of the report to
HKUDS/Vibe-Trading (MIT) — a copy NOT read in this session, see the
disclosure under Gate A. Module `pandas_ta/volatility/g191_158.py`, column
`G191_158`. Tests: `tests/test_g191_158.py` (**26, all passing**). Numbers
below: `python docs/measure_g191_158.py` for Gates A–D and the synthetic
frames, `python -m pytest` for Gate F. Environment: this worktree's pinned
pandas 2.3.3 / numpy 1.26.4. Measured 2026-11-11.

## Gate A: derivation from the published formula, not the prototype

Issue #81 states GTJA191 alpha `#158`:

    ((H-SMA(C,15,2))-(L-SMA(C,15,2)))/C = (H-L)/C

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own named
copy — HKUDS/Vibe-Trading (MIT) — was never read. Everything below is
derived from the issue's own stated formula string, per the issue's own rule
("Gate A starts from the source formula, not the prototype"), then
cross-checked against the issue's own prototype
(`docs/issues/screen/ind_screen.py:517-518`):

    @cand("g191_158", "range over close", G,
          "#158: ((H-SMA(C,15,2))-(L-SMA(C,15,2)))/C = (H-L)/C")
    def _(o, h, l, c, v): return (h - l) / c

`SMA(A,n,m)` is GTJA's own recursive smoother, not this fork's
`pandas_ta.overlap.sma` — `Y[t] = (m*A[t] + (n-m)*Y[t-1]) / n`, an EMA with
`alpha = m/n`, read off the prototype's own docstring
(`ind_screen.py:57-59`) and implemented for real by other GTJA191 ports in
this fork — `g191_109` (`pandas_ta/volatility/g191_109.py:101`) through a
`_gtja_sma` helper, `g191_146` (`pandas_ta/momentum/g191_146.py:106-111`)
inline. **No fork-wide count is given**, deliberately: two earlier drafts of
this file stated one (first "four", then "seven") and both were wrong,
because `git grep "min_periods=n).mean()"` matches only the helper spelling
whose locals are named `n`/`m` and misses every inline call — `g191_146` was
in that grep's output as a docstring hit while its two real call sites were
not. The census is not load-bearing for this port, so it is not made; the
two lines cited above are read. This candidate's
`candidates.csv` row carries NO `conv` field (an empty cell,
`candidates.csv:57`): the `/C` is already inside the source formula, so no
extra scale-free conversion is applied.

### The reduction, and it is the source's, not this port's

Write `S = SMA(C,15,2)` — one series, the same at both occurrences:

    ((H - S) - (L - S)) / C = (H - S - L + S) / C = (H - L) / C

at every bar where `S` is defined, with no assumption on `S` beyond its
being one real number per bar. The source states the cancellation itself
(`= (H-L)/C`), and the prototype computes the reduced right-hand side. This
port ships the reduced form. That is its ONE decision, and the honest
measurement of what it costs is: almost nothing. Three spellings, all run
on the 1,500-bar synthetic walk:

| spelling | non-NaN bars | vs the shipped column |
|---|---|---|
| reduced `(H-L)/C` — **shipped** | **1,500** | — |
| literal `((H-S)-(L-S))/C`, `S` with this fork's `min_periods=15` | **1,486** (14 leading NaNs) | **bit-equal on all 1,486** shared bars |
| literal with the PROTOTYPE's own `sma` (no `min_periods`, `ind_screen.py:59`) | **1,500** | **bit-equal on all 1,500** bars |

So the 14-bar warm-up is **this fork's convention, not the source's** —
written the way the prototype writes `sma`, the literal form has no warm-up
and is indistinguishable from the shipped column on this frame. This port
does not get to claim those 14 bars as the reason for the reduction, and
the earlier draft of this file did; the number above is the correction.

The two spellings are still not identical in general, and that is measured
rather than assumed. On a stress frame (σ 0.20, where the smoother lags far
behind the bar) **50 of 1,486** shared bars differ, max \|diff\|
**5.83e-16**, max \|rel diff\| **5.54e-15**. The mechanism is measured too:
the max ratio between `H`/`L` and `S` is **1.096357** on the ordinary walk
(inside Sterbenz's factor of 2, so both subtractions are exact) and
**6.801292** on the stress frame (outside it, which is why bars move
there and not here). Where they differ the reduced form is the more
accurate of the two, and that is **derived, not measured**: IEEE754
subtraction is correctly rounded, so `H-L` is one correctly-rounded
difference against the literal form's three roundings before the division.
All of it is pinned by
`tests/test_g191_158.py::test_the_literal_spelling_agrees_within_float_noise`
and `::test_the_literal_spelling_is_not_bit_equal_in_general` — the stress
numbers asserted LOOSELY (`0 < differing < 1486`, dust `< 1e-14`), because
pinning `ewm`'s last bit for a spelling this module does not ship would
break the suite on a pandas bump for a reason that cannot touch
`(high - low) / close`.

**So what actually decides it:** the source's own string states the
reduction (`= (H-L)/C`), the prototype computes the reduced form, and this
port is bit-identical to that prototype — the expression whose Gate E
numbers issue #81 quotes. Not a cost table.

### No other reading needed fixing

The string has no ternary, no windowed operator, no `DELAY`, and no bar-0
boundary: `H`, `L` and `C` are all current-bar reads. There is nothing in it
this session had to disambiguate — unlike `g191_003` (three fixed readings)
or `g191_055` (a two-vs-three-branch disagreement between sources). The
whole of Gate A here is the reduction above plus the two edge cases below.

### Two edge cases, both decided here

* **`H == L`** (a zero-range bar: a limit move, a halt, an untraded day) →
  exactly `0.0`, not NaN. `0.0` is the true value of the range and the
  column's floor. The continuous-float walk never reaches it (**0 of
  1,500** bars), so the tie case is measured on a TICK-ROUNDED synthetic
  frame (tick 0.01): **107 of 1,500** bars have `H == L`, and the column is
  exactly `0.0` on those 107 and only those (`(out == 0) == (H == L)` all
  True, measured). On real data exact OHLC ties are common — CLAUDE.md's
  FVGDEAD note measures 21.17% of BIST daily bars closing exactly at an
  extreme, which is a **different** statistic (`C == H` or `C == L`, not
  `H == L`); the real-frame `H == L` rate is not measured here and is owed
  to Gate E's reachability counts.
* **`C == 0.0`** → `+inf` (`NaN` if also `H == L`). Not guarded, and that
  is a decision on record: the prototype divides with a bare `/`
  (`ind_screen.py:518`) where it uses the screen's `sdiv` (inf → NaN) on
  other candidates, and `g191_003` ships an unguarded `/close` for the same
  reason — a zero close is not an OHLC bar this fork models anywhere.
  Pinned by `test_a_zero_close_is_not_guarded`.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived from the issue's own stated formula, whose own reduction this port ships; matched against the REAL screen candidate bit-for-bit, and against both spellings of the literal form | What carries this gate, in order: (1) a hand-derived 6-bar example with every bar's arithmetic written out (`[2/9, 4/12, 4/9, 5/15, 0.5, 6/20]`, all six bars checked — there is no warm-up to skip); (2) the REAL candidate loaded out of `docs/issues/screen/ind_screen.py` through its own registry (present in this worktree, gitignored so the test may not depend on it): same NaN mask, `max\|diff\| = 0.0`, **1,500 of 1,500** bars bit-equal — a genuine external oracle, and the one that matters, since it is the expression Gate E's prior was measured on; (3) the literal spelling, the table above. What does NOT carry it, and is not dressed up as if it did: the per-bar scalar replay at bars 0 / 300 / 600 / 899 of a 900-bar frame (bit-exact: `bar 0 module=0.01106902049904393 loop=0.01106902049904393`, likewise the other three) and the retyped prototype expression (`max\|diff\| = 0.0`) are the same one-line expression written again, so they rule out a pandas-side surprise — an alignment slip, a dtype promotion — not a wrong formula |
| B Causality | pass | The column has no memory at all — `(H[t]-L[t])/C[t]`, no `shift`, no `rolling`, no recursion — so a leak has to be written in on purpose. Future-perturbation sweep (high/low/close jointly rewritten from `j` onward), 37 offsets: real module **0 of 37** leaks. Two mutants (`importlib` source read, `exec`'d in memory), each shown live different from the real module, then caught **37 of 37**: the final write index shifted one bar into the future, and `(high.shift(-1) - low.shift(-1)) / close` (the `bos` look-ahead bug class CLAUDE.md documents) |
| C Reachability | pass on synthetic; real-data counts owed to Gate E | 1,500-bar synthetic high/low/close walk (seed 11, `low <= close <= high` at every bar; `docs/measure_g191_158.py:_walk`): **1,500 of 1,500** bars non-NaN (100.00%), first valid at bar **0** — no warm-up — **1,500 distinct values**, range `[0.000573, 0.044346]`, median `0.011061`, **0 negative**, **0 zero**. Tick-rounded frame (`_tick_walk`, 1,500 bars, tick 0.01): **1,500** non-NaN, **1,393** non-zero, **107** exactly zero (every one a `H == L` bar), **458** distinct values. One column, so there is no second column to check. NaN surface, measured for each input rather than argued from the shape of the expression: a single NaN planted in `high`, `low` or `close` at bar 700 moves exactly one output bar (700) and leaves every other bar bit-identical — three runs, three single-bar results |
| D Scale-free | pass | `(k·H − k·L)/(k·C) = (H−L)/C` for any `k > 0`, exactly; volume is not an argument at all. Measured on the 1,500-bar walk: PRICE ×8/×64 **bit-identical** (`max\|diff\| = 0.0`, 1,500 of 1,500 bars bit-equal); ×10 and ×3.7 within float64 rounding (**2.16e-16** / **1.87e-16** max \|diff\|; 168 and 29 of 1,500 bars still bit-equal), NaN masks matching at all four. `nunique = 1500 > 1` rules out a constant column. **Disclosed:** CLAUDE.md's `0 < fires < n` is vacuous in its upper half for this column — with no warm-up, `fires == n == 1500` on clean data. That clause exists to kill a constant or all-NaN column, which the distinct-value counts above do instead; the column is not held out of the gate, the gate's upper half simply has nothing to bite on here |
| E Attribution | **pending, run by issue-solver after this session** | See the Gate E section below |
| F Suites | this repo: 3 failed, 5257 passed, 83 skipped — the 3 are pre-known and named below; parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q -p no:warnings --tb=no -rf` (this session) |

## Gate E: attribution

**Gate E: pending, run by issue-solver after this session.** This session may
not read `../Backtesting`, so it did not run
`gate_e_overlap.py run --module pandas_ta.volatility.g191_158`. Until the
row lands in `docs/gate_e_ledger.csv`,
`tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
fails here naming `['g191_158', 'mtd_ret']` (measured in this session;
`mtd_ret` pre-dates this issue). CI into `dev` sets `GATE_E_PENDING_OK=1`
and skips it as "Gate E owed" (CLAUDE.md, "Owed, not failed").

**The issue's prototype number is a PRIOR, not a result.** Issue #81
measured the PROTOTYPE on run `screen_20261024`: max |ρ| **0.8834** vs
`pdist_pct` (manifest, n = 398,760), top-5 per-frame max median **0.8858**,
89 ALTPORT-1 frames, 398,849 bars, 329 + 358 comparators, canary bit-equal →
**DISCLOSE_GAP**. Next comparators: `pdist_pct` 0.8834, `pdist_pct_Pctl`
0.7430, `pdist_pct_State` 0.7028. Unlike most ports, that prototype
expression is **bit-identical** to this port's column (`max|diff| = 0.0`,
1,500 of 1,500 bars, measured against the real candidate out of the screen's
registry), so the port's own run is expected to reproduce those numbers
rather than merely resemble them — expected, not measured, and the
launcher's run is what settles it.

`pdist_pct` sitting at the top is structural rather than surprising:
`pdist = 2(H-L) − |C−O| + |O−C₁|` (`pandas_ta/volatility/pdist.py:43`), so
its leading term is twice this column's numerator. On the 900-bar synthetic
frame below, `pdist/close` is the second-nearest comparator (ρ 0.7065,
behind `g191_109`'s 0.7346).

If the launcher's run lands STRUCK (pooled |ρ| ≥ 0.90, or a top-5
comparator's per-frame median ≥ 0.90), the column is reverted and this file
stays as the receipt — the issue's own "Done when" treats that as closing it
exactly as well as a ship.

## The fork column this one is one factor away from

`bw_mfi`'s shipped default is
`MFI_BW_SF_<length> = ((H−L)/C) / (V/SMA(V,length))`
(`pandas_ta/volume/bw_mfi.py:47`) — **this column divided by relative
volume**. That is a strong enough relationship to be measured rather than
described, so it was:

* **Constant volume:** the relative-volume factor is exactly `1.0` once its
  own 20-bar average exists, and the two columns are then **bit-identical**
  from bar 19 — `max|diff| = 0.0`, **1,481 of 1,481** overlapping bars
  bit-equal on the 1,500-bar walk with flat volume, `MFI_BW_SF_20`'s first
  non-NaN bar **19**. Pinned by
  `test_bw_mfi_is_this_column_divided_by_relative_volume`.
* **Varying volume (lognormal, σ 0.6), 900-bar frame:** ρ **0.6922**
  (n = 881). The whole distance between 1.0 and 0.6922 is that one factor.
* **Real data, the owner's own measurement:** the stage-2 fork-overlap
  screen (`docs/issues/screen/fork_overlap.py`, 12 BIST frames, every
  `Category` indicator at defaults, scale-free columns kept) puts this
  candidate's HIGHEST fork overlap at |ρ| **0.8252** against
  `har_park:HARPARK_1_5_22_500`, per-frame max median **0.8217**, verdict
  `new` (`fork_overlap.csv:57`) — below the 0.90 line, so `MFI_BW_SF_20`
  sits at or below 0.8252 there.

  **That `MFI_BW_SF_20` is in that comparator set is a READ, and here is
  the read** — it replaces an inference an earlier draft of this file made
  and a round-3 review response that wrongly reported the file as silent:
  a later round of the same script, with the same hardcoded frames,
  records

      nm_effort_result_20,0.7867,bw_mfi:MFI_BW_SF_20,0.8104,bw_mfi:MFI_BW_SF_20,new

  (`docs/issues/screen/fork_overlap_r7.csv:7`; `candidates_r7.csv:7`
  carries the same pair). So `fork_columns()` computes the column and the
  keep filter keeps it — in the `r7` run. That corroborates rather than
  proves membership in the stage-2 `fork_overlap.csv` run whose 0.8252 row
  is quoted above, which is the honest limit of it. The supporting facts
  are weaker than the read and are stated as such: that run's
  `fork_errors.txt` is **empty** (0 lines, read in this session), which
  says nothing errored in it rather than anything about `bw_mfi`; and
  `MFI_BW_SF_20` satisfies the keep filter on paper (`fork_overlap.py:85-93`:
  ≥100 finite bars, finite masks matching under price ×8, non-constant, max
  relative move `< 1e-6` — its own Gate D result, bit-identical under ×8, is
  strictly stronger than that last clause).

  What stays unknown: the committed `fork_overlap.csv` records only the
  maximum and the top per-frame comparator, not the full matrix, so
  `MFI_BW_SF_20`'s own ρ against this candidate on those 12 frames is
  bounded by 0.8252, not printed anywhere.

This is the disclosure, and it is not comfortable: a miner that already has
`MFI_BW_SF_20` is getting the same numerator again, de-normalised by volume.
What this column adds is the range-to-price measure **without** the volume
factor — which is what makes it a volatility feature rather than a
liquidity-efficiency one. Gate E decides it against the engine's 687
comparators. For scale, `bw_mfi`'s own Gate E number is |ρ| **0.578897**
against `vol_at_low_ratio`, n = 394,399, over 89 BIST daily frames
(`docs/AltportPortsMeasured.md:13`, pinned as a triple by
`tests/test_altport2_ports.py:203`) — **not** the 0.536816 still printed in
`pandas_ta/volume/bw_mfi.py:85`, which is the pre-correction figure tti's
rounding suppressed (`AltportPortsMeasured.md:19`). The comparator count
behind 0.578897 is recorded twice and inconsistently in this repo — **492**
at `AltportPortsMeasured.md:17`, **496** at `tests/test_altport2_ports.py:78`
and `:200` — and this port is not the place to settle it; either way it is
not today's 687. So neither figure is a prediction for this port's run; the
nearest fork column simply sits further from the strike line than this
column's own 0.8834 prototype prior does.

## Non-redundancy on a synthetic frame — NOT Gate E

Spearman ρ of `G191_158` against the nearest shipped columns, on the 900-bar
seed-5 walk with lognormal volume (σ 0.6) and a moving open
(`python docs/measure_g191_158.py`):

| comparator | ρ | n |
|---|---|---|
| `g191_109:G191_109_10_2_10_2` | **0.734603** | 882 |
| `pdist/close` (the Gate E prior's top comparator, in shape) | 0.706474 | 899 |
| `bw_mfi:MFI_BW_SF_20` | 0.692200 | 881 |
| `true_range/close` | 0.495485 | 899 |
| `cvi:CVI_10_10` | 0.382558 | 881 |
| `natr:NATR_14` | 0.203494 | 887 |
| `garman_klass:GKVOL_20` | 0.194016 | 881 |
| `har_park:HARPARK_1_5_22_500` | 0.186225 | 401 |
| `massi:MASSI_9_25` | 0.071564 | 868 |

Nothing here is above the 0.90 strike line, and the ordering is roughly what
the construction predicts: the range-based columns lead (`g191_109` is the
ratio of this column's own numerator smoothed once to the same numerator
smoothed twice — `e = SMA(H−L,10,2)`, `s = SMA(e,10,2)`, `e/s`,
`g191_109.py:157-159`, dimensionless and `SF`-tagged; `pdist` carries
`2(H−L)`), the
window-averaged ones (`natr`, `garman_klass`, `har_park`, `massi` — 9 to 500
bars) trail.

Three caveats, and the first one was wrong in this file's first draft:

* **The open.** `pdist = 2(H−L) − |C−O| + |O−C₁|` and `garman_klass` both
  read the open. The first version of `docs/measure_g191_158.py` built the
  comparator frame with `open == close`, which amputated `|C−O|` and froze
  `garman_klass`'s overnight term, and inflated `pdist/close` to 0.807473.
  The frame now carries a moving open (the prior close clipped into the
  bar's own range: `open == close` on **1 of 900** bars, inside `[low,
  high]` on **900 of 900**), and the two affected rows are the re-run
  numbers above (`pdist/close` 0.807473 → **0.706474**,
  `garman_klass:GKVOL_20` 0.201285 → **0.194016**). The other seven rows do
  not read the open and did not move.
* **It is synthetic.** An i.i.d. lognormal frame, not Gate E, and not real
  tape.
* **`har_park`'s 401 bars.** Its 500-bar fit window leaves only 401
  overlapping bars on a 900-bar frame, so that ρ is the least-supported row
  in the table — which matters, because `har_park` is exactly the column the
  owner's real-frame screen put at the top (0.8252).

The real-frame number that counts against fork columns is the owner's 0.8252
above; the one that decides the port is the launcher's Gate E run.

## Wiring

`Category` **314 → 315** (`volatility` **32 → 33**); `df.ta.<name>()`
accessor count **322 → 323**; dictionary probe **316 → 317** indicators. The
first three are measured (`docs/measure_g191_158.py` prints the `Category`
totals; the accessor count comes from the dictionary generator) and are
pinned by tests — `tests/test_readme_counts.py` asserts the README's
headline 315 and its accessor 323 against the live package,
`tests/test_altport2_ports.py` asserts `CATEGORY_TOTAL` and the
`volatility` bucket. The fourth is **not pinned by any test**: no test reads
the dictionary's "317 indicators probed" header (the two tests that open
`docs/IndicatorDictionary.md` read ML-form tags and candle columns), so that
number is regenerated by `python docs/gen_indicator_dictionary.py` and
trusted, not asserted.

Touch points: `pandas_ta/volatility/g191_158.py` (module),
`pandas_ta/volatility/__init__.py` (export), `pandas_ta/__init__.py` →
`Category["volatility"]` (discovery), `pandas_ta/core.py` →
`AnalysisIndicators.g191_158` (accessor), `tests/test_g191_158.py` (tests).
`README.md`'s headline, its accessor count and its `volatility (33)` row,
and `docs/IndicatorDictionary.md` (regenerated — `G191_158` probes as `SF`
with warm-up **0**, which `atr2` and `hwc` also have in that table, so it is
not the only one), updated and checked by `tests/test_readme_counts.py`.
`docs/MLCompanionContract.md`'s running tag count updated **659 → 660 /
302 → 303 `SF`**, checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` 314 → 315 and
`CATEGORY_BUCKETS["volatility"]` 32 → 33.

`docs/gate_e_ledger.csv` is **not** touched by this session: the row is
recorded after the launcher's Gate E run.

## Review rounds, and what they caught

Four `/brutally-honest-review` rounds (REVISE, REVISE, REVISE, REVISE — the
4-round cap), **20** findings, counted per round off the four verdicts
(8 + 4 + 4 + 4): **1 CRITICAL, 6 MAJOR, 6 MINOR, 7 NIT**. Full
transcripts in `docs/reviews/auto-2026-11-11-g191-158/01-g191-158.md`.
**Not one was a mathematics error.** Every single MAJOR and the CRITICAL
were the same defect class CLAUDE.md names as this repo's dominant one — a
claim written before it was measured:

* round 1: a false "unlike every ratio-form port" comparison (CRITICAL); the
  reduction decision propped up on a 14-bar warm-up that is this fork's
  convention and not the source's; a comparator frame with `open == close`,
  which inflated `pdist/close` to 0.807473; `Returns` saying "NaN only where
  an input is NaN", falsified by the port's own `offset` test.
* round 2: "four sibling GTJA-`SMA` ports" — the volatility count passed off
  as the fork's.
* round 3: "seven" — wrong again (`g191_146` spells the operator inline, and
  the grep that "counted" it cannot see inline calls).
* round 4: a round-3 review response that reported
  `docs/issues/screen/fork_overlap_r7.csv` as containing no `bw_mfi` row
  when line 7 names `bw_mfi:MFI_BW_SF_20` outright, plus two surviving
  universals ("every sibling `g191_*` port") in files that had just sworn no
  fork-wide claim was made, and a wrong description of what `g191_109`
  computes.

Three rounds of wrong census was root-caused rather than patched a fourth
time: **this port now states no fork-wide count at all**, citing two read
lines (`g191_109.py:101`, `g191_146.py:106-111`) and saying why the obvious
grep misleads. Round 4's four fixes landed with the cap spent and were
**not re-reviewed**; they are the last four entries in the run log, each
with the read that verifies it.

## Suite run (this repo)

`python -m pytest -q -p no:warnings --tb=no -rf`, full suite, default
collection order: **3 failed, 5257 passed, 83 skipped** (104.77s on the
final run, 104.78s on the previous one — wall-clock varies, the counts did
not), re-run after every review round's fixes. This port's own module
contributes 26 of the passes
(`python -m pytest tests/test_g191_158.py -q`: 26 passed). The three
failures:

* `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  — "no Gate E ledger row for `['g191_158', 'mtd_ret']`", measured in this
  session by running that test alone. Expected: Gate E is the launcher's
  run (CLAUDE.md, "Owed, not failed"); `mtd_ret` pre-dates this issue.
* `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
  — needs the sibling `../AlternativeRepos` checkout, absent in this
  worktree (CLAUDE.md "Known breaks"; CI deselects it).
* `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
  — the untracked `docs/pine/` corpus (CLAUDE.md "Known breaks").

No pre-port baseline run was made in this session, so no "+N passed" delta
is claimed here; the three failures above are the complete failure list of
the run that was made.
