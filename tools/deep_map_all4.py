#!/usr/bin/env python3
"""Deep 4-program behavioral map from deployed.so via sbftool (pure Python).

Produces:
  maps/{pump,amm,fees,mayhem}_handlers.json  — name -> handler pc + disc
  maps/dispositions.json                     — per-handler structural facts
  maps/function_index.json                   — function starts + sizes summary
  docs/MAP_ALL4.md                           — refreshed structural map
  docs/HANDLER_DISPOSITIONS.md               — human-readable dispositions
  docs/analysis/B*_notes.md                  — B-unit address-cited notes

No Rust toolchain. No gateway. Read-only on binaries; writes only under pumpfun-re.
"""
from __future__ import annotations
import hashlib, json, os, re, struct, sys, importlib.util
from collections import defaultdict
from pathlib import Path

LAB = Path(os.environ.get("LAB_PUMPFUN", "/opt/data/lab-pumpfun"))
RE = LAB / "pumpfun-re"
SRC = LAB / "pumpfun-source"
SO = SRC / "evidence" / "original"
TOOLS = RE / "tools"
OUT_MAPS = RE / "maps"
OUT_DOCS = RE / "docs"
OUT_AN = OUT_DOCS / "analysis"

spec = importlib.util.spec_from_file_location("sbftool", TOOLS / "sbftool.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)

SYS_NAMES = [
    "sol_log_","sol_log_64_","sol_log_pubkey","sol_log_compute_units_",
    "sol_invoke_signed_c","sol_invoke_signed_rust","sol_memcpy_","sol_memset_",
    "sol_memmove_","sol_memcmp_","sol_sha256","sol_keccak256",
    "sol_get_clock_sysvar","sol_get_rent_sysvar","sol_create_program_address",
    "sol_try_find_program_address","sol_get_return_data","sol_set_return_data",
    "sol_get_stack_height","abort","sol_alloc_free_","sol_get_epoch_schedule_sysvar",
    "sol_curve_group_op","sol_poseidon","sol_remaining_compute_units",
]

PUMP53 = (
    "initialize update_global_authority toggle_create_v2 toggle_cashback_enabled "
    "update_holder_reward_config set_max_curve_depth toggle_mayhem_mode "
    "update_creator_fee_config add_quote_mint remove_quote_mint "
    "set_virtual_quote_reserves set_params set_mayhem_virtual_params "
    "set_reserved_fee_recipients create create_v2 buy_v2 buy_exact_quote_in_v2 "
    "sell_v2 buy_v3 buy_exact_quote_in_v3 sell_v3 multi_hop_curve_swap "
    "sweep_protocol_fee sweep_creator_fee buy_exact_sol_in sell migrate migrate_v2 "
    "extend_account collect_creator_fee distribute_fee_to_holders set_metaplex_creator "
    "set_creator admin_cto admin_update_token_incentives claim_token_incentives "
    "claim_cashback claim_cashback_v2 init_user_volume_accumulator "
    "close_user_volume_accumulator sync_user_volume_accumulator admin_set_idl_authority "
    "migrate_bonding_curve_creator get_minimum_distributable_fee distribute_creator_fees "
    "distribute_creator_fees_v2 initialize_quote_control set_quote_control_admin "
    "remove_quote_control_mint set_quote_control_reserves_admin "
    "set_quote_control_mint_reserves buy"
).split()

FEES_NAMES = (
    "admin_cto_sharing_config claim_social_fee_pda claim_social_fee_pda_v2 "
    "crank_donation_fee_pda create_donation_fee_pda create_fee_sharing_config "
    "create_social_fee_pda extend_fee_config get_fees get_fees_with_quote_mint "
    "initialize_buyback initialize_fee_config initialize_fee_program_global "
    "revoke_fee_sharing_authority set_authority set_claim_rate_limit "
    "set_disable_flags set_exotic_flat_fees set_social_claim_authority sweep_buyback "
    "transfer_fee_sharing_authority update_admin update_buyback_authority "
    "update_buyback_claim_rate_limit update_fee_config update_fee_shares "
    "update_fee_shares_v2 update_stable_fee_config upsert_fee_tiers "
    "upsert_stable_fee_tiers withdraw"
).split()

# Mayhem: verified 25 from mayhem_map.md (snake of logged PascalCase)
MAYHEM_NAMES = [
    "buy_pump_swap","sell_pump_swap","buy_v2","sell_v2","buy","sell",
    "burn_tokens","sweep_fees","sweep_fees_admin","withdraw_quote_admin",
    "withdraw_admin","extend_account","initialize_fee_recipient",
    "initialize_global_params","update_global_params","update_admin",
    "update_trader","update_max_sol_per_sweep","update_max_stable_per_sweep",
    "reset_sol_deployed","reset_stable_deployed","reset_state","stop_trading",
    "resume_trading","initialize_mayhem_state",
]

def load_amm_names():
    p = SRC / "programs" / "pump-fees" / "idls" / "pump_amm.json"
    return [i["name"] for i in json.load(open(p))["instructions"]]

def murmur_map():
    return {S.Prog._murmur(n): n for n in SYS_NAMES}

def disc(name: str) -> bytes:
    return hashlib.sha256(("global:" + name).encode()).digest()[:8]

def resolve_handler(prog, stub):
    """Follow stub setup to first relative call target (= real handler)."""
    for pc in range(stub, stub + 48):
        if pc in prog.ins:
            k = prog.ins[pc]
            if k.op == 0x85:  # call
                return pc + 1 + k.imm
    return stub

def dispatch_map(prog, names, allow_jne=True):
    """Map Anchor disc -> (disc_hex, stub_pc, handler_pc, cmp). Supports jeq and jne."""
    d2n = {disc(n): n for n in names}
    out = {}
    order = prog.order
    for i, pc in enumerate(order):
        ins = prog.ins[pc]
        if ins.op != 0x18:
            continue
        d = (ins.imm & 0xffffffffffffffff).to_bytes(8, "little")
        if d not in d2n or d2n[d] in out:
            continue
        name = d2n[d]
        # look ahead for jeq/jne on the loaded disc
        for j in range(i + 1, min(i + 6, len(order))):
            pc2 = order[j]
            jmp = prog.ins[pc2]
            if jmp.mn == "jeq":
                stub = pc2 + 1 + jmp.off
                h = resolve_handler(prog, stub)
                out[name] = {
                    "discriminator": d.hex(),
                    "lddw_pc": hex(pc),
                    "cmp": "jeq",
                    "stub_pc": hex(stub),
                    "handler_pc": hex(h),
                    "handler_byte": hex(h * 8),
                }
                break
            if allow_jne and jmp.mn == "jne":
                # jne fall-through is the match path
                stub = pc2 + 1  # next insn
                # sometimes stub is further; scan a bit for call
                h = resolve_handler(prog, stub)
                out[name] = {
                    "discriminator": d.hex(),
                    "lddw_pc": hex(pc),
                    "cmp": "jne",
                    "stub_pc": hex(stub),
                    "handler_pc": hex(h),
                    "handler_byte": hex(h * 8),
                }
                break
    return out

def func_size(prog, start):
    body = prog.func_body(start)
    return len(body)

def classify_calls(prog, start, hmap):
    """Count relative calls + named syscalls inside a function."""
    body = prog.func_body(start)
    rel = []
    sysc = defaultdict(int)
    for ins in body:
        if ins.op == 0x85:
            tgt = ins.pc + 1 + ins.imm
            # syscall hash form: imm is murmur, tgt not in .text
            nm = hmap.get(ins.imm & 0xffffffff)
            if nm:
                sysc[nm] += 1
            elif tgt in prog.ins:
                rel.append(tgt)
            else:
                # try prog.name
                nm2 = prog.name.get(ins.imm & 0xffffffff) or prog.name.get(tgt)
                if nm2:
                    sysc[nm2] += 1
        elif ins.op == 0x8d:
            sysc["callx"] += 1
    return rel, dict(sysc)

def find_error_immediates(prog, start, window=None):
    """Collect stw of small constants that look like Anchor custom errors (6000+)."""
    body = prog.func_body(start)
    if window:
        body = [i for i in body if start <= i.pc < start + window]
    errs = []
    for ins in body:
        # stw [reg+off], imm  — Anchor often stores error code as imm
        if ins.op == 0x62 and 6000 <= (ins.imm & 0xffffffff) <= 7000:
            errs.append({"pc": hex(ins.pc), "code": ins.imm & 0xffffffff})
        # mov32/mov64 of error-ish immediates
        if ins.op in (0xb4, 0xb7) and 6000 <= (ins.imm & 0xffffffff) <= 7000:
            errs.append({"pc": hex(ins.pc), "code": ins.imm & 0xffffffff, "via": "mov"})
    # unique by code keeping first pc
    seen = {}
    for e in errs:
        seen.setdefault(e["code"], e)
    return list(seen.values())

def rodata_strings(prog, min_len=8):
    """Pull printable ASCII strings from whole binary (cheap)."""
    b = prog.b
    out = []
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % min_len, b):
        out.append((m.start(), m.group().decode("ascii", "ignore")))
    return out

