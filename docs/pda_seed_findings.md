# PDA / seed findings (deployed binaries + on-chain round-trip)

Measured on the four captured programs (`evidence/original/{pump,pump_amm,pump_fees,mayhem}/deployed.so`).
Tags: **[B]** = the seed literal bytes, the `lddw` + `R_BPF_64_RELATIVE` site, the length
immediates, the count immediate and the syscall site are all in the deployed ELF.
**[C]** = additionally closed against mainnet state with `tools/pda_derive_check.py`.

Generated data: `docs/pda_seed_catalog.md` (tables) and `maps/pda_seeds.json` (every site).
Tool: `tools/pda_catalog.py`.

## 1. What this adds to upstream/master

Upstream records seed prefixes inside its per-instruction account lists, tagged `[R]` (from the
reconstruction): `docs/gate_catalogs.md` gives `` `bonding_curve` (`["bonding-curve",
mint]`) `` for the pump trade handlers, and `specs-fees` / `specs-mayhem` name the fee and mayhem
PDAs in the same style.

This PR adds the binary measurement behind those lists, for **all four programs**: the seed
vector of each derivation call with its literal bytes, `.rodata` address, measured lengths, the
count immediate, the call site and the program-id argument. "The account list says the seeds are
`["bonding-curve", mint]`" becomes "the instruction at `insn 0x33e8` builds
`SolBytes[2] = {rodata 0x1b683a, 13} :: {frame, 32}` and derives it under `6EF8rrect…`" — a
statement that can be checked and, for the singleton PDAs, closed against chain state (§4).

## 2. Method

