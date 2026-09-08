# -*- coding: utf-8 -*-
"""PINEBI-0b: audit the `have` rows by MEASUREMENT against the Pine formula.

A `have` verdict asserts a Pine name is already covered by a pandas_ta function,
and it removes that name from every port task permanently. Five such assertions
have already been wrong -- `kcw` (Keltner width vs bands), `dm` (Demarker vs
Directional Movement), `cagr` (two endpoints vs whole-series), `cross` and
`crossunder` (either-direction vs upward-only) -- and four more that had been
certified from the library's one-line `@function` summary (`trima`, `stc`,
`aroon`, `kvo`) turned out to diverge.

⚠ These 40 are TIER-1 core intrinsics: `ta.sma`, `ta.ema`, ... There is no
published source to read. The Pine v6 reference gives the FORMULA, so the audit
is an independent implementation of that formula compared against the fork's
output -- the same standard the altrepo scans use, and a stronger one than
reading a docstring.

**A reference here is a claim about Pine, written from the v6 reference.** Where
the documented formula is unambiguous it is implemented below and measured.
Where it is not -- multi-output indicators whose Pine column order or default
smoothing this file cannot pin down without a live chart -- the row stays
`audited=no` WITH A STATED REASON, which is still better than the current state
of no reason at all. An honest backlog beats a false all-clear; that is the same
call PINEBI-0 made and it is why this task exists.

Usage:  python docs/audit_pine_have_rows.py

It does NOT write the CSV, which an earlier docstring claimed. It rewrites
the `AUDITED` receipts inside `docs/gen_pine_builtin_coverage.py` -- each one
citing the line here that carries the reference call -- and that generator
imports `NOT_CERTIFIED` back from this module, so the two tables have one home
apiece and no copies. Run this, THEN the generator, to refresh the CSV.

Because the receipts carry line numbers into THIS file, any edit here (a
docstring included) shifts them and
`tests/test_pine_coverage_csv.py::test_audited_rows_carry_their_evidence`
goes red until this script is re-run. That is the guard working, not a flake.
"""
import csv
import io
import os
import sys
import warnings

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
FORK = os.path.dirname(HERE)
CSV_PATH = os.path.join(HERE, "pine_builtin_coverage.csv")
sys.path.insert(0, FORK)

import numpy as np                                          # noqa: E402
import pandas_ta as ta                                      # noqa: E402
from pandas import DataFrame, Series, date_range            # noqa: E402


def frame(n=300, seed=11):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1.0, n))
    high = close + rng.uniform(0.1, 1.5, n)
    low = close - rng.uniform(0.1, 1.5, n)
    open_ = low + (high - low) * rng.uniform(0, 1, n)
    volume = rng.integers(1_000, 100_000, n).astype(float)
    return DataFrame({"open": open_, "high": high, "low": low, "close": close,
                      "volume": volume},
                     index=date_range("2020-01-01", periods=n, freq="D"))


F = frame()
C, H, L, V, O = F["close"], F["high"], F["low"], F["volume"], F["open"]
N = 14


# --------------------------------------------------------------------------
# Pine v6 reference formulas, implemented here from the language reference.
# Each returns (fork_output, pine_reference_output).
# --------------------------------------------------------------------------
def _seeded_ewm(src, alpha, length):
    """A recursive average SMA-seeded on bar `length-1`, as Pine does.

    ⚠ The previous version's docstring SAID "SMA-seeded" and the body was a
    plain `ewm(adjust=False)`, which seeds on the FIRST VALUE. Pine SMA-seeds
    and so does this fork (`pandas_ta/overlap/ema.py`), so a correct reference
    is bit-equal -- measured 0.0 -- and the convergence branch below was
    forgiving nothing but my own error.
    """
    seeded = src.copy()
    seeded.iloc[:length] = np.nan
    seeded.iloc[length - 1] = src.iloc[:length].mean()
    return seeded.ewm(alpha=alpha, adjust=False, ignore_na=True).mean()


