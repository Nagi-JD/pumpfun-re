#!/usr/bin/env python3
"""Static byte ledger. Never executes ELF or rewrites its bytes. Standard library only."""
from pathlib import Path
import sys,struct,hashlib,json,collections,argparse
sys.dont_write_bytecode=True
from elf_reader import Elf
HERE=Path(__file__).resolve().parent
BASE='inputs/current/'
sha=lambda b:hashlib.sha256(b).hexdigest()
def differences(a,b):
 n=max(len(a),len(b)); runs=[]; start=None; count=0
 for i in range(n):
  bad=i>=len(a) or i>=len(b) or a[i]!=b[i]
  if bad:
   count+=1
   if start is None:start=i
  elif start is not None:runs.append([start,i]);start=None
 if start is not None:runs.append([start,n])
 return {'count':count,'ranges_half_open':runs,'original_bytes':len(a),'candidate_bytes':len(b),'original_excess_tail':[len(b),len(a)] if len(a)>len(b) else None,'candidate_excess_tail':[len(a),len(b)] if len(b)>len(a) else None}
def sec_for(e,p):
 return [n for n,s in e.secs.items() if s[1]!=8 and s[4]<=p<s[4]+s[5]]
def ptr(e,at):
 if at+16<=len(e.b) and e.lo<=at<e.hi and e.b[at]==0x18:return struct.unpack_from('<I',e.b,at+4)[0]|struct.unpack_from('<I',e.b,at+12)[0]<<32
 if at+8<=len(e.b):return struct.unpack_from('<Q',e.b,at)[0]>>32
 return None
def relocation_rows(e):
 out=[]
 for name,s in e.secs.items():
  if s[1] not in (4,9):continue
  step=s[9] or (24 if s[1]==4 else 16)
  for at in range(s[4],s[4]+s[5],step):
   dest,info=struct.unpack_from('<QQ',e.b,at)
   r={'record_offset':at,'table':name,'site':dest,'type':info&0xffffffff,'symbol_index':info>>32,'symbol':e.symbols.get(info>>32),'raw':e.b[at:at+step].hex(),'site_sections':sec_for(e,dest),'category':'toolchain/build provenance'}
   if s[1]==4:r['addend']=struct.unpack_from('<q',e.b,at+16)[0]
   if r['type']==8:
    p=ptr(e,dest); r.update(pointer=p,pointer_sections=sec_for(e,p) if p is not None else [],referenced_extent='unknown; preview is not consumed data proof',preview_hex=e.b[p:p+32].hex() if p is not None else '',category='diagnostic/data metadata')
   out.append(r)
 return out
def windows(e,funcs=None):
 if funcs is None:return [{'start':a,'size':b-a,'names':[],'boundary':'inferred entry to next entry, not historical function proof'} for a,b in zip(e.entries,e.entries[1:]+[e.hi])]
 groups=collections.defaultdict(list)
 for f in funcs:groups[f['start'],f['size']].append(f['name'])
 return [{'start':a,'size':s,'names':sorted(set(ns)),'boundary':'candidate ELF symbol extent; aliases retained'} for (a,s),ns in sorted(groups.items())]
def category(names):
 name=' '.join(names).lower()
 if any(x in name for x in ('sell_v2','admin_update_token_incentives','claim_token_incentives')):return 'explicitly stopped'
 if 'pump_recovered' in name:
  if any(x in name for x in ('try_accounts','accounts','borsh','exit','serialize','deserialize')):return 'source organization/ownership'
  return 'ambiguous/unattributed'
 if name:return 'linked dependency/helper'
 return 'ambiguous/unattributed'
def enrich(e,rs):
 for r in rs:
  a=r['start'];b=a+r['size'];r.update(end=b,raw_sha256=sha(e.b[a:b]),normalized_sha256=sha(e.normalized[a:b]),category=category(r['names']),semantic_status='not proved',classification_basis='symbol ownership triage only; original owner and exact mismatch cause may remain unknown',calls=[],branches=[],relocations=e.pattern(a,r['size']))
  for at in range(a,b,8):
   if at+8>len(e.b):continue
   op,regs,off,imm=struct.unpack_from('<BBhi',e.b,at)
   if op==0x85:
    reloc=e.relocations.get(at);target=e.calls.get(at)
    r['calls'].append({'site':at,'offset':at-a,'raw':e.b[at:at+8].hex(),'signed_immediate':imm,'target':target,'relocation':reloc,'kind':'signed_relative' if target is not None else 'relocated_external' if reloc else 'unresolved_call','target_inside_text':e.lo<=target<e.hi if target is not None else None})
   elif op==0x8d:r['calls'].append({'site':at,'offset':at-a,'raw':e.b[at:at+8].hex(),'kind':'indirect_call_unresolved','target':None})
   elif op&7 in (5,6) and op!=0x95:
    target=at+8+off*8;r['branches'].append({'site':at,'raw':e.b[at:at+8].hex(),'target':target,'inside_window':a<=target<b,'predicate':'uninterpreted; branch outcome unresolved'})
 return rs
