# B7 — pump_fees + amm buy/sell differential verify (spec)

Harness execution blocked (LiteSVM/Rust). Structural map below is the
pre-harness baseline.

## pump_fees
### get_fees
```
{
  "discriminator": "e7257e55cf5b3f34",
  "lddw_pc": "0x12456",
  "cmp": "jeq",
  "stub_pc": "0x12578",
  "handler_pc": "0x136a0",
  "handler_byte": "0x9b500"
}
```
```
{
  "name": "get_fees",
  "discriminator": "e7257e55cf5b3f34",
  "cmp": "jeq",
  "stub_pc": "0x12578",
  "handler_pc": "0x136a0",
  "handler_byte": "0x9b500",
  "func_start_pc": "0x136a0",
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

### get_fees_with_quote_mint
```
{
  "discriminator": "9aed8a5ca202a2bb",
  "lddw_pc": "0x1245a",
  "cmp": "jeq",
  "stub_pc": "0x12586",
  "handler_pc": "0x13763",
  "handler_byte": "0x9bb18"
}
```
```
{
  "name": "get_fees_with_quote_mint",
  "discriminator": "9aed8a5ca202a2bb",
  "cmp": "jeq",
  "stub_pc": "0x12586",
  "handler_pc": "0x13763",
  "handler_byte": "0x9bb18",
  "func_start_pc": "0x13763",
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

## pump_amm
### buy
```
{
  "discriminator": "66063d1201daebea",
  "lddw_pc": "0x1b7eb",
  "cmp": "jeq",
  "stub_pc": "0x1b951",
  "handler_pc": "0x1cec9",
  "handler_byte": "0xe7648"
}
```
```
{
  "name": "buy",
  "discriminator": "66063d1201daebea",
  "cmp": "jeq",
  "stub_pc": "0x1b951",
  "handler_pc": "0x1cec9",
  "handler_byte": "0xe7648",
  "func_start_pc": "0x1cec9",
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

### sell
```
{
  "discriminator": "33e685a4017f83ad",
  "lddw_pc": "0x1b7f3",
  "cmp": "jeq",
  "stub_pc": "0x1b96d",
  "handler_pc": "0x1d099",
  "handler_byte": "0xe84c8"
}
```
```
{
  "name": "sell",
  "discriminator": "33e685a4017f83ad",
  "cmp": "jeq",
  "stub_pc": "0x1b96d",
  "handler_pc": "0x1d099",
  "handler_byte": "0xe84c8",
  "func_start_pc": "0x1d099",
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

### create_pool / create_config
- create_pool: `0x1c634`
- create_config: `0x1c17f`

## Note
MASTER_GAPS: seed amm fee_config stored bump=255 to clear Fees CPI gate during
harness runs — harness-only detail, not attempted here.
