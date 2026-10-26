# Differential verification — clone vs deployed Pump program

Harness: `~/diffharness` (Rust + LiteSVM). Loads the deployed dependency programs
(SPL Token, Associated Token, Metaplex Token Metadata) and runs the same
instruction against the **original** `deployed.so` and our **clone**
`pump_clone.so`, then compares success/failure, error code, resulting account
bytes, and compute units.

## Results (launchpad bootstrap)

| instruction | orig / clone | resulting-state match | CU (orig/clone) |
|---|---|---|---|
| initialize  | ok / ok   | ✅ byte-identical `Global` | 10872 / 10919 |
| set_params  | ok / ok   | ✅ byte-identical `Global` | 24787 / 24936 |
| create      | ok / ok   | ✅ byte-identical `BondingCurve` | 108640 / 113074 |

| create_user_ata | ok / ok | ✅ | 15136 / 15136 |
| buy         | err / err | ✅ both reject `6062` (BuybackFeeRecipientMissing) | 47160 / 46898 |

`LAUNCHPAD_FLOW_MATCH = true` across init → set_params → create → create_user_ata → buy.

## UPDATE — full successful trade loop verified

After reversing the `buy` buyback-check ordering bug (fixed in `legacy_buy.rs`),
seeding a valid buyback recipient into `Global.buyback_fee_recipients[0]`
(borsh offset 741), and replicating the real mainnet `FeeConfig` account, the
harness now runs a COMPLETE successful trade loop, independently re-verified
with a fresh clone build:

| step | orig/clone | state match |
|---|---|---|
| initialize | ok/ok | ✅ |
| set_params | ok/ok | ✅ |
| create | ok/ok | ✅ byte-identical BondingCurve |
| create_user_ata | ok/ok | ✅ |
| buy (real SOL-in) | ok/ok | ✅ byte-identical curve + user token balance |
| sell (real token-in) | ok/ok | ✅ byte-identical curve + user token balance |

`LAUNCHPAD_FLOW_MATCH = true`. These are SUCCESSFUL matched trades (not shared
rejections): the clone creates, buys, and sells on the bonding curve identically
to the deployed program, with the real captured Fees program computing fees.

Reversed facts: buy account order has `creator_vault` after `token_program`;
sell has `creator_vault` BEFORE `token_program`. `sell` needed no handler change
(already faithful). `create_v2` Mayhem CPI was reconstructed
(disc sha256("global:initialize_mayhem_state"), 10 accounts, no args) and
compiles, but is not exercised by this harness (create path is non-mayhem) and
still lacks the full-flow CPI-ordering + second mint_to.

### buy depth note
`buy` is driven with the real captured **Fees** program loaded and a hand-seeded
`fee_config` (PDA ["fee_config", pump] owned by the Fees program) plus a seeded
`global_volume_accumulator`. The call executes through account validation, the
Fees-program CPI (fees computed by the actual Fees binary), and into the trading
logic, where both the original and the clone reject the test inputs identically
with `6062` — because no buyback fee recipient is configured. To land a fully
successful matched buy, configure buyback (`update_buyback_config` + a registered
buyback recipient) and pass it; then diff a real SOL-in trade. sell / migrate
each have their own prerequisite state.

### What this proves
- The clone **creates a coin identically to the deployed program**: same success,
  same CPIs into Token/Metaplex/ATA, and a byte-identical `BondingCurve` account.
- Behavioral equivalence is verified (not assumed) for the create path and the
  admin path — this is real evidence, produced by executing both programs.

### What this does NOT prove
- **Not .so byte-identity.** Matching *account state* is expected of a correct
  behavioral clone; the compiled binaries still differ (CU differs by ~1–4%,
  a visible symptom). Byte-identity is a separate, unsolved problem (see below).
- **buy / sell not yet verified.** They CPI into the separate **Fees** program
  for the fee schedule, which must itself be loaded and have a valid
  `fee_config` account seeded. That is the next bootstrap layer.
