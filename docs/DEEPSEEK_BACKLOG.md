# DeepSeek — complete work backlog (pump.fun RE, private analysis)

Your lane: **reverse-engineering / analysis** from the deployed binaries. Claude's lane:
build + differential harness + fuzz (toolchain-dependent). Work top-down through the tiers;
pull the next open task whenever you finish one. Hand every deliverable back to the user as
a `.md`/`.json` file — the user relays it, Claude re-verifies against the binary before merge.

## Ground rules (every task)
- Binary-grounded: cite the instruction ADDRESS for every structural claim.
- Tag each claim **[B]** = you confirmed it in the deployed disassembly, **[R]** = from the
  repo reconstruction (reference only), **[partial]** = inconclusive (say why).
- NEVER fabricate a discriminator, offset, address, or a byte-identity/behavioral claim.
- NO pull requests, NO public posting. Private; hand files to the user.
- Reference (read-only): github.com/Nagi-JD/pumpfun-re — `specs-amm/amm_specs.md` for spec
  FORMAT; `maps/*.json` for handler addresses; `tools/sbftool.py` for disassembly.
- Binaries: `evidence/original/{pump,pump_amm,pump_fees,mayhem}/deployed.so` (pull via
  `solana program dump <ID> out.so --url mainnet-beta` if you don't have them).

---

## TIER P0 — unblocks Claude's harness verification (highest value)

**T1. Account byte-layout maps (ALL key state accounts).** The harness must seed these exactly;
Claude is currently reversing offsets ad hoc. Produce `account_layouts.md`: for each account,
the full field→byte-offset table (as the program READS it — note if it's borsh vs in-memory/
zero-copy), the 8-byte discriminator, and total size. Cover:
- pump: `Global` (incl. buyback_fee_recipients offset — pump side was 741), `BondingCurve`,
  `UserVolumeAccumulator`, `GlobalVolumeAccumulator`, `QuoteControl`.
- pump_amm: `GlobalConfig` (incl. the 8-key buyback array @~643 and buyback_basis_points @~899),
  `Pool`, `FeeConfig` consumption.
- pump_fees: `FeeConfig` (bump, admin, flat_fees, fee_tiers Vec, stable_fee_tiers, exotic),
  sharing-config accounts.
- mayhem: `GlobalParams`, `mayhem_state`.
Cite the load/store sites. This is the single most useful thing for finishing verification.

**T2. Trade-handler GATE catalogs (ordered preconditions).** For each trade entrypoint
(pump: buy/sell/buy_v2/sell_v2/buy_v3/sell_v3/buy_exact_quote*; amm: buy/sell/buy_v2/sell_v2),
list the ORDERED sequence of require!/constraint gates with their error codes and the exact
account/arg each needs (like the buyback gate: 6058 → remaining[?]=owner in GlobalConfig 8-key
array). Output `gate_catalogs.md`. This tells Claude exactly what state to seed to reach swap math.

---

## TIER P1 — completes behavioral coverage (specs for everything)

**T3. pump_fees per-handler specs** → `fees_specs.md` (31 handlers, format = amm_specs.md).
Priority: get_fees, get_fees_with_quote_mint, initialize_fee_config, update_fee_config,
upsert_fee_tiers, set_exotic_flat_fees, update_fee_shares(_v2), sweep_buyback, then the rest.
Addresses in `maps/fees_handlers.json`.

**T4. pump per-handler specs (individual, all 53).** We only have 11 CLUSTER specs. Produce
`pump_specs.md` with one section per instruction for the ~42 not individually specced
(addresses in `maps/handlers.json`). Reuse/cite the 11 cluster specs where they already cover one.

**T5. Deep-spec the routing handlers.** `multi_hop_curve_swap` (pump) and `multi_hop_swap`
(pump_amm): the hop loop, per-hop fee flags, depth cap, account layout per hop, the trailing
TradeEvent field. Output `multihop_specs.md`.

**T6. create_v2 Mayhem full flow.** Reverse pump `create_v2` is_mayhem_mode=true end-to-end:
the exact mint_to/CPI ordering, the second mint_to into mayhem_token_vault, the
initialize_mayhem_state CPI payload + account order. Output `create_v2_mayhem.md`.

---

## TIER P2 — catalogs (reference tables, reverse-heavy)

**T7. Full discriminator catalogs.** Per program: every instruction, event, and account
discriminator (name → 8 bytes → where it appears). Output `discriminators.md`.

**T8. Full error-code catalogs.** Per program: every error code → name → raise site(s)
(address). pump PumpError 6000+, amm errors (6000–6088+), fees errors, mayhem errors.
Output `error_catalogs.md`.

**T9. Interprogram CPI graph.** Every cross-program invoke/invoke_signed: caller program+handler
(addr) → callee program id → instruction (disc) → account metas → signer seeds. Cover
pump→fees, pump→mayhem, pump→amm (migrate), amm→fees, pump/amm→Token/Token-2022/ATA/Metaplex.
Output `cpi_graph.md`.

**T10. Event struct layouts.** Reverse TradeEvent (pump) and the amm/fees/mayhem event structs:
field order + byte offsets, including the trailing/unparsed fields. Output `event_layouts.md`.

---

## TIER P3 — byte-identity grind (the Shaw end-goal; one function at a time)

**T11+. Byte-structure proposals.** For each function the repo pass-index marks
"not normalized-identical", compare deployed llvm-objdump vs the recovered build and propose
the specific source-structure change (function split/merge, inline, item order,
monomorphization/specialization) that closes the byte delta, with a self-check/regression plan.
Append to `structure_proposals.md`, one function per entry. This is an endless, high-value queue
— keep pulling functions. (You already did pump_amm::update_buyback_config.)

---

## Done / verified (do NOT redo)
- All 4 programs mapped: pump 53/53, pump_amm 38/38, pump_fees 31/31, mayhem 25/25. [verified]
- amm_specs.md (38), mayhem_specs.md (25), mayhem_map.md. [verified/merged]
- amm buyback gate 6058 reversed (helper 0x6e2a, 8-key array). [verified; Claude applying]