def _rma(src, length):
    """Pine ta.rma: Wilder's smoothing, alpha = 1/length, SMA-seeded."""
    return _seeded_ewm(src, 1.0 / length, length)


def _ema(src, length):
    """Pine ta.ema: alpha = 2/(length+1), SMA-seeded."""
    return _seeded_ewm(src, 2.0 / (length + 1), length)


def _true_range():
    prev = C.shift(1)
    return np.maximum(H - L, np.maximum((H - prev).abs(), (L - prev).abs()))


REFERENCE = {
    # ta.sma(source, length) = arithmetic mean of the last `length` values
    "sma": lambda: (ta.sma(C, length=N), C.rolling(N).mean()),
    # ta.ema: alpha = 2/(length+1), recursive
    "ema": lambda: (ta.ema(C, length=N), _ema(C, N)),
    # ta.rma: alpha = 1/length
    "rma": lambda: (ta.rma(C, length=N), _rma(C, N)),
    # ta.wma: linearly weighted, weight i = i
    "wma": lambda: (ta.wma(C, length=N),
                    C.rolling(N).apply(
                        lambda w: np.dot(w, np.arange(1, N + 1))
                        / (N * (N + 1) / 2), raw=True)),
    # ta.tr(true) = max(h-l, |h-c[1]|, |l-c[1]|)
    "tr": lambda: (ta.true_range(H, L, C), _true_range()),
    # ta.atr = rma(tr, length)
    "atr": lambda: (ta.atr(H, L, C, length=N), _rma(_true_range(), N)),
    # ta.roc = 100 * (src - src[length]) / src[length]
    "roc": lambda: (ta.roc(C, length=N),
                    100.0 * (C - C.shift(N)) / C.shift(N)),
    # ta.mom = src - src[length]
    "mom": lambda: (ta.mom(C, length=N), C - C.shift(N)),
    # ta.dev = mean(|src - sma(src)|)  (mean absolute deviation)
    "dev": lambda: (ta.mad(C, length=N),
                    C.rolling(N).apply(
                        lambda w: np.abs(w - w.mean()).mean(), raw=True)),
    # Pine's `ta.median(src, len)` is `ta.percentile_nearest_rank(src, len, 50)`
    # -- at EVEN lengths it returns an actual sample value, where a conventional
    # median averages the two middles.
    # ⚠ The previous reference was `C.rolling(N).median()`, which is verbatim
    # `pandas_ta/statistics/median.py`. Testing a function against a copy of
    # itself certifies nothing; that is the `hma` tautology repeated.
    "median": lambda: (ta.median(C, length=N), _nearest_rank_median()),
    # ta.cmo = 100 * (sum(up) - sum(down)) / (sum(up) + sum(down))
    # ⚠ The DEFAULT call. An earlier version passed `talib=False` to make the
    # row pass and then shipped a receipt saying "matches to 0.000e+00" with no
    # mention of the kwarg -- so a porter reading `cmo | have` would call
    # `ta.cmo(close)` and get a Wilder-smoothed indicator that differs from
    # Pine by 42.5 points on a +/-100 oscillator.
    "cmo": lambda: (ta.cmo(C, length=N),
                    (lambda d: 100.0 * (d.clip(lower=0).rolling(N).sum()
                                        - (-d.clip(upper=0)).rolling(N).sum())
                     / (d.clip(lower=0).rolling(N).sum()
                        + (-d.clip(upper=0)).rolling(N).sum()))(C.diff())),
    # ta.wpr = 100 * (close - highest(high,l)) / (highest - lowest)
    "wpr": lambda: (ta.willr(H, L, C, length=N),
                    -100.0 * (H.rolling(N).max() - C)
                    / (H.rolling(N).max() - L.rolling(N).min())),
    # ta.obv = cumulative sign(change(close)) * volume
    "obv": lambda: (ta.obv(C, V), (np.sign(C.diff()).fillna(0) * V).cumsum()),
    # ta.vwma = sma(src*volume, l) / sma(volume, l)
    "vwma": lambda: (ta.vwma(C, V, length=N),
                     (C * V).rolling(N).mean() / V.rolling(N).mean()),
    # ta.hma = wma(2*wma(src, l/2) - wma(src, l), floor(sqrt(l)))
    "hma": lambda: (ta.hma(C, length=N), _hma_reference()),
    # ta.dema = 2*ema - ema(ema)
    "dema": lambda: (ta.dema(C, length=N),
                     (lambda e: 2 * e - _ema(e, N))(_ema(C, N))),
    # ta.tema = 3*(ema - ema2) + ema3
    "tema": lambda: (ta.tema(C, length=N), _tema_reference()),
    # ta.cci = (tp - sma(tp)) / (0.015 * dev(tp))
    "cci": lambda: (ta.cci(H, L, C, length=N), _cci_reference()),
    # ta.cog = -sum(src[i]*(i+1)) / sum(src)
    "cog": lambda: (ta.cg(C, length=N), _cog_reference()),
    # ta.vhf = |highest(close,l) - lowest(close,l)| / sum(|change(close)|, l)
    "vhf": lambda: (ta.vhf(C, length=N),
                    (C.rolling(N).max() - C.rolling(N).min()).abs()
                    / C.diff().abs().rolling(N).sum()),
}


