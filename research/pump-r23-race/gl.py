import json,sys
a,b=[{r["start"] for r in json.load(open(f"/home/nagi/pumpround23/out/{x}-m.json"))["original"] if r["matched"]} for x in sys.argv[1:3]]
print("gained",[hex(x) for x in sorted(b-a)]);print("lost",[hex(x) for x in sorted(a-b)])
