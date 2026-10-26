# B6 — token-incentives handlers (spec→Rust port readiness)

Spec 10 is complete. recovered-fixes already contain:
- admin_update_token_incentives.rs
- claim_token_incentives.rs
- token_incentives_mod.rs

## Dispatch (re-verified)
### admin_update_token_incentives
```
{
  "discriminator": "d10b7357d5177ccc",
  "lddw_pc": "0x23793",
  "cmp": "jeq",
  "stub_pc": "0x23a09",
  "handler_pc": "0x25c54",
  "handler_byte": "0x12e2a0"
}
```
```
{
  "name": "admin_update_token_incentives",
  "discriminator": "d10b7357d5177ccc",
  "cmp": "jeq",
  "stub_pc": "0x23a09",
  "handler_pc": "0x25c54",
  "handler_byte": "0x12e2a0",
  "func_start_pc": "0x25c54",
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

### claim_token_incentives
```
{
  "discriminator": "1004471ccc01281b",
  "lddw_pc": "0x23797",
  "cmp": "jeq",
  "stub_pc": "0x23a17",
  "handler_pc": "0x25d0e",
  "handler_byte": "0x12e870"
}
```
```
{
  "name": "claim_token_incentives",
  "discriminator": "1004471ccc01281b",
  "cmp": "jeq",
  "stub_pc": "0x23a17",
  "handler_pc": "0x25d0e",
  "handler_byte": "0x12e870",
  "func_start_pc": "0x25d0e",
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

## Next
Byte-identity of these handlers is STOPPED for pumpfun-source; behavioral port
into a clone remains valid for pumpfun-re. Harness verify blocked on toolchain.
