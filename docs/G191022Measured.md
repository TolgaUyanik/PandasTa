# g191_022 — measured (issue #82)

> **Status: Gates A–E cleared and measured; the column SHIPS. Gate E was run by
> issue-solver on the committed code (run `is82-g191_022-19d9fa07`, measured
> 2026-11-11): `G191_022_6_3_12_1` max |ρ| **0.8842** vs `smi_SMIo_5_20_5`
> (manifest, n = 397,158), per-frame max median **0.8861** over 89 frames →
> **DISCLOSE_GAP**, below the 0.90 strike line on both the pooled and the
> per-frame rule. Recorded in `docs/gate_e_ledger.csv`. Gate F: this repo's
> suite is run below; the parent repo's (`Backtesting`) is run by the launcher in
> a clean worktree. The synthetic-frame 0.9116 against the same comparator that
> earlier sections disclose did NOT carry over to the real tape — see the Gate E
> section for the comparison.**

Smoothed 3-day change of the 6-day bias: Guotai Junan's (2017, "GTJA191",
internal quant report) alpha `#22`, per issue #82, which attributes its copy of
the report to HKUDS/Vibe-Trading (MIT) — a copy this session did **not** read,
see the disclosure under Gate A. Module `pandas_ta/momentum/g191_022.py`, column
`G191_022_6_3_12_1`. Tests: `tests/test_g191_022.py` (**29, all passing**).
Every number in the gate rows and tables below comes from
`python docs/measure_g191_022.py` in this worktree, on synthetic frames, EXCEPT
the Gate E numbers and the real-tape counts in Gate C, which come from the
launcher's Gate E run (`overlap_max.csv` and `meta.json` of
`is82-g191_022-19d9fa07`) on the 89 frozen ALTPORT-1 frames; the test count
comes from that module's own pytest run and the suite line at the end from the
full-suite run quoted there. The environment is this worktree's pinned
pandas/numpy. Measured 2026-11-11.

## Gate A: derivation from the published formula, not the prototype

Issue #82 states GTJA191 alpha `#22`:

    #22: SMA((C-MEAN(C,6))/MEAN(C,6) - DELAY(that,3), 12, 1)

**What this session could NOT do, disclosed up front:** `docs/pine/` and web
access are both unavailable in this worktree, so the issue's own named copy —
HKUDS/Vibe-Trading (MIT) — was never read. Everything below is derived from the
issue's own stated formula string, per the issue's own rule ("Gate A starts from
the source formula, not the prototype"), then cross-checked against the issue's
own prototype (`docs/issues/screen/ind_screen.py:317-321`):

    @cand("g191_022", "smoothed 3-day change of the 6-day bias", G,
          "#22: SMA((C-MEAN(C,6))/MEAN(C,6) - DELAY(that,3), 12, 1)")
    def _(o, h, l, c, v):
        b = (c - mean(c, 6)) / mean(c, 6)
        return sma(b - delay(b, 3), 12, 1)

with the operators read off the same module source: `delay(x, n) = x.shift(n)`
(`ind_screen.py:45`), `mean(x, n) = x.rolling(n).mean()` (`:47`) and
`sma(x, n, m) = x.ewm(alpha=m/n, adjust=False).mean()` (`:57-59`), GTJA's own
recursive smoother `Y[t] = (m*A[t] + (n-m)*Y[t-1]) / n`, **not** this fork's
`pandas_ta.overlap.sma`. The issue's string and the prototype agree, including
all four lengths (6, 3, 12, 1).

### The one reading the string does not fix on its own

**`DELAY(that,3)` refers to the BIAS, not to the whole bracket.** `that` is the
immediately preceding expression `(C-MEAN(C,6))/MEAN(C,6)`, so the smoothed
quantity is `bias[t] - bias[t-3]`. The alternative reading — `that` = the whole
subtraction — gives `bias - (bias - DELAY(bias,3)).shift(3)`. Three independent
things fix the reading taken here: the prototype names the bias `b` and writes
`b - delay(b, 3)`; the issue's own one-line title is "smoothed 3-day change of
the 6-day **bias**"; and the alternative is self-referential in the limit (its
`that` contains a `that`).

It is **not** a cosmetic difference, which is why it was measured rather than
waved through. On the 1,500-bar walk, over the 1,478 bars both define:

