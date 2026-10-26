import json,urllib.request,hashlib,struct,time
RPC=__import__('os').environ.get('SOLANA_RPC') or open('.rpc').read().strip()
P="6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
def rpc(m,p):
    r=urllib.request.Request(RPC,json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode(),{"Content-Type":"application/json"})
    for _ in range(4):
        try: return json.load(urllib.request.urlopen(r,timeout=30)).get("result")
        except Exception: time.sleep(1)
B58="123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def b58d(s):
    n=0
    for c in s: n=n*58+B58.index(c)
    return b'\0'*(len(s)-len(s.lstrip('1')))+n.to_bytes((n.bit_length()+7)//8,'big')
disc=lambda n:hashlib.sha256(n.encode()).digest()[:8]
EV=disc("event:TradeEvent"); MH=disc("global:multi_hop_curve_swap")
before=None; scanned=0; found=0; pages=0
print("paging backward for multi_hop_curve_swap...")
while pages<40 and found<3:
    pages+=1
    params=[P,{"limit":1000,**({"before":before} if before else {})}]
    sigs=rpc("getSignaturesForAddress",params) or []
    if not sigs: break
    before=sigs[-1]["signature"]
    for s in sigs:
        scanned+=1
        if s.get("err"): continue
        tx=rpc("getTransaction",[s["signature"],{"encoding":"json","maxSupportedTransactionVersion":0}])
        if not tx or not tx.get("meta"): continue
        msg=tx["transaction"]["message"]; la=tx["meta"].get("loadedAddresses",{})
        keys=msg["accountKeys"]+la.get("writable",[])+la.get("readonly",[])
        ismh=False
        for ix in msg["instructions"]:
            if keys[ix["programIdIndex"]]==P and b58d(ix["data"])[:8]==MH: ismh=True
        if not ismh: continue
        found+=1; tails=[]
        for inner in tx["meta"].get("innerInstructions") or []:
            for ix in inner["instructions"]:
                d=b58d(ix["data"])
                if keys[ix["programIdIndex"]]==P and d[8:16]==EV and len(d)>=24:
                    e=d[16:]; tails.append(struct.unpack('<Q',e[-8:])[0])
        print(f"MULTIHOP sig={s['signature'][:30]} trade_events={len(tails)} trailing={tails}")
    print(f"  [page {pages}] scanned={scanned} multihop_found={found}")
print(f"DONE scanned={scanned} multihop={found}")
