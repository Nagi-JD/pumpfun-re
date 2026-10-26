# 06 — SELL handlers (binary-verified RE)

Target: `evidence/original/pump/deployed.so` (deployed Pump.fun program).
Tooling: `sbftool.py func/dis/callers/field` over `.text`.
Recovered source cross-checked: `programs/pump/src/{legacy_sell,sell_v2,trade,trade_types}.rs`, `lib.rs`.

## Dispatch architecture (all three handlers)

Each Anchor instruction entry is a thin **trampoline** that (1) `sol_log_`s
`"Instruction: Sell/SellV2/SellV3"`, (2) calls a `try_accounts` deserializer,
(3) calls the real `execute` worker, (4) calls an exit/serialize-back helper.

| ix (name@entry) | log string @len | try_accounts | **execute worker** | recovered source |
|---|---|---|---|---|
| `sell`    @ `0x25656` | `0x1b7e87`/17 (`Instruction: Sell`)   | `0x2e8a4` | **`0x2a511`** | `legacy_sell::execute` |
| `sell_v2` @ `0x25034` | `0x1b7dc0`/19 (`Instruction: SellV2`) | `0x1cc55` | **`0x288a1`** | `sell_v2::execute` |
| `sell_v3` @ `0x25231` | `0x1b7e03`/19 (`Instruction: SellV3`) | `0x204af` | **`0x29515`** | `trade::sell` (lib.rs:146 `sell_v3 → trade::sell`) |

Worker sizes: sell_v2 **1714 insns**, sell 1035, sell_v3 735. The sell_v2 bulk
is the non-native-quote machinery (4× ATA `create_idempotent` + 4× quote
`transfer_checked` + `SharingConfig` deserialize), **not** transfer-fee code.

Shared TradeEvent serializer `0x2c496` is called **twice** by every worker
(`emit!` cpi-log + `emit_cpi!` self-CPI): sell_v2 `0x28ede`,`0x28ef3`;
sell_v3 `0x29773`,`0x29788`; sell `0x2a8b9`,`0x2a8bb`. Trailing event field at
struct offset `0x198` = `unparsed_trailing_field`, written constant `0` in all
three (source `unparsed_trailing_field:0`).

---

## Handler: `sell` — `legacy_sell::execute` @ 0x2a511

**1. Purpose + quote routes.** Legacy native-only sell. The account constraint
`bonding_curve.quote_mint==Pubkey::default()` (`UnsupportedQuoteMint`) forces
**SOL-only**; there is no non-native branch. Payout is by lamport arithmetic
(`sub_lamports`/`add_lamports`), never a quote SPL transfer.

**2. Accounts validated.** `global` (PDA `global`), `fee_recipient` (handler
membership), `mint`, `bonding_curve` (PDA `bonding-curve,mint`; native
constraint), `associated_bonding_curve`/`associated_user` (ATA mint+authority),
`user` signer, `creator_vault` (PDA `creator-vault,creator`), token/fee
programs, `event_authority`. Remaining accounts: `[+0]` user_volume_accumulator
(only if `is_cashback_coin`), then `bonding-curve-v2` PDA, then
`buyback_fee_recipient`.

**3. Errors/order.** rent top-up → `NotAuthorized`(fee recipient) →
`BondingCurveComplete` → `SellZeroAmount`(amount>0) →
`NotEnoughTokensToSell` → fee-program CPI → **`TooLittleSolReceived`
(6003=`0x1773`, worker line `2a682: stw [r10-0x270],0x1773`)** → base
`transfer_checked` → cashback/v2/buyback remaining-account checks.
Minimum-output check is on **gross** `output = quote − pf − cf` (see §mismatch,
same structure as sell_v2/sell_v3).

**4. CPIs.** fee-program `invoke` (quote cap query); base `transfer_checked`
(user→curve); **no quote token transfer** (native lamport moves only). No
TransferFee-extension CPI.

**5. Fee math.** `quote = amount·vq/(vt+amount)`; `pf=(quote·pf_bps+9999)/10000`;
`cf=(quote·cb_bps+9999)/10000` (ceil-div, `cb=0` if creator==default);
`bf=pf·buyback_bps/10000` (`buyback_bps=0` in mayhem); `output=quote−pf−cf`.
Payout: curve `−quote`, user `+output`, fee_recipient `+(pf−bf)`,
creator_vault `+cf` (or user_volume_accumulator for cashback), buyback `+bf`.

