# B1 — util/transfer_fee.rs (analysis, no build)

Status: recovered-fixes/transfer_fee.rs already drafts the Token-2022 fee math
citing helper `@0x12a1c`. This run re-verified structural reachability from the
buy/migrate handlers via sbftool call graphs (shallow).

## Helper
- Cited transfer-fee helper pc: `0x12a1c`
- Program sha256: `7a19affaa2c6187e04a5fe0ea298cee81fa5eb8c24cfcc30d85f615e89f7b02d`

## Affected handlers (disposition excerpt)

### buy_v2
```
{
  "name": "buy_v2",
  "discriminator": "b817ee6167c5d33d",
  "cmp": "jeq",
  "stub_pc": "0x238e3",
  "handler_pc": "0x24ea2",
  "handler_byte": "0x127510",
  "func_start_pc": "0x24ea2",
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

### buy_exact_quote_in_v2
```
{
  "name": "buy_exact_quote_in_v2",
  "discriminator": "c2ab1c46684d5b2f",
  "cmp": "jeq",
  "stub_pc": "0x238f1",
  "handler_pc": "0x24f6b",
  "handler_byte": "0x127b58",
  "func_start_pc": "0x24f6b",
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

### buy_v3
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

### buy_exact_quote_in_v3
```
{
  "name": "buy_exact_quote_in_v3",
  "discriminator": "e1f7501ed5b38488",
  "cmp": "jeq",
  "stub_pc": "0x2391b",
  "handler_pc": "0x25185",
  "handler_byte": "0x128c28",
  "func_start_pc": "0x25185",
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

### migrate_v2
```
{
  "name": "migrate_v2",
  "discriminator": "bbcb121fceedfe29",
  "cmp": "jeq",
  "stub_pc": "0x23999",
  "handler_pc": "0x25749",
  "handler_byte": "0x12ba48",
  "func_start_pc": "0x25749",
  "func_insns": 6,
  "relative_callees": 0,
  "top_callees": [],
  "syscalls": {},
  "has_cpi": false,
  "has_log": false,
  "error_codes": [],
  "calls_transfer_fee_helper": false
}
```

### sell_v2 (control — should NOT use transfer-fee helper)
```
{
  "name": "sell_v2",
  "discriminator": "5df6823ce7e940b2",
  "cmp": "jeq",
  "stub_pc": "0x238ff",
  "handler_pc": "0x25034",
  "handler_byte": "0x1281a0",
  "func_start_pc": "0x25034",
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

## Next (toolchain-blocked)
Wire `transfer_fee.rs` into the four buy quote legs + migrate_v2 harvest, then
LiteSVM differential vs deployed.so. Not attempted this run (no Rust/SBF tools).
