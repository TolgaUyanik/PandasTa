# -*- coding: utf-8 -*-
"""Regenerate docs/IndicatorDictionary.md.

Probes every indicator in the live package on a synthetic OHLCV series and writes the
observed column names, ML form (scale-free / price-level / binary / ordinal), warm-up
bars, signature, and docstring summary as one markdown table per category.

Usage:  python docs/gen_indicator_dictionary.py [docs/IndicatorDictionary.md]
"""
import inspect, warnings, sys, datetime, re
from pathlib import Path
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas_ta as ta

N = 600
SCALE = 137.0
rng = np.random.default_rng(7)


def make_df(level=100.0):
    ret = rng.normal(0, 0.012, N)
    close = level * np.exp(np.cumsum(ret))
    spread = close * np.abs(rng.normal(0, 0.006, N))
    high = close + spread
    low = close - spread
    openp = close * (1 + rng.normal(0, 0.004, N))
    high = np.maximum.reduce([high, openp, close])
    low = np.minimum.reduce([low, openp, close])
    vol = rng.integers(1e5, 1e6, N).astype(float)
    idx = pd.date_range("2022-01-03", periods=N, freq="B")
    return pd.DataFrame({"open": openp, "high": high, "low": low,
                         "close": close, "volume": vol}, index=idx)


df1 = make_df(100.0)
df2 = df1.copy()
for c in ("open", "high", "low", "close"):
    df2[c] = df2[c] * SCALE

PRICE_ARGS = {"open_": "open", "open": "open", "high": "high", "low": "low",
              "close": "close", "volume": "volume"}


def call(fn, d):
    sig = inspect.signature(fn)
    kw = {}
    for name, p in sig.parameters.items():
        if p.kind == p.VAR_KEYWORD:
            continue
        if name in PRICE_ARGS:
            kw[name] = d[PRICE_ARGS[name]]
        elif p.default is inspect.Parameter.empty:
            # required non-price arg (e.g. trend series, benchmark)
            if name in ("trend",):
                kw[name] = (d["close"] > d["close"].rolling(20).mean()).astype(int)
            elif name in ("series_a", "a"):
                kw[name] = d["close"]
            elif name in ("series_b", "b"):
                kw[name] = d["close"].rolling(10).mean()
            elif name in ("benchmark", "bench_close"):
                kw[name] = d["close"].rolling(5).mean()
            elif name == "value":
                kw[name] = float(d["close"].mean())
            else:
                kw[name] = d["close"]
    return fn(**kw)


def as_frame(res):
    if res is None:
        return None
    if isinstance(res, tuple):
        parts = [as_frame(r) for r in res]
        parts = [p for p in parts if p is not None]
        if not parts:
            return None
        f = pd.concat(parts, axis=1)
        return f.loc[:, ~f.columns.duplicated()]
    if isinstance(res, pd.Series):
        return res.to_frame(name=res.name if res.name is not None else "VALUE")
    if isinstance(res, pd.DataFrame):
        return res.loc[:, ~res.columns.duplicated()]
    return None


def classify(col1, col2):
    """price | scale-free | binary | ordinal | unknown"""
    v1 = pd.to_numeric(col1, errors="coerce").astype(float)
    v2 = pd.to_numeric(col2, errors="coerce").astype(float)
    a = v1.dropna()
    if a.empty:
        return "empty", None, None
    uniq = set(np.unique(np.round(a.values, 9)))
    if len(uniq) == 1:
        # One value across the whole probe series. Folding this into "binary"
        # (because {0.0} is a subset of {0, 1}) is how two provably dead fvg
        # columns were recommended as feed-ready.
        warm = int(v1.isna().values.argmin()) if v1.isna().any() else 0
        return "constant", warm, (float(a.min()), float(a.max()))
    kind = None
    if uniq <= {0.0, 1.0} or uniq <= {-1.0, 0.0, 1.0} or uniq <= {0.0, -1.0}:
        kind = "binary"
    elif len(uniq) <= 12 and all(float(u).is_integer() for u in uniq):
        kind = "ordinal"
    m = v1.notna() & v2.notna() & (v1.abs() > 1e-9)
    scale = "unknown"
    if m.sum() >= 20:
        r = float(np.nanmedian((v2[m] / v1[m]).values))
        if abs(r - SCALE) / SCALE < 0.02:
            scale = "price"
        elif abs(r - 1.0) < 0.02:
            scale = "scale-free"
        elif abs(r - SCALE ** 2) / SCALE ** 2 < 0.05:
            scale = "price^2"
        else:
            scale = f"other(x{r:.3g})"
    if kind in ("binary", "ordinal"):
        scale = kind
    warm = int(v1.isna().values.argmin()) if v1.isna().any() else 0
    if v1.notna().sum() == 0:
        warm = -1
    return scale, warm, (float(a.min()), float(a.max()))