**6. TradeEvent.** `sol_amount=quote`, `quote_amount=quote`, `quote_mint=default`,
sol reserves populated (native), `ix_name="sell"`, `shareholders=[]`,
`unparsed_trailing_field=0`.

**7. GAP vs `legacy_sell.rs`.** None material — binary matches recovered source
(native-only, gross min-check, lamport payout).

---

## Handler: `sell_v2` — `sell_v2::execute` @ 0x288a1   ★ focus

**1. Purpose + quote routes.** General sell supporting **native (WSOL/default)
AND arbitrary non-native quote mints**. The quote mint is whatever the curve
was created with (constraint: `quote_mint == if curve.quote_mint==default {WSOL}
else {curve.quote_mint}`, `UnsupportedQuoteMint`). **No restriction to a safe
mint set** — unlike sell_v3 which is WSOL/USDC-only. A non-native quote may be
a **Token-2022 mint carrying a `TransferFeeConfig` extension.**
- native → lamport moves (`sub_lamports`/`add_lamports`).
- non-native → 4× quote `transfer_checked` out of `associated_quote_bonding_curve`.

**2. Accounts validated (non-native branch, worker `0x289e0–0x28a83`).** For a
non-native curve the worker requires `associated_quote_bonding_curve` and
`associated_quote_user` not system-owned, runs `check_token` (mint-equality
only, raising `MintDoesNotMatchBondingCurve` 6005=`0x1775` and
`AccountTypeNotSupported` 6022=`0x1786`), and `create_idempotent`s the 4
destination quote ATAs (fee_recipient, buyback, creator_vault,
user_volume_accumulator) then `check_token`s each. `check_token`
(helper `0x218f`) validates `token.mint == quote_mint` **only** — it does **not**
read or reject the mint's extension set. Plus the standard
global/base_mint/quote_mint/curve/user/creator_vault/sharing_config/fee_config
accounts.

**3. Errors/order.** volume-accumulator init → (non-native) quote-account checks
& ATA creation → rent top-up → `NotAuthorized` → `BondingCurveComplete` →
`SellZeroAmount` → `NotEnoughTokensToSell` → fee-program `invoke` → fee math →
**`TooLittleSolReceived` (`0x1773`, worker `0x28bd7`)** → base `transfer_checked`
→ `BuybackFeeRecipientNotAuthorized` → payout branch → state write → emit×2.

The minimum check (worker `0x28bc1–0x28be3`):
```
28bc1: ldxdw r1,[r10-0x300]     ; r1 = output = quote - pf - cf
28bc3: ldxdw r2,[r10-0x610]     ; r2 = minimum  (raw arg4, stored at entry 0x288a1: stxdw [r10-0x610],r4)
28bc4: jlt  r1, r2, +0x1        ; if output <  minimum -> fall into error path
28bc5: ja   +0x31               ; if output >= minimum -> continue
...
28bd7: stw  [r10-0x270], 0x1773 ; TooLittleSolReceived
```
→ the check is on **gross-of-transfer-fee `output`** directly against the raw
`minimum` arg. **No Token-2022 transfer-fee term is subtracted.**

**4. CPIs.** fee-program `invoke`; base `transfer_checked` (user→curve, opcode
12 via shared builder); non-native: **4× `transfer_checked`** from curve ATA
(`cf`→creator_vault|user_vol, `output`→user, `bf`→buyback, `pf−bf`→fee_recipient),
each a plain `TransferChecked` (opcode 12). **Searched the entire worker for the
TransferFee-extension opcode `0x1a`(26): 0 matches** (the one `0x1a` hit is a
jump offset `jeq r0,0x0,+0x1a` at `0x28b0a`, not an instruction byte). Therefore
**no `transfer_checked_with_fee` (`[26,1,…]`) and no `HarvestWithheldTokensToMint`
(`[26,4]`) CPI** is ever constructed. (Contrast: `migrate_v2.rs:77` *does* build
`vec![26,4]` to harvest — so opcode-26 construction is a recognizable fingerprint
and it is absent here.)

**5. Fee math.** Identical to `sell`/`sell_v3`: ceil-div `pf`,`cf`,
`bf=pf·buyback_bps/10000`, `output=quote−pf−cf`. `creator_fee_bps` overridden
from curve if `>0`. Buyback membership required
(`BuybackFeeRecipientNotAuthorized`).