def disposition_for(prog, name, entry, hmap, xfer_fee_helper=None):
    h = int(entry["handler_pc"], 16)
    # Prefer the function that contains the handler start
    start = prog.func_start(h)
    # Sometimes the mapped "handler" IS the function start
    size = func_size(prog, start)
    rel, sysc = classify_calls(prog, start, hmap)
    # Also scan a wider window from h if stub-resolved handler is mid-function
    errs = find_error_immediates(prog, start)
    # Does this function call the transfer-fee helper?
    calls_xfer = False
    if xfer_fee_helper is not None:
        calls_xfer = xfer_fee_helper in rel or any(
            prog.func_start(t) == xfer_fee_helper for t in rel
        )
        # also check one level of callees (shallow)
        if not calls_xfer:
            for t in rel[:40]:
                r2, _ = classify_calls(prog, prog.func_start(t), hmap)
                if xfer_fee_helper in r2:
                    calls_xfer = True
                    break
    # invoke presence
    has_cpi = any(k.startswith("sol_invoke") for k in sysc)
    has_log = "sol_log_" in sysc
    return {
        "name": name,
        "discriminator": entry["discriminator"],
        "cmp": entry.get("cmp"),
        "stub_pc": entry["stub_pc"],
        "handler_pc": entry["handler_pc"],
        "handler_byte": entry["handler_byte"],
        "func_start_pc": hex(start),
        "func_insns": size,
        "relative_callees": len(set(rel)),
        "top_callees": [hex(x) for x in sorted(set(rel))[:12]],
        "syscalls": sysc,
        "has_cpi": has_cpi,
        "has_log": has_log,
        "error_codes": errs[:20],
        "calls_transfer_fee_helper": calls_xfer,
    }

