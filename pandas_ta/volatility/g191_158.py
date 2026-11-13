# -*- coding: utf-8 -*-
"""Range over close (G191_158) -- Guotai Junan's (2017, "GTJA191", internal
quant report) alpha `#158`, per issue #81, which attributes its copy of the
report to HKUDS/Vibe-Trading (MIT) -- a copy NOT read in this session, see
the disclosure below. Source cited by the issue:

    #158: ((H-SMA(C,15,2))-(L-SMA(C,15,2)))/C = (H-L)/C

**What this session could NOT do, disclosed up front:** `docs/pine/` and
web access are both unavailable in this worktree, so the issue's own named
copy -- HKUDS/Vibe-Trading (MIT) -- was never read. Everything below is
derived from the issue's own stated text (itself a quote of the GTJA191
report), per the issue's own instruction ("Gate A starts from the source
formula, not the prototype"), then cross-checked against the issue's own
prototype (`docs/issues/screen/ind_screen.py:517-518`):

    @cand("g191_158", "range over close", G,
          "#158: ((H-SMA(C,15,2))-(L-SMA(C,15,2)))/C = (H-L)/C")
    def _(o, h, l, c, v): return (h - l) / c

The issue's own string carries its own reduction (`= (H-L)/C`), and the
prototype ships that reduced right-hand side. This port ships it too. That
is the ONE decision this port makes, and it is not free -- see below.
This candidate's `candidates.csv` row carries NO `conv` field (an empty
cell, `docs/issues/screen/candidates.csv:57`): the division by `C` is
already inside the source formula, so no extra scale-free conversion is
applied.

OPERATORS, each read directly off the prototype's own (unambiguous) module
source -- the source this port read, and the one `g191_109` cites too
(`pandas_ta/volatility/g191_109.py:13-21`); no count of the ports that cite
it is claimed here:

* `H`, `L`, `C` = high, low, close of the CURRENT bar. `OPEN` and `VOLUME`
  are not read -- structurally, not by measurement.
* `SMA(A, n, m)` is GTJA's own recursive smoother, NOT this fork's
  `pandas_ta.overlap.sma` -- a name collision called out in the
  prototype's own docstring (`ind_screen.py:57-59`): `Y[t] = (m*A[t] +
  (n-m)*Y[t-1]) / n`, an exponential moving average with `alpha = m/n`.
  Here it is `SMA(C, 15, 2)`, i.e. `alpha = 2/15`. It appears TWICE in the
  source numerator, both times as the SAME series, and it CANCELS -- so
  the shipped code never computes it. Other GTJA191 ports in this fork do
  implement the operator for real -- `g191_109`
  (`pandas_ta/volatility/g191_109.py:101`) is the nearest example, in this
  same category, through a `_gtja_sma` helper; `g191_146`
  (`pandas_ta/momentum/g191_146.py:106-111`) spells it inline instead. **No
  fork-wide count is given here on purpose:** two earlier drafts of this
  docstring stated one (four, then seven) and both were wrong, because the
  obvious `git grep "min_periods=n).mean()"` sees only the helper spelling
  whose locals are named `n`/`m` and misses every inline call. The census
  is not load-bearing for this port; the two cited lines are read.

THE REDUCTION, derived rather than taken on faith. Write `S = SMA(C,15,2)`,
one series, the same at both occurrences:

    ((H - S) - (L - S)) / C = (H - S - L + S) / C = (H - L) / C

for every bar at which `S` is defined, with no assumption on `S` beyond its
being a single real number per bar -- it does not matter what `SMA` is, only
that both subtracted copies are the same series. The source itself states
this (`= (H-L)/C`), so the reduction is the SOURCE's, not this port's.

CALCULATION, in the order computed below (no parameters -- the source's own
`15` and `2` live only inside the cancelled term):
    G191_158 = (H - L) / C

WHAT SHIPPING THE REDUCED SPELLING COSTS, measured, and the honest answer
is: almost nothing, which is why the decision rests on the source's own
statement of the reduction and on agreeing with the prototype Gate E
measured, NOT on a cost table.

1. FLOAT NOISE, measured on two frames because one was not enough. On the
   ordinary 1,500-bar walk (sigma 0.015) the two spellings come out
   BIT-EQUAL on all **1,486** bars both define -- `H`, `L` and `S` are
   within a factor of 2 of each other there (max ratio **1.096357**,
   measured), so by Sterbenz neither `H-S` nor `L-S` loses a bit. They are
   NOT identical in general: on a stress frame (sigma 0.20, max ratio
   **6.801292**, past that factor of 2) **50 of 1,486** bars differ, max
   \|diff\| 5.83e-16, max \|relative diff\| 5.54e-15. Where they differ the
   reduced form is the more accurate of the two, and that is DERIVED rather
   than measured: IEEE754 subtraction is correctly rounded, so `H-L` is the
   single correctly-rounded difference, while `(H-S)-(L-S)` rounds three
   times before the division.
2. WARM-UP, and it is **this fork's convention rather than the source's**.
   Written with the `min_periods=n` this fork's sibling GTJA-`SMA`
   implementations use (`g191_109.py:101`, `g191_146.py:106-111`),
   `SMA(C,15,2)` is NaN for the first 14 bars and
   `(H-NaN)-(L-NaN)` is NaN, so that spelling of the literal form is
   non-NaN on **1,486 of 1,500** bars against the reduced form's **1,500**.
   But the prototype's own `sma` (`ind_screen.py:59`) omits `min_periods`,
   and with the source's own spelling the literal form fires from bar 0 and
   is **bit-equal to the shipped column on all 1,500 bars** (measured). So
   the 14 bars are not a property of the source formula, and this port does
   not get to claim them as the reason for the reduction.

Both numbers come from `docs/measure_g191_158.py`, and
`tests/test_g191_158.py::test_the_literal_spelling_agrees_within_float_noise`
plus `::test_the_literal_spelling_is_not_bit_equal_in_general` pin the
comparison in all three spellings.

So what actually decides it: the source's own string states the reduction
(`= (H-L)/C`), the prototype computes the reduced form, and the port is
bit-identical to that prototype -- which is the expression whose Gate E
numbers issue #81 quotes. The literal spelling would be defensible
arithmetic and a worse port: it would differ from the measured prototype by
float dust at best, and by 14 NaN bars if its `SMA` were written the way
`g191_109.py:101` writes one.

CAUSALITY. `(H[t] - L[t]) / C[t]` reads bar `t` and nothing else: three
pointwise reads, one subtraction, one division, no `shift`, no `rolling`,
no recursion. The column has no memory at all, so there is no weaker
dependency on the past left to argue about. `tests/test_g191_158.py`
proves it both by future-perturbation (real module: 0 leaks, with
high/low/close rewritten jointly from an offset onward) and by two mutants
(`importlib` source read, `exec`'d in memory, each shown live different
from the real module): shifting the final write index one bar into the
future, and reading the NEXT bar's range (`high.shift(-1) -
low.shift(-1)`) -- the same `bos` look-ahead bug class CLAUDE.md
documents.

WARM-UP: none. `min_length = 1`, enforced by `verify_series`, so only an
EMPTY input returns `None`. The column is defined wherever `high`, `low`
and `close` are, which makes Gate D's `0 < fires < n` clause vacuous in
its upper half on clean data -- fires `== n`. That clause exists to kill a
constant or all-NaN column, so this port pins non-degeneracy the other
way: `nunique > 1` on every measured frame, and a measured non-zero count
(see Gate C in `docs/G191158Measured.md`). Disclosed rather than dressed
up as a pass.

EDGE CASES, both reachable and both decided here:

* `H == L` (a zero-range bar: a limit move, a halt, an untraded day) gives
  exactly `0.0`, not NaN -- `0.0` is the true value of the range, and the
  column's floor. The continuous-float walk never reaches it (**0 of
  1,500** bars with `H == L`), which is why the tests and Gate C also use
  a TICK-ROUNDED synthetic frame, where it happens: **107 of 1,500** bars,
  and the column is exactly `0.0` on those 107 and only those (measured,
  `docs/measure_g191_158.py`). On this fork's real data exact OHLC ties
  are common -- CLAUDE.md's FVGDEAD note measures 21.17% of BIST daily
  bars closing exactly at an extreme, which is a DIFFERENT statistic
  (`C == H` or `C == L`, not `H == L`); the `H == L` rate on real frames is
  not measured here and is owed to Gate E's reachability counts.
* `C == 0.0` would give `+inf` (or NaN at `H == L`). Not guarded, for the
  same reason `g191_003` does not guard its `/close`: a zero close is not
  an OHLC bar this fork models anywhere, and the prototype -- which uses
  the screen's `sdiv` (inf -> NaN) on OTHER candidates and a bare `/` on
  this one (`ind_screen.py:518`) -- does not guard it either. A bare
  division is therefore the faithful port.
  `tests/test_g191_158.py::test_a_zero_close_is_not_guarded` pins the
  behaviour so it is a decision on record rather than a surprise.

SCALE-FREE. Let `k > 0` rescale price (`H, L, C -> k*H, k*L, k*C`). The
numerator is linear: `k*H - k*L = k*(H - L)`. The denominator is `k*C`. So
the column is `(k*(H-L)) / (k*C) = (H-L)/C` for ANY `k > 0` -- the `k`
cancels EXACTLY. Volume is not read at all, so volume rescaling cannot
move it either. Measured on a synthetic walk: PRICE x8/x64 land
bit-identical (power-of-two multiplication is exact in IEEE754, so the
cancellation is also exact in floating point), while x10/x3.7 come out
within float64 rounding tolerance of the unscaled column (`k*H` and `k*L`
each round at a non-power-of-two multiplier). Measured in the test file
and `docs/measure_g191_158.py`, not merely asserted.

WHAT THIS IS NEXT TO WHAT THE FORK ALREADY SHIPS, and it is the
uncomfortable part of this port. `bw_mfi`'s shipped column is
`MFI_BW_SF_<length> = ((H-L)/C) / (V/SMA(V,length))`
(`pandas_ta/volume/bw_mfi.py:47`) -- this column's expression DIVIDED by
relative volume. On a frame whose volume is CONSTANT, relative volume is
exactly `1.0` once its own 20-bar average is defined, and the two columns
are then bit-identical from bar 19 onward: measured, not reasoned about --
`max|diff| = 0.0`, **1,481 of 1,481** overlapping bars bit-equal on the
1,500-bar walk with flat volume, `MFI_BW_SF_20`'s first non-NaN bar **19**
(`docs/measure_g191_158.py`) -- and pinned by
`tests/test_g191_158.py::test_bw_mfi_is_this_column_divided_by_relative_volume`.
On real data volume is not constant, and the owner's own stage-2 fork
overlap (12 BIST frames, every `Category` indicator at defaults, scale-free
columns kept -- `docs/issues/screen/fork_overlap.py`) puts this
candidate's HIGHEST fork overlap at |rho| 0.8252 against
`har_park:HARPARK_1_5_22_500`, per-frame max median 0.8217, verdict `new`
(`fork_overlap.csv:57`) -- so `MFI_BW_SF_20` sits at or below 0.8252 there.
That it is in that comparator set at all is read, not assumed: a LATER
round of the same script, same hardcoded frames, records
`nm_effort_result_20,0.7867,bw_mfi:MFI_BW_SF_20,...`
(`docs/issues/screen/fork_overlap_r7.csv:7`), so `fork_columns()` computes
the column and the keep filter keeps it. (The run's own
`fork_errors.txt` is empty, which says nothing errored in it rather than
anything about `bw_mfi` in particular.)
That is the owner's measurement, on real frames, and it is what says this
is not a restatement; the constant-volume identity above is what says the
two are one relative-volume factor apart. On a 900-bar synthetic frame
with LOGNORMAL volume the pair measures rho **0.6922**
(`docs/measure_g191_158.py`) -- a synthetic stand-in, not Gate E, and the
whole distance between 1.0 and 0.6922 is that one factor. Gate E (the
launcher's run)
decides it against the engine's 687 comparators, where the issue's
prototype measured 0.8834 against `pdist_pct` -- `pdist` being
`2(H-L) - |C-O| + |O-C1|` (`pandas_ta/volatility/pdist.py:43`), whose
leading term is twice this column's numerator.
"""
from pandas_ta.utils import get_offset, verify_series


