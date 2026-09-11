# -*- coding: utf-8 -*-
"""Shared internals for the CANDLE-1 chart-pattern shape matchers.

NOT an indicator module. The leading underscore is load-bearing: every
`pandas_ta/<category>/<name>.py` is expected to define one public function
named after the file, and this file defines none. It exists because
`head_shoulders`, `triple_top_bottom` and `triangle_wedge` are three matchers
over ONE pivot stream, and copying that stream three times is how the
`_confirm_pivots` triplication in `zigzag_fib` / `swing_equilibrium` / `dtdb`
happened. `dtdb` already broke the self-contained-module convention by
importing `_confirm_pivots` from `zigzag_fib`; this follows that precedent and
names it.

What lives here:

  `_validated_int` / `_validated_float`  -- the nan/inf/bool rejection
      discipline used verbatim by `atr_push`, `sd_zone_pro` and `dtdb`.
  `_pivot_stream`  -- the alternating confirmed-pivot list. This is the same
      code CANDLE-0's throwaway probe ran
      (`../Backtesting/scripts/analysis/measure_chart_patterns_overlap_full.py`,
      `_pivot_stream`), so the shipped modules and the document that decided
      to build them share one definition of a pivot.
  `_line_at`  -- linear interpolation of a two-point boundary.

CAUSALITY, the one property everything here rests on: `_confirm_pivots` makes
a pivot at bar `i` visible at bar `i + right` and never earlier, and
`_pivot_stream` carries `confirm_bar` alongside `pivot_bar` so a caller can
gate on it. Every matcher in this family iterates bars forward and consumes a
pivot only once `confirm_bar <= T`. Pinned by the future-perturbation mutant
tests in `tests/test_candle1_patterns.py`, not by prefix truncation, which
`CLAUDE.md` Gate B says cannot see back-dating.
"""
import numpy as np

from pandas_ta.trend.zigzag_fib import _confirm_pivots


def _validated_int(value, default, name, positive=True):
    """None -> default (a documented default, not bad input). Anything else
    must be a genuine, finite, integral value, or raise."""
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an int, got bool {value!r}")
    if isinstance(value, float):
        if value != value:
            raise ValueError(f"{name} must be a finite int, got NaN")
        if np.isinf(value):
            raise ValueError(f"{name} must be a finite int, got inf")
        if not value.is_integer():
            raise ValueError(f"{name} must be an integral value, got {value}")
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be an int, got {value!r}")
    if positive and value <= 0:
        raise ValueError(f"{name} must be a positive int, got {value}")
    if not positive and value < 0:
        raise ValueError(f"{name} must be a non-negative int, got {value}")
    return value


def _validated_float(value, default, name, positive=True):
    """Same nan/inf discipline as `_validated_int`, float variant."""
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a float, got bool {value!r}")
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a float, got {value!r}")
    if value != value:
        raise ValueError(f"{name} must be finite, got NaN")
    if np.isinf(value):
        raise ValueError(f"{name} must be finite, got inf")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")
    if not positive and value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}")
    return value


def _pivot_stream(high, low, left, right):
    """Alternating confirmed-pivot list: `(confirm_bar, pivot_bar, price, kind)`.

    `kind` is `+1` for a swing high, `-1` for a swing low. Consecutive
    same-direction pivots collapse: the more extreme one REPLACES the previous
    entry (replace-if-more-extreme, the same rule `zigzag_fib` and `dtdb` use),
    so the returned list strictly alternates.

    The list is sorted by `confirm_bar` and the collapse is applied in that
    order, so the prefix of the list with `confirm_bar <= T` is exactly what a
    bar-`T` observer could have known. That is the whole causality argument and
    it is what the mutant tests perturb.

    A same-bar tie (a high and a low both confirming at bar `j`) is ordered
    HIGH BEFORE LOW, because `sort()` on the 4-tuple breaks the `confirm_bar`
    tie on `pivot_bar` (equal), then on `price` (the high is larger). That is
    an accident of the tuple layout in CANDLE-0's probe and is preserved
    deliberately so the shipped modules reproduce the measured fire rates.
    """
    ph, _ = _confirm_pivots(high, left, right)
    _, pl = _confirm_pivots(low, left, right)
    ph, pl = ph.to_numpy(dtype=float), pl.to_numpy(dtype=float)
    ev = []
    for j in range(len(ph)):
        if ph[j] == ph[j]:
            ev.append((j, j - right, ph[j], 1))
        if pl[j] == pl[j]:
            ev.append((j, j - right, pl[j], -1))
    ev.sort()
    out = []
    for e in ev:
        if out and out[-1][3] == e[3]:
            if (e[3] == 1 and e[2] > out[-1][2]) or \
               (e[3] == -1 and e[2] < out[-1][2]):
                out[-1] = e
        else:
            out.append(e)
    return out


def _line_at(x1, y1, x2, y2, x):
    """Value at `x` of the line through `(x1, y1)` and `(x2, y2)`.

    A vertical pair returns `y2` rather than dividing by zero. That case is
    unreachable from a pivot stream (two pivots cannot share a bar and survive
    the alternation collapse) but is kept because the guard is cheap and its
    absence would be a silent `ZeroDivisionError` if a caller ever changed.
    """
    if x2 == x1:
        return y2
    return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
