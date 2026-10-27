# For every original window: find error!-closure-like stores: lddw filename ptr, then store line (stw imm) and len (stdw imm). Print filename,line,code.
import sys,importlib.util,collections,struct
from pathlib import Path
spec=importlib.util.spec_from_file_location("wm","/home/nagi/pumpre/repo/research/fees-composed-frontier188/window_map.py")
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
img=Path(sys.argv[1]).read_bytes()
other=Path(sys.argv[2]).read_bytes() if len(sys.argv)>2 else None
ws=w.windows(img)
osigs={x["signature"] for x in w.windows(other)} if other else set()
res=[]
for x in ws:
    ins=w.m.instructions(img,x["address"],x["bytes"])
    for i,r in enumerate(ins):
        if "lddw_value" in r:
            # look ahead for stw (0x62) and stdw(0x7a) imm pairs within 8 instrs
            seq=ins[i+1:i+8]
            st=[s for s in seq if s["opcode"] in (0x62,0x7a)]
            imms=[(s["opcode"],int.from_bytes(bytes.fromhex(s["raw"])[4:8],"little")) for s in st]
            ln=[v for o,v in imms if o==0x62 and 1<v<5000]; lens=[v for o,v in imms if o==0x7a and 5<v<120]
            if ln and lens:
                try: name=w.m.at_address(img,r["lddw_value"],lens[0])
                except Exception: continue
                if name.endswith(b".rs"):
                    res.append((x["address"],x["bytes"],name.decode(),ln[0],"M" if x["signature"] in osigs else "-"))
for r in res: print(*r)