**6. TradeEvent (worker `0x28df3–0x28ef3`).** Native-gated sol fields: `r7=!native`
selects `sol_amount / virtual_sol_reserves / real_sol_reserves = 0` when
non-native (`0x28dfd–0x28e09`), else `quote / vq / rq`. `quote_amount = quote`
(**gross** AMM quote), `quote_mint = curve.quote_mint`, `ix_name="sell"`
(`28e57: stw [r7],0x6c6c6573` = "sell"). Curve flag bytes at curve-data offsets
`+0xa2/+0xa3/+0xa5` drive `is_mayhem/is_cashback/is_holder` selection of
cashback/holder_rewards fields (matches source). `unparsed_trailing_field=0`.

**7. GAP vs recovered `sell_v2.rs`.**
- **(a) Net vs minimum:** binary computes **NO** Token-2022 transfer fee and
  compares **gross** `output` (`quote−pf−cf`) against `minimum`
  (`0x28bc4`). ✔ matches source — source also omits it.
- **(b) Harvest:** binary does **NOT** harvest withheld fees (no opcode-26 CPI).
  ✔ matches source.
- **(c) Event amount:** binary records **gross** `quote_amount=quote` and
  `output` is never re-read post-transfer. ✔ matches source.
→ **The recovered `sell_v2.rs` is FAITHFUL to the binary.** There is **no
`util/transfer_fee.rs` behavior in the binary's `sell_v2`** to recover — the
context note's premise (binary sell_v2 nets/harvests a transfer fee that the
source omits) is **not supported by the deployed bytecode**. See dedicated
subsection.

---

### ★ sell_v2 transfer-fee mismatch — binary behavior

**Question (a): does the binary compute a Token-2022 transfer fee and compare
NET output against `minimum`?** — **NO.** The only comparison feeding
`TooLittleSolReceived` is `output = quote − protocol_fee − creator_fee` vs the
raw `minimum` argument (`0x28bc1–0x28be3`, error store `0x28bd7`). No
`TransferFeeConfig`/`calculate_epoch_fee` read precedes it; no extension TLV
walk of `quote_mint` exists in the worker; `check_token` (`0x218f`) checks only
`token.mint == quote_mint`.

**Question (b): does the binary harvest withheld fees?** — **NO.** No
TransferFee-extension instruction (outer opcode `26`/`0x1a`) is built anywhere
in the worker (0 occurrences). Harvest (`vec![26,4]`) exists only in
`migrate_v2` (`migrate_v2.rs:77`), never in a sell path.

**Question (c): what does the event record — gross or net?** — **GROSS.**
`quote_amount = quote` and the native-gated `sol_amount = quote` are the raw AMM
quote, before protocol/creator fees and before any Token-2022 transfer fee
(`0x28ed0` stores `[r10-0x620]`=quote). The user-received `output` is not
recomposed into the event after the transfer.

**Material consequence (the actual bug, in-binary and in-source alike).**
`sell_v2` accepts an arbitrary non-native quote mint, including a **Token-2022
mint with a `TransferFeeConfig`**. For the quote payout it issues a plain
`transfer_checked` of `output` lamports-equivalent from the curve ATA to the
user ATA. The **Token-2022 program itself deducts the mint's transfer fee on
that CPI**, so the user's ATA actually credits `output − token2022_fee(output)`,
strictly **less than `output`**, while the program's `require!(output ≥ minimum)`
guard was evaluated on the pre-fee `output`. Result:
- A seller can receive **less than their specified `minimum`** quote with the
  transaction still succeeding — the slippage guard is bypassed by the
  transfer-fee skim. **WHO loses WHAT:** any seller of a curve whose quote is a
  fee-bearing Token-2022 mint loses up to the mint's `transfer_fee_basis_points`
  (capped by `maximum_fee`) of their proceeds **below the slippage floor they
  set**, per sell.
- The emitted `TradeEvent.quote_amount`/`sol_amount` **overstate** what the
  seller received (gross, not net), so indexers/UIs mis-report fills.
- Withheld fees accumulate on the destination ATAs and are **never harvested**
  by the sell path (only `migrate_v2` harvests), so value is stranded on the
  quote ATAs until/unless a migration runs.