- The known-soft reconstructions (create_v2 Mayhem CPI payload = placeholder;
  buy-leg transfer-fee placements = inferred) are not yet exercised here.

## Byte-identity status (lalalune/pumpfun-source, HEAD e78fc371, through pass 21)
- Whole-file byte equality on the 4 core programs: **0 / 4** — unachieved by
  anyone, consistently through pass 21.
- The only byte-identical artifacts are the two dependencies whose **source is
  public** (SPL Token, Token-2022) — which proves the *method* works when the
  source exists.
- The repo's own `BUILD_IDENTITY_AUDIT.md` states plainly: "Missing original
  source is not proof that byte identity is impossible." So it is an **open
  problem bounded by lost source structure**, NOT proven impossible and NOT
  achieved. Earlier I called it "impossible" — that overstated it; "unachieved
  and open" is correct.

## UPDATE 2 — PumpSwap (pump_amm) recovered vs deployed

Harness: ~/ammharness (Rust+LiteSVM). Loads deployed pump_amm.so and recovered
amm_recovered.so each at pAMMBay…, seeds the mainnet global_config, runs the core
AMM flow. Independently re-verified.

| instruction | deployed/recovered | state match | note |
|---|---|---|---|
| create_pool | ok / ok | ✅ byte-identical | real sqrt-k LP math: lp=√(1e21)=31,622,776,501 both |
| deposit | ok / ok | ✅ byte-identical | LP mint + vault transfers match |
| buy | err / err | ✅ | both Custom(2006) at the pump_fees GetFeesWithQuoteMint CPI (shared external gate, not an AMM bug) |
| sell | err / err | ✅ | same shared fee gate |
| withdraw | ok / ok | ✅ byte-identical | LP burn + vault transfers match |

AMM_FLOW_MATCH=true. Verified: create_pool/deposit/withdraw byte-identical (incl.
the constant-product LP accounting). NOT yet verified: buy/sell swap pricing — both
reach an identical terminal error at the external Fees-program fee_config seed gate;
clearing that gate is required to verify AMM swap math end-to-end.

## UPDATE 3 — pump_fees recovered vs deployed (VERIFIED)
Harness: feesharness (Rust+LiteSVM). get_fees + get_fees_with_quote_mint, both
callers' fee_config PDAs. Independently re-verified.
- All calls byte-identical: successes return Fees{lp=0,protocol=95,creator=30}; FEES_MATCH=true.
- fee_config constraint reversed: seeds=[b"fee_config", config_program_id], bump=fee_config.STORED bump.
  PDA[fee_config,pump] bump=253; PDA[fee_config,amm] bump=255. A wrong stored bump → ConstraintSeeds(2006).
- AMM swap unblock: seed the amm fee_config with stored bump=255 (the real on-chain value) to let
  pump_amm buy/sell clear the fee CPI and verify swap pricing end-to-end.

## UPDATE 4 — PumpSwap swap: fee gate cleared, buyback gate next
Applied the known fix: seed amm fee_config at PDA[b"fee_config", pAMMBay…] with stored
bump=255 (asserted canonical at runtime). Result:
- The Custom(2006) fee gate is GONE. get_fees_with_quote_mint CPI now returns byte-identical
  fees (lp0/protocol95/creator30) on both builds; fee transfers execute identically. buy CU
  93443/55691 (vs ~82k/45k before) — execution now runs deep into the swap handler.
- buy/sell now hit a NEW matched gate: Custom(6058) BuybackFeeRecipientMissing (buy.rs:116),
  identical on both builds (matched rejection, not a divergence).
- Zeroing the IDL-layout buyback fields in global_config did NOT clear it → the live binary
  reads the buyback requirement from a source the stale IDL doesn't capture. Clearing it
  requires RE of buy @0x1cec9 around buy.rs:116 to find the expected buyback recipient
  account(s)/offset, then seeding+passing them. create_pool/deposit/withdraw remain byte-id.
