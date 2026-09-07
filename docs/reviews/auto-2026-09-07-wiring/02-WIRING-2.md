# WIRING-2 — `aberration`'s import bound a module, not a function

Status: **PASS** (3 review rounds). Files: `pandas_ta/volatility/aberration.py`,
`pandas_ta/overlap/zlma.py`, `pandas_ta/volatility/ui.py`, `tests/test_wiring_accessors.py`.

## The defect

`from pandas_ta.overlap import hlc3, sma` binds `sma` to the **submodule** while pandas_ta is still
importing itself, so `aberration.py` raised `TypeError: 'module' object is not callable` on every
call. Fixed by importing from the module that defines the function:
`from pandas_ta.overlap.sma import sma`.

## Round 1 — REVISE, and the finding that mattered

> **MAJOR** — WIRING-2 patched exactly one instance of a class of bug and declared victory. I
> instrumented the import and confirmed the diagnosis is right — but so are the imports in two other
> shipped modules, and they are still live: `ta.zlma(close, mamode="sma")` raises today (same for
> rma/wma/linreg/swma/hma), and `ta.ui(close, everget=True)` raises the identical TypeError.

Verified independently before acting — both reproduced. A package-wide scan found **11 shadowed
bindings across exactly 2 modules**: `overlap/zlma.py` (10 of its 12 helpers) and `volatility/ui.py`.
Both converted to per-submodule imports; all 12 `zlma` mamodes and `ui(everget=True)` now work.

The guard is `test_no_module_shadows_a_function_name_anywhere_in_the_package`, which walks
`sys.modules` for module-typed attributes shadowing a callable — the class, not the instance.
Round 3 verified it fires on an injected offender.

## Rounds 2-3

> **MINOR** (round 1) — the subprocess test's docstring gives a false rationale ("an in-process test
> can pass on import order alone"), and asserts one substring where the criterion says four columns.

Correct: the binding is decided once at `import pandas_ta`; no test can rebind it afterwards.
Docstring rewritten to claim only what the subprocess buys (isolation from an installed copy), and
`test_aberration_returns_its_four_columns_in_a_fresh_interpreter` now asserts the exact list
`ABER_ZG_5_15, ABER_SG_5_15, ABER_XG_5_15, ABER_ATR_5_15`.

Round 3 verified the fresh-interpreter tests and the shadow scan bind, and raised no new finding
against this task.

## Verification

- `ta.aberration(h, l, c)` returns its 4 columns as the first call in a fresh interpreter.
- `ta.zlma(c, mamode=m)` works for all 12 mamodes; `ta.ui(c, everget=True)` returns `UIe_14`.
- Package scan: 0 shadowed bindings remain.