def summary(fn):
    doc = inspect.getdoc(fn) or ""
    if not doc:
        mod = inspect.getmodule(fn)
        doc = (inspect.getdoc(mod) or "") if mod else ""
    lines = doc.splitlines()
    if not lines:
        return "", ""
    title = lines[0].strip()
    body = []
    for ln in lines[1:]:
        s = ln.strip()
        if s.endswith(":") and s.split()[0] in ("Sources", "Calculation", "Args", "Kwargs", "Returns", "Note", "Notes"):
            break
        if s:
            body.append(s)
        elif body:
            break
    return title, " ".join(body)


cats = {}
for cat, names in ta.Category.items():
    cats[cat] = list(names)
extra = {"performance": ["drawdown"], "volume": ["vp"]}
SKIP = {"ma"}  # moving-average dispatcher, not an indicator
for c, ns in extra.items():
    for n in ns:
        if n not in cats.get(c, []):
            cats.setdefault(c, []).append(n)

dfx = pd.DataFrame()
out = {}
for cat, names in cats.items():
    out[cat] = {}
    for name in sorted(names):
        if name in SKIP:
            continue
        fn = getattr(ta, name, None)
        if fn is None or not callable(fn):
            out[cat][name] = {"error": "not exported"}
            continue
        title, desc = summary(fn)
        sig = str(inspect.signature(fn))
        rec = {"title": title, "desc": desc, "signature": sig,
               "ext": hasattr(dfx.ta, name), "cols": [], "error": None}
        try:
            r1 = as_frame(call(fn, df1.copy(deep=True)))
            r2 = as_frame(call(fn, df2.copy(deep=True)))
            if r1 is None:
                rec["error"] = "no frame/series returned"
            else:
                for c in r1.columns:
                    if r2 is not None and c in r2.columns:
                        scale, warm, rng_ = classify(r1[c], r2[c])
                    else:
                        scale, warm, rng_ = "unknown", None, None
                    rec["cols"].append({"name": str(c), "scale": scale,
                                        "warmup": warm, "range": rng_})
        except Exception as e:
            rec["error"] = f"{type(e).__name__}: {e}"
        out[cat][name] = rec

TAG = {"scale-free": "SF", "price": "PX", "price^2": "PX2", "binary": "BIN",
       "ordinal": "ORD", "constant": "CONST", "empty": "??", "unknown": "??"}

# Columns that are NOT causal at default parameters. Keyed by indicator; the value is
# (column-name predicate, why).
LEAK_RULES = {
    "ichimoku": (lambda c: c.startswith("ICS_"),
                 "Chikou span = `close.shift(-kijun)`: it reports the future. Drop this column, "
                 "or use `ichimoku_ml`, which reconstructs the same idea causally."),
    "dpo": (lambda c: True,
            "Default `centered=True` shifts the future into the present. Pass `centered=False`."),
}


def leaks(name, col):
    rule = LEAK_RULES.get(name)
    return bool(rule and rule[0](col))


CAT_ORDER = ["candles", "cycles", "momentum", "overlap", "performance",
             "statistics", "trend", "volatility", "volume"]

PRICE_ARGS = {"open_", "open", "high", "low", "close", "volume"}


def tag(scale):
    if scale.startswith("other"):
        return "??"
    return TAG.get(scale, "??")


def params(sig):
    inner = sig[sig.index("(") + 1: sig.rindex(")")]
    parts, depth, cur = [], 0, ""
    for ch in inner:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip()); cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    keep = []
    for p in parts:
        nm = p.split(":")[0].split("=")[0].strip()
        if nm in PRICE_ARGS or nm.startswith("**") or nm == "offset":
            continue
        p = re.sub(r":\s*[^=]+=", "=", p)          # drop type annotations
        keep.append(p.replace(" ", ""))
    return ", ".join(f"`{k}`" for k in keep) if keep else "—"


def desc(rec, limit=150):
    d = rec.get("desc") or rec.get("title") or ""
    d = re.sub(r"\s+", " ", d).strip()
    if len(d) > limit:
        d = d[:limit].rsplit(" ", 1)[0] + "…"
    return d.replace("|", "/")


def inputs(sig):
    got = [a for a in ("open", "high", "low", "close", "volume")
           if re.search(rf"[(,]\s*{a}_?\s*[=:,)]", sig)]
    return "/".join(g[0] for g in got).upper() or "close"


