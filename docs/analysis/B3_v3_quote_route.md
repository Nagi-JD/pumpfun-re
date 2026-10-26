# B3 — v3 quote-route whitelist (analysis)

Gap: recovered `trade.rs::check_quote` hardcodes non-SOL = USDC; binary uses
quote_control whitelist (WSOL sentinel for native).

## Relevant handlers
- buy_v3 handler `0x250d9`
- buy_exact_quote_in_v3 `0x25185`
- sell_v3 `0x25231`
- initialize_quote_control `0x264a2`
- set_quote_control_mint_reserves `0x267e9`

## buy_v3 disposition
```
{
  "name": "buy_v3",
  "discriminator": "07051dc4f5176550",
  "cmp": "jeq",
  "stub_pc": "0x2390d",
  "handler_pc": "0x250d9",
  "handler_byte": "0x1286c8",
  "func_start_pc": "0x250d9",
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

## Work remaining (source edit — no build this run)
Replace USDC hardcode in recovered trade.rs check_quote with the whitelist
membership test the binary uses. Diff-harness after toolchain available.
