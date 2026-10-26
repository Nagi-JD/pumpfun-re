# B4 — multi_hop_curve_swap depth cap + adapter delta

## Handler
```
{
  "discriminator": "e19a7516d756f667",
  "lddw_pc": "0x23757",
  "cmp": "jeq",
  "stub_pc": "0x23937",
  "handler_pc": "0x252b8",
  "handler_byte": "0x1295c0"
}
```
Disposition:
```
{
  "name": "multi_hop_curve_swap",
  "discriminator": "e19a7516d756f667",
  "cmp": "jeq",
  "stub_pc": "0x23937",
  "handler_pc": "0x252b8",
  "handler_byte": "0x1295c0",
  "func_start_pc": "0x252b8",
  "func_insns": 7,
  "relative_callees": 0,
  "top_callees": [],
  "syscalls": {},
  "has_cpi": false,
  "has_log": false,
  "error_codes": [],
  "calls_transfer_fee_helper": false
}
```

## Known from MASTER_GAPS
- CurveDepthExceeded + SetMaxCurveDepth admin ix exist; depth check in OUTER router
- TradeEvent +0x198 = adapter diff (helper `@0x12a1c` / transfer-fee path)
- recovered-fixes/multi_hop_curve.rs present (423 lines) — port still partial

## Admin related
- set_max_curve_depth `0x24566`