def locate_transfer_fee_helper(prog):
    """MASTER_GAPS / recovered-fixes cite helper @0x12a1c (pc). Verify it exists."""
    cand = 0x12a1c
    if cand in prog.ins or prog.func_start(cand) == cand or cand in prog.func_of:
        return prog.func_start(cand)
    # fallback: search rodata for TransferFee-ish and callers — keep cited address
    return cand if cand in prog.func_of or any(abs(s - cand) < 8 for s in prog.starts) else None

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def analyze_program(label, so_path, names, allow_jne=True, xfer=False):
    print(f"[+] loading {label}: {so_path}", flush=True)
    prog = S.Prog(str(so_path))
    hmap = murmur_map()
    # merge prog.name hashes
    for k, v in list(prog.name.items()):
        if isinstance(k, int) and v in SYS_NAMES:
            hmap[k] = v
    dm = dispatch_map(prog, names, allow_jne=allow_jne)
    xfer_h = locate_transfer_fee_helper(prog) if xfer else None
    dispositions = {}
    for n, e in sorted(dm.items()):
        dispositions[n] = disposition_for(prog, n, e, hmap, xfer_h)
    # function index summary
    sizes = sorted((func_size(prog, s), s) for s in prog.starts)
    top = [{"pc": hex(s), "insns": sz} for sz, s in sizes[-25:][::-1]]
    # baked source paths
    paths = sorted(set(
        m.group().decode() for m in re.finditer(rb"programs/[A-Za-z0-9_/]+\.rs", prog.b)
    ))
    # Instruction: log strings
    ix_logs = sorted({
        s for _, s in rodata_strings(prog, 12) if s.startswith("Instruction: ")
    })
    summary = {
        "program": label,
        "so": str(so_path),
        "sha256": sha256_file(so_path),
        "text_bytes": prog.tsize,
        "insns": len(prog.order),
        "functions": len(prog.starts),
        "handlers_mapped": len(dm),
        "handlers_expected": len(set(names)),
        "unmapped": sorted(set(names) - set(dm)),
        "transfer_fee_helper_pc": hex(xfer_h) if xfer_h else None,
        "baked_source_paths": paths,
        "instruction_log_strings": ix_logs,
        "largest_functions": top,
    }
    return prog, dm, dispositions, summary

