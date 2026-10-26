import json,urllib.request,hashlib,struct,time
RPC=__import__('os').environ.get('SOLANA_RPC') or open('.rpc').read().strip()
P="6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
def rpc(m,p):
    r=urllib.request.Request(RPC,json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode(),{"Content-Type":"application/json"})
    for _ in range(4):
        try: return json.load(urllib.request.urlopen(r,timeout=30)).get("result")
        except Exception as e: time.sleep(1)
B58="123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def b58d(s):
    n=0
    for c in s: n=n*58+B58.index(c)
    b=n.to_bytes((n.bit_length()+7)//8,'big'); return b'\0'*(len(s)-len(s.lstrip('1')))+b
disc=lambda n:hashlib.sha256(n.encode()).digest()[:8]
EV=disc("event:TradeEvent")
IXS={disc("global:"+n):n for n in ["buy","sell","buy_v2","sell_v2","buy_v3","sell_v3",
     "buy_exact_sol_in","buy_exact_quote_in_v3","multi_hop_curve_swap"]}
sigs=rpc("getSignaturesForAddress",[P,{"limit":1000}]) or []
print(f"scanning {len(sigs)} sigs via RPC...")
seen=0; nz=0; bykind={}
for s in sigs:
    if s.get("err"): continue
    tx=rpc("getTransaction",[s["signature"],{"encoding":"json","maxSupportedTransactionVersion":0}])
    if not tx or not tx.get("meta"): continue
    msg=tx["transaction"]["message"]; la=tx["meta"].get("loadedAddresses",{})
    keys=msg["accountKeys"]+la.get("writable",[])+la.get("readonly",[])
    ixn=None
    for ix in msg["instructions"]:
        if keys[ix["programIdIndex"]]==P: ixn=IXS.get(b58d(ix["data"])[:8],ixn)
    for inner in tx["meta"].get("innerInstructions") or []:
        for ix in inner["instructions"]:
            d=b58d(ix["data"])
            if keys[ix["programIdIndex"]]==P and d[8:16]==EV and len(d)>=24:
                e=d[16:]; tail=struct.unpack('<Q',e[-8:])[0]; seen+=1
                k=ixn or "?"; bykind.setdefault(k,[0,0]); bykind[k][0]+=1
                if tail: bykind[k][1]+=1; nz+=1
                if tail and nz<=6: print(f"  NONZERO tail={tail} ix={k} len={len(e)} sig={s['signature'][:28]}")
    if seen>=600: break
print(f"events={seen} nonzero_trailing={nz}")
for k,(t,n) in sorted(bykind.items()): print(f"  {k}: {t} events, {n} nonzero trailing")
