// Coverage-guided differential fuzzer for the pump sBPF program.
// Runs each generated/mutated input against BOTH the deployed original and the
// clone from an identical checkpoint state, diffs {ok, program-error, normalized
// logs, emitted event bytes, resulting account state, CU}, unions the original's
// executed-branch coverage, and minimizes any real divergence into a fixture.
//
// Design: a CPI-heavy prefix (initialize/set_params/create/ATA[/priming buy]) is
// run ONCE per program to reach a known state; all touched accounts are snapshotted;
// every mutant then restores a fresh LiteSVM from that snapshot (no CPIs) and runs
// the single mutated instruction. Snapshot fidelity is validated against a
// from-scratch run before fuzzing begins.
use litesvm::LiteSVM;
use solana_sdk::{pubkey::Pubkey, signature::{Keypair,Signer}, account::Account,
    instruction::{Instruction, AccountMeta}, transaction::Transaction, system_program, sysvar};
use std::str::FromStr;
use std::collections::BTreeSet;

const PUMP_ENTRY:u64=175522; // sbftool_pc = trace_pc + 36

const PUMP:&str="6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P";
const TOKEN:&str="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA";
const ATA:&str="ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL";
const META:&str="metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s";
const FEEP:&str="pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ";
const T22:&str="TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb";
const AMM:&str="pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA";
const MAYHEM:&str="MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e";
const INIT:[u8;8]=[0xaf,0xaf,0x6d,0x1f,0x0d,0x98,0x9b,0xed];
const SETP:[u8;8]=[0x1b,0xea,0xb2,0x34,0x93,0x02,0xbb,0x8d];
const CREATE:[u8;8]=[0x18,0x1e,0xc8,0x28,0x05,0x1c,0x07,0x77];
const BUY:[u8;8]=[102,6,61,18,1,218,235,234];
const SELL:[u8;8]=[51,230,133,164,1,127,131,173];
const BUYV3:[u8;8]=[7,5,29,196,245,23,101,80];
const SELLV3:[u8;8]=[28,146,222,119,38,196,105,213];
const DEP:&str="/mnt/d/dev/ext/pumpfun-source/evidence/dependencies";
const ORIG_FEES:&str="/mnt/d/dev/ext/pumpfun-source/evidence/original/pump_fees/deployed.so";

fn cu(l:&[String])->u64{for x in l.iter().rev(){if let Some(i)=x.find("consumed "){let r=&x[i+9..];if let Some(s)=r.find(char::is_whitespace){if let Ok(v)=r[..s].parse(){return v}}}}0}
fn u64le(v:u64)->Vec<u8>{v.to_le_bytes().to_vec()}
fn u128le(v:u128)->Vec<u8>{v.to_le_bytes().to_vec()}
fn strb(s:&str)->Vec<u8>{let mut o=(s.len() as u32).to_le_bytes().to_vec();o.extend_from_slice(s.as_bytes());o}
fn fees()->Vec<u8>{let mut v=u64le(0);v.extend(u64le(95));v.extend(u64le(30));v}
fn feeconfig_bytes()->Vec<u8>{
    let admin:[u8;32]=[0xd3,0xbb,0x8c,0xab,0x34,0x1c,0xe0,0x52,0x84,0x57,0xf2,0xc3,0x81,0x7d,0x32,0x78,0x44,0x19,0x63,0xdc,0xd5,0x5f,0xed,0x58,0xba,0x24,0xc9,0x99,0xdd,0xac,0x02,0xaa];
    let mut d=vec![143,52,146,187,219,123,76,155u8];
    d.push(253);
    d.extend_from_slice(&admin);
    d.extend(fees());
    d.extend(1u32.to_le_bytes()); d.extend(u128le(0)); d.extend(fees());
    d.extend(1u32.to_le_bytes()); d.extend(u128le(0)); d.extend(fees());
    d.extend(fees());
    d.resize(4097,0);
    d
}
fn gva_bytes()->Vec<u8>{let mut d=vec![202,42,246,43,142,190,30,255u8];d.extend(vec![0u8;536]);d}

// tiny deterministic xorshift PRNG (no external deps, identical across the two runs)
struct Rng(u64);
impl Rng{
    fn new(s:u64)->Self{Rng(s|1)}
    fn next(&mut self)->u64{let mut x=self.0;x^=x<<13;x^=x>>7;x^=x<<17;self.0=x;x}
    fn range(&mut self,n:u64)->u64{if n==0{0}else{self.next()%n}}
    fn pubkey(&mut self)->Pubkey{let mut b=[0u8;32];for i in 0..4{b[i*8..i*8+8].copy_from_slice(&self.next().to_le_bytes());}Pubkey::new_from_array(b)}
}

#[derive(Clone)]
struct Ctx{
    pump:Pubkey, token:Pubkey, feep:Pubkey,
    user:Pubkey, mint:Pubkey, mint3:Pubkey,
    global:Pubkey, bc:Pubkey, abc:Pubkey, auser:Pubkey, cvault:Pubkey, uva:Pubkey, gva:Pubkey,
    bbrecip:Pubkey, recip:Pubkey, feecfg:Pubkey, wsol:Pubkey, qbc:Pubkey, qu:Pubkey, bcv2:Pubkey,
    buy_metas:Vec<AccountMeta>, sell_metas:Vec<AccountMeta>, v3_metas:Vec<AccountMeta>,
    snap_keys:Vec<Pubkey>, result_keys:Vec<(String,Pubkey)>,
}

struct RunResult{ok:bool, errcode:String, logs:String, event:String, cu:u64, frame0:Vec<u32>, instr:BTreeSet<u32>, edges:BTreeSet<(u32,u32)>}