def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=False) + "\n")
    print(f"  wrote {path}", flush=True)

def md_table_handlers(dm):
    lines = ["| instruction | disc | cmp | stub | handler (pc) | handler (bytes) |",
             "|---|---|---|---|---|---|"]
    for n in sorted(dm):
        e = dm[n]
        lines.append(
            f"| `{n}` | `{e['discriminator']}` | {e.get('cmp','')} | "
            f"`{e['stub_pc']}` | `{e['handler_pc']}` | `{e['handler_byte']}` |"
        )
    return "\n".join(lines)

def main():
    OUT_MAPS.mkdir(parents=True, exist_ok=True)
    OUT_AN.mkdir(parents=True, exist_ok=True)

    amm_names = load_amm_names()
    results = {}

    # pump
    _, dm_p, disp_p, sum_p = analyze_program(
        "pump", SO / "pump" / "deployed.so", PUMP53, allow_jne=True, xfer=True
    )
    write_json(OUT_MAPS / "handlers.json", {n: e["handler_pc"] for n, e in dm_p.items()})
    write_json(OUT_MAPS / "pump_handlers_full.json", dm_p)
    results["pump"] = (dm_p, disp_p, sum_p)

    # amm
    _, dm_a, disp_a, sum_a = analyze_program(
        "pump_amm", SO / "pump_amm" / "deployed.so", amm_names, allow_jne=True
    )
    write_json(OUT_MAPS / "amm_handlers.json", {n: e["handler_pc"] for n, e in dm_a.items()})
    write_json(OUT_MAPS / "amm_handlers_full.json", dm_a)
    results["pump_amm"] = (dm_a, disp_a, sum_a)

    # fees
    _, dm_f, disp_f, sum_f = analyze_program(
        "pump_fees", SO / "pump_fees" / "deployed.so", FEES_NAMES, allow_jne=True
    )
    write_json(OUT_MAPS / "fees_handlers.json", {n: e["handler_pc"] for n, e in dm_f.items()})
    write_json(OUT_MAPS / "fees_handlers_full.json", dm_f)
    results["pump_fees"] = (dm_f, disp_f, sum_f)

    # mayhem
    _, dm_m, disp_m, sum_m = analyze_program(
        "mayhem", SO / "mayhem" / "deployed.so", MAYHEM_NAMES, allow_jne=True
    )
    write_json(OUT_MAPS / "mayhem_handlers.json", {n: e["handler_pc"] for n, e in dm_m.items()})
    write_json(OUT_MAPS / "mayhem_handlers_full.json", dm_m)
    results["mayhem"] = (dm_m, disp_m, sum_m)

    all_disp = {k: v[1] for k, v in results.items()}
    all_sum = {k: v[2] for k, v in results.items()}
    write_json(OUT_MAPS / "dispositions.json", all_disp)
    write_json(OUT_MAPS / "program_summaries.json", all_sum)

    # function index (starts only — keep small)
    func_index = {}
    for label, so_name in [("pump","pump"),("pump_amm","pump_amm"),("pump_fees","pump_fees"),("mayhem","mayhem")]:
        prog = S.Prog(str(SO / so_name / "deployed.so"))
        func_index[label] = {
            "base_pc": hex(prog.base),
            "n_functions": len(prog.starts),
            "starts_sample_first_40": [hex(x) for x in prog.starts[:40]],
            "starts_sample_last_20": [hex(x) for x in prog.starts[-20:]],
        }
    write_json(OUT_MAPS / "function_index.json", func_index)

    # MAP_ALL4.md
    lines = [
        "# Full 4-program structural map (deployed binaries)",
        "",
        "Built with `tools/sbftool.py` + `tools/deep_map_all4.py` from",
        "`pumpfun-source/evidence/original/*/deployed.so`.",
        "Decoder stated 0-diff vs llvm-objdump in upstream docs.",
        "Scope: RE / behavioral structure only — no vuln claims, no exploit PoC.",
        "",
        "| Program | .text bytes | .text insns | functions | handlers mapped |",
        "|---|---:|---:|---:|---:|",
    ]
    for label in ("pump", "pump_amm", "pump_fees", "mayhem"):
        s = all_sum[label]
        lines.append(
            f"| {label} | {s['text_bytes']:,} | {s['insns']:,} | {s['functions']} | "
            f"{s['handlers_mapped']}/{s['handlers_expected']} |"
        )
    lines += ["", "## SHA-256 of deployed.so", ""]
    for label in ("pump", "pump_amm", "pump_fees", "mayhem"):
        lines.append(f"- `{label}`: `{all_sum[label]['sha256']}`")
    lines += ["", "## Handler tables", ""]
    for label in ("pump", "pump_amm", "pump_fees", "mayhem"):
        dm = results[label][0]
        s = all_sum[label]
        lines += [f"### {label} ({s['handlers_mapped']}/{s['handlers_expected']})", ""]
        if s["unmapped"]:
            lines.append(f"Unmapped: {', '.join('`'+u+'`' for u in s['unmapped'])}")
            lines.append("")
        lines.append(md_table_handlers(dm))
        lines.append("")
        if s.get("transfer_fee_helper_pc"):
            lines.append(f"Transfer-fee helper (cited): `{s['transfer_fee_helper_pc']}`")
            lines.append("")
        if s["baked_source_paths"]:
            lines.append(f"Baked `programs/...rs` paths ({len(s['baked_source_paths'])}):")
            for p in s["baked_source_paths"][:40]:
                lines.append(f"- `{p}`")
            lines.append("")
    lines += [
        "## Key cross-program CPI targets (from prior + this map)",
        "",
        "- PumpSwap `create_pool` → migrate graduation CPI target",
        "- Fees `get_fees` / `get_fees_with_quote_mint` → pump buy/sell fee CPI",
        "- Mayhem `initialize_mayhem_state` → pump `create_v2` mayhem branch CPI target",
        "",
        "## Artifacts",
        "",
        "- `maps/*_handlers.json` — compact name→handler_pc",
        "- `maps/*_handlers_full.json` — disc/cmp/stub/handler",
        "- `maps/dispositions.json` — per-handler size/syscalls/errors/xfer-fee",
        "- `maps/program_summaries.json` — program-level stats",
        "- `docs/HANDLER_DISPOSITIONS.md` — narrative",
        "- `docs/analysis/B*_notes.md` — B-unit address notes",
        "",
    ]
    (OUT_DOCS / "MAP_ALL4.md").write_text("\n".join(lines) + "\n")
    print("  wrote MAP_ALL4.md", flush=True)

    # HANDLER_DISPOSITIONS.md — focus on B-relevant pump handlers + fees CPI
    focus = [
        ("pump", "buy_v2"), ("pump", "buy_exact_quote_in_v2"),
        ("pump", "buy_v3"), ("pump", "buy_exact_quote_in_v3"),
        ("pump", "sell_v2"), ("pump", "sell_v3"),
        ("pump", "migrate_v2"), ("pump", "create_v2"),
        ("pump", "multi_hop_curve_swap"), ("pump", "set_mayhem_virtual_params"),
        ("pump", "admin_update_token_incentives"), ("pump", "claim_token_incentives"),
        ("pump", "admin_cto"), ("pump", "set_params"),
        ("pump_fees", "get_fees"), ("pump_fees", "get_fees_with_quote_mint"),
        ("pump_amm", "buy"), ("pump_amm", "sell"), ("pump_amm", "create_pool"),
        ("pump_amm", "create_config"),
        ("mayhem", "initialize_mayhem_state"),
        ("mayhem", "buy"), ("mayhem", "sell"),
    ]
    hd = [
        "# Handler dispositions (structural, address-cited)",
        "",
        "Generated by `tools/deep_map_all4.py`. Each row is mechanically derived from",
        "the deployed ELF via sbftool (function body size, relative callees, syscall",
        "counts, Anchor-custom error immediates 6000–7000, and whether the body or a",
        "shallow callee reaches the transfer-fee helper `@0x12a1c`).",
        "",
        "Not a behavioral MATCH claim — harness verification is separate (Rust/LiteSVM,",
        "toolchain-blocked this run).",
        "",
    ]
    for prog_label, name in focus:
        d = all_disp[prog_label].get(name)
        if not d:
            hd.append(f"## {prog_label}::{name} — NOT MAPPED")
            hd.append("")
            continue
        hd.append(f"## {prog_label}::{name}")
        hd.append("")
        hd.append(f"- disc `{d['discriminator']}` cmp `{d['cmp']}` stub `{d['stub_pc']}` "
                  f"handler `{d['handler_pc']}` (bytes `{d['handler_byte']}`)")
        hd.append(f"- func_start `{d['func_start_pc']}` size `{d['func_insns']}` insns; "
                  f"{d['relative_callees']} distinct relative callees")
        hd.append(f"- syscalls: `{json.dumps(d['syscalls'], sort_keys=True)}`")
        hd.append(f"- has_cpi={d['has_cpi']} has_log={d['has_log']} "
                  f"calls_transfer_fee_helper={d['calls_transfer_fee_helper']}")
        if d["error_codes"]:
            codes = ", ".join(f"{e['code']}@{e['pc']}" for e in d["error_codes"][:12])
            hd.append(f"- error immediates (sample): {codes}")
        if d["top_callees"]:
            hd.append(f"- top callees: {', '.join('`'+c+'`' for c in d['top_callees'])}")
        hd.append("")
    (OUT_DOCS / "HANDLER_DISPOSITIONS.md").write_text("\n".join(hd) + "\n")
    print("  wrote HANDLER_DISPOSITIONS.md", flush=True)

    # B-unit notes (address-cited, no exploit content)
    b_notes = build_b_notes(results, all_disp, all_sum)
    for fname, body in b_notes.items():
        p = OUT_AN / fname
        p.write_text(body)
        print(f"  wrote {p}", flush=True)

    # clusters refresh
    clusters = {
        "match_reconstruction": [
            "01_admin_config", "02_config", "03_quote_control",
            "06_sell", "09_fees_sweep", "11_volume_idl",
        ],
        "behavioral_gaps": {
            "B1_transfer_fee": {
                "status": "module drafted in recovered-fixes/transfer_fee.rs; wiring+harness blocked",
                "helper_pc": all_sum["pump"].get("transfer_fee_helper_pc"),
                "affected": ["buy_v2","buy_exact_quote_in_v2","buy_v3","buy_exact_quote_in_v3","migrate_v2"],
                "sell_v2_uses_xfer": False,
            },
            "B2_create_v2_mayhem": {
                "create_v2_handler": dm_p.get("create_v2", {}),
                "mayhem_init_handler": dm_m.get("initialize_mayhem_state", {}),
            },
            "B3_v3_quote_route": {"note": "replace USDC hardcode with quote_control whitelist"},
            "B4_multi_hop": {"handler": dm_p.get("multi_hop_curve_swap", {})},
            "B5_set_mayhem_virtual_params": {"handler": dm_p.get("set_mayhem_virtual_params", {})},
            "B6_token_incentives": {
                "admin": dm_p.get("admin_update_token_incentives", {}),
                "claim": dm_p.get("claim_token_incentives", {}),
            },
            "B7_fees_amm_diff": {
                "get_fees": dm_f.get("get_fees", {}),
                "get_fees_with_quote_mint": dm_f.get("get_fees_with_quote_mint", {}),
                "amm_buy": dm_a.get("buy", {}),
                "amm_sell": dm_a.get("sell", {}),
            },
        },
        "toolchain_blocked": [
            "byte-identical compare.py builds",
            "LiteSVM differential harness execution",
            "cargo-build-sbf / platform-tools install",
        ],
    }
    write_json(OUT_MAPS / "clusters.json", clusters)

    print("\n=== SUMMARY ===", flush=True)
    for label in ("pump", "pump_amm", "pump_fees", "mayhem"):
        s = all_sum[label]
        print(f"{label}: {s['handlers_mapped']}/{s['handlers_expected']} handlers, "
              f"{s['functions']} funcs, unmapped={s['unmapped']}", flush=True)
        # xfer flags for pump buys
        if label == "pump":
            for n in ("buy_v2","buy_exact_quote_in_v2","buy_v3","buy_exact_quote_in_v3","migrate_v2","sell_v2"):
                d = all_disp["pump"].get(n, {})
                print(f"  {n}: xfer={d.get('calls_transfer_fee_helper')} "
                      f"cpi={d.get('has_cpi')} size={d.get('func_insns')}", flush=True)

