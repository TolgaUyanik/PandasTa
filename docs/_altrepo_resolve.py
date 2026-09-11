# -*- coding: utf-8 -*-
"""ALTFIX-1: ONE way to call a fork function, shared by all three scanners.

Three scanners grew three near-identical resolution paths and they disagreed
about the same fork function: `LINEARREG_SLOPE` shipped `have` from the TA-Lib
scan while `linregslope` shipped `port` from the classic one. That is not a
disagreement about pandas_ta; it is two probes with different blind spots.

**The recurring defect this module exists to kill.** Eight indicators were
published as ABSENT while the fork ships them, across three review rounds. Every
single one had the same cause: the probe called fork functions in exactly one
narrow way, so anything reachable another way looked missing.

    round 1  ad adosc mom roc pvt massi donchian pvo    (wrong acronym guess)
    round 1  CORREL                                     (two-series signature)
    round 2  TimeSeriesForecast VolumeRateOfChange      (kwargs / volume input)
    round 2  LINEARREG_ANGLE LINEARREG_SLOPE            (kwargs)
    round 3  linregslope linregangle correl             (all of the above)

So a resolution attempt here is a CARTESIAN sweep, not a single call: every
declared kwargs variant x the default and pinned window. Whatever a scanner
wants to claim about absence, it claims after this has run.

`resolve_fork` is the only entry point. `probe_variants` is what a gap guard
re-runs to prove a `port` verdict rather than trusting a list of names somebody
already caught.
"""
import inspect
import warnings

import numpy as np

# Fork-side parameterisations that COLLAPSE one indicator into another. Without
# these the surface sweep is two default calls per function, which is how
# `stochf` -- `ta.stoch(smooth_k=1)`, identical on all 247 values -- was
# published as absent. False gap #10, and the tenth with the same cause.
#
# Keyed by fork function name. Each entry is tried IN ADDITION to the default.
SURFACE_KWARGS = {
    # Raw/unsmoothed ease of movement: classic's `emv` has neither parameter,
    # so the fork only meets it with the smoothing off AND the 100,000,000
    # divisor out of the way.
    "eom": [{"divisor": 1}],
    "stoch": [{"smooth_k": 1}],                 # fast stochastic
    "linreg": [{"slope": True}, {"intercept": True}, {"tsf": True},
               {"angle": True, "degrees": True}],
    "decay": [{"mode": "exp"}],
    "cmo": [{"talib": False}],                  # unsmoothed, the Pine form
    "rsi": [{"talib": False}],
    "willr": [{"talib": False}],
    "supertrend": [{"multiplier": 3.0}],
    "macd": [{"asmode": True}],
    "psar": [{"af0": 0.02}],
    "adx": [{"lensig": 14}],
    # `ta.dm`'s mamode is a NO-OP while TA-Lib is installed (`mode_tal`
    # defaults True), so the only kwarg that changes its behaviour is
    # `talib=False` -- and without it `plus_dm`/`minus_dm` were published as
    # flatly ABSENT while the fork ships `DMP_14`/`DMN_14`.
    "dm": [{"talib": False}, {"talib": False, "mamode": "rma"}],
    "atr": [{"talib": False}, {"percent": True}],
    "natr": [{"talib": False}],
    "stochrsi": [{"talib": False}],
    "ppo": [{"talib": False}],
    "apo": [{"talib": False}],
    "bbands": [{"ddof": 0}],
}

# The window pinned when comparing like-for-like. Both sides see the SAME
# number; which number it is does not matter, only that they agree.
PINNED_LENGTH = 14

# Parameter name -> which probe column feeds it.
SERIES_PARAMS = {
    "open": "open", "open_": "open", "high": "high", "low": "low",
    "close": "close", "volume": "volume", "source": "close",
    "source_a": "close", "series": "close", "trend": "close",
}
# A genuine SECOND series. Feeding the same column twice makes
# `correlation(x, x)` identically 1.0 and hides the real answer.
SECOND_SERIES_PARAMS = {"source_b", "close2", "other", "series_b",
                        "benchmark"}   # pandas-ta-classic's correl/beta


def fork_signature_kind(fn):
    """-> ('two-series' | 'series' | 'none'), for reporting why a probe failed."""
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return "none"
    if any(p in SECOND_SERIES_PARAMS for p in params):
        return "two-series"
    if any(p in SERIES_PARAMS for p in params):
        return "series"
    return "none"


