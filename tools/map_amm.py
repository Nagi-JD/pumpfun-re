import importlib.util, hashlib, json
spec=importlib.util.spec_from_file_location('s','D:/dev/pumpfun-re/sbftool.py')
S=importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
AMM='D:/dev/ext/pumpfun-source/evidence/original/pump_amm/deployed.so'
p=S.Prog(AMM)
idl=json.load(open('D:/dev/ext/pumpfun-source/programs/pump-fees/idls/pump_amm.json'))
names=[i['name'] for i in idl['instructions']]
d2n={hashlib.sha256(("global:"+n).encode()).digest()[:8]:n for n in names}
H={}
order=p.order
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
print(f"PumpSwap (pump_amm): {len(p.order)} insns, {len(p.starts)} functions")
print(f"instructions mapped: {len(H)}/{len(set(names))}")
for n in sorted(H): print(f"  {n:<34} {H[n]}")
un=[n for n in set(names) if n not in H]
if un: print("unmapped:", un)
json.dump(H, open('D:/dev/pumpfun-re/amm_handlers.json','w'), indent=0)
