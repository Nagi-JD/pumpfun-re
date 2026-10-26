# Full structural map of the deployed Pump program, built on sbftool.
import importlib.util, hashlib, struct, re, sys
spec=importlib.util.spec_from_file_location('s','D:/dev/pumpfun-re/sbftool.py')
S=importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
P=S.Prog('D:/dev/ext/pumpfun-source/evidence/original/pump/deployed.so')

# 1) Instruction names seen in the binary (Anchor "Instruction: X" strings), -> snake_case
names=["initialize","update_global_authority","toggle_create_v2","toggle_cashback_enabled",
"update_holder_reward_config","set_max_curve_depth","toggle_mayhem_mode","update_creator_fee_config",
"add_quote_mint","remove_quote_mint","set_virtual_quote_reserves","set_params","set_mayhem_virtual_params",
"set_reserved_fee_recipients","create","create_v2","buy_v2","buy_exact_quote_in_v2","sell_v2","buy_v3",
"buy_exact_quote_in_v3","sell_v3","multi_hop_curve_swap","sweep_protocol_fee","sweep_creator_fee",
"buy_exact_sol_in","sell","migrate","migrate_v2","extend_account","collect_creator_fee",
"distribute_fee_to_holders","set_metaplex_creator","set_creator","admin_cto","admin_update_token_incentives",
"claim_token_incentives","claim_cashback","claim_cashback_v2","init_user_volume_accumulator",
"close_user_volume_accumulator","sync_user_volume_accumulator","admin_set_idl_authority",
"migrate_bonding_curve_creator","get_minimum_distributable_fee","distribute_creator_fees",
"distribute_creator_fees_v2","initialize_quote_control","set_quote_control_admin","remove_quote_control_mint",
"set_quote_control_reserves_admin","set_quote_control_mint_reserves","buy","collect_creator_fee"]
disc2name={hashlib.sha256(("global:"+n).encode()).digest()[:8]:n for n in names}

# 2) Walk the dispatcher: every `lddw r4, DISC ; jeq r3, r4, +OFF` pair -> handler stub target
rows=[]
order=P.order
for i,pc in enumerate(order):
    ins=P.ins[pc]
    if ins.op==0x18:                                  # lddw
        d=(ins.imm & 0xffffffffffffffff).to_bytes(8,'little')
        if d in disc2name:
            # find the next jeq within a few insns
            for pc2 in order[i+1:i+4]:
                j=P.ins[pc2]
                if j.op in (0x1d,0x15) and j.mn=='jeq':   # jeq r3,r4,+off
                    tgt=pc2+1+j.off
                    rows.append((disc2name[d], d.hex(), pc2, tgt))
                    break

# 3) resolve dispatch stub -> real handler (stub: setup then `call H` or `ja H`)
def resolve(stub):
    for pc in range(stub, stub+40):
        if pc in P.ins:
            k=P.ins[pc]
            if k.op==0x85: return pc+1+k.imm
            if k.op==0x05: continue
    return stub

# 4) name functions by nearest baked-in source path (panic handlers embed file paths)
b=P.b
paths=sorted(set(re.findall(rb'programs/pump/src/[A-Za-z0-9_./]+\.rs', b)))
print(f"deployed Pump: {len(P.order)} insns, {len(P.starts)} functions, {len(P.name)} named syscalls")
print(f"source files referenced in binary: {len(paths)}")
print(f"\n{'instruction':<34}{'discriminator':<18}{'handler':>10}")
seen=set()
for name,dh,stub,tgt in sorted(rows):
    if name in seen: continue
    seen.add(name)
    h=resolve(tgt)
    print(f"{name:<34}{dh:<18}{hex(h):>10}")
missing=[n for n in names if n not in seen and n!='collect_creator_fee']
print(f"\nmatched {len(seen)}/{len(set(names))} instruction names to dispatcher entries")
print("unmatched:", missing)
