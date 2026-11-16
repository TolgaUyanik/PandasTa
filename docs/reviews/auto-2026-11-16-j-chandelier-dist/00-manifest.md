# /brutally-honest-review --auto — run manifest

**Run id:** `auto-2026-11-16-j-chandelier-dist`
**Mode:** C (batch task execution), one task.
**Invocation:**

```
/brutally-honest-review --auto "J-CHANDELIER-DIST-22: port the indicator of
issue #122 through Gates A-D, the wiring, the tests and
docs/<Name>Measured.md, per the issue and the rules in your system prompt
(distance to the Chandelier Exit, long (22, 3). Source: jesse (MIT); also
Skender Chandelier — `chande.py: HH22 - 3*ATR22`.). Gate E and the suites
are run by the launcher afterwards."
```

## Phase 1 — the task

| id | scope | source |
|---|---|---|
| `j-chandelier-dist` | Port *distance to the Chandelier Exit, long (22, 3)* as `pandas_ta/trend/j_chandelier_dist.py` through Gates A–D, five wiring touch points, tests, `docs/JChandelierDistMeasured.md`. Gate E and both repos' suites are the launcher's. | PandasTa issue #122 (owner text in the session prompt; the local tracker copy is `docs/issues/121-j-chandelier-dist-22.md` — the tracker numbered it 121 and GitHub numbered it 122, and that file says so in its own header; `docs/issues/` is gitignored) |

Run folder: `docs/reviews/auto-2026-11-16-j-chandelier-dist/`.

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in this headless session, and the skill's
rule for that case is to take the **most conservative reading — the smaller
scope — and log it as an ASSUMPTION**. No questions were asked. The five
decisions that would otherwise have been questions:

**ASSUMPTION 1 — the ATR is Wilder's, SMA-seeded, not the screen
prototype's.** The issue says *"Gate A starts from the source formula, not
the prototype"*, and the formula it quotes is `HH22 - 3*ATR22`. The reading
rests on two things this session can check: Wilder's 1978 specification of
his own smoothing (seed with the SMA of the first `n`, then recurse at
`1/n`), and TA-Lib's `ATR`, which is what a bare "ATR" conventionally names
and which is installed here and run in §A2. ⚠ It does **not** rest on what
jesse's or Skender's code calls: neither library is installed, web access is
unavailable, and this session therefore claims nothing about either. (A
first draft of this manifest, of the module docstring and of the receipt did
make those claims, from recollection; the round-1 review caught it and they
are gone.)
The prototype's bare `ewm(alpha=1/22, adjust=False)` from bar 0 is a
different column for the first ~700 bars. **Cost, measured:** the screen's
Gate E figures describe a neighbouring column rather than this one.
Disclosed in §A3 of the receipt, in the module docstring and in the test
module's header. The port's own Gate E run is what decides its band, which
is the launcher's job anyway.

**ASSUMPTION 2 — the category is `trend`, not `volatility`.** The
Chandelier Exit is a trailing stop; its nearest in-fork neighbours (`cksp`,
`vstop`, `tvstop`, `j_safezone_dist`) are all in `trend`. The smaller-scope
reading: follow the siblings rather than start a new home for stop
distances.

**ASSUMPTION 3 — 22 and 3 are module constants, not arguments.** The issue
quotes exactly `(22, 3)`, the prototype spells exactly those two, and
`docs/gate_e_ledger.py` refuses a run taken at non-default parameters. A
`period=`/`mult=` surface would ship combinations nothing has measured.
Same decision as `j_safezone_dist` and `j_damiani`.

**ASSUMPTION 4 — the LONG side only, one column.** Issue #122 names the
long side and the screen measured only the long candidate, so no short-side
column has a Gate E figure. The short side is out of scope. ⚠ Whether
either library's function also takes a short direction is not checkable
here and is not claimed (see ASSUMPTION 1).

**ASSUMPTION 5 — the true range is spelled inline rather than imported from
`pandas_ta.volatility.true_range`.** The fork's version routes `high - low`
through `non_zero_range`, whose epsilon is ABSOLUTE and therefore not
scale-free. ⚠ This one was *tested rather than assumed* after the first
measurement refuted the obvious justification: on the six varying frames
the `true_range`-based variant is **bit-equal** to this module (none of
them has a `high == low` bar), and it only loses Gate D on a tie-bearing
frame — at a price level of 100 for ×8, and at 1e-6 for both factors.
Receipt §A4(e) carries both halves.

## Phase 3 — execution map

| task | lane | why |
|---|---|---|
| `j-chandelier-dist` | main thread | One indicator, five wiring touch points, a measurement script that must be run and read between edits, and numbers that have to flow from the run into three documents. Nothing here is parallelisable across non-overlapping file scopes, and every claim needs the main context that produced it. |

No subagent lanes. No destructive or irreversible steps: the session never
pushes, never touches `../Backtesting`, and writes only inside this
worktree.

## Deliverables

| file | status |
|---|---|
| `pandas_ta/trend/j_chandelier_dist.py` | new |
| `pandas_ta/trend/__init__.py` | +1 export |
| `pandas_ta/__init__.py` | +1 `Category["trend"]` entry |
| `pandas_ta/core.py` | +1 accessor |
| `tests/test_j_chandelier_dist.py` | new, 254 tests |
| `docs/measure_j_chandelier_dist.py` | new — the receipt's numbers, except the six exceptions it names above its §A1 |
| `docs/measure_j_chandelier_dist_cpu.py` | new — the same under reduced numpy dispatch |
| `docs/JChandelierDistMeasured.md` | new — the receipt |
| `README.md` | 356 → 357, 364 → 365, trend 63 → 64 |
| `docs/IndicatorDictionary.md` | regenerated |
| `docs/MLCompanionContract.md` | 701 → 702 tagged columns, 339 → 340 `SF` |
| `tests/test_altport2_ports.py` | `CATEGORY_TOTAL` 356 → 357, trend bucket 63 → 64 |
| `docs/reviews/auto-2026-11-16-j-chandelier-dist/` | this folder |