def call_fork(fn, frame, kwargs=None, length=None, input_override=None):
    """Call `fn` with the probe frame. Returns None when it cannot be driven.

    `input_override` redirects the PRIMARY series -- `roc` is the Volume Rate of
    Change when fed volume, which is how `VolumeRateOfChange` came to be
    published as absent.
    """
    if fn is None or not callable(fn):
        return None
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return None

    call = {}
    for pname in params:
        if pname in SECOND_SERIES_PARAMS:
            call[pname] = frame["open"]
        elif pname in SERIES_PARAMS:
            column = SERIES_PARAMS[pname]
            if input_override and pname in ("close", "source", "source_a"):
                column = input_override
            call[pname] = frame[column]
    if not call:
        return None

    extra = dict(kwargs or {})
    if length is not None:
        # The window parameter is not always called `length`. classic's
        # `stochf` takes `fastk`, the fork's `stoch` takes `k`, TA-Lib takes
        # `timeperiod` -- so pinning only `length` left those pairs compared at
        # two different windows forever. That is how `stochf` survived as a
        # false gap even after the kwargs sweep landed.
        for window_param in ("length", "k", "fastk", "period", "timeperiod",
                             "window"):
            if window_param in params and window_param not in extra:
                extra[window_param] = length
                break
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            np.seterr(all="ignore")
            return fn(**call, **extra)
    except Exception:                                       # noqa: BLE001
        return None


def surface_variants(fork_name):
    """The declared kwargs variants for a fork function, plus its default."""
    return list(SURFACE_KWARGS.get(fork_name, [])) + [None]


def probe_variants(fn, frame, kwargs_variants=None, input_override=None,
                   fork_name=None):
    """Every way this scanner knows how to call `fn`, as (label, output).

    A `port` verdict means NONE of these reproduced the alt-repo output. That is
    a much stronger claim than "the default call did not match", and it is the
    claim the gap guards re-run.
    """
    out = []
    variants = list(kwargs_variants or [])
    # A surface probe with no declared variants was the bug: two default calls
    # backing an absence claim. When the caller names the fork function, its
    # declared collapsing kwargs are swept too.
    if fork_name:
        for extra in SURFACE_KWARGS.get(fork_name, []):
            if extra not in variants:
                variants.append(extra)
    if None not in variants:
        variants.append(None)
    for kwargs in variants:
        for length in (None, PINNED_LENGTH):
            value = call_fork(fn, frame, kwargs=kwargs, length=length,
                              input_override=input_override)
            if value is None:
                continue
            label = (f"kwargs={kwargs or '{}'}"
                     f"{'' if length is None else f', length={length}'}"
                     f"{'' if not input_override else f', input={input_override}'}")
            out.append((label, value))
    return out


def fork_surface_cache(frame, surface, module, input_overrides=("volume",),
                       extra_lengths=(1, 5, 30)):
    """Every probed variant of every fork function, as {name: [outputs]}.

    THE single search surface. Three scanners and the verifier each had their
    own; two of them pinned only the literal parameter name `length` and one
    carried a verbatim copy of SERIES_PARAMS missing the two-series path. A
    surface that differs between the scanner and its guard means the guard
    cannot see what the scanner missed.

    `input_overrides` sweeps the primary series too -- `roc` IS the volume rate
    of change when fed volume, which is how `VolumeRateOfChange` was published
    as absent.
    """
    out = {}
    for name in sorted(surface):
        fn = getattr(module, name, None)
        if fn is None or not callable(fn):
            continue
        for _label, value in probe_variants(fn, frame, fork_name=name):
            out.setdefault(name, []).append(value)
        # The alt-repo side has its OWN defaults -- TA-Lib's STOCHF is fastk=5,
        # classic's stochf is 5, TA-Lib's CORREL is 30 -- so a surface probed
        # only at {default, 14} can never meet them.
        #
        # `1` is in that sweep for a whole CLASS, not one name: where the fork
        # ships the SMOOTHED form of an indicator and the alt-repo ships the
        # RAW one, the counterpart is the fork function at length=1. Classic's
        # `emv` takes no `length` at all and is exactly `ta.eom(length=1,
        # divisor=1)` -- Spearman +1.000000, max affine residual 5.42e-20 over
        # 259 bars -- yet it shipped as "genuinely absent" because the surface
        # started at 5. At length=14 the two correlate +0.21, so no threshold
        # on the default probe could ever have rescued it.
        for length in extra_lengths:
            for kwargs in surface_variants(name):
                value = call_fork(fn, frame, kwargs=kwargs, length=length)
                if value is not None:
                    out.setdefault(name, []).append(value)
        for column in input_overrides:
            value = call_fork(fn, frame, input_override=column)
            if value is not None:
                out.setdefault(name, []).append(value)
    return out


def validate_alias_targets(alias_map, surface, where):
    """An alias is a claim of equivalence. An unresolvable one once fabricated a
    `have` with a note claiming "reachable as df.ta.abs()"."""
    missing = sorted({v for v in alias_map.values() if v not in surface})
    if missing:
        raise SystemExit(
            f"{where}: alias targets that do not exist on the fork surface: "
            f"{missing}. An unresolvable alias silently became a verdict once."
        )
