# -*- coding: utf-8 -*-
"""PINEBI-0: classify every Pine `ta.*` name the corpus uses against this fork.

Writes `docs/pine_builtin_coverage.csv`. The classifier IS the artifact -- the
counts are whatever it prints on the day it runs, so a changed count is not a
finding, but a changed VERDICT is.

"Built-in" is three populations and only two are portable:

  tier 1  core `ta.*` compiler intrinsics (`ta.sma`, `ta.pivothigh`). No source
          is published; the spec is the Pine v6 reference.
  tier 2  the official `TradingView/ta` library, MPL-2.0, (c) TradingView. Its
          source IS on disk: `docs/pine/RA2vGpkA-ta.pine`.
  tier 3  the Indicators-dialog built-ins ("Bollinger Bands"). Closed source,
          nothing to port against -- out of scope, and not in this CSV.

⚠ Tier 1 and tier 2 share the namespace `ta`. `import TradingView/ta/<n>` binds
the library to that name WITH OR WITHOUT an `as` clause, so a `ta.foo` call in a
file carrying that import may be either. Every row therefore records how many
files use it WITH and WITHOUT the library import; a name used only in importing
files is tier 2, not core.

Usage:  python docs/gen_pine_builtin_coverage.py [out.csv]
"""
import collections
import csv
import os
import re
import sys
import warnings

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
FORK = os.path.dirname(HERE)
sys.path.insert(0, FORK)

import pandas_ta as ta  # noqa: E402

CORPUS = os.path.join(HERE, "pine")
LIB = os.path.join(CORPUS, "RA2vGpkA-ta.pine")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    HERE, "pine_builtin_coverage.csv")