**Severity note:** this is a real accounting/slippage-bypass consequence, but it
is a property of BOTH the deployed binary AND the recovered source — it is **not**
a binary-vs-recovered-source divergence. The RE conclusion is that the recovered
`sell_v2.rs` already captures the binary's behavior exactly; no missing
`util/transfer_fee.rs` logic exists in the deployed `sell_v2`.

---

## Handler: `sell_v3` — `trade::sell` @ 0x29515

**1. Purpose + quote routes.** Current sell. Quote is **restricted to WSOL or
USDC** by `check_quote` (trade.rs): WSOL/default → native (`Ok(None)`); USDC →
non-native (`Ok(Some(decimals))`); anything else →
`ReconstructionBranchUnsupported`. **USDC is standard SPL (no transfer fee)**, so
sell_v3 has no fee-bearing-quote exposure. Rejects cashback coins
(`CashbackCoinNotSupported`).

**2. Accounts validated.** `#[event_cpi]` SellV3: global, base_mint, quote_mint
(unchecked; validated by `check_quote`), base/quote token programs, bonding_curve
(PDA), associated_base_bonding_curve/base_user (ATA), associated_quote_*
(unchecked, validated in `check_quote`: owner==quote_token_program, mint==USDC,
ATA address, user/ buyback ownership), user_volume_accumulator,
fee_config (owner==FEE_PROGRAM, PDA), buyback_fee_recipient, system_program.

**3. Errors/order.** `prepare_bonding_curve` (rent) → `check_quote` →
`CashbackCoinNotSupported` → `BondingCurveComplete` → `SellZeroAmount` →
`NotEnoughTokensToSell` → (native) buyback membership → fee_config read →
`FeeTiersEmpty` → fee math → **`TooLittleSolReceived` (`0x1773`, worker
`0x29622`)** on **gross** `user_output = quote − pf − cf` → base transfer_checked
→ payout. Fees come from `FeeConfig` tiers (`selected()` by market cap; stable
tiers for USDC).

**4. CPIs.** fee via local `FeeConfig` read (not a CPI invoke like v1/v2);
base `transfer_checked` (user→curve); non-native(USDC): **2× `transfer_checked`**
(`user_output`→user, `buyback_fee`→buyback), each plain opcode-12. Native:
lamport moves. **No opcode-26 TransferFee CPI** (0 `0x1a` in worker).

**5. Fee math.** `fee(a,b)=(a·b+9999)/10000`; `buyback_fee=pf·buyback_bps/10000`;
`user_output=quote−pf−cf`; curve accrues `creator_fee += cf`,
`protocol_fees += (pf−bf)`.

**6. TradeEvent.** `sol_amount=is_sol?quote:0`, `quote_amount=quote`,
`fee_recipient=Pubkey::default()`, `quote_mint=curve.quote_mint`, no cashback
(`cashback_*=0`), `shareholders=[]`, `ix_name="sell"`,
`unparsed_trailing_field=0`. Serializer `0x2c496` ×2.

**7. GAP vs `trade.rs::sell`.** None material — binary matches source. Min-check
on gross `user_output`; USDC-only non-native quote means the transfer-fee issue
of sell_v2 cannot arise here.

---

## Cross-handler summary

| | sell | sell_v2 | sell_v3 |
|---|---|---|---|
| quote mints | native only | **native + ANY curve quote (incl. Token-2022 fee mint)** | WSOL/USDC only |
| quote transfers | none (lamports) | 4× `transfer_checked` (op 12) | 2× `transfer_checked` (op 12) |
| min-output check basis | gross `output` | **gross `output`** | gross `user_output` |
| Token-2022 fee computed? | n/a | **NO** | n/a (USDC) |
| harvest withheld? | no | **NO** | no |
| event quote_amount | gross | **gross** | gross |
| opcode-26 (TransferFee) CPI | 0 | **0** | 0 |

**Decisive finding:** the deployed `sell_v2` neither computes a Token-2022 quote
transfer fee, nets it against `minimum`, nor harvests withheld fees; it records
the gross quote in the event. This exactly matches the recovered `sell_v2.rs`
(which also omits all of it). The binary contains no `sell_v2`-side
`util/transfer_fee.rs` logic to reverse — the only harvest/extension-aware code
in the whole program is in `migrate_v2`. The practical transfer-fee
minimum-output/event mismatch is a genuine property of the program (slippage
guard + event are computed on gross, while Token-2022 skims the quote payout),
present identically in binary and source.
