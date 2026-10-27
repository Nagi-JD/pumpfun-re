#!/usr/bin/env python3
"""measure.py ORIGINAL CANDIDATE_STRIPPED SYMBOLS [--dump out.json]
Wraps lalalune pass-01 after-fixes analyze.analyze() (copied verbatim) with explicit paths."""
import sys,json,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
import analyze as A
from elf_reader import Elf
def run(orig,cand,syms):
    o=Elf(Path(orig));c=Elf(Path(cand));sym=Elf(Path(syms))
    assert c.b[c.lo:c.hi]==sym.b[sym.lo:sym.hi]
    os_=A.enrich(o,A.windows(o));cs=A.enrich(c,A.windows(c,sym.funcs))
    ob={r["start"]:r for r in os_};cb={r["start"]:r for r in cs}
    idx=collections.defaultdict(list)
    for r in os_:idx[r["size"],r["normalized_sha256"]].append(r)
    pairs=[]
    for r in cs:
        r["pattern_candidates"]=[]
        for v in idx[r["size"],r["normalized_sha256"]]:
            if v["relocations"]!=r["relocations"]:continue
            r["pattern_candidates"].append(v["start"]);pairs.append((r["start"],v["start"]))
    possible=set(pairs)
    while True:
        bad=[]
        for ca,oa in possible:
            r=cb[ca];v=ob[oa];oc={x["offset"]:x for x in v["calls"]}
            for call in r["calls"]:
                x=oc.get(call["offset"])
                if x is None:bad.append((ca,oa));break
                if call["kind"]=="signed_relative" and x["kind"]=="signed_relative":
                    ct,ot=call["target"],x["target"]
                    if ca<=ct<r["end"] and oa<=ot<v["end"] and ct-ca==ot-oa:continue
                    if ct in cb and ot in ob and (ct,ot) not in possible:bad.append((ca,oa));break
        if not bad:break
        possible-=set(bad)
    raw={r["raw_sha256"] for r in cs}
    matched=[r for r in os_ if any(oa==r["start"] for _,oa in pairs)]
    m=set(oa for _,oa in pairs); cc=set(oa for _,oa in possible)
    exact=sum(r["raw_sha256"] in raw for r in os_)
    return dict(original_windows=len(os_),candidate_windows=len(cs),matched=len(m),exact=exact,unmatched=len(os_)-len(m),call_consistent_original=len(cc)),os_,cs,pairs,possible
if __name__=="__main__":
    s,os_,cs,pairs,possible=run(*sys.argv[1:4])
    print(json.dumps(s))
    if "--dump" in sys.argv:
        out=sys.argv[sys.argv.index("--dump")+1]
        m=set(oa for _,oa in pairs)
        json.dump(dict(summary=s,original=[dict(start=r["start"],size=r["size"],matched=r["start"] in m,raw=r["raw_sha256"],calls=[x.get("target") for x in r["calls"]]) for r in os_],
          candidate=[dict(start=r["start"],size=r["size"],names=r["names"],raw=r["raw_sha256"],matched=bool(r["pattern_candidates"]),calls=[x.get("target") for x in r["calls"]]) for r in cs]),open(out,"w"))