TA_CALL = re.compile(r"\bta\.([A-Za-z_][A-Za-z0-9_]*)")
LIB_IMPORT = re.compile(r"^\s*import\s+TradingView/ta/\d+", re.M)
# `export [method] <type> <name>(` -- the library's public surface.
# `export <name>(args) =>` -- the library declares no return type.
LIB_EXPORT = re.compile(
    r"^\s*export\s+(?:method\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.M)

# pandas_ta equivalents that are not a bare name match.
ALIAS = {
    # ⚠ No `bbw` and no `kcw` entry. `ta.bbw` never appears in the corpus and is
    # not a library export, so an alias for it was dead code; `ta.kcw` is the
    # Keltner WIDTH and `pandas_ta.kc` emits no width column (round 4).
    "tr": "true_range", "dmi": "adx", "bb": "bbands",
    "cog": "cg", "wpr": "willr", "dev": "mad", "sar": "psar",
    "change": "mom", "rising": "increasing", "falling": "decreasing",
    "crossover": "cross", "crossunder": "cross", "stochRsi": "stochrsi",
    "stochFull": "stoch", "atr2": "atr", "ema2": "ema", "rma2": "rma",
    "dema2": "dema", "tema2": "tema", "t3Alt": "t3_tv",
    "supertrend2": "supertrend",   # no `vStop2` -> `vStop`: the fork has neither
    # camelCase library names -> the snake_case primitives PINEBI-1a shipped
    "highestSince": "highest_since", "lowestSince": "lowest_since",
    "max": "alltime_max", "min": "alltime_min",
    # Library names that hide a shipped indicator behind an abbreviation. Caught
    # by reading the library's own @function docstrings -- porting these would
    # have duplicated `fisher` and `vortex` under new names.
    "ft": "fisher",             # "Calculates the value of the Fisher Transform"
    "vi": "vortex",             # "Calculates the values of the Vortex Indicator"
    # NOT an alias -- see NOT_PORTED below. Kept out of ALIAS on purpose.
}

# Names whose corpus hits are comments or third-party library methods rather
# than Pine built-ins. Checked by hand 2026-09-07; see the `note` column.
# ⚠ Corrected 2026-09-07 (review round 2). `max`, `min` and `sum` were hand-
# labelled here as "not Pine built-ins". All three ARE built-ins and the corpus
# proves it: `docs/pine/c1pPR2kI.pine:137-139` comments `// All Time High and
# Low` directly over `ta.max(HIGH_)` / `ta.min(LOW_)`, and `sHoqdgZr.pine:118`
# calls the two-argument `ta.sum(x, Days)`. `max`/`min` are now PRIMITIVES (they
# are all-time, NOT rolling); `sum` keeps its verdict but for the right reason.
# A real built-in that the corpus never actually calls. Its own bucket, because
# labelling it `n/a - not a Pine built-in` put a falsehood in the machine-readable
# verdict column that the -1a..-1e scopes are cut from.
NEVER_CALLED = {
    "sum": ("`ta.sum(src, len)` IS a real built-in (sliding sum), but every "
            "corpus hit is a comment or `math.sum`/`array.sum` -- nothing live "
            "to port against"),
}

# Not every primitive is a rolling window, and the note column says so. Driven
# by a map rather than an if/else on two names: round 3 flagged `max`/`min` being
# described as "rolling", that was patched for those two names only, and `cum`
# and `pivot_point_levels` -- neither of which takes a length -- kept shipping
# the same wrong word into the artifact the -1b..-1e scopes are read from.
SHAPE = {
    "max": "all-time running extreme (no length)",
    "min": "all-time running extreme (no length)",
    "cum": "all-time running total (no length)",
    "pivot_point_levels": "period-anchored levels (no rolling window)",
}
DEFAULT_SHAPE = "rolling primitive"

NOT_BUILTIN = {
    "adx": ("not a Pine built-in -- the built-in is `ta.dmi`. Both corpus hits "
            "are comments: `PTBeZtM4-BestTimeFrameFinder.pine:5` "
            "('hand-rolled ADX (identical to ta.adx)') and "
            "`dUWBKgXM-SimTradeIndicators.pine:271`. It escaped the hand check "
            "because it RESOLVED to a pandas_ta name and so never reached this "
            "branch -- the check had been applied to names that failed to "
            "resolve, not to the population"),
    "pivot": "user-defined; the built-in is `ta.pivot_point_levels`",
    "normalize": "hit is a comment in a third-party lib describing its own fn",
    "covariance": 'hit is the comment "Pine has no native ta.covariance"',
}

# Rolling primitives: real core built-ins, but vocabulary rather than features.
# ⚠ `audited` is a claim, so it now carries its receipt.
#
# Round 6 answered "nobody read the sources" with a NAME LIST of 29. Round 7
# broke four of them in twenty minutes -- `trima`, `stc`, `aroon`, `kvo`, all
# `audited=yes`, all divergent, one with the correct formula sitting in
# pandas_ta's own docstring. A list long enough to pass a test is not an audit.
#
# The value is the EVIDENCE: which library line was read and what the comparison
# found. `test_audited_rows_carry_their_evidence` requires it to be non-empty and
# to cite a line. A name with no receipt is `audited=no`, and no is fine -- the
# 28-row backlog is PINEBI-0b, and an honest backlog beats a false all-clear.
# PINEBI-0b: `have` rows the audit did NOT certify, each with the reason.
# Silence is what let five wrong `have` verdicts ship, so an uncertified
# row must say why.
#
# IMPORTED, not retyped. This was a hand-maintained duplicate sitting under
# a comment that claimed `audit_pine_have_rows.py` wrote it. No such writer
# existed, so the two copies could drift with nothing to catch it -- the
# same defect as the `audited` column, one file over.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    # The test suite loads this module by path, not as `docs.<name>`, so a bare
    # `import audit_pine_have_rows` resolves for the CLI and nowhere else.
    sys.path.insert(0, _HERE)
from audit_pine_have_rows import NOT_CERTIFIED as PINEBI_0B_UNCERTIFIED

AUDITED = {
    # PINEBI-1b tranche 1 (2026-09-11). These are `have` BECAUSE they were
    # ported in this batch, which is certification by construction: each is a
    # line-by-line transcription of the cited source with a test module
    # carrying Gate B (mutant), Gate C (fires) and Gate D (scale-free).
    'kcw': 'Pine v6 core built-in `ta.kcw` ported as pandas_ta/volatility/kcw.py:24 `def kcw(high, low, close, length=None, scalar=None, mamode=None, offset=None,` -- `(upper - lower) / basis` over `kc`s own three columns, DELEGATED to `kc` rather than re-deriving the channel (pinned by test_kcw_delegates_to_kc_rather_than_reimplementing_the_channel). Was misclassified `have` until round 4: `kc` emits KCLe_/KCBe_/KCUe_, three price LEVELS and no width. Gate D bit-identical under x8/x64; column KCWe_20_2.0',
    'rwi': 'RA2vGpkA-ta.pine:512 `export rwi(simple int length) =>` ported as pandas_ta/momentum/rwi.py:37 `def rwi(high, low, close, length=None, offset=None, **kwargs):` -- `(high - nz(low[length])) / (atr * sqrt(length))`. TWO transcription traps pinned: Pine `ta.atr` is WILDER smoothing so the port uses `wilder_rma`, NOT this forks `rma` (a different filter, PINEBI-1c measured it); and Pines nz() maps the missing prior bar to 0, which is a real large value, so the warm-up is masked instead of shipped (test_rwi_masks_the_nz_warmup_instead_of_shipping_a_zeroed_prior). Columns RWIh_14/RWIl_14',
    'pzo': 'RA2vGpkA-ta.pine:322 `export pzo(simple int length) =>` ported as pandas_ta/momentum/pzo.py:22 `def pzo(close, length=None, offset=None, **kwargs):` via the shared `zone()` helper (pandas_ta/momentum/_zone.py, Pine L315), one implementation for both pzo and vzo per the FVGENG no-fourth-copy rule. Gate D bit-identical x8/x64; column PZO_14',
    'vzo': 'RA2vGpkA-ta.pine:820 `export vzo(simple int length) =>` ported as pandas_ta/volume/vzo.py:31 `def vzo(close, volume, length=None, offset=None, **kwargs):` via the same `zone()` helper. THE TRAP, pinned by test_vzo_signs_volume_by_price_direction_not_its_own: Pines zone() signs the source by `sign(ta.change(close))`, the PRICE direction, while vzo passes `volume` as the source -- reading `sign(change(volume))` gives a plausible series in the same range answering a different question. Scale-free in BOTH price and volume; column VZO_14',
    'szo': 'RA2vGpkA-ta.pine:715 `export szo(series float source, simple int length) =>` ported as pandas_ta/momentum/szo.py:41 `def szo(close, length=None, offset=None, **kwargs):` -- triple-EMA of `sign(change(close))`, divided by `length`. The `/length` is the sources own behaviour and gives a range of about +/-100/length (+/-7.1 at the default 14), NOT +/-100; it reads like a bug and is reproduced exactly because a mined rule would match on its thresholds (test_szo_range_is_scaled_by_one_over_length_not_plus_minus_100). Column SZO_14',
    'rms': 'RA2vGpkA-ta.pine:505 `export rms(series float source, series int length) =>` ported as pandas_ta/statistics/rms.py:36 `def rms(close, length=None, offset=None, **kwargs):`. `sqrt(mean(close**2))` is a PRICE LEVEL and therefore not an ML feature, so the shipped column is the percent distance `RMS_DIST_PCT_14` and the level sits behind `raw=True` -- the same convention TALIB-1 set for HT_TRENDLINE/MAMA/FAMA/SAREXT. test_rms_raw_is_a_price_level_and_therefore_not_scale_free asserts the raw form is NOT scale-free, so the escape hatch cannot silently become the default',
    'wpo': 'RA2vGpkA-ta.pine:860 `export wpo(simple int length) =>` ported as pandas_ta/momentum/wpo.py:40 `def wpo(high, close, length=None, offset=None, **kwargs):` -- `ema(sign(change(close)) * 2*pi/asin(close[1]/high), length)`. `asin` is undefined where `close[1] > high` (any gap down); those bars are NaN by design rather than clamped into the domain, because clamping would manufacture a period reading exactly where the construction has none (test_wpo_is_nan_where_asin_is_out_of_domain_and_not_clamped). Column WPO_14',
    'atr2': 'RA2vGpkA-ta.pine:102 `export atr2(series float length) =>` ported as pandas_ta/volatility/atr2.py:56 `def atr2(high, low, close, length=None, drift=None, offset=None, **kwargs):` -- PINEBI-1c measured: 14 bars of warm-up saved vs `atr(14)`, per-bar Series length reached; rho vs sibling 0.9708 on the 400-bar fixture, 0.9963-1.0000 across 40 BIST_100 daily parquets',
    'dema2': 'RA2vGpkA-ta.pine:168 `export dema2(series float source, series float length) =>` ported as pandas_ta/overlap/dema2.py:33 `def dema2(close, length=None, offset=None, **kwargs):` -- PINEBI-1c measured: 9 bars of warm-up saved vs `dema(10)`, per-bar Series length reached; rho 0.99997 / 0.9980-1.0000',
    'ema2': 'RA2vGpkA-ta.pine:158 `export ema2(series float source, series float length)` ported as pandas_ta/overlap/ema2.py:176 `def ema2(close, length=None, offset=None, **kwargs):` -- PINEBI-1c measured: 9 bars of warm-up saved vs `ema(10)`, per-bar Series length and a fractional scalar length reached; rho 0.99999 / 0.9998-1.0000',
    'rma2': 'RA2vGpkA-ta.pine:496 `export rma2(series float source, series float length)` ported as pandas_ta/overlap/rma2.py:44 `def rma2(close, length=None, offset=None, **kwargs):` -- PINEBI-1c measured against `wilder_rma`, NOT `rma`: 9 bars saved, per-bar Series length reached; max|diff| 0.0711 vs wilder_rma against 0.4667 vs rma, so the two fork functions are not interchangeable',
    'stochFull': 'RA2vGpkA-ta.pine:541 `export stochFull(simple int periodK, simple int smoothK, simple int periodD) =>` against pandas_ta/momentum/stoch.py:28 `stoch_k = sma(stoch, length=smooth_k)` -- PINEBI-1c measured: `stoch(k=periodK, d=periodD, smooth_k=smoothK)` reproduces it to max|diff| 0.0 on the 400-bar fixture, including at smoothK != periodD; 2.59e-12 worst case across 40 BIST_100 dailies (float summation order in a ~5,700-bar rolling window, not a behavioural difference), rho 1.0 on all 40. DELETED rather than shipped',
    'stochRsi': 'RA2vGpkA-ta.pine:554 `export stochRsi(` against pandas_ta/momentum/stochrsi.py:28 `stochrsi_k = sma(stoch, length=k)` -- PINEBI-1c measured: `stochrsi(length=periodK, rsi_length=lengthRsi, k=smoothK, d=periodD)` reproduces it to max|diff| 0.0; DELETED rather than shipped',
    'supertrend2': 'RA2vGpkA-ta.pine:602 `export supertrend2(series float factor, series float atrLength, simple bool wicks = false) =>` ported as pandas_ta/overlap/supertrend2.py:65 `def supertrend2(high, low, close, length=None, multiplier=None, wicks=None,` -- PINEBI-1c measured: 7 bars of warm-up saved vs `supertrend(7, 3.0)`; THREE parameters reached, the per-bar ATR length, the per-bar factor (L602 declares both `series float`) and `wicks`; rho 0.9928 on the fixture but 0.7901-1.0000 across 40 tickers, so on some tickers this is a materially different line. Direction follows Pine: -1 is the UPTREND, the negation of SUPERTd',
    't3Alt': 'RA2vGpkA-ta.pine:661 `export t3Alt(series float source, series float length, simple float vf = 0.7) =>` ported as pandas_ta/overlap/t3_tv.py:55 `def t3_tv(close, length=None, vf=None, offset=None, **kwargs):` -- PINEBI-1c measured: 9 bars of warm-up saved vs `t3(10, 0.7)`, per-bar Series length reached, and the volume factor left unclamped where `t3` rewrites anything outside (0, 1) to 0.7 without saying so; rho 0.99998 / 0.9970-1.0000',
    'tema2': 'RA2vGpkA-ta.pine:681 `export tema2(series float source, series float length) =>` ported as pandas_ta/overlap/tema2.py:31 `def tema2(close, length=None, offset=None, **kwargs):` -- PINEBI-1c measured: 9 bars of warm-up saved vs `tema(10)`, per-bar Series length reached; rho 0.99994 / 0.9982-1.0000',
    "cci": "PINEBI-0b measured: docs/audit_pine_have_rows.py:168 `ta.cci(` -- matches an independent implementation of the Pine v6 formula to 0.000e+00 over 287 bars",
    "cog": "PINEBI-0b measured: docs/audit_pine_have_rows.py:170 `ta.cg(` -- matches an independent implementation of the Pine v6 formula to 4.441e-15 over 287 bars",
    "dema": "PINEBI-0b measured: docs/audit_pine_have_rows.py:163 `ta.dema(` -- matches an independent implementation of the Pine v6 formula to 0.000e+00 over 287 bars",
    "dev": "PINEBI-0b measured: docs/audit_pine_have_rows.py:130 `ta.mad(` -- matches an independent implementation of the Pine v6 formula to 0.000e+00 over 287 bars",
    "ema": "PINEBI-0b measured: docs/audit_pine_have_rows.py:112 `ta.ema(` -- matches an independent implementation of the Pine v6 formula to 0.000e+00 over 287 bars",
    "mom": "PINEBI-0b measured: docs/audit_pine_have_rows.py:128 `ta.mom(` -- matches an independent implementation of the Pine v6 formula to 0.000e+00 over 286 bars",
    "obv": "PINEBI-0b measured: docs/audit_pine_have_rows.py:156 `ta.obv(` -- identical to the Pine v6 formula up to a CONSTANT offset of 40429 over 300 bars -- an initialisation convention -- the fork seeds the running total with the first bar's volume, Pine's `ta.cum` treats the leading `na` as 0. ⚠ the offset is volume[0], so it differs per ticker: harmless within one series, NOT harmless across a cross-ticker feature matrix",
    "roc": "PINEBI-0b measured: docs/audit_pine_have_rows.py:125 `ta.roc(` -- matches an independent implementation of the Pine v6 formula to 0.000e+00 over 286 bars",
    "sma": "PINEBI-0b measured: docs/audit_pine_have_rows.py:110 `ta.sma(` -- matches an independent implementation of the Pine v6 formula to 0.000e+00 over 287 bars",
    "tema": "PINEBI-0b measured: docs/audit_pine_have_rows.py:166 `ta.tema(` -- matches an independent implementation of the Pine v6 formula to 0.000e+00 over 287 bars",
    "tr": "PINEBI-0b measured: docs/audit_pine_have_rows.py:121 `ta.true_range(` -- matches an independent implementation of the Pine v6 formula to 0.000e+00 over 299 bars",
    "vhf": "PINEBI-0b measured: docs/audit_pine_have_rows.py:172 `ta.vhf(` -- matches an independent implementation of the Pine v6 formula to 0.000e+00 over 286 bars",
    "vwma": "PINEBI-0b measured: docs/audit_pine_have_rows.py:158 `ta.vwma(` -- matches an independent implementation of the Pine v6 formula to 0.000e+00 over 287 bars",
    "wma": "PINEBI-0b measured: docs/audit_pine_have_rows.py:116 `ta.wma(` -- matches an independent implementation of the Pine v6 formula to 0.000e+00 over 287 bars",
    "wpr": "PINEBI-0b measured: docs/audit_pine_have_rows.py:152 `ta.willr(` -- matches an independent implementation of the Pine v6 formula to 1.421e-14 over 287 bars",
    # Compared body-to-body, round 6-7. Those that diverged carry a
    # SEMANTIC_CAVEAT; the divergence IS the evidence the comparison happened.
    "crossunder": "core namespace, no library body; "
                  "pandas_ta/utils/_signals.py:79 -- "
                  "`cross = current & previous if above else` is upward-only "
                  "by default. Caveated.",
    "cross": "core `ta.cross` is either-direction; "
             "pandas_ta/utils/_signals.py:79 "
             "`cross = current & previous if above else` is one direction per "
             "call. Caveated.",
    "swma": "pandas_ta/overlap/swma.py:8 `length = int(length)` defaults to 10 "
            "against TradingView's fixed 4-bar kernel. Caveated.",
    "supertrend": "RA2vGpkA-ta.pine:591 `direction == -1` is the uptrend; "
                  "pandas_ta/overlap/supertrend.py:35 `dir_[i] = 1` is the "
                  "uptrend there. Caveated.",
    "eom": "RA2vGpkA-ta.pine:196 `div = 10000` vs "
           "pandas_ta/volume/eom.py:10 `100000000`. Caveated.",
    "trima": "RA2vGpkA-ta.pine:693 `math.ceil(length / 2)` (two different "
             "windows) vs "
             "pandas_ta/overlap/trima.py:16 `half_length` used for both "
             "passes. Caveated.",
    "aroon": "RA2vGpkA-ta.pine:94 `ta.highestbars(high, length)` (L-bar) vs "
             "pandas_ta/trend/aroon.py:19 `rolling(length + 1)`. Caveated.",
    "kvo": "RA2vGpkA-ta.pine:292 `* 100` absent from "
           "pandas_ta/volume/kvo.py:41 `signed_volume`. Caveated.",
    "change": "core `ta.change` defaults to 1; "
              "pandas_ta/momentum/mom.py:8 `else 10`. Caveated.",
    "sar": "core returns one series; pandas_ta/trend/psar.py:104 "
           "`PSARl` is emitted beside PSARs. Caveated.",
    "stoch": "core `ta.stoch` is raw %K; pandas_ta/momentum/stoch.py:12 "
             "`smooth_k` resolves to 3. Caveated.",
    # NO caveat: measured, and there is no divergence to record.
    "variance": "core defaults `biased=true` (ddof=0); "
                "pandas_ta/statistics/variance.py:9 `else 0` resolves to the "
                "same. MATCHES -- no caveat. (An earlier round pasted `stdev`'s "
                "caveat here without running the code.)",
    "stdev": "core defaults `biased=true` (ddof=0); "
             "pandas_ta/statistics/stdev.py:7 `ddof=1` in the signature -- "
             "genuinely differs, unlike `variance`. Caveated.",
    "rising": "core is monotone over `length`; "
              "pandas_ta/trend/increasing.py:9 `strict` resolves to "
              "False. Caveated.",
    "falling": "core is monotone over `length`; "
               "pandas_ta/trend/decreasing.py:9 `strict` resolves to "
               "False. Caveated.",
}

# `have`, but not a drop-in: the shipped function computes the same idea with a
# different default or shape. Recorded so a porter does not transliterate a Pine
# call into a pandas_ta call that quietly means something else.
# PINEBI-1c CLOSED 2026-09-08. These nine were `port - alternate impl` -- each
# restates an indicator the fork already ships, so Gate E reads rho ~ 1.0 and the
# revert rule would have deleted all nine unread. The rule was suspended and the
# nine were measured on two axes instead, warm-up saved and parameter reach, on a
# 400-bar seeded fixture and on 40 BIST_100 daily parquets. Seven earned a column;
# two were reproduced BIT FOR BIT by their sibling and were deleted rather than
# shipped, which is the outcome this map has to be able to express -- a verdict
# vocabulary that can only say "ported" cannot record a measured deletion.
# Full table: docs/PineAlternatesMeasured.md.
PINEBI_1C = {
    "ema2": "pandas_ta.ema2 -- PINEBI-1c KEPT: saves 9 bars of warm-up over "
            "`ema(10)` and takes a per-bar `Series` length, which `ema` raises on",
    "rma2": "pandas_ta.rma2 -- PINEBI-1c KEPT: saves 9 bars over `wilder_rma(10)` "
            "(NOT `rma`, which is `adjust=True` and a different filter) and takes "
            "a per-bar `Series` length",
    "dema2": "pandas_ta.dema2 -- PINEBI-1c KEPT: saves 9 bars over `dema(10)` and "
             "takes a per-bar `Series` length",
    "tema2": "pandas_ta.tema2 -- PINEBI-1c KEPT: saves 9 bars over `tema(10)` and "
             "takes a per-bar `Series` length",
    "t3Alt": "pandas_ta.t3_tv -- PINEBI-1c KEPT: saves 9 bars over `t3(10, 0.7)`, "
             "takes a per-bar `Series` length, and reaches a volume factor >= 1 "
             "that `t3` silently clamps back to 0.7 while still naming the column "
             "T3_10_0.7",
    "atr2": "pandas_ta.atr2 -- PINEBI-1c KEPT: saves 14 bars over `atr(14)` and "
            "takes a per-bar `Series` length",
    "supertrend2": "pandas_ta.supertrend2 -- PINEBI-1c KEPT: saves 7 bars over "
                   "`supertrend(7, 3.0)`, takes a per-bar `Series` ATR length, and "
                   "reaches `wicks`, which the sibling swallows into **kwargs. "
                   "⚠ DIRECTION SIGN follows Pine (-1 is the uptrend), the "
                   "opposite of SUPERTd",
    "stochFull": "pandas_ta.stoch -- PINEBI-1c DELETED, not shipped: "
                 "`stoch(k=periodK, d=periodD, smooth_k=smoothK)` reproduces it "
                 "bit for bit on the 400-bar fixture (max|diff| 0.0, including at "
                 "smoothK != periodD) and to 2.59e-12 across 40 BIST_100 dailies, "
                 "rho 1.0 on all 40; saves no warm-up and reaches no parameter the "
                 "sibling lacks -- `smooth_k` has always been separate from `d`",
    "stochRsi": "pandas_ta.stochrsi -- PINEBI-1c DELETED, not shipped: "
                "`stochrsi(length=periodK, rsi_length=lengthRsi, k=smoothK, "
                "d=periodD)` reproduces it bit for bit (max|diff| 0.0, rho 1.0 on "
                "all 40 tickers)",
}

SEMANTIC_CAVEAT = {
    "atr": "inherits `rma`'s divergence: `pandas_ta.atr` smooths the true range with `pandas_ta.rma`, which is `ewm(adjust=True)` rather than Wilder's recursion. Max divergence 0.0349 from the Pine formula.",
    "cmo": "`pandas_ta.cmo` DEFAULTS to `talib=True`, which Wilder-smooths the up/down sums; Pine's `ta.cmo` sums them plainly. Max divergence 42.48 on a +/-100 oscillator. `ta.cmo(close, talib=False)` matches Pine exactly -- the default does not.",
    "hma": "Pine's `ta.hma` smooths with `math.round(sqrt(length))`; `pandas_ta/overlap/hma.py` uses `int(sqrt(length))` (floor). At length=14 the roots are 4 vs 3 and the outputs differ by 0.474 on a ~103 price. Differs at every length where floor != round: 7, 14, 15, 22, 23, 30, ...",
    "median": "Pine's `ta.median` is the nearest-rank median (`percentile_nearest_rank(src, len, 50)`), which returns an actual sample value; `pandas_ta.median` is `rolling().median()`, which averages the two middles at even lengths. Max divergence 1.0122 at length 14.",
    "rma": "`pandas_ta.rma` is `ewm(alpha=1/length, adjust=True)` -- verified bit-equal to that -- which is NOT Wilder's smoothing. Pine's `ta.rma` is the SMA-seeded `adjust=False` recursion. Max divergence 0.2138 on a ~103 price, and 189 of 287 bars differ by more than 1e-6, so this is a permanent difference, not a warm-up.",
    "rising": "Pine's `ta.rising` is monotone over `length` bars; pass "
              "`strict=True` (and mind the window: pandas_ta compares "
              "`length` values, Pine `length` diffs)",
    "falling": "⚠ Pine's `ta.falling` is monotone over `length` bars; pass "
               "`strict=True` (and mind the window: pandas_ta compares "
               "`length` values, Pine `length` diffs)",
    "change": "Pine's `ta.change` defaults to length 1; `pandas_ta.mom` "
              "defaults to 10",
    "stoch": "Pine's `ta.stoch` is the raw %K; `pandas_ta.stoch` smooths it "
             "unless `smooth_k=1`",
    # (no `stochFull` entry: it is classified `port - alternate impl` before the
    # `have` branch is reached, so a caveat here would never be emitted --
    # `test_every_map_entry_is_reachable` now proves that for all five maps.)
    "crossunder": "⚠ DIRECTION: `pandas_ta.cross` defaults `above=True` and "
                  "detects UPWARD crosses only; a crossunder needs "
                  "`cross(a, b, above=False)`",
    "cross": "⚠ Pine's `ta.cross` is EITHER direction; `pandas_ta.cross` is "
             "one direction per call -- use `cross(a,b,True) | cross(a,b,False)`",
    "swma": "⚠ Pine's `ta.swma` is the FIXED 4-bar [1,2,2,1]/6 kernel and takes "
            "no length; `pandas_ta.swma` defaults to length=10 and says so in "
            "its own docstring ('variable length in contrast to TradingView's "
            "fixed length') -- pass `length=4`",
    "supertrend": "⚠ DIRECTION SIGN IS INVERTED: the library's `direction == -1` "
                  "is the uptrend (`RA2vGpkA-ta.pine:591`), pandas_ta's "
                  "`SUPERTd == 1` is. The library also has a `wicks` option "
                  "(reverse on high/low) with no pandas_ta equivalent",
    "eom": "⚠ divisor default differs by 1e4: the library uses `div = 10000` "
           "(`RA2vGpkA-ta.pine:196`), `pandas_ta.eom` uses 100000000",
    "trima": "⚠ DIFFERENT LENGTHS: the library is "
             "`sma(sma(src, ceil(L/2)), floor(L/2)+1)` "
             "(`RA2vGpkA-ta.pine:692`) -- two different windows; "
             "`pandas_ta.trima` uses `round(0.5*(L+1))` for BOTH passes, so the "
             "two diverge at every EVEN length (L=10 -> Pine 5,6 vs fork 6,6). "
             "pandas_ta's own docstring quotes the formula it does not implement",
    "aroon": "⚠ window off by one: the library is "
             "`100 * (highestbars(high, L) + L) / L` (`RA2vGpkA-ta.pine:93`), an "
             "L-bar window whose Aroon-Up cannot fall below 100/L; "
             "`pandas_ta.aroon` rolls L+1 bars and does reach 0",
    "kvo": "⚠ scale: the library's trend is `sign(change(hlc3)) * volume * 100` "
           "(`RA2vGpkA-ta.pine:292`); `pandas_ta.kvo` omits the x100, so every "
           "value is 100x smaller. It also trims to `first_valid_index()` "
           "before the EMAs, changing the warm-up seed",
    "stdev": "Pine defaults `biased=true` (ddof=0); pandas_ta defaults to 1",
    "sar": "Pine's `ta.sar` is one series; `pandas_ta.psar` returns "
           "complementary `PSARl`/`PSARs` -- combine with `PSARl.fillna(PSARs)`",
}

PRIMITIVES = {
    "highest", "lowest", "highestbars", "lowestbars", "valuewhen", "barssince",
    "cum", "correlation", "percentrank", "percentile_nearest_rank",
    "percentile_linear_interpolation", "pivot_point_levels", "pivothigh",
    "pivotlow", "highestSince", "lowestSince",
    # All-time, not rolling: `ta.max(high)` takes no length and returns the
    # running extreme from bar 0.
    "max", "min",
}

DATA_REQUEST = {"requestVolumeDelta", "requestUpAndDownVolume"}

# ⚠ Names where a bare match to a pandas_ta function is WRONG -- the two
# libraries use the same short name for different indicators. Found by reading
# the `@function` line above every tier-2 export rather than trusting the name;
# `test_every_tier2_have_row_was_docstring_audited` keeps that audit honest.
WRONG_NAME_MATCH = {
    "stc": ("the library is `ema(stoch(ema(stoch(macd, cycle), d1), cycle), d2)` "
            "clamped to [0,100] (`RA2vGpkA-ta.pine:527`), with `d1`/`d2` as "
            "parameters. `pandas_ta.stc` has NEITHER -- it substitutes a "
            "fixed-alpha recursion (`factor=0.5`) and no clamp, and its "
            "`if lowest_xmacd.iloc[i] > 0` guard (`stc.py:195`) freezes the "
            "first stochastic whenever the rolling MACD minimum is <= 0, which "
            "for a zero-centred oscillator is the normal case. Not expressible "
            "as a call to the shipped function"),
    "dm": ("the library's `dm` is the **Demarker** oscillator "
           "(`RA2vGpkA-ta.pine:174`: `sma(demax)/(sma(demax)+sma(demin))`, "
           "bounded 0-1). `pandas_ta.dm` is Wilder's Directional Movement "
           "(`DMP_`/`DMN_`) -- a different indicator, no ratio column"),
}

# Portable, but deliberately not ported, with the reason recorded.
# ⚠ `kcw` was aliased to `kc` and classified `have` until round 4. It is not
# had: Pine's `ta.kcw` is the Keltner WIDTH, `(upper - lower) / basis`, and
# `pandas_ta.kc` returns `KCLe_/KCBe_/KCUe_` with no width column and no
# parameter that produces one. The sibling `bbw -> bbands` is correct only by
# accident, because `bbands` does emit `BBB_`. A `have` verdict would have
# deleted a real port permanently -- `P8mcVgcu-FastMetrix.pine:58` calls it live.
NOT_PORTED = {
    "cagr": ("`cagr(entryTime, entryPrice, exitTime, exitPrice)` is a two-POINT "
             "growth rate over arbitrary endpoints (`RA2vGpkA-ta.pine:114`). "
             "`pandas_ta.cagr` is a whole-series scalar over the first and last "
             "bar with no endpoint arguments -- it cannot express the call. A "
             "two-point CAGR is a one-liner; same ruling as `changePercent`"),
    "changePercent": (
        "`100 * (a - b) / b` on two ARBITRARY series (library docstring: "
        "'between two distinct values'). `percent_return` is a one-series "
        "rolling return and is NOT the same function; this one is a one-liner "
        "at the call site and needs no primitive"),
}


def scan_corpus():
    """-> {name: [files_without_lib_import, files_with_lib_import]}"""
    usage = collections.defaultdict(lambda: [0, 0])
    files = 0
    for entry in sorted(os.listdir(CORPUS)):
        if not entry.endswith(".pine"):
            continue
        files += 1
        src = open(os.path.join(CORPUS, entry), encoding="utf8",
                   errors="replace").read()
        has_lib = bool(LIB_IMPORT.search(src))
        for name in set(TA_CALL.findall(src)):
            usage[name][1 if has_lib else 0] += 1
    return usage, files


def library_exports():
    if not os.path.exists(LIB):
        return set()
    src = open(LIB, encoding="utf8", errors="replace").read()
    return set(LIB_EXPORT.findall(src))


def equivalent(name):
    """The pandas_ta callable this Pine name maps to, or ''."""
    for candidate in (name, name.lower(), ALIAS.get(name, "")):
        if candidate and callable(getattr(ta, candidate, None)):
            return candidate
    return ""


def classify(name, clean_files, lib_files, exports):
    """-> (tier, verdict, note)"""
    if name in NOT_BUILTIN:
        return "none", "n/a - not a Pine built-in", NOT_BUILTIN[name]

    if name in NEVER_CALLED:
        return "1", "n/a - never called live in the corpus", NEVER_CALLED[name]

    tier2 = name in exports
    core_only = clean_files > 0
    if tier2 and not core_only:
        tier = "2"
    elif tier2:
        tier = "1+2"          # the library re-exports a core name
    else:
        tier = "1"

    if name in WRONG_NAME_MATCH:
        return tier, "port", WRONG_NAME_MATCH[name] + "; PINEBI-1b"

    if name in NOT_PORTED:
        return tier, "n/a - not worth a primitive", NOT_PORTED[name]

    if name in DATA_REQUEST:
        return tier, "port - blocked on data", (
            "needs lower-timeframe data below the engine's 1h floor; PINEBI-1d")

    eq = equivalent(name)
    if name in PINEBI_1C:
        return tier, "have", PINEBI_1C[name]
    # PRIMITIVES outranks a namespace match ON PURPOSE. Once PINEBI-1a landed,
    # `equivalent()` started resolving all 18 against the fork's own utils and
    # flipped them to `have`, which would make this CSV unreproducible -- the
    # one thing PINEBI-0 has to be. A name declared vocabulary stays vocabulary;
    # `pandas_ta_equivalent` still records where it now lives.
    if name in PRIMITIVES:
        landed = " (landed: pandas_ta.%s)" % eq if eq else ""
        # `max`/`min` are all-time, not rolling. Emitting the generic note for
        # them would ship the exact wrong semantic into the artifact that the
        # -1a..-1e scopes are read from -- which it did, for one round.
        shape = SHAPE.get(name, DEFAULT_SHAPE)
        return tier, "port - primitive", (
            "%s, belongs in pandas_ta/utils/, not Category; PINEBI-1a%s"
            % (shape, landed))
    if eq:
        caveat = SEMANTIC_CAVEAT.get(name)
        return tier, "have", ("pandas_ta.%s (⚠ %s)" % (eq, caveat) if caveat
                              else "pandas_ta.%s" % eq)
    if tier == "1":
        return tier, "port", ("no pandas_ta equivalent; PINEBI-1b "
                              "(tier-1 core gap, no MPL attribution)")
    return tier, "port", "no pandas_ta equivalent; PINEBI-1b"


def main():
    usage, files = scan_corpus()
    exports = library_exports()
    print("corpus files scanned: %d" % files)
    print("library exports found in %s: %d" % (os.path.basename(LIB),
                                               len(exports)))

    rows = []
    for name in sorted(usage, key=lambda n: (-sum(usage[n]), n)):
        clean, with_lib = usage[name]
        tier, verdict, note = classify(name, clean, with_lib, exports)
        rows.append({
            "tier": tier,
            "name": name,
            "files_using": clean + with_lib,
            "files_without_lib_import": clean,
            "files_with_lib_import": with_lib,
            "in_tradingview_ta_library": int(name in exports),
            "pandas_ta_equivalent": equivalent(name),
            "verdict": verdict,
            "audited": ("yes" if name in AUDITED else
                        "no" if verdict == "have" else "n/a"),
            "audit_evidence": AUDITED.get(name, ""),
            "note": note + (
                " | PINEBI-0b not certified: "
                + PINEBI_0B_UNCERTIFIED[name]
                if verdict == "have" and name in PINEBI_0B_UNCERTIFIED
                and name not in AUDITED else ""),
        })

    # Library exports the corpus never calls are still portable candidates.
    seen = {r["name"] for r in rows}
    for name in sorted(exports - seen):
        tier, verdict, note = classify(name, 0, 0, exports)
        rows.append({
            "tier": "2", "name": name, "files_using": 0,
            "files_without_lib_import": 0, "files_with_lib_import": 0,
            "in_tradingview_ta_library": 1,
            "pandas_ta_equivalent": equivalent(name),
            "verdict": verdict,
            "audited": ("yes" if name in AUDITED else
                        "no" if verdict == "have" else "n/a"),
            "audit_evidence": AUDITED.get(name, ""),
            "note": note + " (exported but never called in the corpus)" + (
                " | PINEBI-0b not certified: "
                + PINEBI_0B_UNCERTIFIED[name]
                if verdict == "have" and name in PINEBI_0B_UNCERTIFIED
                and name not in AUDITED else ""),
        })

    # Same stamp the three altrepo CSVs carry. These verdicts are conditional
    # on the probe environment -- installing TA-Lib moved `dm` -- and this was
    # the one of the four files that did not say so.
    try:
        import talib
        _have = f"talib {talib.__version__}"
    except Exception:                                       # noqa: BLE001
        _have = "talib ABSENT"
    import pandas as _pd
    _env = f"{_have}; pandas {_pd.__version__}"
    for _r in rows:
        _r["probe_env"] = _env

    with open(OUT, "w", encoding="utf8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print("WROTE %s (%d rows)" % (OUT, len(rows)))

    by_verdict = collections.Counter(r["verdict"] for r in rows)
    for verdict, n in by_verdict.most_common():
        print("  %-26s %3d" % (verdict, n))

    core = [r for r in rows if r["tier"].startswith("1")]
    lib = [r for r in rows if "2" in r["tier"]]
    print("tier 1 (core, incl. 1+2): %d used, %d have, %d port" % (
        len(core), sum(r["verdict"] == "have" for r in core),
        sum(r["verdict"].startswith("port") for r in core)))
    print("tier 2 (TradingView/ta):  %d exports, %d have, %d port" % (
        len(lib), sum(r["verdict"] == "have" for r in lib),
        sum(r["verdict"].startswith("port") for r in lib)))


if __name__ == "__main__":
    main()