| | shipped reading | rejected reading |
|---|---|---|
| bit-equal bars | — | **0** |
| max \|diff\| | — | **0.02137858239070601** |
| Spearman ρ | — | **0.131234** |

The shipped column's own full range is `[-0.01020038, 0.01319801]`, i.e. a span
of 0.02339839, so the maximum disagreement (0.02137858) is **1.62× the column's
largest magnitude and 91% of its full span** — the two readings are different
indicators, not two spellings of one.
`tests/test_g191_022.py::test_the_rejected_reading_of_the_back_reference_is_a_different_column`
pins all three numbers.

### The fork's `min_periods` is a convention, not the source's

The prototype's own `sma` omits `min_periods` (`ind_screen.py:59`); this fork's
sibling GTJA ports spell the identical operator with `min_periods=n`
(`pandas_ta/volatility/g191_109.py:101`, `g191_152.py:144`, both read in this
session), and this port
follows the fork. Measured consequence on the 1,500-bar walk, so the warm-up is
not credited to the source:

* with `min_periods=12` (shipped): **1,481** non-NaN, first fire bar **19**;
* without it (the prototype's own spelling): **1,492** non-NaN, first fire bar
  **8**;
* on the **1,481** bars both define: `max |diff| = 0.0`, **bit-equal on all
  1,481**.

So the fork's convention masks 11 extra bars and changes no value.
`test_the_forks_min_periods_only_masks_bars_it_does_not_change_them` pins it.

### The shipped `bias` is the same inner term, in the other spelling

`pandas_ta.momentum.bias` at `length=6, mamode="sma"` computes
`(close / SMA(close,6)) - 1` — the same mathematical quantity as
`(C - MEAN(C,6)) / MEAN(C,6)`. This port spells the SOURCE's subtraction form,
because Gate A is settled bit-for-bit against the prototype and the prototype
subtracts. The two spellings differ in float64, measured on the 1,500-bar walk:

| comparison | n | max \|diff\| | bit-equal | max \|rel diff\| |
|---|---|---|---|---|
| inner term vs `BIAS_SMA_6` | 1,495 | 1.11e-16 | **26** of 1,495 | 3.50e-11 |
| whole column vs the column rebuilt on `BIAS_SMA_6` | 1,481 | 2.78e-17 | 49 of 1,481 | — |

Spearman between the column and the `bias`-built version is **1.0** (printed as
`1.00000000`). So the spelling is a float-rounding detail, not a different
indicator — and the port is the spelling that matches the prototype bit-for-bit.
`test_the_inner_term_is_the_shipped_bias_to_float_tolerance` pins it.

### What it measures

`bias` is where today's close sits relative to its own 6-bar mean, as a fraction
of that mean. `change = bias - DELAY(bias,3)` is how far that lead/lag moved in
three bars — the first difference of a mean-reversion gap, i.e. an
acceleration-like quantity. The final GTJA `SMA` (`alpha = 1/12`) smooths it.
What the column adds over the shipped `bias` is exactly that differencing and
smoothing; how much overlap remains against the engine's comparators was Gate
E's question, and Gate E measured it at max |ρ| 0.8842 (DISCLOSE_GAP).

## Gates

| Gate | Result | Evidence |
|---|---|---|
| A Correctness | derived from the issue's own stated formula with the one `that` reading fixed and disclosed above, then matched against the prototype BIT-FOR-BIT | A hand-derived 8-bar example at `bias_length=2, delay_length=1, smooth_length=2, smooth_weight=1` with every bar's arithmetic written out (including the `adjust=False` seeding: the recursion starts AT its first valid input, which `min_periods` then masks): column `[nan, nan, nan, -0.045548654244306416, 0.04063146997929607, -0.0028324131585001112, -0.03845324361628709, 0.035006182424660685]`. An independent per-bar replay at the shipped defaults (plain Python loop over numpy scalars — no `.rolling()`, no `.shift()`, no `.ewm()`) on a 900-bar frame: bar 19 `module=-0.009856101951829276` / `loop=-0.009856101951829295`, bar 300 `-0.0012465408500817363` / `-0.0012465408500817547`, bar 600 `0.004575053647730131` / `0.004575053647730138`, bar 899 `0.0039009482213807596` / `0.00390094822138076` — agreement to **2e-17 absolute**, not bit-for-bit, because pandas sums the rolling window and runs the recursion in a different order. The retyped prototype expression in the fork's spelling: same NaN mask, `max\|diff\| = 0.0`, **bit-equal on all 1,481** firing bars. The REAL candidate loaded out of `docs/issues/screen/ind_screen.py` through its own registry (present in this worktree, gitignored so the test may not depend on it): port vs candidate `max\|diff\| = 0.0`, bit-equal on all 1,481 shared bars; retyped vs candidate bit-equal on all **1,492** bars, so the retyping hides no slip |
| B Causality | pass | Future-perturbation sweep (`close` rewritten from `j` onward with another walk), **37** offsets past the 19-bar warm-up: real module **0 of 37** leaks. Three mutants (`importlib` source read, `exec`'d in memory), each shown live different from the real module, then caught **37 of 37**: the final write index shifted `smooth_length=12` bars into the future; `rolling(bias_length, center=True)` in place of the causal trailing mean (the `bos` look-ahead bug class CLAUDE.md documents); and `bias.shift(-delay_length)` in place of the backward `DELAY` — this formula's own most plausible sign slip |
| C Reachability | pass on synthetic and on the real tape | SYNTHETIC: 1,500-bar close-only lognormal walk (seed 11, σ 0.015; `docs/measure_g191_022.py:_walk`), shipped defaults: **1,481 of 1,500** bars non-NaN (98.73%) — exactly `n - 19` — first valid at bar **19**, the structural warm-up boundary (`min_length - 1`). **1,481 distinct values** (every firing bar distinct). Range `[-0.01020038, 0.01319801]`, median `0.00006976`, **749 positive / 732 negative / 0 exactly zero**. REAL DATA, from the launcher's Gate E run (`overlap_max.csv`, 89 ALTPORT-1 frames, 398,849 pooled bars): **397,158 non-NaN** and **397,158 non-zero** of those 398,849 bars, and **0 degenerate** frames — so the one shipped column fires on the real tape too, and never as a constant |
| D Scale-free | pass | A rolling mean is linear, so `close -> k*close` sends `bias` to `(k*C - k*mean)/(k*mean) = bias` — the `k` cancels exactly for any positive `k`, and everything downstream is built from `bias` alone. Measured on the 1,500-bar walk: PRICE ×8/×64 **bit-identical** (`max\|diff\| = 0.0`, bit-equal on all 1,481 bars); ×10/×3.7 within float64 rounding (**8.33e-17 / 5.81e-17**); NaN masks matching at all four multipliers; and **0 bars change sign** at each of the four (printed by the measure script as `sign-changed bars=0`) — informative at ×10/×3.7 only, since ×8/×64 reproduce the bits exactly and make the sign check vacuous there. The column is signed, so a sign flip would break it even at unchanged magnitude. `0 < 1481 fires < 1500` and **1,481 > 1** distinct values rule out a constant column. Volume is not an input, so there is nothing to rescale on that side |
| E Attribution | **DISCLOSE_GAP — ships** | Run by issue-solver on the committed code, measured 2026-11-11, run `is82-g191_022-19d9fa07`: `G191_022_6_3_12_1` max \|ρ\| **0.8842095326433863** vs `smi_SMIo_5_20_5` (manifest set, n = 397,158), per-frame max median **0.886086750749589** over **89** frames, **687** comparators (329 `compute_all` + 358 manifest), 398,849 pooled bars, canary bit-equal. Under 0.90 on both the pooled and the per-frame rule → **DISCLOSE_GAP**, so no strike and no waiver. Row recorded in `docs/gate_e_ledger.csv` with `python docs/gate_e_ledger.py record <run dir> --measured 2026-11-11` |
| F Suites | this repo only; the parent repo (`Backtesting`) is run by the launcher in clean worktrees | `python -m pytest -q` (this session): see the run below |

## Gate E: measured — DISCLOSE_GAP, the column ships

Run by issue-solver on the code committed by the port session, not by that
session: harness `gate_e_overlap.py run --module pandas_ta.momentum.g191_022`,
run id `is82-g191_022-19d9fa07`, measured **2026-11-11**, default parameters
(`kwargs {}`), no columns excluded. Run facts from the run's own `meta.json`:
**89** frozen ALTPORT-1 frames, **398,849** pooled bars, **687** comparators
(**329** engine `compute_all` + **358** `ml_features` manifest `1d`), canary
`AKBNK.IS, BIENY.IS, AGHOL.IS, SASA.IS bit-equal`, pandas 2.3.3 / numpy 1.26.4,
module sha1 `17eb39d0`, `pandas_ta_src_sha1` `2b5ade8e`.

| column | max \|ρ\| | against | set | n | per-frame max median | frames | verdict |
|---|---|---|---|---|---|---|---|
| `G191_022_6_3_12_1` | **0.8842095326433863** | `smi_SMIo_5_20_5` | manifest | 397,158 | **0.886086750749589** (same comparator) | 89 | **DISCLOSE_GAP** |

Band arithmetic, both of CLAUDE.md's strike rules: pooled 0.8842 < 0.90 and the
top-5 comparator's per-frame median 0.8861 < 0.90, so neither fires; 0.8842 is
≥ 0.80, so the verdict is DISCLOSE_GAP rather than DISCLOSE or SHIP. The margin
to the strike line is **0.0158** pooled and **0.0139** per-frame. Split by
comparator set, the manifest side is the binding one: `compute_all`'s own max is
**0.8212610575452909** vs `week_trend` (n = 397,158), 0.063 lower. **3 of 89
frames (3.37%)** have a per-frame \|ρ\| ≥ 0.90 against the top comparator — the
band is defined on the median, not the tail, and the median is what is quoted
above. **0** comparators were degenerate on this universe.

Nothing is struck, nothing is waived, and the column ships as it stands.

⚠ **One stale sentence is left in place on purpose.**
`pandas_ta/momentum/g191_022.py`'s docstring still reads "the overlap that
remains is Gate E's business, and Gate E is pending". It is NOT corrected here
because the ledger row pins that module's sha1 (`17eb39d0…`) and the whole
`pandas_ta` tree's sha1 (`2b5ade8e…`) as the code the run measured, and
`tests/test_gate_e_ledger.py` fails if either moves after the run — so editing
the docstring would invalidate the measurement it describes. The numbers above
and the row in `docs/gate_e_ledger.csv` are the live statement; the
`tests/test_g191_022.py` docstring carries the same note.

**The synthetic frame over-read the real tape, as the port session warned it
might.** On its 1,500-bar lognormal walk the column measured Spearman 0.9116
against `smi:SMIo_5_20_5`, above the strike line; the same pair on the 89 real
frames is **0.8842** pooled — the synthetic number was **0.0274** high, and the
issue's prototype number (0.8842 vs `smi_SMIo_5_20_5`, n = 397,158) was the
better prior, exactly as Gate A's bit-identity to the prototype suggested. The
port reproduces the prototype's pooled ρ to the four decimals the issue quoted.
The `g191_003` precedent (0.906 synthetic, 0.831 real) held again here.

## Non-redundancy on a synthetic frame — NOT Gate E

Spearman ρ of `G191_022_6_3_12_1` against the nearest shipped columns, on the
1,500-bar walk with a synthetic OHLCV frame wrapped around it
(`python docs/measure_g191_022.py`). These are fork columns on a synthetic
frame, not the engine's 687 comparators on real frames, so they bound nothing
about Gate E's verdict:

| comparator | ρ | n |
|---|---|---|
| `smi:SMIo_5_20_5` (the issue's Gate E top comparator for the prototype) | **0.911597** | 1,481 |
| `bias:BIAS_SMA_6` (the inner term itself) | **0.808845** | 1,481 |
| `roc:ROC_10` | 0.440859 | 1,481 |
| the UNSMOOTHED `bias - bias.shift(3)` | 0.395114 | 1,481 |
| `cmo:CMO_14` | 0.371478 | 1,481 |
| `rsi:RSI_14` | 0.371478 | 1,481 |
| `bias:BIAS_SMA_26` (the shipped default) | 0.337055 | 1,475 |
| `g191_167:G191_167_12` | 0.289808 | 1,481 |
| `g191_129:G191_129_12` | -0.280635 | 1,481 |
| `slope:SLOPE_1` | 0.270294 | 1,481 |
| `smi:SMI_5_20_5` (the same indicator's first line) | 0.232162 | 1,481 |
| `ppo:PPO_12_26_9` | -0.206086 | 1,475 |
| `g191_002:G191_002_1` | -0.017952 | 1,481 |

Three of these deserve a sentence rather than a row:

* **`SMIo_5_20_5` at 0.9116 is ABOVE the 0.90 strike line on this frame**, and
  it is the exact column issue #82 measured the PROTOTYPE against on real data,
  where it came in at 0.8842 pooled / 0.8861 per-frame max median
  (DISCLOSE_GAP). So the synthetic frame reads ~0.027 higher than the real
  tape did for the same pair. Two facts bound what that means and neither
  dismisses it: (i) this is a 1,500-bar i.i.d.-lognormal walk, not the 89 frozen
  ALTPORT-1 frames, and Gate E's bands are defined only on the latter
  (`g191_003` is the precedent: `kdj:J_9_3` measured 0.906 synthetic and 0.831
  on the real frames); (ii) the port is bit-identical to the prototype on every
  bar they share (Gate A), so the prototype's own 0.8842 is the better prior for
  the port's real-data number than this 0.9116 is. **Settled: the launcher's run
  came back 0.8842 pooled / 0.8861 per-frame max median against this same
  comparator — prior (ii) was right and the synthetic 0.9116 was 0.0274 high, so
  the column ships.** The column is selected BY NAME in the measure script
  (`df.ta.smi()["SMIo_5_20_5"]`) rather than positionally, because `df.ta.smi()`
  returns three columns and `iloc[:, 0]` would quietly measure `SMI_5_20_5` —
  which sits at 0.2322 and would have flattered this table.
* **`BIAS_SMA_6` at 0.8088 is the structural one**, and it is the column this
  port is built out of. On this frame the smoothed 3-bar difference still tracks
  the level it differences — below the 0.90 strike line, but inside the
  DISCLOSE_GAP band were this Gate E, which it is not. Whether `bias` at
  `length=6` is even among the engine's 687 comparators is not known in this
  session.
* **The unsmoothed change, at 0.3951, is the LOWER correlation** — the final
  `SMA` does not merely de-noise the difference, it changes what the column
  ranks like. `rsi:RSI_14` and `cmo:CMO_14` tie at 0.371478 because `CMO = 2·RSI
  − 100` is monotone in `RSI`, so Spearman cannot tell them apart; that is a
  property of the comparators, not of this column.

## Wiring

`Category` **315 → 316** (`momentum` **80 → 81**); dictionary probe **317 → 318**
indicators, `df.ta.<name>()` accessors **323 → 324** (both counts re-emitted by
`python docs/gen_indicator_dictionary.py`). Touch points:
`pandas_ta/momentum/g191_022.py` (module), `pandas_ta/momentum/__init__.py`
(export), `pandas_ta/__init__.py` → `Category["momentum"]` (discovery),
`pandas_ta/core.py` → `AnalysisIndicators.g191_022` (accessor),
`tests/test_g191_022.py` (tests). `README.md`'s headline and `momentum (81)`
row, and `docs/IndicatorDictionary.md` (regenerated), both updated and checked
by `tests/test_readme_counts.py`. `docs/MLCompanionContract.md`'s running tag
count updated **660 → 661 / 303 → 304 `SF`** (`G191_022_6_3_12_1` probes cleanly
at the dictionary's synthetic frame with a 19-bar warm-up and takes many
distinct values, so the generator tags it `SF`), checked by
`tests/test_ml_companions.py::test_the_contract_quotes_the_dictionarys_actual_ml_form_counts`.
`tests/test_altport2_ports.py`'s `CATEGORY_TOTAL` updated to match (315 → 316);
no `CATEGORY_BUCKETS` entry needed (that dict tracks only
`trend`/`volatility`/`volume`, not `momentum`).

`docs/gate_e_ledger.csv` carries the port's row, recorded in this receipt
session from the launcher's run directory (`is82-g191_022-19d9fa07`), not
hand-written: `g191_022,pandas_ta.momentum.g191_022,G191_022_6_3_12_1,
DISCLOSE_GAP,…`.

## NaN handling, measured because it is counter-intuitive

A single NaN in `close` empties `bias_length = 6` bars of the mean and
`bias_length + delay_length = 9` bars of `change`, but pandas' `ewm` SKIPS a NaN
input (carrying its previous value forward) instead of emptying its output. So
on the 1,500-bar walk with `close[700] = NaN`: **no output bar changes
NaN-ness**, and **448** of the 1,481 firing bars move — from bar **700** to bar
**1,147**, past which the displacement falls below float64 resolution. Where it falls
below resolution is platform float detail: CI's runner measured **647** moved bars, so
the test pins only the start (bar 700) and a lower bound (>= 400 bars). Pinned by
`test_a_single_nan_close_empties_no_output_bar_but_displaces_many`. Nothing is
guarded: a NaN close is not a bar this fork models, and the prototype does not
guard it either.

## Review record

Four `/brutally-honest-review` rounds (the owner's cap; BHR's own cap is 3),
all four **REVISE**: **17 findings** — 1 CRITICAL, 6 MAJOR, 4 MINOR, 6 NIT
(round 1: 3 MAJOR + 2 MINOR + 1 NIT; round 2: 1 MAJOR + 2 MINOR + 1 NIT;
round 3: 1 CRITICAL + 1 MAJOR + 2 NIT; round 4: 1 MAJOR + 2 NIT), counted
from the four verdicts in the log rather than estimated.
Full verdicts and the fix-by-fix log:
`docs/reviews/auto-2026-11-11-g191-022/01-g191-022.md`.

**Not one finding was a mathematics error.** Every round re-ran the measure
script and the suites and reproduced every number; what failed, four times
running, was prose attached to a correct computation — a subtraction never
done ("larger than the column's entire range"; "0.0002 under the strike
line" when 0.90 − 0.8900 = 0.0100), citations never opened (`wilder_rma`'s
non-existent `min_periods`, twice), unmeasurable universals ("GTJA's `m` is
always…", "every other `g191_*` port"), and one over-broad guard claim
("any `m > smooth_length` raises", false at `12 ≤ m < 13`).

Two findings changed the delivery rather than its wording: the `smi`
comparator was being selected positionally, so the issue's own Gate E top
comparator was never measured (fixing it produced the 0.9116 above), and the
`smooth_weight` band at `alpha = 1.0` silently disables the smoother (now two
tests and the table below).

⚠ **Round 4's fixes landed with the cap spent and were NOT re-reviewed:** the
three-band `smooth_weight` note and its two tests, the reflowed Gate E
paragraph, the `pandas_ta/volatility/g191_109.py:101` citation, this section,
the table below, and the test/suite counts that moved with them (26 → 29
tests, 5,291 → 5,294 passed). Everything in that list was measured in this
session; none of it has been through the gate.

## The `smooth_weight` guard's three bands, measured

`m` is cast with `int()` and nothing validates `alpha = m/n`, so the one
tunable with no measured value besides its default has three behaviours, all
three now pinned (the guard itself is left sibling-consistent with `g191_152`
rather than widened — the narrower change, logged as an assumption):

| `smooth_weight` | `alpha = int(m)/12` | what happens |
|---|---|---|
| `0.5` | 0.0 | pandas' `ewm` raises `ValueError` |
| `12`, `12.5` | **1.0** | **accepted** — no smoothing at all: the column equals the raw 3-bar change bit-for-bit on all 381 firing bars of a 400-bar frame, named `G191_022_6_3_12_12` |
| `13`, `20` | 13/12, 5/3 | pandas' `ewm` raises `ValueError` |

The middle row is why the public docstring does not promise an exception for
"any `m > smooth_length`": an earlier draft did, and
`test_a_weight_of_alpha_one_silently_disables_the_smoother` is what
disproved it.

## Suite run (this repo)

`python -m pytest -q -p no:warnings --tb=no -rf`, full suite, default collection
order, re-run in the receipt session after the Gate E row landed: **3 failed,
5301 passed, 83 skipped** (105.63s). The port session's own run of the same
command was **3 failed, 5294 passed, 83 skipped** (106.56s); the **+7** are the
seven per-row/per-indicator parametrizations in `tests/test_gate_e_ledger.py`
(lines 168, 173, 180, 191, 198, 210, 218) that the new ledger row instantiates.

* `tests/test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one`
  — now "no Gate E ledger row for `['mtd_ret']`" (measured in the receipt
  session: `g191_022` is off that list since its row was recorded). `mtd_ret`
  pre-dates this issue and is not touched here. CI into `dev` sets
  `GATE_E_PENDING_OK=1` and skips it; a local run fails it.
* `tests/test_altrepo_talib_csv.py::test_regenerating_reproduces_the_committed_rows`
  — needs the sibling `../AlternativeRepos` checkout, absent in this worktree
  (CLAUDE.md "Known breaks"; CI deselects it).
* `tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
  — the untracked `docs/pine/` corpus (CLAUDE.md "Known breaks").

No other test fails. The pre-port baseline was not re-run in this session, so
the passed count is reported as measured rather than decomposed into "this
port's 29 tests plus X".
