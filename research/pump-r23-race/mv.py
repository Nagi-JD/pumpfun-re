import sys,re
d=sys.argv[1]; L=open(d+"/lib.rs").read().rstrip("\n").split("\n")
def take(f,modname,start_line,pre_use):
    s=open(d+"/"+f).read().split("\n")
    a=next(i for i,l in enumerate(s) if l.startswith("fn add("))
    b=next(i for i in range(a,len(s)) if s[i]=="}" and i>a)  # end of execute
    body=s[a:b+1]; extra=[l for l in s[b+1:] if l.startswith("use ")]
    rest=s[:a]+["pub use crate::%s::execute;"%modname]+[l for l in s[b+1:] if not l.startswith("use ")]
    open(d+"/"+f,"w").write("\n".join(rest))
    hdr=[l for l in s[:a] if l.startswith("use ")]+extra+["use crate::%s::*;"%pre_use]
    blk=["pub mod %s{"%modname]+hdr+body+["}"]
    while len(L)+1 < start_line-len(hdr)-1: L.append("")
    L.extend(blk)
which=sys.argv[3]
take(which+".rs","legacy_%s_exec"%which,int(sys.argv[2]),"legacy_"+which)
open(d+"/lib.rs","w").write("\n".join(L)+"\n")
