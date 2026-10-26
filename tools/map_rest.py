import importlib.util, hashlib, json, re
spec=importlib.util.spec_from_file_location('s','D:/dev/pumpfun-re/sbftool.py')
S=importlib.util.module_from_spec(spec); spec.loader.exec_module(S)

def snake(x): return re.sub(r'(?<!^)(?=[A-Z])','_',x).lower()

FEES=("D:/dev/ext/pumpfun-source/evidence/original/pump_fees/deployed.so",
 "admin_cto_sharing_config claim_social_fee_pda claim_social_fee_pda_v2 crank_donation_fee_pda create_donation_fee_pda create_fee_sharing_config create_social_fee_pda extend_fee_config get_fees get_fees_with_quote_mint initialize_buyback initialize_fee_config initialize_fee_program_global revoke_fee_sharing_authority set_authority set_claim_rate_limit set_disable_flags set_exotic_flat_fees set_social_claim_authority sweep_buyback transfer_fee_sharing_authority update_admin update_buyback_authority update_buyback_claim_rate_limit update_fee_config update_fee_shares update_fee_shares_v2 update_stable_fee_config upsert_fee_tiers upsert_stable_fee_tiers withdraw".split())

mnames=["Buy","BuyPumpSwap","BuyV2","BurnTokens","InitializeGlobalParams","ResetStableDeployed","ResetState","ResumeTrading","Sell","SweepFees","UpdateGlobalParams","UpdateMaxSolPerSweep","UpdateTrader","WithdrawAdmin"]
MAY=("D:/dev/ext/pumpfun-source/evidence/original/mayhem/deployed.so",
 [snake(x) for x in mnames]+["initialize_mayhem_state","set_mayhem_virtual_params"])

def mapprog(label, so, names):
    p=S.Prog(so)
    d2n={hashlib.sha256(("global:"+n).encode()).digest()[:8]:n for n in names}
    H={}; order=p.order
    for i,pc in enumerate(order):
        ins=p.ins[pc]
        if ins.op==0x18:
            dd=(ins.imm&0xffffffffffffffff).to_bytes(8,'little')
            if dd in d2n and d2n[dd] not in H:
                for pc2 in order[i+1:i+4]:
                    j=p.ins[pc2]
                    if j.mn=='jeq':
                        t=pc2+1+j.off; h=t
                        for q in range(t,t+40):
                            if q in p.ins and p.ins[q].op==0x85: h=q+1+p.ins[q].imm; break
                        H[d2n[dd]]=hex(h); break
    print(f"\n=== {label}: {len(p.order)} insns, {len(p.starts)} functions ===")
    print(f"mapped: {len(H)}/{len(set(names))}")
    for n in sorted(H): print(f"  {n:<34} {H[n]}")
    un=[n for n in set(names) if n not in H]
    if un: print("  unmapped:", un)
    return H

mapprog("pump_fees", *FEES)
mapprog("mayhem", *MAY)
