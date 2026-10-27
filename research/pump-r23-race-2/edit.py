import sys,re
D=sys.argv[1]+"/programs/pump/src/"; step=sys.argv[2]
def rd(f): return open(D+f).read()
def wr(f,s): open(D+f,"w").write(s)
if step=="A":  # buy_v2 498/500 real closures
    s=rd("buy_v2.rs"); L=s.split("\n"); l=L[468]
    a='.ok_or_else(||err_at!(PumpError::Overflow,"programs/pump/src/buy_v2.rs",498))'
    b='.ok_or_else(||err_at!(PumpError::Overflow,"programs/pump/src/buy_v2.rs",500))'
    assert l.count(a)==1 and l.count(b)==1
    mid=sys.argv[3] if len(sys.argv)>3 else "499"
    i=l.index(a); j=l.index(b)
    between=l[i+len(a):j]
    x='.ok_or_else(||error!(PumpError::Overflow))'; assert between.count(x)==1
    nm=int(mid) if mid!="fn" else 498
    k1=498-469; k2=nm-498; k3=500-nm
    between=between.replace(x,'.ok_or_else(||'+"\n"*k2+'error!(PumpError::Overflow))')
    l=l[:i]+'.ok_or_else(||'+"\n"*k1+'error!(PumpError::Overflow))'+between+'.ok_or_else(||'+"\n"*k3+'error!(PumpError::Overflow))'+l[j+len(b):]
    if mid=="fn": l=l.replace(" )?}; let cb="," )?}; fn creator_fee_add_overflow()->Error{error!(PumpError::Overflow)} let cb=",1)
    L[468]=l
    # remove 31 padding newlines from line 470's expression (lines 471.. are blank)
    for _ in range(31):
        assert L[470]=="" ; del L[470]
    wr("buy_v2.rs","\n".join(L))
if step=="B":  # lib.rs legacy sell pf sub -> fn item on line 1037
    s=rd("lib.rs"); L=s.split("\n")
    a='.ok_or_else(||err_at!(PumpError::Overflow,"programs/pump/src/lib.rs",1037))'
    assert L[984].count(a)==1; L[984]=L[984].replace(a,'.ok_or_else(protocol_fee_underflow)')
    assert L[1036].startswith(" if protocol_fee!=0")
    L[1036]=" fn protocol_fee_underflow()->Error{error!(PumpError::Overflow)}"+L[1036]
    wr("lib.rs","\n".join(L))
if step=="C":  # nested_create QuoteChainAccountsRequired -> fn item in create_v2.rs:412
    s=rd("nested_create.rs")
    a='|| err_at!(PumpError::QuoteChainAccountsRequired,"programs/pump/src/create_v2.rs",412)'
    assert s.count(a)==1; wr("nested_create.rs",s.replace(a,"crate::create_v2::quote_chain_accounts_required"))
    c=rd("create_v2.rs").rstrip("\n").split("\n")
    while len(c)<411: c.append("")
    c.append("pub(crate) fn quote_chain_accounts_required()->anchor_lang::error::Error{anchor_lang::prelude::error!(crate::PumpError::QuoteChainAccountsRequired)}")
    wr("create_v2.rs","\n".join(c)+"\n")
if step=="D":  # set_params Truncation -> fn item at lib.rs:268, enum compressed
    s=rd("set_params.rs")
    a='.map_err(|_|err_at!(PumpError::Truncation,"programs/pump/src/lib.rs",268))'
    assert s.count(a)==1; wr("set_params.rs",s.replace(a,".map_err(crate::final_real_sol_reserves_truncation)"))
    L=rd("lib.rs").split("\n")
    assert L[216]=="#[error_code]" and L[217].startswith("pub enum PumpError") and L[423]=="}"
    body=[x.strip() for x in L[218:423]]
    n=268-1-219  # lines available for body: 219..267 (1-based) -> 48 lines, closing } at 267
    body=[("/*"+x[2:]+" */") if x.startswith("//") else x for x in body]; assert not any("//" in x for x in body)
    per=-(-len(body)//n); chunks=[" ".join(body[k:k+per]) for k in range(0,len(body),per)]
    assert len(chunks)<=n
    newenum=chunks+[""]*(n-len(chunks))+["}"]
    fn="fn final_real_sol_reserves_truncation(_:core::num::TryFromIntError)->Error{error!(PumpError::Truncation)}"
    tail=[""]*(424-268)
    L=L[:218]+newenum+[fn]+tail+L[424:]
    assert L[267]==fn, L.index(fn)
    wr("lib.rs","\n".join(L))
if step=="M":  # drop macro
    s=rd("lib.rs"); i=s.index("#[path=") ; assert s.startswith("macro_rules! err_at"); wr("lib.rs",s[i:])
print("ok",step)
if step=="A2":  # use the fn item for the creator-fee add (deployed buy_v2.rs:469)
    s=rd("buy_v2.rs"); a='.checked_add(ceil_fee(raw_quote,cb)?).ok_or_else(||error!(PumpError::Overflow))?>available'
    assert s.count(a)==1 and "fn creator_fee_add_overflow" in s
    wr("buy_v2.rs",s.replace(a,'.checked_add(ceil_fee(raw_quote,cb)?).ok_or_else(creator_fee_add_overflow)?>available'))
    print("ok A2")
if step=="E":  # migrate.rs: deployed adds post_complete_quote_in (+0x98) [280] then subtracts fee [282]
    L=rd("migrate.rs").split("\n")
    assert L[54]==" let quote=real_quote.checked_sub(fee).ok_or_else(||" and L[279]=="error!(PumpError::Overflow))?;" and L[281]==" move_lamports(&curve,&tmpq,quote)?;"
    L[54]=" let quote=(real_quote).checked_add(a.bonding_curve.post_complete_quote_in).ok_or_else(||"
    L[279]="error!(PumpError::Overflow))?.checked_sub(fee).ok_or_else(||"
    L[281]="error!(PumpError::Overflow))?; move_lamports(&curve,&tmpq,quote)?;"
    wr("migrate.rs","\n".join(L))
if step=="F":  # migrate_v2.rs: add [309], native fee sub [313], post-transfer delta sub [326]
    L=rd("migrate_v2.rs").split("\n")
    assert L[65]==" let quote=if native{real_quote.checked_sub(fee).ok_or_else(||" and L[308]=="error!(PumpError::Overflow))?}else{real_quote};"
    old311,old312,old313=L[310],L[311],L[312]
    tail_q=' let quote=quote_amount(&tmpq)?.checked_sub(quote_before).ok_or_else(||error!(PumpError::Overflow))?;'
    assert old313==" let base=amount(&tmpb)?;"+tail_q[0:0]+tail_q[1:] or old313.endswith(tail_q[1:]), old313
    L[65]=" let total_quote=(real_quote).checked_add(a.bonding_curve.post_complete_quote_in).ok_or_else(||"
    new=["error!(PumpError::Overflow))?;let quote=if native{total_quote.checked_sub(fee).ok_or_else(||",
         L[309],"","","error!(PumpError::Overflow))?}else{total_quote};",
         old311,old312,
         " let base=amount(&tmpb)?;let quote=quote_amount(&tmpq)?.checked_sub(quote_before).ok_or_else(||"]
    new+=[""]*(325-308-len(new))+["error!(PumpError::Overflow))?;"]
    L=L[:308]+new+L[313:]
    assert L[325]=="error!(PumpError::Overflow))?;" and L[312].startswith("error!") and L[308].startswith("error!")
    wr("migrate_v2.rs","\n".join(L))
