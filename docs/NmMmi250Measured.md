# Market Meanness Index of daily returns (250) — measured (`nm_mmi_250`)

Issue #184 (NM-MMI-250), from the 2026-10-25 follow-up of round 6
(`docs/issues/screen/candidates_r7.csv`). Named in a Reddit thread only (tier 4):
the thread named this indicator but did not define it, so the definition comes
from the article the issue cites, not the thread — existence, not evidence, is
what this port ships; nothing here tests the article's own claim on BIST.

**Source:** Johann Christian Lotter, "The Market Meanness Index",
financial-hacker.com — named in rd:algotrading:hr30er (Reddit, tier 4). The
issue restates the article's own formula in Zorro's own array order:
`MMI = 100*(nl + nh)/(n - 1)`, counting `x_i` (a daily return) against the
window's median and its one-step-older neighbour. The issue's own "Prototype"
line discloses the scale-free form explicitly chosen for this fork: "on daily
returns (the article: about 75 for random changes)"; `250` is the article's
own test period, kept here as the `length` parameter's default.

**Status:** Gates A-D measured below. Gate E: pending, run by issue-solver
after this session. Whole-suite run is owed to the launcher, per the
issue-solver's own rules (it must not run the whole suite).

| module | category | column | range |
|---|---|---|---|
| `pandas_ta/statistics/nm_mmi_250.py` | statistics | `NM_MMI_250` | `[0, 100]` (percentage, bounded by construction); measured 60.24 .. 81.53 across three 1,500-bar synthetic frames below, or NaN |

Tests: `tests/test_nm_mmi_250.py` (53 tests). Numbers: `python
docs/measure_nm_mmi_250.py`, run from the repo root. Environment: Python
3.11.2, pandas 2.3.3, numpy 1.26.4. Measured 2026-11-27.

## Decisions

1. **The formula is read from the issue's own restatement, not the screen
   prototype** (`docs/issues/screen/ind_screen_r7.py`'s `nm_mmi_250`, which is
   mathematically the same reading but is not what Gate A cites, per this
   fork's own protocol: "Gate A starts from the source formula, not the
   prototype"). The issue's formula is given in Zorro's own array order
   (`Data[0]` the most recent bar, higher index further back in time); the
   module's docstring translates it bar-by-bar into this fork's own
   forward-chronological convention before any code is written.
2. **`length` is a parameter, not hard-coded**, defaulting to `250` — the
   issue's own test period, "the article's test period" — matching this
   fork's standing convention for every other rolling-window port.
3. **The median is taken over the WHOLE window**, not just the subset being
   compared — the issue's own formula names one `median` per window, and the
   screen prototype's `_mmi` helper computes it the same way (`np.median(W, 1,
   keepdims=True)` over the full `length`-return window), not a median of only
   the first or last `length - 1` returns.
4. **`MIN_LENGTH = 3`, not 2.** A 2-return window's median is the pair's own
   mean, so `older > median` and `older > newer` always agree in sign (and
   likewise for `<`): every non-tied pair is a FORCED 100, an exact tie a
   forced 0 — never anything else (measured: 3,000 random 2-return draws all
   land on `{100.0}`). At `length = 3`, hand enumeration of the 6 orderings of
   3 distinct values gives `{50, 100}` (2 of 6 orderings have BOTH pairs
   reverse, MMI=100; the other 4 have exactly ONE pair reverse, MMI=50) —
   still only two values, but not a SINGLE forced constant, so 3 is the
   floor (confirmed by 30,000 random
   3-return draws: `{50.0, 100.0}`, not a singleton).
5. **Column name carries the one parameter**, `NM_MMI_{length}` — e.g.
   `NM_MMI_250` at the default, `NM_MMI_100` at `length=100`.

## Gate A — correctness

The issue's own formula (not the prototype — issue #184's explicit
instruction), translated out of Zorro order and read bar-by-bar in the
module's docstring:

```
r[t]  = close[t] / close[t-1] - 1                      -- daily simple return
w     = r[T-length+1 .. T], oldest first                -- the window
m     = median(w)
for k = 0 .. length-2 (older = w[k], newer = w[k+1]):
    reversal[k] = (older > m and older > newer) or (older < m and older < newer)