def g191_158(high, low, close, offset=None, **kwargs):
    """Indicator: Range over Close (G191_158)"""
    # Validate Arguments
    min_length = 1
    high = verify_series(high, min_length)
    low = verify_series(low, min_length)
    close = verify_series(close, min_length)
    offset = get_offset(offset)

    if high is None or low is None or close is None:
        return

    if not (high.index.equals(low.index) and high.index.equals(close.index)):
        raise ValueError(
            "g191_158: `high`, `low` and `close` are indexed differently. A "
            "range read off misaligned series is a silent nonsense number."
        )

    # Calculate Result
    result = (high - low) / close

    # Offset
    if offset != 0:
        result = result.shift(offset)

    # Handle fills
    if "fillna" in kwargs:
        result.fillna(kwargs["fillna"], inplace=True)
    if "fill_method" in kwargs:
        result.fillna(method=kwargs["fill_method"], inplace=True)

    # Name & Category
    result.name = "G191_158"
    result.category = "volatility"

    return result


g191_158.__doc__ = \
"""Range over Close (G191_158)

Guotai Junan's (2017, "GTJA191") alpha `#158`, per issue #81. Today's
high-low range as a fraction of today's close: one bar's realised range,
normalised so a tree can compare it across instruments and across price
levels. The source spells it as the difference of two distances to the same
`SMA(C,15,2)`, which cancels -- the source states the cancellation itself
(`= (H-L)/C`), and this port ships the reduced form, as the issue's own
prototype does. No window, no recursion, no warm-up: the column is a
function of bar `t` alone. Full Gate A derivation (including what the
literal spelling would cost in warm-up and in float64 rounding), causality
and scale-free arguments are in the module source above; see
docs/G191158Measured.md for the measured numbers, and note the measured
relationship to `bw_mfi`'s `MFI_BW_SF_<length>`, which is this column
divided by relative volume.

Calculation:
    G191_158 = (high - low) / close

Args:
    high (pd.Series): Series of 'high's
    low (pd.Series): Series of 'low's
    close (pd.Series): Series of 'close's
    offset (int): How many periods to offset the result. Default: 0

Kwargs:
    fillna (value, optional): pd.DataFrame.fillna(value)
    fill_method (value, optional): Type of fill method

Returns:
    pd.Series: G191_158, a scale-free (dimensionless) column, NON-NEGATIVE
        on OHLC-consistent data with a positive close (`high >= low`), and
        exactly `0.0` on a zero-range bar, which is its floor. No warm-up:
        bar 0 fires. NaN where an input is NaN -- one NaN empties that bar
        and no other, measured for each of the three inputs
        (`tests/test_g191_158.py::test_a_nan_in_any_input_nans_exactly_that_bar`)
        -- plus NaN in the first `offset` bars for `offset > 0` and in the
        last `|offset|` bars for `offset < 0`, where the column reads the
        future ON PURPOSE: a negative `offset` is the only non-causal door
        this module has, and it is the caller's choice
        (`tests/test_g191_158.py::test_offset_shifts_the_column` pins both
        directions). `+inf` at a zero close, which is not guarded (see the
        module source).
"""
