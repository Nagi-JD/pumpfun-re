import json,sys
def load(x):
    d=json.load(open(f"/home/nagi/pumpround23/out/{x}-m.json")); o=d["original"]
    return d, {r["start"] for r in o if r["matched"]}, {r["start"] for r in o if r.get("exact")}
a,am,ae=load(sys.argv[1]); b,bm,be=load(sys.argv[2])
print(list(a["original"][0].keys()))
print("matched",len(am),"->",len(bm),"lost",[hex(x) for x in am-bm],"gained",[hex(x) for x in sorted(bm-am)])
print("exact",len(ae),"->",len(be),"lost",[hex(x) for x in ae-be],"gained",[hex(x) for x in be-ae])