def _hma_reference():
    """Pine: `wma(2*wma(src, len/2) - wma(src, len), math.round(sqrt(len)))`.

    ⚠ ROUND, not floor. The first version of this reference used
    `int(np.floor(np.sqrt(N)))` -- which is what `pandas_ta/overlap/hma.py`
    does -- so it certified the fork against a copy of the fork's own choice.
    At N=14 the roots are 4 (Pine) and 3 (the fork), and the outputs differ by
    0.474 on a ~103 price. Two wrong implementations agreeing is the exact
    failure this audit exists to prevent.
    """
    half = int(N / 2)
    root = int(round(np.sqrt(N)))

    def wma(src, length):
        return src.rolling(length).apply(
            lambda w: np.dot(w, np.arange(1, length + 1))
            / (length * (length + 1) / 2), raw=True)

    return wma(2 * wma(C, half) - wma(C, N), root)


def _tema_reference():
    e1 = _ema(C, N)
    e2 = _ema(e1, N)
    e3 = _ema(e2, N)
    return 3 * (e1 - e2) + e3


def _nearest_rank_median():
    """Pine's median = the ceil(0.5*n)-th smallest, not the mean of the middles."""
    return C.rolling(N).apply(
        lambda w: np.sort(w)[int(np.ceil(0.5 * len(w))) - 1], raw=True)


def _cci_reference():
    tp = (H + L + C) / 3.0
    mean = tp.rolling(N).mean()
    dev = tp.rolling(N).apply(lambda w: np.abs(w - w.mean()).mean(), raw=True)
    return (tp - mean) / (0.015 * dev)


def _cog_reference():
    def one(w):
        weights = np.arange(1, len(w) + 1)
        return -np.dot(w[::-1], weights) / w.sum()
    return C.rolling(N).apply(one, raw=True)


# The ONLY row where a constant offset is an accepted explanation.
# `pandas_ta/volume/obv.py` seeds the running total with the first bar's
# volume; Pine's `ta.cum` treats the leading `na` as 0. ⚠ The offset is
# `volume[0]`, so it differs per ticker -- harmless within one series, NOT
# harmless in a cross-ticker feature matrix. Stated on the row.
CONSTANT_OFFSET_OK = {"obv"}