def cover(e,rs):
 events=collections.Counter({e.lo:0,e.hi:0})
 for r in rs:events[max(e.lo,r['start'])]+=1;events[min(e.hi,r['end'])]-=1
 last=e.lo;depth=0;gaps=[];overlaps=[]
 for p,d in sorted(events.items()):
  if p>last:
   if depth==0:gaps.append([last,p])
   if depth>1:overlaps.append([last,p,depth])
  depth+=d;last=p
 return {'uncovered':gaps,'overlap':overlaps}
def image(e):
 fields=['type','machine','version','entry','phoff','shoff','flags','ehsize','phentsize','phnum','shentsize','shnum','shstrndx']
 h=dict(zip(fields,struct.unpack_from('<HHIQQQIHHHHHH',e.b,16)))
 ph=[]
 for i in range(h['phnum']):
  at=h['phoff']+i*h['phentsize'];ph.append({'index':i,'offset':at,'raw':e.b[at:at+h['phentsize']].hex(),'fields':list(struct.unpack_from('<IIQQQQQQ',e.b,at))})
 return {'bytes':len(e.b),'sha256':sha(e.b),'header':h,'elf_ident_hex':e.b[:16].hex(),'program_headers':ph,'sections':[{'name':n,'fields':list(s),'sha256':sha(e.b[s[4]:s[4]+s[5]]) if s[1]!=8 else None} for n,s in e.secs.items()],'relocations':relocation_rows(e),'text':[e.lo,e.hi]}
