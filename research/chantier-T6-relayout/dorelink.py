import json, sys, subprocess
inv, ord_ld, out_so, mapf = sys.argv[1:5]
d = json.load(open(inv))
fw = list(d['forwarded'])
for i, a in enumerate(fw):
    if a in ('--script', '-T'):
        fw[i + 1] = ord_ld
    elif a == '-o':
        fw[i + 1] = out_so
    elif a.startswith('-Map='):
        fw[i] = '-Map=' + mapf
    elif a.startswith('--script='):
        fw[i] = '--script=' + ord_ld
r = subprocess.run([d['real_linker'], *fw])
sys.exit(r.returncode)
