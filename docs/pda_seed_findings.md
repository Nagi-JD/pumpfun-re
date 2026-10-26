# PDA / seed findings (deployed binaries + on-chain round-trip)

Read-only RE of the four captured programs (`evidence/original/{pump,pump_amm,pump_fees,mayhem}/deployed.so`).
Tags: **[B]** = the seed literal bytes, the `lddw` + `R_BPF_64_RELATIVE` site, the length
immediates, the count immediate and the syscall site are all in the deployed ELF.
**[C]** = additionally closed against mainnet state with `tools/pda_derive_check.py`.

Generated data: `docs/pda_seed_catalog.md` (tables) and `maps/pda_seeds.json` (every site).
Tool: `tools/pda_catalog.py`.

## 1. What this adds that upstream/master does not have

Upstream documents seed *names* only as part of per-instruction account lists, tagged [R]
(from the read-only reconstruction), e.g. `` `bonding_curve` (`["bonding-curve", mint]`) `` in
`docs/gate_catalogs.md`, and it has no seed entry for `pump_fees` or `mayhem` outside those
lists. It never states *which site* builds a seed, never gives the `.rodata` address of a
prefix, and never says under which program id an address is derived.

This adds, for **all four programs**, a binary-measured seed vocabulary and per-call-site seed
vectors, plus the program-id argument recovered from the call. The practical difference is that
"the account list says seeds are `["bonding-curve", mint]`" becomes "this instruction at
`insn 0x33e8` builds `SolBytes[2] = {rodata 0x1b683a, 13} :: {frame, 32}` and derives it under
`6EF8rrect…`", which can be checked and, for singletons, closed against chain state.

## 2. Method (and why the ABI is not assumed)

