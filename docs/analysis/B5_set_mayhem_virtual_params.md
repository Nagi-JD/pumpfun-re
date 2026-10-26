# B5 — set_mayhem_virtual_params persistence

## Handler
```
{
  "discriminator": "3da9bcbf99952a61",
  "lddw_pc": "0x2372f",
  "cmp": "jeq",
  "stub_pc": "0x238ab",
  "handler_pc": "0x24ab5",
  "handler_byte": "0x1255a8"
}
```
Disposition:
```
{
  "name": "set_mayhem_virtual_params",
  "discriminator": "3da9bcbf99952a61",
  "cmp": "jeq",
  "stub_pc": "0x238ab",
  "handler_pc": "0x24ab5",
  "handler_byte": "0x1255a8",
  "func_start_pc": "0x24ab5",
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

## Trace targets from MASTER_GAPS
- `@0x19a7b` and `@0x1447e` — locate param write-back / Mayhem CPI
- Event disc cited: `757be4b6a1a8dcd6`
- Bounds: lamport 1e6 / 1e7 / 1e12; dual emit; 6–8×u64 virtual-param block

## This run
Disposition captures callees/syscalls/errors for the dispatch handler frame.
Persistence site still needs focused `sbftool func` / `callers` / `field` on
the two trace PCs (see follow-up script `tools/trace_b5.py` if present).