def analyze(root=HERE):
 o=Elf(root/'inputs/original.so');c=Elf(root/BASE/'candidate.so');sym=Elf(root/BASE/'symbols.so')
 assert c.b[c.lo:c.hi]==sym.b[sym.lo:sym.hi]
 assert c.pattern(c.lo,c.hi-c.lo)==sym.pattern(sym.lo,sym.hi-sym.lo)
 assert all(s[3]==s[4] for e in (o,c,sym) for n,s in e.secs.items() if n=='.text'), 'reader requires text VA=file offset'
 os=enrich(o,windows(o));cs=enrich(c,windows(c,sym.funcs));ci=enrich(c,windows(c));ob={r['start']:r for r in os};cb={r['start']:r for r in cs}
 idx=collections.defaultdict(list)
 for r in os:idx[r['size'],r['normalized_sha256']].append(r)
 pairs=[]
 for r in cs:
  r['pattern_candidates']=[]
  for v in idx[r['size'],r['normalized_sha256']]:
   if v['relocations']!=r['relocations']:continue
   r['pattern_candidates'].append(v['start']);pairs.append((r['start'],v['start']))
 possible=set(pairs);rounds=[]
 while True:
  bad=[]
  for ca,oa in possible:
   r=cb[ca];v=ob[oa];oc={x['offset']:x for x in v['calls']}
   for call in r['calls']:
    x=oc.get(call['offset'])
    if x is None:bad.append((ca,oa));break
    if call['kind']=='signed_relative' and x['kind']=='signed_relative':
     ct,ot=call['target'],x['target']
     # Self/local entry still requires consistent relative location or a retained target relation.
     if ca<=ct<r['end'] and oa<=ot<v['end'] and ct-ca==ot-oa:continue
     if ct in cb and ot in ob and (ct,ot) not in possible:bad.append((ca,oa));break
  if not bad:break
  rounds.append(len(set(bad)));possible-=set(bad)
 comparisons=[]
 for ca,oa in pairs:
  r=cb[ca];v=ob[oa];oc={x['offset']:x for x in v['calls']};checks=[];datas=[]
  for call in r['calls']:
   x=oc.get(call['offset']);ct=call.get('target');ot=x.get('target') if x else None
   if call['kind']=='relocated_external':state='same_external_symbol' if x and x['relocation']==call['relocation'] else 'conflict'
   elif ct is not None and ot is not None:
    state='local_relative_target' if ca<=ct<r['end'] and oa<=ot<v['end'] and ct-ca==ot-oa else 'target_pattern_relation' if (ct,ot) in possible else 'conflict' if ct in cb and ot in ob else 'unresolved_target_boundary'
   else:state='unresolved'
   checks.append({'offset':call['offset'],'candidate_target':ct,'original_target':ot,'state':state,'actual_absolute_target_equal':ct==ot if ct is not None and ot is not None else None})
  for rel in r['relocations']:
   if rel['type']!=8:continue
   cp=ptr(c,ca+rel['offset']);op=ptr(o,oa+rel['offset']);datas.append({'offset':rel['offset'],'candidate_pointer':cp,'original_pointer':op,'candidate_sections':sec_for(c,cp),'original_sections':sec_for(o,op),'referenced_data_equality':'unresolved extent; equal previews do not close this obligation','preview_32_equal':o.b[op:op+32]==c.b[cp:cp+32]})
  comparisons.append({'candidate':ca,'original':oa,'bytes':r['size'],'raw_body_equal':r['raw_sha256']==v['raw_sha256'],'raw_differences':differences(o.b[oa:oa+r['size']],c.b[ca:ca+r['size']]),'normalized_instruction_equal':True,'call_consistent_fixed_point':(ca,oa) in possible,'calls':checks,'data':datas,'transitive_data_equal':None,'semantic_equivalence':None})
 for r in cs:r['call_consistent_candidates']=[oa for ca,oa in pairs if ca==r['start'] and (ca,oa) in possible]
 for r in os:
  r['pattern_candidates']=[ca for ca,oa in pairs if oa==r['start']];r['call_consistent_candidates']=[ca for ca,oa in pairs if oa==r['start'] and (ca,oa) in possible]
  # Original semantic ownership stays unknown even if candidate names suggest an owner.
  r['candidate_category_hypotheses']=sorted({cb[x]['category'] for x in r['pattern_candidates']})
  if r['candidate_category_hypotheses']==['explicitly stopped']:r['category']='explicitly stopped'
 # Exact size, few changed normalized instructions: retain ALL alternatives as hypotheses.
 sizes=collections.defaultdict(list)
 for r in os:sizes[r['size']].append(r)
 near=[]
 for r in cs:
  if r['pattern_candidates'] or r['category']=='explicitly stopped' or r['size']<64:continue
  for v in sizes[r['size']]:
   a=r['start'];b=v['start'];diff=[]
   for d in range(0,r['size'],8):
    if c.normalized[a+d:a+d+8]!=o.normalized[b+d:b+d+8]:diff.append(d)
    if len(diff)>8:break
   if len(diff)>8:continue
   near.append({'candidate':a,'original':b,'bytes':r['size'],'status':'same-size near-pattern hypothesis, NOT identity','different_normalized_instructions':[{'offset':d,'candidate_raw':c.b[a+d:a+d+8].hex(),'original_raw':o.b[b+d:b+d+8].hex()} for d in diff],'raw_mismatches':differences(o.b[b:b+r['size']],c.b[a:a+r['size']]),'relocation_pattern_equal':v['relocations']==r['relocations']})
 sections=[]
 for name in sorted(set(o.secs)|set(c.secs)):
  a=o.secs.get(name);b=c.secs.get(name)
  sections.append({'name':name,'original_fields':list(a) if a else None,'candidate_fields':list(b) if b else None,'payload_differences':differences(o.b[a[4]:a[4]+a[5]] if a and a[1]!=8 else b'',c.b[b[4]:b[4]+b[5]] if b and b[1]!=8 else b''),'category':'diagnostic/data metadata' if name in ('.rodata','.data.rel.ro') else 'toolchain/build provenance','alignment':'section-relative raw offsets; not semantic object alignment'})
 source=[]
 bindings=json.loads((root/BASE/'source-sha256.json').read_text())
 for p,h in sorted(bindings.items()):
  actual=sha((root/'inputs/source'/p).read_bytes())
  source.append({'path':p,'bound_sha256':h,'actual_sha256':actual,'matches_build_binding':actual==h})
 result={'revision':None,'scope':'selected accepted Pump working integration; exact artifact hash; no target execution','whole_file_equal':o.b==c.b,'original':image(o),'candidate':image(c),'symbol_artifact':image(sym),'source_bindings':source,'positional_differences':differences(o.b,c.b),'sections':sections,'original_windows':os,'candidate_symbol_windows':cs,'candidate_inferred_windows':ci,'all_raw_symbol_rows':sym.funcs,'original_coverage':cover(o,os),'candidate_symbol_coverage':cover(c,cs),'candidate_inferred_coverage':cover(c,ci),'pattern_comparisons':comparisons,'call_pruning_rounds':rounds,'near_pattern_hypotheses':near,'summary':{'original_windows':len(os),'candidate_symbol_windows':len(cs),'candidate_inferred_windows':len(ci),'candidate_with_pattern':sum(bool(r['pattern_candidates']) for r in cs),'candidate_with_call_consistent_pattern':sum(bool(r['call_consistent_candidates']) for r in cs),'original_with_call_consistent_pattern':sum(bool(r['call_consistent_candidates']) for r in os),'pattern_pairs':len(pairs),'call_consistent_pairs':len(possible),'raw_equal_pairs':sum(r['raw_body_equal'] for r in comparisons),'ambiguous_candidate_rows':sum(len(r['call_consistent_candidates'])>1 for r in cs),'near_hypotheses':len(near)}}
 return result
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');args=ap.parse_args();r=analyze();p=HERE/'residual-ledger.json'
 if args.check:assert r==json.loads(p.read_text()),'ledger differs'
 else:p.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'summary':r['summary'],'whole_file_equal':r['whole_file_equal'],'positional_mismatches':r['positional_differences']['count']}))