fn norm_logs(l:&[String])->String{l.iter().filter(|x|!x.contains("consumed ")).cloned().collect::<Vec<_>>().join("\n")}
fn event_of(l:&[String])->String{l.iter().filter_map(|x|x.strip_prefix("Program data: ").map(|s|s.to_string())).collect::<Vec<_>>().join("|")}

const LDIR:&str="/home/jojod/sbfcov/progs"; // local ext4 copies (fast reads; /mnt/d is the bottleneck)
fn add_programs(svm:&mut LiteSVM, pump_so:&str){
    svm.add_program_from_file(Pubkey::from_str(PUMP).unwrap(),pump_so).unwrap();
    svm.add_program_from_file(Pubkey::from_str(TOKEN).unwrap(),format!("{}/spl_token.so",LDIR)).unwrap();
    svm.add_program_from_file(Pubkey::from_str(ATA).unwrap(),format!("{}/ata.so",LDIR)).unwrap();
    svm.add_program_from_file(Pubkey::from_str(META).unwrap(),format!("{}/meta.so",LDIR)).unwrap();
    svm.add_program_from_file(Pubkey::from_str(FEEP).unwrap(),format!("{}/fees.so",LDIR)).unwrap();
    svm.add_program_from_file(Pubkey::from_str(AMM).unwrap(),format!("{}/amm.so",LDIR)).unwrap();
    svm.add_program_from_file(Pubkey::from_str(T22).unwrap(),format!("{}/t22.so",LDIR)).unwrap();
    svm.add_program_from_file(Pubkey::from_str(MAYHEM).unwrap(),format!("{}/mayhem.so",LDIR)).unwrap();
}

fn send_capture(svm:&mut LiteSVM, user:&Keypair, prog:Pubkey, data:Vec<u8>, mut metas:Vec<AccountMeta>, extra:&[&Keypair])->RunResult{
    // Sanitize signer flags: a mutant may repoint a signer slot at a key we cannot
    // sign for (which would panic Transaction::sign with NotEnoughSigners). The real
    // on-chain equivalent is "account present but did not sign" -> is_signer=false,
    // which yields a proper comparable Signer/AccountNotSigner error from the program.
    let mut allowed:BTreeSet<Pubkey>=BTreeSet::new();
    allowed.insert(user.pubkey());
    for k in extra{ allowed.insert(k.pubkey()); }
    for m in metas.iter_mut(){ if m.is_signer && !allowed.contains(&m.pubkey){ m.is_signer=false; } }
    let ix=Instruction{program_id:prog,accounts:metas,data};
    let bh=svm.latest_blockhash();
    let mut all=vec![user]; all.extend_from_slice(extra);
    let cbud=Pubkey::from_str("ComputeBudget111111111111111111111111111111").unwrap();
    let mut cbd=vec![2u8]; cbd.extend_from_slice(&1_400_000u32.to_le_bytes());
    let cbix=Instruction{program_id:cbud,accounts:vec![],data:cbd};
    let tx=Transaction::new_signed_with_payer(&[cbix,ix],Some(&user.pubkey()),&all,bh);
    let (ok,errcode,logs,cuv)=match svm.send_transaction(tx){
        Ok(m)=>(true,"OK".to_string(),m.logs.clone(),cu(&m.logs)),
        Err(e)=>(false,format!("{:?}",e.err),e.meta.logs.clone(),cu(&e.meta.logs)),
    };
    let traces=litesvm::take_last_traces();
    let mut instr=BTreeSet::new(); let mut edges=BTreeSet::new(); let mut frame0:Vec<u32>=vec![];
    for fr in traces.iter(){
        if fr.first().map(|e|e[11])==Some(PUMP_ENTRY){
            let pcs:Vec<u32>=fr.iter().map(|e|e[11] as u32).collect();
            if frame0.is_empty(){frame0=pcs.clone();}
            for &pc in &pcs{instr.insert(pc);}
            for w in pcs.windows(2){edges.insert((w[0],w[1]));}
        }
    }
    RunResult{ok,errcode,logs:norm_logs(&logs),event:event_of(&logs),cu:cuv,frame0,instr,edges}
}