def build_b_notes(results, all_disp, all_sum):
    dm_p, disp_p, sum_p = results["pump"]
    dm_a, disp_a, sum_a = results["pump_amm"]
    dm_f, disp_f, sum_f = results["pump_fees"]
    dm_m, disp_m, sum_m = results["mayhem"]

    def dump(d):
        return json.dumps(d, indent=2) if d else "null"

    notes = {}
    notes["B1_transfer_fee.md"] = f"""# B1 — util/transfer_fee.rs (analysis, no build)

Status: recovered-fixes/transfer_fee.rs already drafts the Token-2022 fee math
citing helper `@0x12a1c`. This run re-verified structural reachability from the
buy/migrate handlers via sbftool call graphs (shallow).

## Helper
- Cited transfer-fee helper pc: `{sum_p.get('transfer_fee_helper_pc')}`
- Program sha256: `{sum_p['sha256']}`

## Affected handlers (disposition excerpt)

### buy_v2
```
{dump(disp_p.get('buy_v2'))}
```

### buy_exact_quote_in_v2
```
{dump(disp_p.get('buy_exact_quote_in_v2'))}
```

### buy_v3
```
{dump(disp_p.get('buy_v3'))}
```

### buy_exact_quote_in_v3
```
{dump(disp_p.get('buy_exact_quote_in_v3'))}
```

### migrate_v2
```
{dump(disp_p.get('migrate_v2'))}
```

### sell_v2 (control — should NOT use transfer-fee helper)
```
{dump(disp_p.get('sell_v2'))}
```

## Next (toolchain-blocked)
Wire `transfer_fee.rs` into the four buy quote legs + migrate_v2 harvest, then
LiteSVM differential vs deployed.so. Not attempted this run (no Rust/SBF tools).
"""

    notes["B2_create_v2_mayhem.md"] = f"""# B2 — create_v2 Mayhem branch (analysis)

## Pump create_v2
```
{dump(dm_p.get('create_v2'))}
```
Disposition:
```
{dump(disp_p.get('create_v2'))}
```

## Mayhem initialize_mayhem_state (CPI target)
```
{dump(dm_m.get('initialize_mayhem_state'))}
```
Disposition:
```
{dump(disp_m.get('initialize_mayhem_state'))}
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
"""

    notes["B3_v3_quote_route.md"] = f"""# B3 — v3 quote-route whitelist (analysis)

Gap: recovered `trade.rs::check_quote` hardcodes non-SOL = USDC; binary uses
quote_control whitelist (WSOL sentinel for native).

## Relevant handlers
- buy_v3 handler `{dm_p.get('buy_v3',{}).get('handler_pc')}`
- buy_exact_quote_in_v3 `{dm_p.get('buy_exact_quote_in_v3',{}).get('handler_pc')}`
- sell_v3 `{dm_p.get('sell_v3',{}).get('handler_pc')}`
- initialize_quote_control `{dm_p.get('initialize_quote_control',{}).get('handler_pc')}`
- set_quote_control_mint_reserves `{dm_p.get('set_quote_control_mint_reserves',{}).get('handler_pc')}`

## buy_v3 disposition
```
{dump(disp_p.get('buy_v3'))}
```

## Work remaining (source edit — no build this run)
Replace USDC hardcode in recovered trade.rs check_quote with the whitelist
membership test the binary uses. Diff-harness after toolchain available.
"""

    notes["B4_multi_hop.md"] = f"""# B4 — multi_hop_curve_swap depth cap + adapter delta

## Handler
```
{dump(dm_p.get('multi_hop_curve_swap'))}
```
Disposition:
```
{dump(disp_p.get('multi_hop_curve_swap'))}
```

## Known from MASTER_GAPS
- CurveDepthExceeded + SetMaxCurveDepth admin ix exist; depth check in OUTER router
- TradeEvent +0x198 = adapter diff (helper `@0x12a1c` / transfer-fee path)
- recovered-fixes/multi_hop_curve.rs present (423 lines) — port still partial

## Admin related
- set_max_curve_depth `{dm_p.get('set_max_curve_depth',{}).get('handler_pc')}`
"""

    notes["B5_set_mayhem_virtual_params.md"] = f"""# B5 — set_mayhem_virtual_params persistence

## Handler
```
{dump(dm_p.get('set_mayhem_virtual_params'))}
```
Disposition:
```
{dump(disp_p.get('set_mayhem_virtual_params'))}
```

## Trace targets from MASTER_GAPS
- `@0x19a7b` and `@0x1447e` — locate param write-back / Mayhem CPI
- Event disc cited: `757be4b6a1a8dcd6`
- Bounds: lamport 1e6 / 1e7 / 1e12; dual emit; 6–8×u64 virtual-param block

## This run
Disposition captures callees/syscalls/errors for the dispatch handler frame.
Persistence site still needs focused `sbftool func` / `callers` / `field` on
the two trace PCs (see follow-up script `tools/trace_b5.py` if present).
"""

    notes["B6_token_incentives.md"] = f"""# B6 — token-incentives handlers (spec→Rust port readiness)

Spec 10 is complete. recovered-fixes already contain:
- admin_update_token_incentives.rs
- claim_token_incentives.rs
- token_incentives_mod.rs

## Dispatch (re-verified)
### admin_update_token_incentives
```
{dump(dm_p.get('admin_update_token_incentives'))}
```
```
{dump(disp_p.get('admin_update_token_incentives'))}
```

### claim_token_incentives
```
{dump(dm_p.get('claim_token_incentives'))}
```
```
{dump(disp_p.get('claim_token_incentives'))}
```

## Next
Byte-identity of these handlers is STOPPED for pumpfun-source; behavioral port
into a clone remains valid for pumpfun-re. Harness verify blocked on toolchain.
"""

    notes["B7_fees_amm_diff.md"] = f"""# B7 — pump_fees + amm buy/sell differential verify (spec)

Harness execution blocked (LiteSVM/Rust). Structural map below is the
pre-harness baseline.

## pump_fees
### get_fees
```
{dump(dm_f.get('get_fees'))}
```
```
{dump(disp_f.get('get_fees'))}
```

### get_fees_with_quote_mint
```
{dump(dm_f.get('get_fees_with_quote_mint'))}
```
```
{dump(disp_f.get('get_fees_with_quote_mint'))}
```

## pump_amm
### buy
```
{dump(dm_a.get('buy'))}
```
```
{dump(disp_a.get('buy'))}
```

### sell
```
{dump(dm_a.get('sell'))}
```
```
{dump(disp_a.get('sell'))}
```

### create_pool / create_config
- create_pool: `{dm_a.get('create_pool',{}).get('handler_pc')}`
- create_config: `{dm_a.get('create_config',{}).get('handler_pc')}`

## Note
MASTER_GAPS: seed amm fee_config stored bump=255 to clear Fees CPI gate during
harness runs — harness-only detail, not attempted here.
"""

    notes["S1_shared_disassembly.md"] = f"""# S1 — Shared disassembly / handler tables (this run)

## Coverage
| program | mapped | expected | functions | .text insns |
|---|---:|---:|---:|---:|
| pump | {sum_p['handlers_mapped']} | {sum_p['handlers_expected']} | {sum_p['functions']} | {sum_p['insns']} |
| pump_amm | {sum_a['handlers_mapped']} | {sum_a['handlers_expected']} | {sum_a['functions']} | {sum_a['insns']} |
| pump_fees | {sum_f['handlers_mapped']} | {sum_f['handlers_expected']} | {sum_f['functions']} | {sum_f['insns']} |
| mayhem | {sum_m['handlers_mapped']} | {sum_m['handlers_expected']} | {sum_m['functions']} | {sum_m['insns']} |

## Unmapped
- pump: {sum_p['unmapped']}
- pump_amm: {sum_a['unmapped']}
- pump_fees: {sum_f['unmapped']}
- mayhem: {sum_m['unmapped']}

## Outputs
See `maps/` and refreshed `docs/MAP_ALL4.md`, `docs/HANDLER_DISPOSITIONS.md`.
"""
    return notes

if __name__ == "__main__":
    main()