`sbftool.py` decodes `.text` but not `.rel.dyn`; the loader applies `.rel.dyn`
(`R_BPF_64_32` → syscall name, `R_BPF_64_RELATIVE` → the `lddw` whose low 32 bits are the
target VA), drops relocated call sites from the function starts, adds `e_entry`, and bounds
the last function by the last decoded pc (the three corrections measured in #2).

Anchor builds a `SolBytes` array in the frame: `{addr: *const u8, len: u64}` per seed, 16 bytes
apart. For each derivation call the argument registers `r1..r5` are abstract-interpreted from
the function entry; a seed array is accepted only when a `(base, n)` pair exists such that all
`n` slots have an immediate length and each address is either a relocated `.rodata` pointer
(literal or hard-coded 32-byte key) or a pointer into the frame. Identification therefore does
not depend on the C ABI argument order, and a shape that does not fit is rejected instead of
guessed. When no argument carries the count as an immediate, the count is taken from the array
boundary; those rows are marked `count_source = boundary` in the JSON and only three such rows
exist (`social-fee-pda` in pump_fees), so they are called out below.

The PDA syscalls sit in one-line wrapper functions in pump / pump_amm / pump_fees, so the
analysed site is the call *to the wrapper* and the enclosing function is the caller.

## 3. Coverage

| program | insns | functions | derivation sites | seed vector recovered | not recovered | handlers |
|---|---:|---:|---:|---:|---:|---:|
| pump | 215873 | 906 | 202 | 110 | 92 | 53 |
| pump_amm | 139524 | 663 | 88 | 46 | 42 | 38 |
| pump_fees | 96083 | 489 | 84 | 48 | 36 | 31 |
| mayhem | 83947 | 374 | 96 | 25 | 71 | 25 |

`pump` is 199 `sol_try_find_program_address` + 2 `sol_create_program_address` + 1
`sol_invoke_signed_rust`; `mayhem` is 70 + 26 `sol_invoke_signed_rust` and no
`create_program_address`. The unrecovered sites are vectors whose pointer or count is a register
value at the call (seeded from a callee return or forwarded as an argument), which the local
interpretation cannot resolve; they are listed with `array: null` rather than guessed.

## 4. Round-trip validation against mainnet [C]

`tools/pda_derive_check.py` derives `find_program_address` offline (pure-Python ed25519 on-curve
test, no toolchain) for the recovered vectors and asks a public RPC for the account. Measured
output:

```
G1 ["global"] @pump: 4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5SKy2uB4Jjaxnjf (bump 255) -> len=1088 owner=6EF8… disc=a7e8e8b1c86c727f owner_ok=True disc_ok=True
G2 ["fee_config", pump] @fees: 8Wf5TiAheLUqBrKXeYg2JtAFFMWtKdG2BSFgqUcPVwTt (bump 253) -> len=4097 owner=pfeeUx… disc=8f3492bbdb7b4c9b owner_ok=True disc_ok=True
G3 ["mayhem-state", pump] @mayhem: CM6rMhAQJs6QaJppS4yBkv71N1FfBdjWgCeH8n9s9kuG (bump 255) -> DOES NOT EXIST (variable seed is not the pump id)
G4 ["fee-program-global"] @fees: CHqnuTkj6sXDFknM652aEFPECZh9qVsBXWkhPohmV9dA (bump 254) -> len=338 owner=pfeeUx… disc=a2a5f5311d2537f2 owner_ok=True disc_ok=True
G5 ["fee_config", amm] @fees: 5PHirr8joyTMp9JMm6nW7hNDVyEYdkzDqazxPD7RaTjx (bump 255) -> len=4097 owner=pfeeUx… disc=8f3492bbdb7b4c9b owner_ok=True disc_ok=True
```

- **G1** closes `["global"]` under pump: the derived address holds a 1088-byte pump-owned
  account with disc `a7e8e8b1c86c727f` (`Global`), which also confirms the 1088-byte size
  upstream documents for this account.
- **G2/G5** close the recovered `fee_config + key(program id) + 1-byte` vector: the address
  derived from `["fee_config", <pump id>]` under the **fees** program is a 4097-byte
  fees-owned `FeeConfig` (`8f3492bbdb7b4c9b`), and the same holds for the AMM id. This is the
  vector recovered at pump `insn 0x1b90f` / `0x20a60` and pump_amm `0x16a41` / `0x1798d`,
  i.e. the extra key seed is the *caller's* program id and the trailing byte is the bump.
- **G4** closes `["fee-program-global"]` under fees (338-byte `FeeProgramGlobal`,
  `a2a5f5311d2537f2`), which is the vector recovered as `fee-program-global + {1B}` at seven
  pump_fees sites: the one dynamic byte in those vectors is the bump.
- **G3** is a negative control: deriving `["mayhem-state", <pump id>]` produces an address that
  does not exist, so the second seed of the mayhem-state vector is *not* the pump id and is not
  claimed to be.

What is *not* claimed: no PDA was computed for a vector whose dynamic seeds are unknown (no mint
or creator key is available here), and nothing below is a byte-identity or behavioral-MATCH claim.

## 5. Findings

### F1 — seed vocabulary: 22 prefixes, 3 key seeds [B]

Recovered as vector elements (sites = number of derivation sites loading that literal):

`bonding-curve`(13) 31 · `bonding-curve-v2`(16) 4 · `boost_vault`(11) 2 · `buyback-vault`(13) 3 ·
`creator-vault`(13) 16 · `creator_vault`(13) 9 · `donation-fee-pda`(16) 2 ·
`fee-program-global`(18) 7 · `fee-recipient`(13) 1 · `fee_config`(10) 16 · `holder-rewards`(14) 4 ·
`mayhem-state`(12) 9 · `metadata`(8) 4 · `pool`(4) 9 · `pool-authority`(14) 18 · `pool-v2`(7) 3 ·
`pool_lp_mint`(12) 3 · `referral-vault`(14) 1 · `sharing-config`(14) 13 · `social-fee-pda`(14) 3 ·
`sol-vault`(9) 5 · `user_volume_accumulator`(23) 20.

Three hard-coded 32-byte **keys** appear in the address position of a seed: the pump id
(`6EF8…`, pump 0x1b79df), the AMM id (`pAMM…`, pump_amm 0x11e53e) and the Metaplex id
(`metaqbx…`, pump 0x1b5bc8 / pump_amm 0x11bdb0). Per-program `.rodata` addresses for every
literal are in `docs/pda_seed_catalog.md` §"Seed / prefix vocabulary".

### F2 — two distinct creator-vault prefixes coexist [B]

`creator-vault` (hyphen) and `creator_vault` (underscore) are two different literals, both used
as seed prefixes in the same three programs:

| literal | pump | pump_amm | pump_fees |
|---|---|---|---|
| `creator-vault` (13) | 0x1b69ca | 0x11e28e | 0xc4de0 |
| `creator_vault` (13) | 0x1b74a9 | 0x11c868 | 0xc4ded |

- pump `insn 0x4911`: `creator-vault` + 32-byte key, derived under the pump id.
- pump `insn 0x17595`, function `0x16caf`: `lddw r1, 0x1b74a9` at `insn 0x17581`, stored to
  `[fp-0x4a0]`, length `0xd` at `[fp-0x498]`, count `2` at `insn 0x17594` (r3), program id at
  `[fp-0x508]` → `["creator_vault", <32-byte key>]`.
- pump_fees `insn 0xf307` / `0xfbcc` derive `creator_vault + {32B}` under the **AMM** id, while
  `0xf162` derives `creator-vault + {32B}` under the **pump** id.

Both literals being seeds means the two derive different addresses; a spec that quotes one
prefix for all creator-vault references (or silently normalises the underscore) is describing a
different account.

### F3 — cross-program PDA ownership [B,C]

A program deriving another program's PDA needs that program's id as a seed, and the recovered
vectors show exactly that:

| deriving site | vector | derived under |
|---|---|---|
| pump `0x1b90f`, `0x20a60`; pump_amm `0x16a41`, `0x1798d` | `fee_config + <pump/amm id> + bump` | pump_fees (**closed**, G2/G5) |
| pump `0x1518e`, `0x18143`; pump_fees `0xbc17`, `0xf003`, `0xf8b5` | `sharing-config + {32B} + bump` | pump and pump_fees |
| mayhem `0x744a`, `0xa99e`, `0xb2a6`, `0xbed2`, `0xc951` | `bonding-curve + {32B}` | pump |
| mayhem `0xaa6f`, `0xb37a` | `bonding-curve-v2 + {32B}` | not recovered |
| pump `0x15f27` | `mayhem-state + {32B}` | mayhem |
| pump `0x3191`; pump_fees `0x55d0`, `0x5817` | `pool + <u16> + {32B}×3` | pump_amm |

A call can carry more than one 32-byte constant (pump `0x1526f`, for instance, has the fees id
in r1 *and* the ATA id in r4 around the same three dynamic seeds), so the per-site record keeps
every constant and its register; none of the rows above rests on a single ambiguous constant.

So "the fees `fee_config` PDA" is not a fee-only derivation: it is computed inside pump and
pump_amm with the caller's id as an extra seed, and mayhem recomputes pump's `bonding-curve`
(and a `bonding-curve-v2`) itself.

### F4 — Metaplex metadata PDA derived with the Metaplex id as a seed [B]

pump `0x1933a`, `0x196a8`, `0x2d378`; pump_amm `0x12918`: vector =
`metadata`(8) + key `metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s` + 32-byte frame key, count 3.
At `0x2d378` the three slots are `[fp-0xa58]=0x1b648f`, `[fp-0xa50]=0x8`,
`[fp-0xa48]=0x1b5bc8`, `[fp-0xa40]=0x20`, `[fp-0xa38]=<frame ptr>`, `[fp-0xa30]=0x20`, with
`mov64 r3, 0x3` at `0x2d377`. That is the canonical `["metadata", metaplex_id, mint]` shape;
the docs' account lists mention the Metaplex program, this gives the seed vector and the site.

### F5 — ATA derivation: three dynamic seeds, no literal [B]

34 sites in pump, 4 in pump_amm, 2 in mayhem derive an address under
`ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL` with a vector of exactly three 32-byte frame
keys and no literal prefix (e.g. pump `0x14c9c`, `0x14dac`, `0x33274`; mayhem `0x12bcb`). That
is SPL's `(wallet, token_program, mint)` with no prefix — a useful internal consistency check
for the method: the analyser found no literal because there is none.

### F6 — `pool` vectors carry a 2-byte element [B]

Recovered as `pool`(4) + **2-byte** + 32-byte×3 under the AMM id (pump `0x3191`, `0x174ca`,
`0x1a49b`; pump_amm `0x12641`, `0x136f4`; pump_fees `0x714e`), and in pump_fees with a trailing
1-byte bump as well (`0x55d0`, `0x5817`: `pool + {2B} + {32B}×3 + {1B}`). The 2-byte dynamic
seed matches a `u16` pool index; nothing wider appears anywhere in the recovered `pool`
vectors.

### F7 — mayhem inlines the PDA wrapper; the other three do not [B]

| program | derivation sites inside a handler function | via a wrapper function |
|---|---:|---:|
| pump | 0 | 202 |
| pump_amm | 0 | 88 |
| pump_fees | 0 | 84 |
| mayhem | 20 | 76 |

Every mayhem handler has exactly one derivation in its own body (25/25 handlers), because
mayhem's `find_program_address` call is inlined into the handler. In the other three programs
the seed array is always built by the caller of a shared wrapper, which is why account
resolution appears "centralised" in those binaries.

## 6. Limits

- 229 of 470 derivation sites resolved. The rest have a register-valued pointer or count at the
  call; they are reported with `array: null`, not filled in.
- `social-fee-pda` (3 sites, pump_fees `0xe606`, `0xbf54`, `0xc2da`) is the only literal whose
  count came from the array boundary rather than an argument; treat its single-seed vector as
  partial. Every other row has `count_source = arg-imm`.
- A slot whose address register was lost is kept as `<?>` with its measured length; the count
  still comes from the argument, so the vector *shape* is authoritative while that slot's
  content is not.
- Roles ("this PDA is the creator vault of mint X") are read from the surrounding account
  resolution; only G1/G2/G4/G5 are closed against chain state.
- The dynamic seeds are not resolved to account indices here; that is the natural next step.
