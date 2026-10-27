import sys,importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location("wm","/home/nagi/pumpre/repo/research/fees-composed-frontier188/window_map.py")
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
img=Path(sys.argv[1]).read_bytes()
for x in w.windows(img):
    if x["bytes"]!=520: continue
    ins=w.m.instructions(img,x["address"],x["bytes"])
    imms=[int.from_bytes(bytes.fromhex(r["raw"])[4:8],"little",signed=True) for r in ins]
    codes=sorted({v for v in imms if 6000<=v<6300})
    print(x["address"],codes)
