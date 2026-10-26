# Full 4-program structural map (deployed binaries)

Built with sbftool.py from evidence/original/*/deployed.so. Decoder 0-diff vs llvm-objdump.

| Program | .text insns | functions | instructions mapped |
|---|---:|---:|---|
| pump | 215,873 | 1169 | 53/53 |
| pump_amm (PumpSwap) | 139,524 | 831 | 30/31 |
| pump_fees | 96,083 | 637 | 31/31 |
| mayhem | 83,947 | 502 | 25/25 (jeq+jne dispatch, collaborator-verified) |

Handler tables saved: handlers.json (pump), amm_handlers.json (PumpSwap).
Key handlers:
- PumpSwap create_pool @ 0x1c634  (migrate graduation CPI target)
- PumpSwap create_config @ 0x1c17f (mainnet-admin gated)
- Fees get_fees_with_quote_mint @ 0x13763 (pump buy/sell CPI target)
- Fees get_fees @ 0x136a0
- Mayhem initialize_mayhem_state @ 0x101de (pump create_v2 CPI target)

Byte-identity status (repo HEAD 0b29240a): 0/4 core, 1/5 deps truly raw-exact (SPL Token only).
