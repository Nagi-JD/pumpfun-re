import json,sys
def load(p): return {w['start']:w for w in json.load(open(p))['original']}
def cand(p): return json.load(open(p))
a=load(sys.argv[1]); b=load(sys.argv[2])
# raw-exact per original window: measure marks matched; raw hash compared against candidate raw hashes
def rawset(p):
    d=json.load(open(p)); ch={c.get('raw') for c in d['candidate'] if c.get('raw')}
    return {w['start'] for w in d['original'] if w['raw'] in ch}
ma={k for k in a if a[k]['matched']}; mb={k for k in b if b[k]['matched']}
ra=rawset(sys.argv[1]); rb=rawset(sys.argv[2])
print('matched %d -> %d  +%s  -%s' % (len(ma),len(mb),[hex(x) for x in sorted(mb-ma)],[hex(x) for x in sorted(ma-mb)]))
print('raw %d -> %d  +%s  -%s' % (len(ra),len(rb),[hex(x) for x in sorted(rb-ra)],[hex(x) for x in sorted(ra-rb)]))