out_path = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parent / "IndicatorDictionary.md")
lines = []
A = lines.append
today = datetime.date.today().isoformat()

A("# Indicator Dictionary")
A("")
A("Every indicator in this fork: inputs, parameters, the exact columns it emits, the")
A("**ML form** of each column, and its warm-up cost. Generated by probing the live")
A(f"package on a synthetic 600-bar OHLCV series (probe run {today}) — column names and")
A("forms below are observed, not transcribed.")
A("")
A("See [README](../README.md) for the ML feature rules this table serves.")
A("")
A("## How to read the ML form tag")
A("")
A("| tag | meaning | feed to a model? |")
A("|---|---|---|")
A("| `SF` | scale-free — value did not change when the price series was multiplied by 137 | yes, directly |")
A("| `PX` | price level — value scaled 1:1 with price | **no** — convert to a relation first, e.g. `(close - col) / close` |")
A("| `PX2` | price squared — scaled with price² (variance-like) | no — take a root or normalize by price² |")
A("| `BIN` | binary / sign, values in {-1, 0, 1} | yes, as a flag |")
A("| `ORD` | small integer set (counts, states) | yes, as ordinal or one-hot |")
A("| `CONST` | **one value across the whole probe series** — the column never fires | **no** — it carries no information; check the indicator before using it |")
A("| `??` | no value produced on the synthetic probe series (event-driven column), or a mixed form | inspect on real data before using |")
A("")
A("Warm-up = index of the first non-NaN value on the probe series at default parameters.")
A("It scales with `length`, so treat it as a floor, not a constant. Drop the warm-up")
A("window per ticker before concatenating tickers.")
A("")
A("`*(standalone)*` after an indicator name = it has NO `df.ta.<name>()` method, so it is")
A("invisible to `ta.Strategy`; call `ta.<name>(...)` and join the result yourself.")
A("")

# ---- summary counts
tot = sum(len(v) for v in out.values())
broken_now = [n for cat in CAT_ORDER for n, r in out.get(cat, {}).items() if r.get("error")]
if broken_now:
    A(f"**{tot} indicators** probed; {len(broken_now)} raise on this environment "
      f"(pandas 2.x) -- see [Known breaks](#known-breaks).")
else:
    A(f"**{tot} indicators** probed. All of them call cleanly on this environment "
      f"(pandas {pd.__version__}).")
A("")

for cat in CAT_ORDER:
    recs = out.get(cat, {})
    if not recs:
        continue
    A(f"## {cat} ({len(recs)})")
    A("")
    A("| indicator | inputs | params (defaults) | outputs — ML form | warm-up | what it measures |")
    A("|---|---|---|---|---|---|")
    for name in sorted(recs):
        r = recs[name]
        if r.get("error") and not r.get("cols"):
            A(f"| `{name}` | — | — | ⚠ {r['error'][:60]} | — | {desc(r, 90)} |")
            continue
        cols = r.get("cols", [])
        cell = "<br>".join(
            f"`{c['name']}` {tag(c['scale'])}" + (" **LEAK**" if leaks(name, c["name"]) else "")
            for c in cols) or "—"
        warms = [c["warmup"] for c in cols if isinstance(c["warmup"], int) and c["warmup"] >= 0]
        warm = str(max(warms)) if warms else "—"
        ext = "" if r.get("ext") else " *(standalone)*"
        A(f"| `{name}`{ext} | {inputs(r['signature'])} | {params(r['signature'])} | {cell} | {warm} | {desc(r)} |")
    A("")

# ---- ML shortlists
A("## Feed-ready shortlist")
A("")
A("Indicators whose every column is `SF`, `BIN`, or `ORD` — no transformation needed.")
A("")
ready, needs = [], []
for cat in CAT_ORDER:
    for name, r in sorted(out.get(cat, {}).items()):
        cols = r.get("cols") or []
        if not cols:
            continue
        tags = {tag(c["scale"]) for c in cols}
        if tags <= {"SF", "BIN", "ORD"} and "CONST" not in tags:
            ready.append(name)
        elif "PX" in tags or "PX2" in tags:
            needs.append((name, [c["name"] for c in cols if tag(c["scale"]) in ("PX", "PX2")]))
A(" ".join(f"`{n}`" for n in ready))
A("")

# ---- columns that cannot fire at all
dead = [(name, [c["name"] for c in (r.get("cols") or []) if tag(c["scale"]) == "CONST"])
        for cat in CAT_ORDER for name, r in sorted(out.get(cat, {}).items())
        if any(tag(c["scale"]) == "CONST" for c in (r.get("cols") or []))]
