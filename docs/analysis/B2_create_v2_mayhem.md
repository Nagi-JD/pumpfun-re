# B2 — create_v2 Mayhem branch (analysis)

## Pump create_v2
```
{
  "discriminator": "d6904cec5f8b31b4",
  "lddw_pc": "0x2373b",
  "cmp": "jeq",
  "stub_pc": "0x238d5",
  "handler_pc": "0x24d15",
  "handler_byte": "0x1268a8"
}
```
Disposition:
```
{
  "name": "create_v2",
  "discriminator": "d6904cec5f8b31b4",
  "cmp": "jeq",
  "stub_pc": "0x238d5",
  "handler_pc": "0x24d15",
  "handler_byte": "0x1268a8",
  "func_start_pc": "0x24d15",
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

## Mayhem initialize_mayhem_state (CPI target)
```
{
  "discriminator": "9dbd5e485545cc2d",
  "lddw_pc": "0xfb59",
  "cmp": "jeq",
  "stub_pc": "0xfbf0",
  "handler_pc": "0x101de",
  "handler_byte": "0x80ef0"
}
```
Disposition:
```
{
  "name": "initialize_mayhem_state",
  "discriminator": "9dbd5e485545cc2d",
  "cmp": "jeq",
  "stub_pc": "0xfbf0",
  "handler_pc": "0x101de",
  "handler_byte": "0x80ef0",
  "func_start_pc": "0x101de",
  "func_insns": 5,
  "relative_callees": 0,
  "top_callees": [],
  "syscalls": {},
  "has_cpi": false,
  "has_log": false,
  "error_codes": [],
  "calls_transfer_fee_helper": false
}
```

## Notes from recovered-fixes/create_v2.rs (already in tree)
- execute body cited `@0x3cf8..0x4492`
- Mayhem gate errors: 6046 CreateV2Disabled, 6048 MayhemModeDisabled,
  6071 MayhemModeQuoteMintNotAllowed; 6047 CpitializeMayhemFailed wraps CPI result
- Seeds baked: `global-params`, `sol-vault`, `mayhem-state`
- Mayhem program id `MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e`

## Open (analysis)
mayhem_map.md verifies Mayhem uses Anchor-style sha256 discriminators with
jeq+jne dispatch (25/25). The placeholder note in create_v2.rs about a non-Anchor
enum tag should be reconciled: prefer `9dbd5e485545cc2d` =
sha256("global:initialize_mayhem_state")[:8] which this map confirms is present
in the Mayhem dispatcher.

## Next
Harness-verify CPI sequence (toolchain-blocked). Static account-order recovery
can continue with sbftool field/callers on `@0x158d9` try_accounts.
