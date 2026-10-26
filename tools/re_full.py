import importlib.util, hashlib, re, json, sys
spec=importlib.util.spec_from_file_location('s','D:/dev/pumpfun-re/sbftool.py')
S=importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
BASE='D:/dev/ext/pumpfun-source/evidence/original'
PROGS=['pump','pump_amm','pump_fees','mayhem']

PUMP53="initialize update_global_authority toggle_create_v2 toggle_cashback_enabled update_holder_reward_config set_max_curve_depth toggle_mayhem_mode update_creator_fee_config add_quote_mint remove_quote_mint set_virtual_quote_reserves set_params set_mayhem_virtual_params set_reserved_fee_recipients create create_v2 buy_v2 buy_exact_quote_in_v2 sell_v2 buy_v3 buy_exact_quote_in_v3 sell_v3 multi_hop_curve_swap sweep_protocol_fee sweep_creator_fee buy_exact_sol_in sell migrate migrate_v2 extend_account collect_creator_fee distribute_fee_to_holders set_metaplex_creator set_creator admin_cto admin_update_token_incentives claim_token_incentives claim_cashback claim_cashback_v2 init_user_volume_accumulator close_user_volume_accumulator sync_user_volume_accumulator admin_set_idl_authority migrate_bonding_curve_creator get_minimum_distributable_fee distribute_creator_fees distribute_creator_fees_v2 initialize_quote_control set_quote_control_admin remove_quote_control_mint set_quote_control_reserves_admin set_quote_control_mint_reserves buy".split()
def idl_names(p):
    if p=="pump": return PUMP53
    f={'pump':'D:/dev/ext/pumpfun-source/programs/pump-fees/idls/pump.json',
       'pump_amm':'D:/dev/ext/pumpfun-source/programs/pump-fees/idls/pump_amm.json'}.get(p)
    if not f: return []
    return [i['name'] for i in json.load(open(f))['instructions']]

SYS=["sol_log_","sol_log_64_","sol_log_pubkey","sol_log_compute_units_","sol_invoke_signed_c","sol_invoke_signed_rust","sol_memcpy_","sol_memset_","sol_memmove_","sol_memcmp_","sol_sha256","sol_keccak256","sol_get_clock_sysvar","sol_get_rent_sysvar","sol_create_program_address","sol_try_find_program_address","sol_get_return_data","sol_set_return_data","sol_get_stack_height","abort","sol_alloc_free_","sol_get_epoch_schedule_sysvar","sol_curve_group_op","sol_poseidon","sol_remaining_compute_units"]
def syscalls(prog):
    hmap={prog._murmur(n):n for n in SYS}
    for n in SYS: 
        pass
    c={}
    for pc,ins in prog.ins.items():
        if ins.op==0x85:
            t=(pc+1+ins.imm) & 0xffffffff
            nm=hmap.get(ins.imm & 0xffffffff) or prog.name.get(pc+1+ins.imm)
            if nm and nm in SYS: c[nm]=c.get(nm,0)+1
    return c
    c={}
    for pc,ins in prog.ins.items():
        if ins.op==0x85:
            t=pc+1+ins.imm
            nm=prog.name.get(t)
            if nm and ('sol_' in nm or 'invoke' in nm or nm.startswith('abort')): c[nm]=c.get(nm,0)+1
    return c

def dispatch_map(prog, names):
    disc2name={hashlib.sha256(("global:"+n).encode()).digest()[:8]:n for n in names}
    out={}
    order=prog.order
    for i,pc in enumerate(order):
        ins=prog.ins[pc]
        if ins.op==0x18:
            d=(ins.imm & 0xffffffffffffffff).to_bytes(8,'little')
            if d in disc2name and disc2name[d] not in out:
                for pc2 in order[i+1:i+4]:
                    j=prog.ins[pc2]
                    if j.mn=='jeq':
                        tgt=pc2+1+j.off
                        h=tgt
                        for q in range(tgt,tgt+40):
                            if q in prog.ins and prog.ins[q].op==0x85: h=q+1+prog.ins[q].imm; break
                        out[disc2name[d]]=(d.hex(),h); break
    return out

rep=["# Deployed Pump.fun Programs - Structural Reverse-Engineering Map",
"",
"Built with `sbftool.py` directly from the on-chain binaries in",
"`evidence/original/*/deployed.so`. Decoder verified 0-diff vs llvm-objdump",
"across every instruction. This maps structure (instructions, handlers,",
"syscalls, functions); it is not a byte-identity claim.",""]
for p in PROGS:
    prog=S.Prog(f'{BASE}/{p}/deployed.so')
    b=prog.b
    paths=set()
    for mm in re.finditer(rb'programs/', b):
        seg=b[mm.start():mm.start()+120]
        e=seg.find(b'.rs')
        if e!=-1 and re.fullmatch(rb'programs/[A-Za-z0-9_/]+', seg[:e]): paths.add(seg[:e+3].decode())
    paths=sorted(paths)
    ncall=sum(1 for i in prog.ins.values() if i.op==0x85)
    ncallx=sum(1 for i in prog.ins.values() if i.op==0x8d)
    sysnames=sorted(set(v for v in prog.name.values() if v.startswith('sol_') or v in ('abort',)))
    rep.append(f"## {p}")
    rep.append(f"- size: {prog.tsize:,} bytes .text, {len(prog.order):,} instructions")
    rep.append(f"- functions recovered: {len(prog.starts)}  |  call sites: {ncall:,}")
    rep.append(f"- syscalls linked ({len(sysnames)}, via {ncallx} callx sites): " + ", ".join(sysnames))
    rep.append(f"- source files baked into binary ({len(paths)}):")
    for pa in paths: rep.append(f"    - {pa}")
    nm=idl_names(p)
    if nm:
        dm=dispatch_map(prog,nm)
        rep.append(f"- instructions mapped to handlers: {len(dm)}/{len(set(nm))}")
        rep.append("")
        rep.append("    | instruction | discriminator | handler |")
        rep.append("    |---|---|---|")
        for n in sorted(dm): rep.append(f"    | {n} | `{dm[n][0]}` | `{hex(dm[n][1])}` |")
        un=[n for n in set(nm) if n not in dm]
        if un: rep.append(f"\n    unmapped (IDL-only / variant): {un}")
    rep.append("")
open('D:/dev/pumpfun-re/REVERSE_ENGINEERING.md','w').write("\n".join(rep))
print("\n".join(rep[:40]))
print("...\nwrote D:/dev/pumpfun-re/REVERSE_ENGINEERING.md", len("\n".join(rep)), "bytes")