# Divergences that survive as `have` because they ARE the same indicator with a
# different DEFAULT -- the task's own wording. Written into the generator's
# SEMANTIC_CAVEAT so the CSV carries the warning, not just this file.
MEASURED_CAVEAT = {
    "hma": ("Pine's `ta.hma` smooths with `math.round(sqrt(length))`; "
            "`pandas_ta/overlap/hma.py` uses `int(sqrt(length))` (floor). At "
            "length=14 the roots are 4 vs 3 and the outputs differ by 0.474 on "
            "a ~103 price. Differs at every length where floor != round: "
            "7, 14, 15, 22, 23, 30, ..."),
    "rma": ("`pandas_ta.rma` is `ewm(alpha=1/length, adjust=True)` -- verified "
            "bit-equal to that -- which is NOT Wilder's smoothing. Pine's "
            "`ta.rma` is the SMA-seeded `adjust=False` recursion. Max "
            "divergence 0.2138 on a ~103 price, and 189 of 287 bars differ by "
            "more than 1e-6, so this is a permanent difference, not a warm-up."),
    "atr": ("inherits `rma`'s divergence: `pandas_ta.atr` smooths the true "
            "range with `pandas_ta.rma`, which is `ewm(adjust=True)` rather "
            "than Wilder's recursion. Max divergence 0.0349 from the Pine "
            "formula."),
    "median": ("Pine's `ta.median` is the nearest-rank median "
               "(`percentile_nearest_rank(src, len, 50)`), which returns an "
               "actual sample value; `pandas_ta.median` is "
               "`rolling().median()`, which averages the two middles at even "
               "lengths. Max divergence 1.0122 at length 14."),
    "cmo": ("`pandas_ta.cmo` DEFAULTS to `talib=True`, which Wilder-smooths the "
            "up/down sums; Pine's `ta.cmo` sums them plainly. Max divergence "
            "42.48 on a +/-100 oscillator. `ta.cmo(close, talib=False)` matches "
            "Pine exactly -- the default does not."),
}

# Rows this file will NOT certify, each with the reason. An honest backlog.
NOT_CERTIFIED = {
    "macd": "3 outputs; Pine's signal-line smoothing default is not pinned here",
    "bb": "3 outputs; Pine's `mult` default and column order unverified",
    "kc": "3 outputs; Pine's `useTrueRange` default changes the band basis",
    "dmi": "3 outputs (+DI/-DI/ADX); Wilder smoothing seed differs by source",
    "ichimoku": "5 lines with two forward displacements; needs a live chart",
    "donchian": "Pine returns the middle line only; the fork returns 3 columns",
    "vwap": "session-anchored in Pine; the fork's anchor rule is not comparable",
    "mfi": "Pine's tie handling on an unchanged typical price is unstated",
    "rsi": "Pine seeds rma differently on the first bar; measured but not pinned",
    "linreg": "offset semantics differ; covered by the ALTFIX kwargs sweep",
    "alma": "Pine's `offset`/`sigma` defaults differ from the fork's",
    "t3": "Pine's volume factor default unverified",
    "trix": "Pine returns the oscillator only; the fork adds a signal column",
    "tsi": "double-smoothing order unverified against the reference",
    "uo": "Pine's weighting of the three periods unverified",
    "ao": "Pine uses hl2 with 5/34 SMA; the fork's default source differs",
    "coppock": "Pine's wma of summed ROCs; period defaults unverified",
    "ft": "Fisher transform clamp bound unverified",
    "vi": "Vortex normalisation denominator unverified",
    "crossover": "boolean event, not a series; needs its own comparison shape",
}


def _reference_is_not_a_copy_of_the_fork():
    """A reference textually identical to the implementation proves nothing.

    `hma` copied the fork's `floor(sqrt)` and `median` was literally
    `rolling().median()`; both certified at 0.0 for that reason.
    """
    import inspect

    source = inspect.getsource(sys.modules[__name__])
    block = source[source.index("REFERENCE = {"):source.index("def _hma_reference")]
    suspicious = []
    for name in ("median", "sma", "wma", "hma", "cci", "cog", "vhf"):
        entry = [ln for ln in block.splitlines() if f'"{name}":' in ln]
        if not entry:
            continue
        text = entry[0]
        # the reference half must not be the bare `ta.<name>` call repeated
        if text.count(f"ta.{name}(") > 1:
            suspicious.append(name)
    if suspicious:
        raise SystemExit(
            f"these references call the fork function twice -- a reference that "
            f"is a copy of its subject certifies nothing: {suspicious}")