NM_MMI = 100 * count(reversal) / (length - 1)
```

A hand-derived fixture, chosen on paper before the module ever ran
(`tests/test_nm_mmi_250.py::test_hand_derived_window`): returns `[1, 2, 3, 4]`
at `length=4` have median 2.5. Pair `(1, 2)`: `1 < 2.5` and `1 < 2` — a
reversal (below median, rising back toward it). Pair `(2, 3)`: `2 < 2.5` and
`2 < 3` — a reversal. Pair `(3, 4)`: `3 > 2.5` but `3 > 4` is false — not a
reversal (above median, still rising away from it). 2 of 3 pairs reverse, so
`NM_MMI = 200/3 = 66.66666666666667`. Module's measured output: exactly
`66.66666666666667` (`python docs/measure_nm_mmi_250.py`).

Cross-checked against an independent per-window Python loop built straight
from the formula above (plain Python scalars and `sorted()`, no numpy
windowing, no shared helper with the module except the close series itself) on
a 400-bar synthetic random walk (`length=50`, 350 defined bars): NaN masks
identical, **max |diff| 0.0** (`test_matches_an_independent_scalar_loop`,
`python docs/measure_nm_mmi_250.py`) — exact agreement, not merely close,
because both implementations compute the same median-and-comparison logic
with no floating-point reduction-order difference (no sums, no means — only a
sort and a handful of comparisons).

## Gate B — causality

- **The real module never reads the future, swept, not spot-checked.** Three
  1,500-bar synthetic frames (`walk`, `tick-rounded`, `ar1`) each spliced at
  `J` with 4 independent random futures: bars `< J` come only from the
  original path in both the base and the spliced series, so if the module
  reads no later bar than `T` its output on `[0, J)` cannot move. Measured
  over **31 swept J values** per frame (`J` = 260, 300, ..., 1460, past the
  250-bar default warm-up; `python docs/measure_nm_mmi_250.py`): **real module
  leaked at 0 of 31 on every one of the 3 frames.**
- **Three independent mutants, each live and each caught at a strictly
  positive, frame-specific swept-offset count (24/31 on `ar1`, 19/31 on
  `tick-rounded`, 20/31 on `walk` — never zero, but not every offset
  either):**
  - `write-back-dated`: the final write (`out[length - 1:] = ...`) shifted one
    bar earlier (`out[length - 2:-1] = ...`), so bar `T-1`'s output actually
    describes the window ending at `T`.
  - `forward-value`: the computed `mmi` array rolled forward by one row
    (`np.roll(mmi, -1)`) before being written, so bar `T`'s output is the
    value computed for the window ending at `T+1`.
  - `forward-return`: the return calculation's write index shifted
    (`r[1:] = ...` → `r[:-1] = ...`), so the return meant for bar `t` is
    written to bar `t-1`, reading tomorrow's close into today's return.

  Measured leak counts (`python docs/measure_nm_mmi_250.py`, out of the same
  31 swept offsets as the real module above):

  | mutant | ar1 | tick-rounded | walk |
  |---|---|---|---|
  | `write-back-dated` | 24 | 19 | 20 |
  | `forward-value` | 24 | 19 | 20 |
  | `forward-return` | 24 | 19 | 20 |

  All three mutants land on the IDENTICAL count per frame — not a
  coincidence of this architecture: each one shifts exactly one bar's worth
  of window content relative to its output position, so the three
  constructions are observationally equivalent perturbations even though
  they edit different lines of the module. `tests/test_nm_mmi_250.py`'s
  `CAUGHT` table pins these exact counts rather than a guessed lower bound,
  per the issue-solver's own CPU-variant rule (float arithmetic does not
  enter this comparison-and-count logic, so the counts are stable across
  CPUs, unlike a bit-level float count would be).

## Gate C — reachability

Synthetic, from the port session, three 1,500-bar frames at the default
`length=250` (`python docs/measure_nm_mmi_250.py`):

| frame | fires | warm-up | min | max | distinct values |
|---|---|---|---|---|---|
| `ar1` (phi=0.6) | 1,250 of 1,500 | 250 | 60.2410 | 69.8795 | 25 |
| `tick-rounded` | 1,250 of 1,500 | 250 | 70.6827 | 81.5261 | 28 |
| `walk` | 1,250 of 1,500 | 250 | 69.4779 | 80.7229 | 29 |

Every frame fires on exactly `n - 250` bars (the fixed warm-up) and reads a
genuine spread of distinct values, not a narrow or degenerate subset. The
persistent `ar1` frame (phi=0.6, momentum, not noise) reads noticeably LOWER
(60-70) than the two more random-walk-shaped frames (70-82) — consistent with
the metric's own claim (fewer reversals on a trending series) without this
port independently testing that claim on real data. The `walk`/`tick-rounded`
range also sits close to the article's own calibration point ("about 75 for
random changes") — a loose sanity check, not independent evidence.

A window holding a close that is NaN, infinite, zero, negative or subnormal
reads NaN by construction (`test_a_bad_close_empties_its_own_windows_and_nothing_earlier`,
measured: exactly the `length + 1` windows containing it, nothing earlier
moves), and a window holding a close PAIR whose ratio overflows to an
infinite return reads NaN the same way
(`test_an_overflowing_return_pair_is_emptied`). Real-data reachability: not
measured here — Gate E (which runs on real BIST data) is owed; see below.

## Gate D — scale-free

- **Bit-identical under a power-of-two price rescale (x8/x64); measured
  bit-identical under x10/x3.7 too on every tested frame.** The return
  `r[t] = close[t]/close[t-1] - 1` is a price RATIO: `(k*a)/(k*b)` is the
  identical double to `a/b` whenever `k` is an exactly representable power of
  two (the multiply introduces no rounding, so numerator and denominator are
  both scaled by the same exact factor and IEEE-754 division returns a
  bit-for-bit unchanged quotient). Every step downstream of the return array
  (`median`, `>`, `<`, the count, the final ratio by the constant
  `length - 1`) is a pure function of that bit-identical array, so the whole
  column is BIT-IDENTICAL under x8/x64 by construction.
- A non-power-of-two rescale (x10, x3.7) is not exact at the return's own
  multiply step, so each return can in principle pick up independent
  last-bit rounding noise that flips a `>`/`<` comparison on a window where
  two returns sit exactly at the rounding floor apart — which would move
  that one window's count by a whole `100 / (length - 1)` step. **Measured on
  three 1,500-bar frames, 1,250 co-finite cells each**
  (`python docs/measure_nm_mmi_250.py`): **0 exact mismatches at every one of
  x8, x64, x10 and x3.7, on every frame** — the theoretical risk above did not
  materialise on any tested frame; `tests/test_nm_mmi_250.py`'s
  `test_other_price_scales_move_at_most_a_measured_number_of_cells` bounds
  this at the measured `0` plus a 2-cell margin (not a tighter pin), per the
  issue-solver's own CPU-variant rule — a future run on a different CPU's
  dispatched kernels could, in principle, flip one comparison that happens
  to sit exactly at the rounding floor, and the test is written to tolerate
  that without being a false failure.
- `0 < fires < n`, not constant: 1,250 of 1,500 bars fire on every frame
  above, 25-29 distinct values per frame, min/max both strictly inside
  `(0, 100)` — not even approaching either bound, so a constant column
  cannot pass.

## Gate E — attribution

**Pending, run by issue-solver after this session.**

## Gate F — suites

This session's own command (per the issue-solver rules, never the whole
suite):

```
python -m pytest -q tests/test_nm_mmi_250.py tests/test_readme_counts.py \
    tests/test_altport2_ports.py tests/test_wiring_accessors.py \
    tests/test_ml_companions.py tests/test_gate_e_ledger.py \
    tests/test_pine_coverage_csv.py tests/test_prose_counts_match_the_csvs.py
