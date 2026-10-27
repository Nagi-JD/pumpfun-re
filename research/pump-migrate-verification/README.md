# Pump migrate / migrate_v2: post_complete_quote_in verification (executed)

Date: 2026-10-27. Change under test: commit 5c1d9bf2c (`pump-r23-race`, packet `research/pump-r23-race-2/`, source `w_F`).

## Verdict: CONFIRMED

In every executed case, AFTER produces the same result as DEPLOYED on all compared fields: error, every tracked account's bytes after the run, events, inner CPIs and return data. When post_complete_quote_in = 0, all builds agree. When it is nonzero, BEFORE differs: the migrated quote it passes to the pump_amm `create_pool` CPI (native) or the quote `TransferChecked` (stable) is smaller by exactly post_complete_quote_in. At the overflow boundaries, DEPLOYED and AFTER fail with the same error at the same source line, while BEFORE succeeds.

This also confirms the field identification by execution. The bytes I seeded sit at account offset 158, which is `post_complete_quote_in` in the upstream IDL (`evidence/upstream/pump.json`). It is the last field of BondingCurve; the account is 166 bytes, offset 158..166. The deployed program adds exactly that value to the migrated quote, so its in-memory +0x98 is `post_complete_quote_in` and not some other field.

## Binaries (sha256)

| Role | File | sha256 |
|---|---|---|
| DEPLOYED | evidence/original/pump/deployed.so | 7a19affa…b02d |
| BEFORE (packet 1, cf3fd4823 = s10 clean rebuild) | /home/nagi/pumpround23/out/final-candidate.so | a016b22e…d6e8 |
| BEFORE_uD (control: err_at removed, migrate unchanged; w_D migrate*.rs == w1) | out/uD-candidate.so | cc45426e…5fb6 |
| AFTER (packet 2, matches packet candidate.sha256) | out/uF-candidate.so | e53249d6…9cd1 |

No rebuilds were needed.

## Harness

I reused lalalune's LiteSVM fixtures `/home/nagi/pumpre/repo/scripts/pump_migrate_probe.py` and `pump_migrate_v2_probe.py`. They load deployed pump, pump_amm, token, token-2022 and ATA, start from a saved completed curve (real_quote_reserves = 85,005,359,063, pool_migration_fee = 15,000,001), sign normally, and capture the real CPIs. Each candidate is loaded at the same program id.

The driver is `pump_migrate_verification/migdiff.py`. It patches bonding-curve bytes 158..166 (post_complete_quote_in), with the boost accounts present, and compares `error, after, events, inner, return` against DEPLOYED. The probes needed `solders` 0.27.1, which I installed into a new venv at `/home/nagi/migverify-venv`.

Full raw output: `pump_migrate_verification/out_v1.txt`, `out_v2.txt`, `out_v2s.txt`.

## Results (mismatched fields vs DEPLOYED)

### migrate
| Case | DEPLOYED error | BEFORE | BEFORE_uD | AFTER |
|---|---|---|---|---|
| post=0 | ok | [] | [] | [] |
| post=12345 | ok | after, events, inner | after, events, inner | [] |
| post=1e9 (+1e9 curve lamports) | ok | after, events, inner | after, events, inner | [] |
| post=u64max | Custom 6024 Overflow, `migrate.rs:280` | error (BEFORE succeeds) + all | same | [] (same error and line) |
| post=2^64−rq (sum wraps by 0) | 6024 @ migrate.rs:280 | error + all | same | [] |
| post=2^64−1−rq (sum=u64max) | ArithmeticOverflow (later) | error + all | same | [] |

### migrate_v2 native
Same six cases with the same pattern. Overflow cases fail with `6024 @ migrate_v2.rs:309` on DEPLOYED and AFTER. The u64max-sum case fails with ArithmeticOverflow on both. AFTER = [] in all cases, and BEFORE differs in every case where post ≠ 0.

### migrate_v2 stable quote (quote ATA funded to rq+post)
| Case | BEFORE | AFTER |
|---|---|---|
| post=0 | [] | [] |
| post=12345 | after, events, inner | [] |
| post=1e9 | after, events, inner | [] |

I also ran a stable case without the extra quote balance. DEPLOYED and AFTER both fail with Token `insufficient funds` (Custom 1) because they try to transfer rq+post; BEFORE succeeds. That is again AFTER == DEPLOYED.

## The CPI amount (decoded from captured inner-instruction bytes)

- **Native, pump_amm create_pool quote arg:**
  - BEFORE: 84,990,359,062 (= rq − fee)
  - DEPLOYED and AFTER, post=12345: 84,990,371,407 (+12,345)
  - DEPLOYED and AFTER, post=1e9: 85,990,359,062 (+1,000,000,000)
- **Stable, TransferChecked amount** (no fee subtracted on the stable path, as in the source):
  - BEFORE: 85,005,359,063
  - DEPLOYED and AFTER, post=12345: 85,005,371,408 (+12,345)
  - DEPLOYED and AFTER, post=1e9: 86,005,359,063 (+1e9)
- **Curve lamports after native migrate:** BEFORE leaves post_complete_quote_in lamports on the curve. DEPLOYED and AFTER move them out (660,825,647 vs 660,837,992 at post=12345).

Side note, the same on every binary: the pool quote vault grows by 9,791 for a +12,345 create_pool arg. The difference happens inside pump_amm and is not related to this change.

## Limits

- The state is synthetic: a saved curve with patched fields. The compared fields are the probe's tracked accounts plus the full logs/CPIs; the rest of the bank is not compared.
- Stable cases use the probe's synthetic whitelisted quote mint.
- The pump-r23-race source was not modified.
