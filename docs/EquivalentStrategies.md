# Equivalent strategies

Candidates that turned out to restate, or nearly restate, something the package already ships. Check this list
before porting a new candidate: if it is here, the work is already done.

| Strategy to be implemented | Existing equivalent strategy | Related GitHub issue |
|---|---|---|
| `b2_kvo_hlc3_34_55` — Klinger-style volume force oscillator, `VF = ±V` by hlc3 sign, `EMA34(VF) − EMA55(VF)` | `kvo` (`KVO_34_55_13`) — kvo's construction, not the same formula. Differences read in code include these. Ties: kvo signs a zero hlc3 change 0, the candidate gives +V. EMA seeding: kvo's `ema` starts from an SMA, the candidate's `ewm(adjust=False)` from the first value. The candidate also divides by `EMA55(V)`. Per-frame max median ρ 0.8986 vs `KVO_34_55_13` (stage-2 fork overlap on 12 frames, not Gate E; just under the 0.90 line). It also overlaps the MFI family: `MFI_Pctl` 0.7989 (prototype Gate E, run `screen_r8_20261026`) | [#192](https://github.com/TolgaUyanik/PandasTa/issues/192) |
| `b2_close_beyond_prev` — +1 if `close > high[t-1]`, −1 if `close < low[t-1]`, else 0 | `priorday_fib` — exactly `(PDFIB_HIGH > 0) − (PDFIB_LOW < 0)`; 0 mismatches on 36 synthetic tick-rounded frames (179,964 bars, 7,635 ties) | [#193](https://github.com/TolgaUyanik/PandasTa/issues/193) |