`sbftool.py` decodes `.text`; the loader here also applies `.rel.dyn` (`R_BPF_64_32` → syscall
name, `R_BPF_64_RELATIVE` → the `lddw` whose low 32 bits are the target VA), drops relocated call
sites from the function starts, adds `e_entry`, and bounds the last function by the last decoded
pc (the three corrections measured in #2).

Anchor builds a `SolBytes` array in the frame: `{addr: *const u8, len: u64}` per seed, 16 bytes
apart. For each derivation call the argument registers `r1..r5` are abstract-interpreted from the
function entry, and a seed array is accepted when a `(base, n)` pair has an immediate length in
every one of the `n` slots and each address is either a relocated `.rodata` pointer (literal, or
a hard-coded 32-byte key such as a program id) or a pointer into the frame. Identification is
therefore independent of the C ABI argument order. The PDA syscalls sit in one-line wrapper
functions in pump / pump_amm / pump_fees, so the analysed site is the call *to the wrapper* and
the enclosing function is the caller.

## 3. Coverage

| program | insns | functions | derivation sites | seed vectors recovered | handlers |
|---|---:|---:|---:|---:|---:|
| pump | 215873 | 906 | 202 | 110 | 53 |
| pump_amm | 139524 | 663 | 88 | 46 | 38 |
| pump_fees | 96083 | 489 | 84 | 48 | 31 |
| mayhem | 83947 | 374 | 96 | 25 | 25 |

`pump` is 199 `sol_try_find_program_address` + 2 `sol_create_program_address` + 1
`sol_invoke_signed_rust`; `mayhem` is 70 + 26 `sol_invoke_signed_rust` and no
`create_program_address`. Every site is recorded in `maps/pda_seeds.json` with its argument
shapes, including the ones whose pointer or count is a register value at the call — those are the
next pass, and their `arg_shapes` field names the registers to follow.

## 4. Round-trip validation against mainnet [C]

`tools/pda_derive_check.py` derives `find_program_address` offline (pure-Python ed25519 on-curve
test) for the recovered vectors and reads the resulting account. Measured output:

```
G1 ["global"] @pump: 4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5SKy2uB4Jjaxnjf (bump 255) -> len=1088 owner=6EF8… disc=a7e8e8b1c86c727f owner_ok=True disc_ok=True
G2 ["fee_config", pump] @fees: 8Wf5TiAheLUqBrKXeYg2JtAFFMWtKdG2BSFgqUcPVwTt (bump 253) -> len=4097 owner=pfeeUx… disc=8f3492bbdb7b4c9b owner_ok=True disc_ok=True
G4 ["fee-program-global"] @fees: CHqnuTkj6sXDFknM652aEFPECZh9qVsBXWkhPohmV9dA (bump 254) -> len=338 owner=pfeeUx… disc=a2a5f5311d2537f2 owner_ok=True disc_ok=True
G5 ["fee_config", amm] @fees: 5PHirr8joyTMp9JMm6nW7hNDVyEYdkzDqazxPD7RaTjx (bump 255) -> len=4097 owner=pfeeUx… disc=8f3492bbdb7b4c9b owner_ok=True disc_ok=True
```

- **G1** closes `["global"]` under pump: the derived address holds a 1088-byte pump-owned
  `Global` account (`a7e8e8b1c86c727f`), which matches the 1088-byte size upstream documents.
- **G2/G5** close the recovered `fee_config + key(program id) + 1-byte` vector, i.e. the address
  derived from `["fee_config", <pump id>]` under the **fees** program is a 4097-byte fees-owned
  `FeeConfig` (`8f3492bbdb7b4c9b`), and the same holds for the AMM id. That is the vector
  recovered at pump `insn 0x1b90f` / `0x20a60` and pump_amm `0x16a41` / `0x1798d`: the extra key
  seed is the *caller's* program id and the trailing byte is the bump.
- **G4** closes `["fee-program-global"]` under fees (338-byte `FeeProgramGlobal`,
  `a2a5f5311d2537f2`), the vector recovered as `fee-program-global + {1B}` at seven pump_fees
  sites — the single dynamic byte in those vectors is the bump.

The remaining dynamic seeds are account/mint keys; resolving them to account indices is the next
step, and the per-site `arg_shapes` in the JSON names the registers that carry them.

## 5. Findings

### F1 — seed vocabulary: 22 prefixes, 3 key seeds [B]

Recovered as vector elements (sites = derivation sites loading that literal):

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
- pump `insn 0x17595` (fn `0x16caf`): `lddw r1, 0x1b74a9` at `insn 0x17581`, stored to
  `[fp-0x4a0]`, length `0xd` at `[fp-0x498]`, count `2` at `insn 0x17594` (r3), program id at
  `[fp-0x508]` → `["creator_vault", <32-byte key>]`.
- pump_fees `insn 0xf307` / `0xfbcc` derive `creator_vault + {32B}` under the **AMM** id, while
  `0xf162` derives `creator-vault + {32B}` under the **pump** id.

Both literals being seeds means the two derive different addresses, so each reference in a spec
belongs to exactly one of them.

### F3 — cross-program PDA ownership [B,C]

A program deriving another program's PDA carries that program's id as a seed, and the recovered
vectors show it:

| deriving site | vector | derived under |
|---|---|---|
| pump `0x1b90f`, `0x20a60`; pump_amm `0x16a41`, `0x1798d` | `fee_config + <pump/amm id> + bump` | pump_fees (**closed**, G2/G5) |
| pump `0x1518e`, `0x18143`; pump_fees `0xbc17`, `0xf003`, `0xf8b5` | `sharing-config + {32B} + bump` | pump and pump_fees |
| mayhem `0x744a`, `0xa99e`, `0xb2a6`, `0xbed2`, `0xc951` | `bonding-curve + {32B}` | pump |
| mayhem `0xaa6f`, `0xb37a` | `bonding-curve-v2 + {32B}` | — |
| pump `0x15f27` | `mayhem-state + {32B}` | mayhem |
| pump `0x3191`; pump_fees `0x55d0`, `0x5817` | `pool + <u16> + {32B}×3` | pump_amm |

A call can carry more than one 32-byte constant (pump `0x1526f` has the fees id in r1 and the
ATA id in r4 around the same three dynamic seeds), so the per-site record keeps every constant
with its register.

The fees `fee_config` PDA is therefore computed inside pump and pump_amm with the caller's id as
an extra seed, and mayhem recomputes pump's `bonding-curve` plus a `bonding-curve-v2` itself.

### F4 — Metaplex metadata PDA derived with the Metaplex id as a seed [B]

pump `0x1933a`, `0x196a8`, `0x2d378`; pump_amm `0x12918`: vector =
`metadata`(8) + key `metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s` + 32-byte frame key, count 3.
At `0x2d378` the three slots are `[fp-0xa58]=0x1b648f`, `[fp-0xa50]=0x8`,
`[fp-0xa48]=0x1b5bc8`, `[fp-0xa40]=0x20`, `[fp-0xa38]=<frame ptr>`, `[fp-0xa30]=0x20`, with
`mov64 r3, 0x3` at `0x2d377`: the canonical `["metadata", metaplex_id, mint]` shape, with the
site.

### F5 — ATA derivation: three dynamic seeds, no literal [B]

34 sites in pump, 4 in pump_amm, 2 in mayhem derive an address under
`ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL` with a vector of exactly three 32-byte frame keys
and no literal prefix (e.g. pump `0x14c9c`, `0x14dac`, `0x33274`; mayhem `0x12bcb`): SPL's
`(wallet, token_program, mint)`. The analyser reporting no literal for these is the internal
consistency check — there is none.

### F6 — `pool` vectors carry a 2-byte element [B]

Recovered as `pool`(4) + **2-byte** + 32-byte×3 under the AMM id (pump `0x3191`, `0x174ca`,
`0x1a49b`; pump_amm `0x12641`, `0x136f4`; pump_fees `0x714e`), and in pump_fees with a trailing
1-byte bump as well (`0x55d0`, `0x5817`: `pool + {2B} + {32B}×3 + {1B}`). The 2-byte dynamic
seed matches a `u16` pool index; no wider element appears in any recovered `pool` vector.

### F7 — mayhem inlines the PDA wrapper; the other three call one [B]

| program | derivation sites inside a handler function | via a wrapper function |
|---|---:|---:|
| pump | 0 | 202 |
| pump_amm | 0 | 88 |
| pump_fees | 0 | 84 |
| mayhem | 20 | 76 |

Every mayhem handler has one derivation in its own body (25/25 handlers): mayhem's
`find_program_address` call is inlined into the handler. In the other three programs the seed
array is built by the caller of a shared wrapper, which is where their account resolution lives.

## 6. Next

Resolve the dynamic seed slots to account indices (the `arg_shapes` registers in the JSON), then
close the remaining singletons the same way as §4 — the `pool` vectors and `mayhem-state` become
reachable as soon as one live pool / mayhem mint is in hand.
