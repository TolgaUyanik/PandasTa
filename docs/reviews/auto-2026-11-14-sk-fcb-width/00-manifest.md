# Auto run — SK-FCB-WIDTH (PandasTa issue #107)

**Mode:** C (batch task execution), `--auto` with one task.
**Date:** 2026-11-14 · **Run folder:** `docs/reviews/auto-2026-11-14-sk-fcb-width/`
**Reviewer:** fresh read-only `Explore` subagent per round, Fletcher persona ON
(automatic in `--auto`), capped at 4 rounds by the user's standing review-loop rule.

## Phase 1 — the task, resolved

One task, given verbatim in the invocation:

> SK-FCB-WIDTH: port the indicator of issue #107 through Gates A-D, the wiring, the
> tests and `docs/<Name>Measured.md`, per the issue and the rules in your system
> prompt (Fractal Chaos Band width (span 2). Source: Skender Stock.Indicators
> (Apache-2.0) — `Fcb.Series.cs: upper - lower`.). Gate E and the suites are run by
> the launcher afterwards.

Source of the issue text: the launcher's prompt, plus the owner's local tracker copy at
`docs/issues/106-sk-fcb-width.md` (gitignored; GitHub #107 is the source of truth) and
the screen prototype `docs/issues/screen/ind_screen_r2.py`, candidate `sk_fcb_width`.

**Done criterion** (from the issue): shipped through Gates A–F with the numbers in
`docs/<Name>Measured.md`, OR measured and reverted with that file kept as the receipt.
Gate E and both suites are the launcher's, so this session owes Gates A–D, the five
wiring touch points, the tests, and the receipt.

## Phase 2 — clarifications

`AskUserQuestion` is unavailable in this headless session, so per the skill's rule every
ambiguity took **the most conservative reading (smaller scope)** and is logged here.

| # | Ambiguity | Conservative reading taken | Why |
|---|---|---|---|
| A1 | How many columns? | **One**, `SK_FCB_WIDTH_2` | The issue names one formula, `upper - lower`, and the prototype returns one series. Shipping `upper`/`lower` separately would add price-level columns nothing measured. |
| A2 | Is the span a parameter? | **Module constant `SPAN = 2`** | Span 2 is the only span the issue's title, the prototype and the Gate E figures cover. A `span=` keyword would ship unmeasured combinations. |
| A3 | Where is a fractal read? | **`SPAN` bars after its centre** (confirmed) | Skender's `Fractal` returns it ON the centre bar; read there the column looks ahead `SPAN` bars and fails Gate B. The confirmed reading is the prototype's and the causal one. The divergence is measured, not hidden: §A3 of the receipt. |
| A4 | Guard non-finite high/low? | **Yes, mask to NaN** | `+inf > x` is True, so an unguarded infinity becomes a fractal and the band carries `inf`. The guard changes nothing on a clean frame (bit-equal to the guard-free prototype) and is priced in §G3. |
| A5 | Category? | **volatility** | It is a band width over close; the screen's nearest comparator is `natr`, also volatility. |
| A6 | Run Gate E? | **No** | The launcher's rules override the issue: the receipt says "Gate E: pending, run by issue-solver after this session", and nothing outside this worktree is read or written. |

No destructive or irreversible step is in scope; nothing was pre-authorised and nothing
was needed.

## Phase 3 — execution map

One task, **main thread**: every file touches the same five wiring points plus shared
count files (`README.md`, `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py`),
so there is no non-overlapping scope to split and no parallel lane would be safe.

Order worked: module → measurement script → run every section → wiring (5 touch points
+ 3 count files + regenerate the dictionary) → test module → CPU-reduced re-run → receipt
→ review rounds, which are logged verbatim with their outcomes in
[`01-sk-fcb-width.md`](01-sk-fcb-width.md) and summarised in
[`99-summary.md`](99-summary.md).

## Files in scope

| path | change |
|---|---|
| `pandas_ta/volatility/sk_fcb_width.py` | new — the indicator |
| `pandas_ta/volatility/__init__.py` | export |
| `pandas_ta/__init__.py` | `Category["volatility"]` |
| `pandas_ta/core.py` | `df.ta.sk_fcb_width()` accessor |
| `tests/test_sk_fcb_width.py` | new — 160 tests (157 at round 1, 158 after round 1's fixes, 160 after round 2's) |
| `docs/measure_sk_fcb_width.py` | new — every number in the receipt |
| `docs/measure_sk_fcb_width_cpu.py` | new — the same under reduced numpy dispatch |
| `docs/SkFcbWidthMeasured.md` | new — the receipt |
| `docs/IndicatorDictionary.md` | regenerated from the live probe |
| `README.md`, `docs/MLCompanionContract.md`, `tests/test_altport2_ports.py` | counts |
| `docs/reviews/auto-2026-11-14-sk-fcb-width/**` | this run |

Out of scope and untouched: `docs/gate_e_ledger.csv` (the receipt session's, after the
launcher's Gate E run), and anything under `docs/issues/` (read-only, gitignored).
