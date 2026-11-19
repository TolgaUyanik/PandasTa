# auto run — 2026-11-16 — j-wae

`/brutally-honest-review --auto "J-WAE: port the indicator of issue #123
through Gates A-D, the wiring, the tests and docs/<Name>Measured.md, per the
issue and the rules in your system prompt (Waddah Attar Explosion:
MACD-change power over Bollinger width. Source: jesse (MIT) —
`waddah_attar_explosion.py: t1 = (MACD20/40 - MACD20/40[1])*150, e1 = BB20,2
upper - lower`.). Gate E and the suites are run by the launcher afterwards."`

**Mode C** (batch task execution): the argument is a free-form TASK, not a
plan file, so there is no Mode D pre-gate — Mode C resolves tasks, which do
not carry load-bearing reasoning the way a plan does. One task.

## Phase 1 — the task

| id | scope | source |
|---|---|---|
| `j-wae` | port jesse's Waddah Attar Explosion power as `j_wae`, Gates A–D, five wiring touch points, tests, `docs/JWaeMeasured.md` | PandasTa issue #123, quoted verbatim in the session's system prompt |

Run folder: `docs/reviews/auto-2026-11-16-j-wae/`.

## Phase 2 — clarifications

`AskUserQuestion` is **unavailable** in this headless session, and the
system prompt says: *where a skill says to ask, take the most conservative
reading (the smaller scope) and log it as an ASSUMPTION*. So no questions
were asked, and every open choice is below with the reading taken.

### ASSUMPTIONS

1. **ONE column, not jesse's three.** jesse's indicator carries an
   explosion line and a dead zone beside the power. The issue quotes only
   `t1`/`e1` and names one scale-free conversion ("t1 / e1 (both price
   units)"), and the screen measured one column. Smaller scope wins: one
   column, `J_WAE_150_20_40_20_2.0`.
2. **Category = `momentum`.** The column is a MACD displacement normalised
   by a volatility; the issue gives no category. `momentum` is where the
   fork keeps `j_acosc` and `j_gator`, the other jesse ports of the same
   shape. (`volatility` was the alternative; the numerator, not the
   divisor, is what the column is about.)
3. **Constants, not parameters.** 150 / 20 / 40 / 20 / 2.0 are module
   constants. The issue quotes exactly those, the screen measured exactly
   those, and `docs/gate_e_ledger.py record` refuses a run taken at
   non-default parameters. A `fast=`/`slow=` surface would ship
   combinations nothing has measured.
4. **`EMA` means the SMA-seeded EMA** (this fork's `ema`, TA-Lib's), not
   the screen prototype's seedless `ewm`. The issue says Gate A starts
   from the SOURCE FORMULA, not the prototype. The gap is measured rather
   than assumed small (§A4) — it is large and does not wash out, so the
   screen's Gate E band is explicitly treated as describing a neighbouring
   column.
5. **`e1` is the LITERAL band subtraction**, `(mid + dev) - (mid - dev)`,
   not the algebraic `2 * MULT * sd`. The issue writes "BB20,2 upper -
   lower". The difference is measured (§A6), not asserted to be nil.
6. **The EMA is imported; the width is spelled from the issue.** The
   module takes `ema` from its own module, `from pandas_ta.overlap.ema
   import ema`, the form `CLAUDE.md` prescribes and ten other momentum
   modules already use (`trix`, `stc`, `pfe`, `ewmac`, `wpo`, `szo`,
   `stc_tv`, `squeeze_pro`, `macd_area_divergence`, `_zone` -- found by
   grep). The Bollinger width is the issue's `upper - lower` written out
   rather than a call to `bbands`, which would also build a band-width
   percentage and a four-column frame; §A6 pins it BIT-EQUAL to `bbands`,
   and §A3 pins the MACD leg BIT-EQUAL to `macd`.
   ⚠ Changed in round 2: round 1 shipped a local copy of `ema`, justified
   by an import cycle through another overlap module that review round 1
   showed does not exist. The copy and the claim are both gone.
7. **Gate E is not run here.** The session's rules forbid touching
   `../Backtesting`; the receipt says "Gate E: pending, run by issue-solver
   after this session" and `tests/test_gate_e_ledger.py` fails locally
   until the launcher records the row. That failure is expected and is
   named in the receipt's §F.

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| `j-wae` | main thread | one task, one coherent file scope, and every step needs judgment about what the measurement actually showed |

No parallel subagent lane: a single port is one indivisible unit of work,
and the measurement loop (write a probe, read the numbers, change the
prose) does not decompose.

## File scope

Added: `pandas_ta/momentum/j_wae.py`, `tests/test_j_wae.py`,
`docs/measure_j_wae.py`, `docs/measure_j_wae_cpu.py`,
`docs/JWaeMeasured.md`, this run folder.
Modified: `pandas_ta/momentum/__init__.py`, `pandas_ta/__init__.py`,
`pandas_ta/core.py`, `README.md`, `docs/IndicatorDictionary.md`
(regenerated), `docs/MLCompanionContract.md`,
`tests/test_altport2_ports.py`.

Done criterion: Gates A–D measured and written down, the five wiring touch
points live, `tests/test_j_wae.py` green on both numpy dispatches, the
receipt carrying every number, and the Fletcher gate at PASS or at round 4.