// Builds the full checkpoint from scratch for `pump_so`. Returns the live svm, the
// user keypair, and the Ctx. If `prime`, also executes one standard buy so the user
// holds base tokens (needed to fuzz sell/sell_v3).
fn checkpoint(pump_so:&str, prime:bool)->(LiteSVM, Keypair, Ctx){
    let pump=Pubkey::from_str(PUMP).unwrap();
    let token=Pubkey::from_str(TOKEN).unwrap();
    let ata=Pubkey::from_str(ATA).unwrap();
    let meta=Pubkey::from_str(META).unwrap();
    let feep=Pubkey::from_str(FEEP).unwrap();
    let mut svm=LiteSVM::new();
    add_programs(&mut svm,pump_so);
    let user=solana_sdk::signer::keypair::keypair_from_seed(&[7u8;32]).unwrap();
    svm.airdrop(&user.pubkey(),1_000_000_000_000).unwrap();
    let (global,_)=Pubkey::find_program_address(&[b"global"],&pump);
    let (mint_auth,_)=Pubkey::find_program_address(&[b"mint-authority"],&pump);
    let (evauth,_)=Pubkey::find_program_address(&[b"__event_authority"],&pump);
    let (gva,_)=Pubkey::find_program_address(&[b"global_volume_accumulator"],&pump);
    let (feecfg,_)=Pubkey::find_program_address(&[b"fee_config",pump.as_ref()],&feep);
    let mut tmp=vec![];
    let mut go=|svm:&mut LiteSVM,name:&str,prog:Pubkey,data:Vec<u8>,metas:Vec<AccountMeta>,signers:&[&Keypair]|{
        let r=send_capture(svm,&user,prog,data,metas,signers);
        if !r.ok{ tmp.push(format!("checkpoint step {} FAILED: {}",name,r.errcode)); }
    };
    go(&mut svm,"initialize",pump,INIT.to_vec(),
        vec![AccountMeta::new(global,false),AccountMeta::new(user.pubkey(),true),AccountMeta::new_readonly(system_program::ID,false)],&[]);
    let mut d=SETP.to_vec();
    d.extend(u64le(1_073_000_000_000_000)); d.extend(u64le(30_000_000_000));
    d.extend(u64le(793_100_000_000_000));   d.extend(u64le(1_000_000_000_000_000));
    d.extend(u64le(100)); d.extend(user.pubkey().to_bytes()); d.push(1); d.extend(u64le(15_000_000_000));
    d.extend(u64le(0)); d.extend(user.pubkey().to_bytes()); d.extend(user.pubkey().to_bytes());
    let mut sm=vec![AccountMeta::new(global,false),AccountMeta::new(user.pubkey(),true),AccountMeta::new_readonly(evauth,false),AccountMeta::new_readonly(pump,false)];
    for i in 1u8..=8{let r=Pubkey::new_from_array([i;32]); svm.airdrop(&r,1_000_000_000).unwrap(); sm.push(AccountMeta::new_readonly(r,false));}
    go(&mut svm,"set_params",pump,d,sm,&[]);
    let bbrecip=Pubkey::new_from_array([0x42u8;32]);
    if let Some(mut g)=svm.get_account(&global){ g.data[741..773].copy_from_slice(&bbrecip.to_bytes()); g.data[450]=1; g.data[515]=1; svm.set_account(global,g).unwrap(); }
    let mint=solana_sdk::signer::keypair::keypair_from_seed(&[0x11u8;32]).unwrap();
    let (bc,_)=Pubkey::find_program_address(&[b"bonding-curve",mint.pubkey().as_ref()],&pump);
    let (abc,_)=Pubkey::find_program_address(&[bc.as_ref(),token.as_ref(),mint.pubkey().as_ref()],&ata);
    let (mdpda,_)=Pubkey::find_program_address(&[b"metadata",meta.as_ref(),mint.pubkey().as_ref()],&meta);
    let mut cd=CREATE.to_vec(); cd.extend(strb("T")); cd.extend(strb("T")); cd.extend(strb("u")); cd.extend(user.pubkey().to_bytes());
    go(&mut svm,"create",pump,cd,vec![
        AccountMeta::new(mint.pubkey(),true),AccountMeta::new_readonly(mint_auth,false),
        AccountMeta::new(bc,false),AccountMeta::new(abc,false),AccountMeta::new_readonly(global,false),
        AccountMeta::new_readonly(meta,false),AccountMeta::new(mdpda,false),AccountMeta::new(user.pubkey(),true),
        AccountMeta::new_readonly(system_program::ID,false),AccountMeta::new_readonly(token,false),
        AccountMeta::new_readonly(ata,false),AccountMeta::new_readonly(sysvar::rent::ID,false),
        AccountMeta::new_readonly(evauth,false),AccountMeta::new_readonly(pump,false)],&[&mint]);
    svm.set_account(feecfg, Account{lamports:37_292_293,data:feeconfig_bytes(),owner:feep,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(gva, Account{lamports:5_000_000,data:gva_bytes(),owner:pump,executable:false,rent_epoch:0}).unwrap();
    let (auser,_)=Pubkey::find_program_address(&[user.pubkey().as_ref(),token.as_ref(),mint.pubkey().as_ref()],&ata);
    go(&mut svm,"create_user_ata",ata,vec![1u8],vec![
        AccountMeta::new(user.pubkey(),true),AccountMeta::new(auser,false),AccountMeta::new_readonly(user.pubkey(),false),
        AccountMeta::new_readonly(mint.pubkey(),false),AccountMeta::new_readonly(system_program::ID,false),AccountMeta::new_readonly(token,false)],&[]);
    let recip=Pubkey::new_from_array([1u8;32]);
    let (cvault,_)=Pubkey::find_program_address(&[b"creator-vault",user.pubkey().as_ref()],&pump);
    let (uva,_)=Pubkey::find_program_address(&[b"user_volume_accumulator",user.pubkey().as_ref()],&pump);
    let bcv2=Pubkey::find_program_address(&[b"bonding-curve-v2",mint.pubkey().as_ref()],&pump).0;
    // WSOL mint for v3 native-quote branch
    let wsol=Pubkey::from_str("So11111111111111111111111111111111111111112").unwrap();
    { let mut wm=vec![0u8;82]; wm[44]=9; wm[45]=1; svm.set_account(wsol, Account{lamports:1_000_000_000,data:wm,owner:token,executable:false,rent_epoch:0}).unwrap(); }
    let qbc=Pubkey::find_program_address(&[bc.as_ref(),token.as_ref(),wsol.as_ref()],&ata).0;
    let qu =Pubkey::find_program_address(&[user.pubkey().as_ref(),token.as_ref(),wsol.as_ref()],&ata).0;
    let buy_metas=vec![
        AccountMeta::new_readonly(global,false),AccountMeta::new(recip,false),AccountMeta::new_readonly(mint.pubkey(),false),
        AccountMeta::new(bc,false),AccountMeta::new(abc,false),AccountMeta::new(auser,false),AccountMeta::new(user.pubkey(),true),
        AccountMeta::new_readonly(system_program::ID,false),AccountMeta::new_readonly(token,false),
        AccountMeta::new(cvault,false),AccountMeta::new_readonly(evauth,false),AccountMeta::new_readonly(pump,false),
        AccountMeta::new_readonly(gva,false),AccountMeta::new(uva,false),
        AccountMeta::new_readonly(feecfg,false),AccountMeta::new_readonly(feep,false),
        AccountMeta::new_readonly(bcv2,false),AccountMeta::new(bbrecip,false)];
    let sell_metas=vec![
        AccountMeta::new_readonly(global,false),AccountMeta::new(recip,false),AccountMeta::new_readonly(mint.pubkey(),false),
        AccountMeta::new(bc,false),AccountMeta::new(abc,false),AccountMeta::new(auser,false),AccountMeta::new(user.pubkey(),true),
        AccountMeta::new_readonly(system_program::ID,false),AccountMeta::new(cvault,false),AccountMeta::new_readonly(token,false),
        AccountMeta::new_readonly(evauth,false),AccountMeta::new_readonly(pump,false),
        AccountMeta::new_readonly(feecfg,false),AccountMeta::new_readonly(feep,false),
        AccountMeta::new_readonly(bcv2,false),AccountMeta::new(bbrecip,false)];
    let v3_metas=vec![
        AccountMeta::new_readonly(global,false),AccountMeta::new_readonly(mint.pubkey(),false),AccountMeta::new_readonly(wsol,false),
        AccountMeta::new_readonly(token,false),AccountMeta::new_readonly(token,false),AccountMeta::new(bc,false),
        AccountMeta::new(abc,false),AccountMeta::new(qbc,false),AccountMeta::new(user.pubkey(),true),
        AccountMeta::new(auser,false),AccountMeta::new(qu,false),AccountMeta::new(uva,false),
        AccountMeta::new_readonly(feecfg,false),AccountMeta::new(bbrecip,false),AccountMeta::new_readonly(system_program::ID,false),
        AccountMeta::new_readonly(evauth,false),AccountMeta::new_readonly(pump,false)];
    if prime{
        let mut bd=BUY.to_vec(); bd.extend(u64le(1_000_000_000)); bd.extend(u64le(1_000_000_000_000)); bd.push(0); bd.push(0);
        go(&mut svm,"prime_buy",pump,bd,buy_metas.clone(),&[]);
    }
    for m in &tmp{ eprintln!("[checkpoint:{}] {}",pump_so,m); }
    let snap_keys=vec![global,evauth,gva,feecfg,mint.pubkey(),bc,abc,auser,cvault,uva,bbrecip,recip,wsol,qbc,qu,bcv2,user.pubkey(),mdpda,mint_auth,
        Pubkey::new_from_array([1;32]),Pubkey::new_from_array([2;32]),Pubkey::new_from_array([3;32]),Pubkey::new_from_array([4;32]),
        Pubkey::new_from_array([5;32]),Pubkey::new_from_array([6;32]),Pubkey::new_from_array([7;32]),Pubkey::new_from_array([8;32])];
    let result_keys=vec![("bc".into(),bc),("abc".into(),abc),("auser".into(),auser),("cvault".into(),cvault),
        ("uva".into(),uva),("gva".into(),gva),("bbrecip".into(),bbrecip),("recip".into(),recip),("global".into(),global)];
    let mint3=Pubkey::new_from_array([0x55u8;32]);
    let ctx=Ctx{pump,token,feep,user:user.pubkey(),mint:mint.pubkey(),mint3,global,bc,abc,auser,cvault,uva,gva,
        bbrecip,recip,feecfg,wsol,qbc,qu,bcv2,buy_metas,sell_metas,v3_metas,snap_keys,result_keys};
    (svm,user,ctx)
}

fn snapshot(svm:&LiteSVM, ctx:&Ctx)->Vec<(Pubkey,Account)>{
    let mut v=vec![];
    for k in &ctx.snap_keys{ if let Some(a)=svm.get_account(k){ v.push((*k,a)); } }
    v
}
// Minimal program set for the hot loop: buy/sell/buy_v3/sell_v3 (native) only CPI
// into spl-token, pump_fees, the system program (builtin) and ATA. Loading the 10MB
// amm/mayhem + t22/metadata on every restore was the runtime bottleneck.
fn add_programs_min(svm:&mut LiteSVM, pump_so:&str){
    svm.add_program_from_file(Pubkey::from_str(PUMP).unwrap(),pump_so).unwrap();
    svm.add_program_from_file(Pubkey::from_str(TOKEN).unwrap(),format!("{}/spl_token.so",LDIR)).unwrap();
    svm.add_program_from_file(Pubkey::from_str(ATA).unwrap(),format!("{}/ata.so",LDIR)).unwrap();
    svm.add_program_from_file(Pubkey::from_str(FEEP).unwrap(),format!("{}/fees.so",LDIR)).unwrap();
}
fn restore(pump_so:&str, snap:&[(Pubkey,Account)])->LiteSVM{
    let mut svm=LiteSVM::new();
    add_programs_min(&mut svm,pump_so);
    for (k,a) in snap{ svm.set_account(*k,a.clone()).unwrap(); }
    svm
}
fn snap_bytes(snap:&[(Pubkey,Account)])->String{
    let mut s=String::new();
    for (k,a) in snap{ s.push_str(&format!("{} {} {}\n",k,a.lamports,a.data.iter().map(|b|format!("{:02x}",b)).collect::<String>())); }
    s
}

// ---- mutation model ----
#[derive(Clone,Debug)]
enum Mut{ Scalar(usize,u64), DropAcct(usize), ReplaceAcct(usize,Pubkey), WrongOwner(Pubkey), ClearData(Pubkey) }

#[derive(Clone)]
struct Mutant{ label:String, muts:Vec<Mut> }

fn result_snap(svm:&LiteSVM, ctx:&Ctx)->Vec<(String,Option<(u64,Vec<u8>)>)>{
    ctx.result_keys.iter().map(|(n,k)|(n.clone(), svm.get_account(k).map(|a|(a.lamports,a.data)))).collect()
}

// Apply a mutant to (base_data, base_metas) and the restored svm pre-state, run it.
fn run_mutant(pump_so:&str, snap:&[(Pubkey,Account)], user:&Keypair, ctx:&Ctx,
              base_data:&[u8], base_metas:&[AccountMeta], m:&Mutant)
    ->(RunResult, Vec<(String,Option<(u64,Vec<u8>)>)>)
{
    let mut data=base_data.to_vec();
    let mut metas=base_metas.to_vec();
    let mut svm=restore(pump_so,snap);
    for mu in &m.muts{
        match mu{
            Mut::Scalar(off,v)=>{ if *off+8<=data.len(){ data[*off..*off+8].copy_from_slice(&v.to_le_bytes()); } }
            Mut::DropAcct(i)=>{ if *i<metas.len(){ metas.remove(*i); } }
            Mut::ReplaceAcct(i,pk)=>{ if *i<metas.len(){ metas[*i].pubkey=*pk; } }
            Mut::WrongOwner(pk)=>{ if let Some(mut a)=svm.get_account(pk){ a.owner=system_program::ID; let _=svm.set_account(*pk,a); } }
            Mut::ClearData(pk)=>{ if let Some(mut a)=svm.get_account(pk){ for b in a.data.iter_mut(){*b=0;} let _=svm.set_account(*pk,a); } }
        }
    }
    let prog=ctx.pump;
    let r=send_capture(&mut svm,user,prog,data,metas,&[]);
    let rs=result_snap(&svm,ctx);
    (r,rs)
}

// Divergence signature + field list between original and clone.
fn diff(o:&RunResult, c:&RunResult, os:&[(String,Option<(u64,Vec<u8>)>)], cs:&[(String,Option<(u64,Vec<u8>)>)])->Vec<String>{
    let mut f=vec![];
    if o.ok!=c.ok{ f.push(format!("ok(orig={},clone={})",o.ok,c.ok)); }
    if o.errcode!=c.errcode{ f.push(format!("error(orig={},clone={})",o.errcode,c.errcode)); }
    if o.logs!=c.logs{ f.push("logs".to_string()); }
    if o.event!=c.event{ f.push("event".to_string()); }
    for (i,(n,ov)) in os.iter().enumerate(){
        let cv=&cs[i].1;
        if ov!=cv{ f.push(format!("acct:{}",n)); }
    }
    f
}
// signature used by the minimizer to decide "same divergence"
fn sig(o:&RunResult,c:&RunResult)->(bool,String,bool,String){ (o.ok,o.errcode.clone(),c.ok,c.errcode.clone()) }

fn fmt_acct(v:&Option<(u64,Vec<u8>)>)->String{
    match v{ None=>"<absent>".into(), Some((lam,d))=>format!("lamports={} len={} data[0..96]={}",lam,d.len(),d.iter().take(96).map(|b|format!("{:02x}",b)).collect::<String>()) }
}
fn metas_dump(metas:&[AccountMeta])->String{
    metas.iter().enumerate().map(|(i,m)|format!("  [{}] {} signer={} writable={}",i,m.pubkey,m.is_signer,m.is_writable)).collect::<Vec<_>>().join("\n")
}

fn main(){
    let args:Vec<String>=std::env::args().collect();
    let orig_so = if args.len()>1 {args[1].clone()} else {"/home/jojod/sbfcov/progs/pump_orig.so".to_string()};
    let clone_so= if args.len()>2 {args[2].clone()} else {"/home/jojod/sbfcov/progs/pump_clone.so".to_string()};
    let home="/home/jojod/sbfcov";
    std::fs::create_dir_all(format!("{}/fixtures",home)).unwrap();
    std::fs::create_dir_all(format!("{}/corpus",home)).unwrap();
    let mut log=String::new();
    macro_rules! logln{($($a:tt)*)=>{{let s=format!($($a)*);println!("{}",s);log.push_str(&s);log.push('\n');}}}

    logln!("=== pump differential fuzzer ===");
    logln!("orig  = {}",orig_so);
    logln!("clone = {}",clone_so);

    // global coverage accumulators (original program, trace_pc space)
    let mut cov_instr:BTreeSet<u32>=BTreeSet::new();
    let mut cov_edges:BTreeSet<(u32,u32)>=BTreeSet::new();
    let mut total_runs=0usize;
    let mut corpus_accepts=0usize;
    let mut cu_class_diffs=0usize;
    let mut divergences:Vec<String>=vec![];
    let mut fixture_n=0usize;
    let mut div_total=0usize;
    let mut div_by_key:std::collections::BTreeMap<String,usize>=std::collections::BTreeMap::new();
    const FIX_CAP:usize=3; // max fixtures written per (handler|diverging-field-signature)

    // scalar value menu for u64 fields
    let valset:Vec<u64>=vec![0,1,2,1000,1_000_000_000,30_000_000_000,85_000_000_000,
        500_000_000,793_100_000_000_000,1_000_000_000_000_000,1_073_000_000_000_000,999_999_999_999,u64::MAX];

    // handler specs: (name, prime, disc, baseline_tail_builder, metas selector)
    // data layout for all four: disc(8) + amount u64 @8 + arg2 u64 @16 + optional trailing byte(s)
    struct Spec{ name:&'static str, prime:bool, base_data:Vec<u8>, use_metas:u8 } // use_metas: 0 buy,1 sell,2 v3buy,3 v3sell
    let mut specs=vec![];
    { let mut d=BUY.to_vec(); d.extend(u64le(1_000_000_000)); d.extend(u64le(1_000_000_000_000)); d.push(0); d.push(0);
      specs.push(Spec{name:"buy",prime:false,base_data:d,use_metas:0}); }
    { let mut d=BUYV3.to_vec(); d.extend(u64le(100_000_000)); d.extend(u64le(1_000_000_000_000)); d.push(0);
      specs.push(Spec{name:"buy_v3",prime:false,base_data:d,use_metas:2}); }
    { let mut d=SELL.to_vec(); d.extend(u64le(500_000_000)); d.extend(u64le(0));
      specs.push(Spec{name:"sell",prime:true,base_data:d,use_metas:1}); }
    { let mut d=SELLV3.to_vec(); d.extend(u64le(100_000_000)); d.extend(u64le(0));
      specs.push(Spec{name:"sell_v3",prime:true,base_data:d,use_metas:3}); }

    // Build checkpoints (fresh + primed) for both programs, validate snapshot fidelity.
    for prime in [false,true]{
        logln!("");
        logln!("--- checkpoint prime={} ---",prime);
        let (osvm,ouser,octx)=checkpoint(&orig_so,prime);
        let osnap=snapshot(&osvm,&octx);
        let (csvm,_cuser,cctx)=checkpoint(&clone_so,prime);
        let csnap=snapshot(&csvm,&cctx);
        // checkpoint-state divergence?
        let ob=snap_bytes(&osnap); let cb=snap_bytes(&csnap);
        if ob!=cb{
            logln!("CHECKPOINT STATE DIVERGES between orig and clone (prime={})",prime);
            // identify which accounts differ
            for (i,(k,a)) in osnap.iter().enumerate(){
                let cmatch = csnap.iter().find(|(ck,_)|ck==k);
                match cmatch{ Some((_,ca)) if ca.data==a.data && ca.lamports==a.lamports =>{}, Some((_,ca))=>{ logln!("  differs: {} (orig {}B lam {} / clone {}B lam {})",k,a.data.len(),a.lamports,ca.data.len(),ca.lamports); }, None=>{ logln!("  only-orig: {}",k); } }
                let _=i;
            }
        } else {
            logln!("checkpoint state byte-identical across orig/clone ({} accounts)",osnap.len());
        }
        // fidelity validation: restore orig snapshot, run a reference buy/sell, compare to scratch
        {
            let spec_ref = if prime { ("sell",octx.sell_metas.clone(),{let mut d=SELL.to_vec();d.extend(u64le(500_000_000));d.extend(u64le(0));d}) }
                                    else { ("buy",octx.buy_metas.clone(),{let mut d=BUY.to_vec();d.extend(u64le(1_000_000_000));d.extend(u64le(1_000_000_000_000));d.push(0);d.push(0);d}) };
            // scratch run on a fresh from-scratch checkpoint
            let (mut s2,u2,c2)=checkpoint(&orig_so,prime);
            let r_scratch=send_capture(&mut s2,&u2,c2.pump,spec_ref.2.clone(),spec_ref.1.clone(),&[]);
            let m0=Mutant{label:"fidelity".into(),muts:vec![]};
            let (r_restore,_)=run_mutant(&orig_so,&osnap,&ouser,&octx,&spec_ref.2,&spec_ref.1,&m0);
            let okmatch = r_scratch.ok==r_restore.ok && r_scratch.errcode==r_restore.errcode && r_scratch.event==r_restore.event;
            logln!("snapshot fidelity ({}): scratch ok={} err={} | restore ok={} err={} => {}",
                spec_ref.0,r_scratch.ok,r_scratch.errcode,r_restore.ok,r_restore.errcode, if okmatch{"PASS"}else{"FAIL"});
            if !okmatch{ logln!("  WARNING: snapshot/restore not faithful; divergences in this phase may be unreliable."); }
        }

        for spec in specs.iter().filter(|s|s.prime==prime){
            let metas = match spec.use_metas {0=>octx.buy_metas.clone(),1=>octx.sell_metas.clone(),2=>octx.v3_metas.clone(),_=>octx.v3_metas.clone()};
            let nmetas=metas.len();
            // --- generate mutants ---
            let mut mutants:Vec<Mutant>=vec![];
            mutants.push(Mutant{label:"baseline".into(),muts:vec![]}); // seed
            // systematic scalar boundaries (fields @8 and @16)
            for &off in &[8usize,16usize]{
                for &v in &valset{ mutants.push(Mutant{label:format!("scalar@{}={}",off,v),muts:vec![Mut::Scalar(off,v)]}); }
            }
            // two-field extremes
            for (a,b) in [(u64::MAX,0u64),(0,u64::MAX),(1,1),(u64::MAX,u64::MAX),(0,0)]{
                mutants.push(Mutant{label:format!("two@8={}@16={}",a,b),muts:vec![Mut::Scalar(8,a),Mut::Scalar(16,b)]});
            }
            // account drops
            for i in 0..nmetas{ mutants.push(Mutant{label:format!("drop[{}]",i),muts:vec![Mut::DropAcct(i)]}); }
            // wrong-pubkey replaces on key indices
            let mut rng=Rng::new(0xC0FFEE ^ spec.name.bytes().fold(0u64,|a,b|a.wrapping_mul(131).wrapping_add(b as u64)));
            for i in 0..nmetas{ let pk=rng.pubkey(); mutants.push(Mutant{label:format!("replace[{}]=rand",i),muts:vec![Mut::ReplaceAcct(i,pk)]}); }
            // wrong-owner / cleared-data pre-state on key accounts
            for (nm,pk) in [("bc",octx.bc),("abc",octx.abc),("auser",octx.auser),("feecfg",octx.feecfg),("global",octx.global)]{
                mutants.push(Mutant{label:format!("wrongowner:{}",nm),muts:vec![Mut::WrongOwner(pk)]});
                mutants.push(Mutant{label:format!("cleardata:{}",nm),muts:vec![Mut::ClearData(pk)]});
            }
            // random phase
            for _ in 0..40{
                let mut muts=vec![];
                let nm=1+rng.range(2) as usize;
                for _ in 0..nm{
                    match rng.range(4){
                        0=>{let off=if rng.range(2)==0{8}else{16}; let v=valset[rng.range(valset.len() as u64) as usize]; muts.push(Mut::Scalar(off,v));}
                        1=>{let i=rng.range(nmetas as u64) as usize; muts.push(Mut::ReplaceAcct(i,rng.pubkey()));}
                        2=>{let off=if rng.range(2)==0{8}else{16}; muts.push(Mut::Scalar(off,rng.next()));}
                        _=>{let i=rng.range(nmetas as u64) as usize; muts.push(Mut::DropAcct(i));}
                    }
                }
                mutants.push(Mutant{label:"random".into(),muts});
            }

            logln!("");
            logln!("[{}] {} mutants (prime={}, {} accounts)",spec.name,mutants.len(),prime,nmetas);
            let mut local_div=0usize;
            for m in &mutants{
                let (o,os)=run_mutant(&orig_so,&osnap,&ouser,&octx,&spec.base_data,&metas,m);
                let before=cov_instr.len()+cov_edges.len();
                for &pc in &o.instr{ cov_instr.insert(pc); }
                for &e in &o.edges{ cov_edges.insert(e); }
                if cov_instr.len()+cov_edges.len()>before{
                    corpus_accepts+=1;
                    // save corpus entry (input that added new coverage)
                    let cf=format!("{}/corpus/{}_{}.txt",home,spec.name,corpus_accepts);
                    let _=std::fs::write(cf,format!("handler={}\nlabel={}\nmuts={:?}\ndata={}\n",spec.name,m.label,m.muts,
                        {let mut dd=spec.base_data.clone(); for mu in &m.muts{ if let Mut::Scalar(off,v)=mu{ if off+8<=dd.len(){dd[*off..*off+8].copy_from_slice(&v.to_le_bytes());}}} dd.iter().map(|b|format!("{:02x}",b)).collect::<String>()}));
                }
                let (c,cs)=run_mutant(&clone_so,&csnap,&ouser,&cctx,&spec.base_data,&metas,m);
                total_runs+=2;
                // CU class (coarse: only when both succeed) — informational, not a divergence
                if o.ok&&c.ok&&o.cu!=c.cu{ cu_class_diffs+=1; }
                let fields=diff(&o,&c,&os,&cs);
                if !fields.is_empty(){
                    local_div+=1; div_total+=1;
                    let target=sig(&o,&c);
                    // minimize ONLY scalar-only mutants (shrink amounts toward 0/1 keeping the
                    // same divergence signature); account mutants are already minimal.
                    let scalar_only=!m.muts.is_empty() && m.muts.iter().all(|x|matches!(x,Mut::Scalar(_,_)));
                    let mut best=m.clone(); let mut bo=o; let mut bc_=c; let mut bos=os; let mut bcs=cs;
                    if scalar_only && m.muts.len()>=1 {
                        let mut cand:Vec<Mutant>=vec![];
                        if m.muts.len()>1{ for mu in &m.muts{ cand.push(Mutant{label:format!("{}|single",m.label),muts:vec![mu.clone()]}); } }
                        for mu in &m.muts{ if let Mut::Scalar(off,_)=mu{ for v in [1u64,0]{ cand.push(Mutant{label:format!("{}|@{}={}",m.label,off,v),muts:vec![Mut::Scalar(*off,v)]}); } } }
                        for cm in &cand{
                            let (co,cos)=run_mutant(&orig_so,&osnap,&ouser,&octx,&spec.base_data,&metas,cm);
                            let (cc,ccs)=run_mutant(&clone_so,&csnap,&ouser,&cctx,&spec.base_data,&metas,cm);
                            total_runs+=2;
                            if sig(&co,&cc)==target && !diff(&co,&cc,&cos,&ccs).is_empty(){
                                best=cm.clone(); bo=co; bc_=cc; bos=cos; bcs=ccs; break;
                            }
                        }
                    }
                    let bfields=diff(&bo,&bc_,&bos,&bcs);
                    let key=format!("{}|{}",spec.name,bfields.join(","));
                    let cnt=div_by_key.entry(key.clone()).or_insert(0); *cnt+=1;
                    let write_fix = *cnt<=FIX_CAP;
                    // offset localization: pump PCs executed by one program but not the other
                    let only_o:Vec<u32>=bo.instr.difference(&bc_.instr).take(10).map(|p|p+36).collect();
                    let only_c:Vec<u32>=bc_.instr.difference(&bo.instr).take(10).map(|p|p+36).collect();
                    // frame0 first-divergence PC (if the main pump frame diverges in-stream)
                    let mut first_pc=String::from("(pump frame0 identical/absent; divergence is in a CPI, event, account, or a later frame)");
                    let n=bo.frame0.len().min(bc_.frame0.len());
                    for i in 0..n{ if bo.frame0[i]!=bc_.frame0[i]{ first_pc=format!("frame0 index {}: sbftool_pc orig={} clone={}",i,bo.frame0[i]+36,bc_.frame0[i]+36); break; } }
                    if !first_pc.starts_with("frame0") && bo.frame0.len()!=bc_.frame0.len() && n>0 {
                        first_pc=format!("frame0 length differs (orig {} / clone {}); diverges after sbftool_pc {}",bo.frame0.len(),bc_.frame0.len(),bo.frame0[n-1]+36);
                    }
                    if write_fix {
                        // byte-level dump of each diverging account (orig vs clone)
                        let mut acctdump=String::new();
                        for f in &bfields{ if let Some(name)=f.strip_prefix("acct:"){
                            let ov=bos.iter().find(|(n,_)|n==name).and_then(|(_,v)|v.clone());
                            let cv=bcs.iter().find(|(n,_)|n==name).and_then(|(_,v)|v.clone());
                            acctdump.push_str(&format!("  [{}]\n    orig : {}\n    clone: {}\n",name,fmt_acct(&ov),fmt_acct(&cv)));
                        }}
                        if acctdump.is_empty(){ acctdump.push_str("  (no account-state divergence; see logs/error/event)\n"); }
                        // reproducibility: re-run the minimized case and assert the same divergence
                        let (ro,ros)=run_mutant(&orig_so,&osnap,&ouser,&octx,&spec.base_data,&metas,&best);
                        let (rc,rcs)=run_mutant(&clone_so,&csnap,&ouser,&cctx,&spec.base_data,&metas,&best);
                        total_runs+=2;
                        let repro = diff(&ro,&rc,&ros,&rcs)==bfields;
                        let mut fdata=spec.base_data.clone(); let mut fmetas=metas.clone();
                        for mu in &best.muts{ match mu{ Mut::Scalar(off,v)=>{ if off+8<=fdata.len(){fdata[*off..*off+8].copy_from_slice(&v.to_le_bytes());}}, Mut::DropAcct(i)=>{ if *i<fmetas.len(){fmetas.remove(*i);}}, Mut::ReplaceAcct(i,pk)=>{ if *i<fmetas.len(){fmetas[*i].pubkey=*pk;}}, _=>{} } }
                        fixture_n+=1;
                        let fx=format!("{}/fixtures/{}_{:02}.txt",home,spec.name,fixture_n);
                        let body=format!(
"=== DIVERGENCE FIXTURE {} ===
handler        : {}
original .so   : {}
clone .so      : {}
mutant label   : {}
minimized muts : {:?}
diverging field: {}
pre-state muts : {}
REPRODUCED on re-run: {}
sbftool PCs executed by ORIGINAL only (first 10): {:?}
sbftool PCs executed by CLONE only    (first 10): {:?}
frame0 note    : {}

--- instruction data (hex, after ComputeBudget ix) ---
{}

--- accounts ({} metas) ---
{}

--- diverging account state (orig vs clone) ---
{}
--- ORIGINAL result ---
ok={} error={} cu={}
event={}
logs:
{}

--- CLONE result ---
ok={} error={} cu={}
event={}
logs:
{}
",
                            fx,spec.name,orig_so,clone_so,best.label,best.muts,bfields.join(", "),
                            best.muts.iter().filter(|x|matches!(x,Mut::WrongOwner(_)|Mut::ClearData(_))).map(|x|format!("{:?}",x)).collect::<Vec<_>>().join(";"),
                            repro,
                            only_o,only_c,first_pc,
                            fdata.iter().map(|b|format!("{:02x}",b)).collect::<String>(),
                            fmetas.len(),metas_dump(&fmetas),
                            acctdump,
                            bo.ok,bo.errcode,bo.cu,bo.event,bo.logs,
                            bc_.ok,bc_.errcode,bc_.cu,bc_.event,bc_.logs);
                        std::fs::write(&fx,&body).unwrap();
                        divergences.push(format!("{} [{}] fields=[{}] origCU={} cloneCU={} | only_o_pc={:?} only_c_pc={:?}",spec.name,best.label,bfields.join(","),bo.cu,bc_.cu,only_o.get(0),only_c.get(0)));
                        logln!("  DIVERGENCE[{}x]: {} label={} fields=[{}] -> {}",*cnt,spec.name,best.label,bfields.join(","),fx);
                    }
                }
            }
            logln!("[{}] divergences in this handler: {}",spec.name,local_div);
        }
    }

    // write unioned fuzz coverage trace for cov_report
    {
        let mut fo=String::new();
        fo.push_str("INSTR ");
        fo.push_str(&cov_instr.iter().map(|p|p.to_string()).collect::<Vec<_>>().join(" "));
        fo.push('\n');
        for (x,y) in cov_edges.iter(){ fo.push_str(&format!("EDGE {} {}\n",x,y)); }
        std::fs::write(format!("{}/traces/fuzz_union.trace",home),fo).unwrap();
    }

    logln!("");
    logln!("=== FUZZ SUMMARY ===");
    logln!("total differential runs (incl. minimizer): {}",total_runs);
    logln!("corpus-accepted inputs (added new coverage): {}",corpus_accepts);
    logln!("TOTAL diverging mutants (all)              : {}",div_total);
    logln!("distinct divergence signatures            : {}",div_by_key.len());
    logln!("fixtures written (capped {}/signature)      : {}",FIX_CAP,fixture_n);
    logln!("CU-class-only differences (not divergences): {}",cu_class_diffs);
    logln!("fuzz-added distinct pump instructions: {}",cov_instr.len());
    logln!("fuzz-added distinct pump edges       : {}",cov_edges.len());
    logln!("");
    logln!("--- divergence signatures (handler|fields => count of mutants) ---");
    for (k,v) in div_by_key.iter(){ logln!("  {} => {}",k,v); }
    if !divergences.is_empty(){
        logln!("");
        logln!("--- representative divergences (one line each, capped) ---");
        for d in &divergences{ logln!("  {}",d); }
    }
    std::fs::write(format!("{}/fuzz_run.log",home),&log).unwrap();
}