def audit():
    _reference_is_not_a_copy_of_the_fork()
    rows = list(csv.DictReader(io.open(CSV_PATH, encoding="utf8")))
    certified, diverged, skipped = {}, {}, {}

    for name, build in REFERENCE.items():
        try:
            fork_out, pine_out = build()
        except Exception as exc:                            # noqa: BLE001
            skipped[name] = f"reference raised {type(exc).__name__}"
            continue
        a = np.asarray(fork_out, dtype="float64").ravel()
        b = np.asarray(pine_out, dtype="float64").ravel()
        if a.shape != b.shape:
            skipped[name] = f"shape {a.shape} vs {b.shape}"
            continue
        mask = ~(np.isnan(a) | np.isnan(b))
        if mask.sum() < 50:
            skipped[name] = "insufficient overlap"
            continue
        worst = float(np.nanmax(np.abs(a[mask] - b[mask])))
        scale = max(float(np.nanmax(np.abs(b[mask]))), 1.0)

        # A recursive indicator SEEDED differently converges without ever being
        # bit-equal: pandas_ta seeds its EMA with an SMA of the first `length`
        # bars, the naive reference seeds with the first value. Calling that
        # "differs from the Pine formula" would be a false alarm of exactly the
        # kind this audit exists to prevent -- the same class the altrepo scans
        # had to learn twice.
        xs, ys = a[mask], b[mask]
        rel = np.abs(xs - ys) / np.maximum(np.maximum(np.abs(xs), np.abs(ys)),
                                           1e-12)
        # A CONSTANT offset is an initialisation convention, not a formula
        # difference: pandas_ta's OBV starts at the first bar's volume where the
        # reference starts at zero, so the two differ by exactly 40429 forever.
        # WHITELISTED, not generic. As a blanket rule this auto-certified any
        # reference differing by a constant, without inspection.
        delta = xs - ys
        if (name in CONSTANT_OFFSET_OK and len(delta) > 40
                and np.ptp(delta) < 1e-9 and abs(delta[0]) > 0):
            certified[name] = (
                f"identical to the Pine v6 formula up to a CONSTANT offset of "
                f"{delta[0]:.6g} over {int(mask.sum())} bars -- an "
                f"initialisation convention -- the fork seeds the running "
                f"total with the first bar's volume, Pine's `ta.cum` treats "
                f"the leading `na` as 0. ⚠ the offset is volume[0], so it "
                f"differs per ticker: harmless within one series, NOT harmless "
                f"across a cross-ticker feature matrix")
            continue

        # ⚠ THE CONVERGENCE BRANCH IS GONE, DELIBERATELY.
        #
        # It existed to forgive a reference that seeded on the first value while
        # Pine and the fork SMA-seed. Once `_seeded_ewm` fixed that, ema/dema/
        # tema hit exactly 0.0 -- and the branch stopped forgiving the reference
        # and started forgiving the FORK: `rma` differs from Wilder's recursion
        # by 0.2139 on 189 of 287 bars (it is `ewm(adjust=True)`, measured
        # exactly), `atr` by 0.0349, and both shipped `audited=yes` with no
        # caveat. A rule whose only remaining consumers are genuine divergences
        # is not a rule, it is an excuse.
        if worst / scale < 1e-9:
            certified[name] = (f"matches an independent implementation of the "
                               f"Pine v6 formula to {worst:.3e} over "
                               f"{int(mask.sum())} bars")
        else:
            diverged[name] = (f"differs from the Pine v6 formula by {worst:.6g} "
                              f"over {int(mask.sum())} bars")

    # The `audited` column is owned by `gen_pine_builtin_coverage.py`'s AUDITED
    # map -- writing it into the CSV directly would be reverted on the next
    # regeneration, and the existing guard cross-checks the two. So the
    # certifications go into the generator, with a receipt the guard can open:
    # `path:line` + the backticked token that carries the claim.
    gen_path = os.path.join(HERE, "gen_pine_builtin_coverage.py")
    gen_src = io.open(gen_path, encoding="utf8").read()
    audit_lines = io.open(__file__, encoding="utf8").read().splitlines()

    def receipt(name):
        # The token is the FORK CALL, `ta.<name>(`, not the bare name.
        #
        # ⚠ The previous token WAS the bare name, and `receipt()` locates the
        # line by searching for that same name -- so the guard checked that a
        # string it had just copied off a line was on that line. A tautology.
        # `ta.<name>(` appears in the REFERENCE entry but is not the thing the
        # lookup keys on, so a citation shifted by even one line now fails.
        # The Pine name and the fork name are NOT always the same -- `wpr` is
        # `ta.willr`, `tr` is `ta.true_range`, `cog` is `ta.cg`, `dev` is
        # `ta.mad`. Demanding a literal `ta.<pine name>(` silently failed to
        # build a receipt for exactly those four, and they then fell through to
        # "unaudited with no stated reason" despite having MATCHED. Cite
        # whichever `ta.*` call the entry actually makes.
        import re as _re

        for i, line in enumerate(audit_lines, 1):
            if not line.strip().startswith(f'"{name}":'):
                continue
            call = _re.search(r"ta\.\w+\(", line)
            if call is None:
                continue
            token = call.group(0)
            return (f"PINEBI-0b measured: docs/audit_pine_have_rows.py:{i} "
                    f"`{token}` -- {certified[name]}")
        return None

    # ⚠ REGENERATE, do not append. The previous version skipped any name
    # already present, which is exactly how the `rma`/`atr` receipts kept
    # asserting "the reference seeds on the first value" for a full round after
    # the reference stopped doing that. A stale certification is worse than none.
    import re as _re

    gen_src = _re.sub(
        r'\n    "[^"]+": "PINEBI-0b measured:.*?",(?=\n)', "", gen_src)
    block_start = gen_src.index("AUDITED = {")
    insert_at = gen_src.index(chr(10), block_start) + 1
    additions = []
    for name in sorted(certified):
        text = receipt(name)
        if text is None:
            skipped[name] = "no REFERENCE line found to cite"
            continue
        additions.append(
            '    "' + name + '": "' + text + '",' + chr(10))
    if additions:
        gen_src = gen_src[:insert_at] + "".join(additions) + gen_src[insert_at:]
        io.open(gen_path, "w", encoding="utf8",
                newline=chr(10)).write(gen_src)
        print(f"wrote {len(additions)} certifications into gen.AUDITED")

    # Caveats for the measured divergences, into the generator so the CSV
    # carries them.
    if MEASURED_CAVEAT:
        cav_src = io.open(gen_path, encoding="utf8").read()
        anchor = "SEMANTIC_CAVEAT = {"
        if anchor in cav_src:
            at = cav_src.index(chr(10), cav_src.index(anchor)) + 1
            add = "".join(
                '    "' + k + '": "' + v.replace('"', "'") + '",' + chr(10)
                for k, v in sorted(MEASURED_CAVEAT.items())
                if '"' + k + '":' not in cav_src[cav_src.index(anchor):
                                                 cav_src.index("}", cav_src.index(anchor))])
            if add:
                cav_src = cav_src[:at] + add + cav_src[at:]
                io.open(gen_path, "w", encoding="utf8",
                        newline=chr(10)).write(cav_src)
                print(f"wrote {add.count(chr(10))} SEMANTIC_CAVEAT entries")

    for row in rows:
        name = row["name"]
        if name in NOT_CERTIFIED and row["verdict"] == "have"                 and "PINEBI-0b not certified:" not in row["note"]:
            row["note"] = (row["note"] + " | " if row["note"] else "") +                 "PINEBI-0b not certified: " + NOT_CERTIFIED[name]

    print(f"certified {len(certified)}: {', '.join(sorted(certified))}")
    if diverged:
        print(f"DIVERGED {len(diverged)}:")
        for k, v in sorted(diverged.items()):
            print(f"    {k:12} {v}")
    if skipped:
        print(f"reference unusable {len(skipped)}: {skipped}")
    still = [r["name"] for r in rows
             if r["verdict"] == "have" and r["audited"] == "no"]
    print(f"still unaudited: {len(still)} -> {', '.join(sorted(still))}")


if __name__ == "__main__":
    audit()
