import re,sys,glob,collections
def cnt(d):
    c=collections.Counter()
    for f in glob.glob(d+'/programs/pump/src/**/*.rs',recursive=True):
        s=open(f).read()
        for k in re.findall(r'PumpError::(\w+)',s): c['V:'+k]+=1
        for k in re.findall(r'\b(require\w*!|checked_\w+|narrow|try_from)\b',s): c[k]+=1
    return c
a,b,c,d=[cnt(x) for x in sys.argv[1:5]]
keys=sorted(set(a)|set(b)|set(c)|set(d))
print('%-40s %6s %6s | %6s %6s'%('key','R23','w_F','R34','final'))
for k in keys:
    if b[k]-a[k]!=d[k]-c[k]: print('%-40s %6d %6d | %6d %6d  <-- delta differs'%(k,a[k],b[k],c[k],d[k]))
print('others: identical deltas')