if dead:
    A("## Never fires on the probe")
    A("")
    A("One value across the whole probe series. A column that cannot fire is worse than an")
    A("absent one: it looks like a feature, occupies a slot, and the miner can match on it.")
    A("Confirm on real data, then repair or delete the column.")
    A("")
    A("| indicator | column(s) | owning task |")
    A("|---|---|---|")
    DEAD_TASKS = {"fvg": "FVGDEAD in `TODO.md` — the zone is evicted on the bar that "
                         "creates it (`pandas_ta/trend/fvg.py:46`, `:54`)"}
    for name, cols in dead:
        A(f"| `{name}` | {' '.join(f'`{c}`' for c in cols)} | {DEAD_TASKS.get(name, '— unregistered, file one')} |")
    A("")

A("## Needs a transform before modelling")
A("")
A("These emit at least one absolute price level. Convert each `PX` column to a distance,")
A("ratio, or z-score against `close` (or drop it and keep the indicator's `SF` columns).")
A("")
A("| indicator | price-level columns |")
A("|---|---|")
for n, cs in needs:
    A(f"| `{n}` | {' '.join('`%s`' % c for c in cs)} |")
A("")

A("## Leak watchlist")
A("")
A("Columns that are **not** causal at default parameters. Everything else in this file was")
A("written to read only bars `<= T`; these are the documented exceptions.")
A("")
A("| indicator | column | why |")
A("|---|---|---|")
for cat in CAT_ORDER:
    for name, r in sorted(out.get(cat, {}).items()):
        rule = LEAK_RULES.get(name)
        if not rule:
            continue
        hit = [c["name"] for c in r.get("cols", []) if rule[0](c["name"])] or ["(all)"]
        for c in hit:
            A(f"| `{name}` | `{c}` | {rule[1]} |")
A("")

A("## Known breaks")
A("")
BREAK_NOTES = {
    "mcgd": "`Series.append` was removed in pandas 2.0; port the line to `pd.concat`.",
    "aberration": "Import-order bug: `pandas_ta.overlap.sma` resolves to the submodule, "
                  "not the function, at the time `aberration` is imported. Broken on every call.",
}
brk = [(n, r["error"]) for cat in CAT_ORDER for n, r in sorted(out.get(cat, {}).items())
       if r.get("error")]
if brk:
    A("Observed while probing on pandas 2.3.3 / numpy 2.x:")
    A("")
    A("| indicator | failure | note |")
    A("|---|---|---|")
    for n, e in brk:
        A(f"| `{n}` | `{e[:90]}` | {BREAK_NOTES.get(n, '')} |")
else:
    A("None. Every registered indicator was probed and returned data on "
      f"pandas {pd.__version__} / numpy {np.__version__}.")
    A("")
    A("Previously broken and now fixed (WIRING, 2026-09-07): `mcgd` "
      "(`Series.append`, removed in pandas 2.0), `aberration`, `zlma` (every "
      "`mamode`) and `ui` (`everget=True`) -- the last three all bound a "
      "SUBMODULE where a function of the same name was meant, and raised "
      "`TypeError: 'module' object is not callable` on every call.")
A("")
A("## Not indicators")
A("")
A("| callable | what it is |")
A("|---|---|")
A("| `ta.ma(name, source, **kwargs)` | moving-average dispatcher — returns the named MA (`dema`, `ema`, `fwma`, `hma`, `linreg`, `midpoint`, `pwma`, `rma`, `sinwma`, `sma`, `swma`, `t3`, `tema`, `trima`, `vidya`, `wma`, `zlma`). Used internally by every `mamode` kwarg. |")
A("| `ta.above` `ta.above_value` `ta.below` `ta.below_value` `ta.cross` | comparison helpers returning 0/1 series — building blocks for rules and labels. |")
A("| `ta.cagr` `ta.calmar_ratio` `ta.downside_deviation` `ta.jensens_alpha` `ta.log_max_drawdown` `ta.max_drawdown` `ta.pure_profit_score` `ta.sharpe_ratio` `ta.sortino_ratio` `ta.volatility` | performance metrics — take a close series, return a single `float`. Not features. |")
A("")

A("## Regenerating this file")
A("")
A("This document is generated, not hand-maintained. Re-probe after adding or changing an")
A("indicator so the column names, forms, and warm-ups stay true:")
A("")
A("```sh")
A("python docs/gen_indicator_dictionary.py docs/IndicatorDictionary.md")
A("```")
A("")

open(out_path, "w", encoding="utf8").write("\n".join(lines) + "\n")
print("wrote", out_path, len(lines), "lines")