```

**1,783 passed, 7 skipped, 1 failed.** The one failure is
`test_gate_e_ledger.py::test_every_indicator_that_needs_a_row_has_one` —
expected, per the issue-solver's own rules, until the launcher's Gate E run
and a later receipt session record this port's ledger row.
`tests/test_nm_mmi_250.py` alone: 53 passed.

CPU-feature variant (`AVX512F AVX512_SKX AVX2 FMA3` disabled, standing in for
a GitHub runner without AVX-512 — the four features issue-solver's rules
name, not this machine's full dispatchable set, which also has
`AVX512CD`/`AVX512_CLX`/`AVX512_CNL`/`AVX512_ICL` enabled):
`python docs/measure_nm_mmi_250_cpu.py` — **53 passed** (just
`tests/test_nm_mmi_250.py`; the ledger/readme/wiring modules above are not
CPU-sensitive and are not re-run under this flag).

Whole suites: run by issue-solver in clean worktrees (see the PR body).

## Counters touched

- `CATEGORY_TOTAL` 418 → 419 (`tests/test_altport2_ports.py`).
- README: 418 → 419 registered, 426 → 427 callable, statistics (84) → (85).
- `docs/MLCompanionContract.md`: 763 → 764 tagged and 388 → 389 `SF` (newest
  first in the chain). `NM_MMI_250` tags `SF` because the input is a price
  RATIO and every downstream step (median, comparisons, count) is a pure
  function of that ratio — measured bit-identical under x8/x64 and, on the
  tested frames, under x10/x3.7 too.
- `docs/IndicatorDictionary.md`, regenerated with this environment's package
  (`python docs/gen_indicator_dictionary.py`): adds `nm_mmi_250` under
  `## statistics (85)`, tagged `SF`, warm-up 250. Its diff is the
  `nm_mmi_250` row, the three header counts, the statistics section count,
  and the no-transform-needed shortlist, and nothing else (checked: `git diff
  docs/IndicatorDictionary.md`).
- `Category`: `nm_mmi_250` is placed alphabetically between `median_ad_hl2`
  and `osap_retskew_21` in `statistics`.
- Module sha1 (LF-normalised, for the later `docs/gate_e_ledger.csv` row,
  re-measured after the pre-push review's docstring-wording fixes -- the
  Gate A-D numbers above are unchanged, the module text is not):
  `1a9bacb22f9070cbdfe5b34c00c93fc84dfffd5c` (measured, `python
  docs/measure_nm_mmi_250.py`).

## Next step

Launcher runs Gate E (`gate_e_overlap.py run --module
pandas_ta.statistics.nm_mmi_250`). A later receipt session records the
ledger row in `docs/gate_e_ledger.csv` and fills in this file's Gate E
section with the measured verdict — SHIP, DISCLOSE/DISCLOSE_GAP, or a
measured revert if STRUCK.
