// Differential harness for pump_fees ADMIN handlers: initialize_fee_config,
// initialize_buyback, sweep_buyback. DEPLOYED (oracle) vs RECOVERED, side-by-side in LiteSVM
// on identical deterministically-seeded state. For each handler we drive the REAL handler body
// (success) or a matched account-validation rejection, then compare
//   { ok, exact error code, resulting account bytes, normalized logs }.
// CU is informational only.
//
// Dispatch: we send the SAME instruction bytes to BOTH programs; each program's own on-chain
// Anchor dispatcher routes by discriminator to its own handler. We never reference recovered
// handler addresses. deployed.so is loaded ONLY as the pfeeUxB... program for the oracle run;
// it is never a build input.
//
// Account order + args + PDA seeds reversed from the DEPLOYED binary and cross-checked against
// the upstream IDL /mnt/d/dev/ext/pumpfun-source/evidence/upstream/pump_fees.json :
//   initialize_fee_config @0x12d72 : [admin(signer,addr=8LWu..), fee_config(init,["fee_config",cfg]),
//       system, config_program_id, event_authority(["__event_authority"]), program]  args: none
//   initialize_buyback    @0x13d6a : [payer(signer), buyback_vault(init,["buyback-vault",index]),
//       buyback_vault_ata(ATA), system, ata_prog, mint, token_prog, event_authority, program]  args: index:u8
//   sweep_buyback         @0x13e01 : [destination(mut), authority(signer), buyback_vault(["buyback-vault",index],
//       has_one authority->6016), buyback_vault_ata, destination_ata, system, ata_prog, mint,
//       token_prog, event_authority, program]  args: index:u8
// Fixed admin const 8LWu7QM2dGR1G8nKDHthckea57bkCzXyBTAKPJUBDHo8 @ .rodata 0xc36e0 (6001 InvalidAdmin).
// BuybackVault 208B: disc 99a64790b3bd89fb, authority@8, total_claimed@40, token1@48, token2@56,
//   last_claimed@64, claim_rate_limit@72, _reserved[128]@80.  seed literal "buyback-vault" @ file 0xc3fa8 (dec 802792).
//
// Sigverify is DISABLED (litesvm .with_sigverify(false)) so the fixed-admin (8LWu..) path of
// initialize_fee_config can be driven with 8LWu.. as a message signer. This only skips the
// cryptographic signature check; the runtime still sets the is_signer flag the Anchor Signer /
// address constraint reads, so the handler logic executes exactly as on-chain. Both builds run
// under the identical setting, so this cannot create an asymmetry between them.

use litesvm::LiteSVM;
use solana_sdk::{pubkey::Pubkey, signature::{Signer, Signature}, account::Account,
    instruction::{Instruction, AccountMeta}, message::Message, transaction::Transaction};
use std::str::FromStr;

const FEEP:&str = "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ";
const PUMP:&str = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P";
const WSOL:&str = "So11111111111111111111111111111111111111112";
const TOKEN:&str= "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA";
const ATA:&str  = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL";
const ADMIN:&str= "8LWu7QM2dGR1G8nKDHthckea57bkCzXyBTAKPJUBDHo8"; // fixed admin (6001 InvalidAdmin gate)
const DEP:&str  = "/mnt/d/dev/ext/pumpfun-source/evidence/dependencies";

const D_INIT_FC:[u8;8]      = [0x3e,0xa2,0x14,0x85,0x79,0x41,0x91,0x1b];
const D_INIT_BUYBACK:[u8;8] = [0xfa,0x81,0xec,0xa0,0xe3,0x24,0x67,0x86];
const D_SWEEP:[u8;8]        = [0x8a,0x21,0xcc,0x26,0xcf,0xa1,0x9f,0xe2];

const BV_DISC:[u8;8] = [0x99,0xa6,0x47,0x90,0xb3,0xbd,0x89,0xfb]; // BuybackVault account disc

struct Step{
    name:String,
    ok:bool,
    err:String,
    cu:u64,
    // labeled post-state snapshots: label -> Option<(lamports, data_bytes)>
    snaps:Vec<(String,Option<(u64,Vec<u8>)>)>,
    logs:Vec<String>,
}

fn pk(s:&str)->Pubkey{Pubkey::from_str(s).unwrap()}
fn cu(l:&[String])->u64{for x in l.iter().rev(){if let Some(i)=x.find("consumed "){let r=&x[i+9..];if let Some(s)=r.find(char::is_whitespace){if let Ok(v)=r[..s].parse(){return v}}}}0}
// Normalize logs: drop CU-bearing lines (informational only); keep program flow + event data.
fn norm(logs:&[String])->Vec<String>{logs.iter().filter(|l|!l.contains("compute units")&&!l.contains("consumed ")).cloned().collect()}
// Canonicalize the volatile, compile-time source-location string inside Anchor error logs
// ("AnchorError thrown in <src path>:<line>."). That path+line is baked in from the source TREE
// LAYOUT at build time (std::panic::Location), exactly the class of compilation artifact static
// bindiff reports; it is not behavioral. Behavioral log compare uses this canonical form; the raw
// divergence is still printed verbatim so nothing is hidden.
fn canon_line(l:&str)->String{
    if let Some(p)=l.find("AnchorError thrown in "){
        if let Some(q)=l[p..].find(". Error Code"){
            return format!("{}AnchorError thrown in <SRC>{}",&l[..p],&l[p+q..]);
        }
    }
    l.to_string()
}
fn canon(logs:&[String])->Vec<String>{logs.iter().map(|l|canon_line(l)).collect()}

fn spl_mint82(dec:u8)->Vec<u8>{let mut v=vec![0u8;82];v[44]=dec;v[45]=1;v}
fn spl_tok165(mint:Pubkey,owner:Pubkey,amount:u64)->Vec<u8>{let mut v=vec![0u8;165];v[0..32].copy_from_slice(&mint.to_bytes());v[32..64].copy_from_slice(&owner.to_bytes());v[64..72].copy_from_slice(&amount.to_le_bytes());v[108]=1;v}
fn ata(owner:Pubkey,tok:Pubkey,mint:Pubkey,atap:Pubkey)->Pubkey{Pubkey::find_program_address(&[owner.as_ref(),tok.as_ref(),mint.as_ref()],&atap).0}
// BuybackVault 208 bytes with a chosen authority (disc + authority@8, rest zero).
fn bv_bytes(authority:Pubkey)->Vec<u8>{let mut d=BV_DISC.to_vec();d.extend_from_slice(&authority.to_bytes());d.resize(208,0);d}

fn new_svm(fees_so:&str)->(LiteSVM,Pubkey){
    let mut svm=LiteSVM::new().with_sigverify(false);
    svm.add_program_from_file(pk(FEEP),fees_so).unwrap();
    svm.add_program_from_file(pk(TOKEN),format!("{}/spl_token/deployed.so",DEP)).unwrap();
    svm.add_program_from_file(pk(ATA),format!("{}/associated_token/deployed.so",DEP)).unwrap();
    let user=solana_sdk::signer::keypair::keypair_from_seed(&[7u8;32]).unwrap();
    svm.airdrop(&user.pubkey(),1_000_000_000_000).unwrap();
    (svm,user.pubkey())
}

// Build [compute-budget, ix], sign with the right number of dummy signatures (sigverify off),
// send, snapshot the requested accounts, return a Step.
fn exec(svm:&mut LiteSVM, name:&str, payer:Pubkey, metas:Vec<AccountMeta>, data:Vec<u8>, snap:&[(&str,Pubkey)])->Step{
    let ix=Instruction{program_id:pk(FEEP),accounts:metas,data};
    let cbud=pk("ComputeBudget111111111111111111111111111111");
    let mut cbd=vec![2u8]; cbd.extend_from_slice(&1_400_000u32.to_le_bytes());
    let cbix=Instruction{program_id:cbud,accounts:vec![],data:cbd};
    let bh=svm.latest_blockhash();
    let msg=Message::new_with_blockhash(&[cbix,ix],Some(&payer),&bh);
    let nsig=msg.header.num_required_signatures as usize;
    let tx=Transaction{signatures:vec![Signature::default();nsig],message:msg};
    let (ok,err,logs,cuv)=match svm.send_transaction(tx){
        Ok(m)=>(true,String::new(),m.logs.clone(),cu(&m.logs)),
        Err(e)=>(false,format!("{:?}",e.err),e.meta.logs.clone(),cu(&e.meta.logs)),
    };
    let snaps=snap.iter().map(|(lbl,p)|{
        let a=svm.get_account(p).map(|ac|(ac.lamports,ac.data.clone()));
        (lbl.to_string(),a)
    }).collect();
    Step{name:name.into(),ok,err,cu:cuv,snaps,logs:norm(&logs)}
}

fn run(fees_so:&str)->Vec<Step>{
    let feep=pk(FEEP); let pump=pk(PUMP); let token=pk(TOKEN); let atap=pk(ATA);
    let wsol=pk(WSOL); let admin=pk(ADMIN);
    let sys=solana_sdk::system_program::id();
    let ev=Pubkey::find_program_address(&[b"__event_authority"],&feep).0;
    let mut out=vec![];

    // ============ initialize_fee_config ============
    // Case A: wrong admin (our user) -> expect 6001 InvalidAdmin, matched rejection, no account created.
    {
        let (mut svm,user)=new_svm(fees_so);
        let (fc,_b)=Pubkey::find_program_address(&[b"fee_config",pump.as_ref()],&feep);
        let metas=vec![
            AccountMeta::new(user,true),            // admin (wrong)
            AccountMeta::new(fc,false),             // fee_config (init)
            AccountMeta::new_readonly(sys,false),   // system
            AccountMeta::new_readonly(pump,false),  // config_program_id
            AccountMeta::new_readonly(ev,false),    // event_authority
            AccountMeta::new_readonly(feep,false),  // program
        ];
        out.push(exec(&mut svm,"ifc_reject_wrongadmin",user,metas,D_INIT_FC.to_vec(),&[("fee_config",fc)]));
    }
    // Case B: correct fixed admin 8LWu.. (impersonated) -> expect SUCCESS, fee_config created (2512).
    {
        let (mut svm,_user)=new_svm(fees_so);
        svm.airdrop(&admin,1_000_000_000).unwrap(); // fund the fixed admin as payer
        let (fc,_b)=Pubkey::find_program_address(&[b"fee_config",pump.as_ref()],&feep);
        let metas=vec![
            AccountMeta::new(admin,true),
            AccountMeta::new(fc,false),
            AccountMeta::new_readonly(sys,false),
            AccountMeta::new_readonly(pump,false),
            AccountMeta::new_readonly(ev,false),
            AccountMeta::new_readonly(feep,false),
        ];
        out.push(exec(&mut svm,"ifc_success_fixedadmin",admin,metas,D_INIT_FC.to_vec(),&[("fee_config",fc)]));
    }

    // ============ initialize_buyback ============
    let mint=Pubkey::new_from_array([0x33u8;32]); // custom classic SPL mint, 6 decimals
    // Case C: index=0 -> SUCCESS, buyback_vault(208)+ata created.
    {
        let (mut svm,user)=new_svm(fees_so);
        svm.set_account(mint,Account{lamports:1_000_000_000,data:spl_mint82(6),owner:token,executable:false,rent_epoch:0}).unwrap();
        let (bv,_b)=Pubkey::find_program_address(&[b"buyback-vault",&[0u8]],&feep);
        let bv_ata=ata(bv,token,mint,atap);
        let metas=vec![
            AccountMeta::new(user,true),             // payer
            AccountMeta::new(bv,false),              // buyback_vault (init)
            AccountMeta::new(bv_ata,false),          // buyback_vault_ata (init_if_needed)
            AccountMeta::new_readonly(sys,false),
            AccountMeta::new_readonly(atap,false),
            AccountMeta::new_readonly(mint,false),
            AccountMeta::new_readonly(token,false),
            AccountMeta::new_readonly(ev,false),
            AccountMeta::new_readonly(feep,false),
        ];
        let mut d=D_INIT_BUYBACK.to_vec(); d.push(0);
        out.push(exec(&mut svm,"ib_success_idx0",user,metas,d,&[("buyback_vault",bv),("buyback_vault_ata",bv_ata)]));
    }
    // Case D: index=8 -> expect 6026 InvalidBuybackIndex, matched rejection.
    {
        let (mut svm,user)=new_svm(fees_so);
        svm.set_account(mint,Account{lamports:1_000_000_000,data:spl_mint82(6),owner:token,executable:false,rent_epoch:0}).unwrap();
        let (bv,_b)=Pubkey::find_program_address(&[b"buyback-vault",&[8u8]],&feep);
        let bv_ata=ata(bv,token,mint,atap);
        let metas=vec![
            AccountMeta::new(user,true),
            AccountMeta::new(bv,false),
            AccountMeta::new(bv_ata,false),
            AccountMeta::new_readonly(sys,false),
            AccountMeta::new_readonly(atap,false),
            AccountMeta::new_readonly(mint,false),
            AccountMeta::new_readonly(token,false),
            AccountMeta::new_readonly(ev,false),
            AccountMeta::new_readonly(feep,false),
        ];
        let mut d=D_INIT_BUYBACK.to_vec(); d.push(8);
        out.push(exec(&mut svm,"ib_reject_idx8",user,metas,d,&[("buyback_vault",bv)]));
    }

    // ============ sweep_buyback ============
    // seed helper closure body inlined per case (fresh svm each).
    let dest=Pubkey::new_from_array([0x44u8;32]);
    // Case E: SUCCESS, non-WSOL mint (token2 branch), excess lamports + token balance to sweep.
    {
        let (mut svm,user)=new_svm(fees_so);
        svm.set_account(mint,Account{lamports:1_000_000_000,data:spl_mint82(6),owner:token,executable:false,rent_epoch:0}).unwrap();
        let (bv,_b)=Pubkey::find_program_address(&[b"buyback-vault",&[0u8]],&feep);
        let bv_ata=ata(bv,token,mint,atap);
        let dest_ata=ata(dest,token,mint,atap);
        let rent=svm.minimum_balance_for_rent_exemption(208);
        svm.set_account(bv,Account{lamports:rent+1_000_000,data:bv_bytes(user),owner:feep,executable:false,rent_epoch:0}).unwrap();
        svm.set_account(bv_ata,Account{lamports:2_039_280,data:spl_tok165(mint,bv,500_000),owner:token,executable:false,rent_epoch:0}).unwrap();
        svm.set_account(dest_ata,Account{lamports:2_039_280,data:spl_tok165(mint,dest,0),owner:token,executable:false,rent_epoch:0}).unwrap();
        svm.set_account(dest,Account{lamports:1_000_000,data:vec![],owner:sys,executable:false,rent_epoch:0}).unwrap();
        let metas=vec![
            AccountMeta::new(dest,false),            // destination
            AccountMeta::new(user,true),             // authority (== vault.authority)
            AccountMeta::new(bv,false),              // buyback_vault
            AccountMeta::new(bv_ata,false),          // buyback_vault_ata
            AccountMeta::new(dest_ata,false),        // destination_ata
            AccountMeta::new_readonly(sys,false),
            AccountMeta::new_readonly(atap,false),
            AccountMeta::new_readonly(mint,false),
            AccountMeta::new_readonly(token,false),
            AccountMeta::new_readonly(ev,false),
            AccountMeta::new_readonly(feep,false),
        ];
        let mut d=D_SWEEP.to_vec(); d.push(0);
        out.push(exec(&mut svm,"sweep_success_token2",user,metas,d,
            &[("buyback_vault",bv),("buyback_vault_ata",bv_ata),("destination_ata",dest_ata),("destination",dest)]));
    }
    // Case F: SUCCESS, WSOL mint (native/token1 branch).
    {
        let (mut svm,user)=new_svm(fees_so);
        svm.set_account(wsol,Account{lamports:1_000_000_000,data:spl_mint82(9),owner:token,executable:false,rent_epoch:0}).unwrap();
        let (bv,_b)=Pubkey::find_program_address(&[b"buyback-vault",&[0u8]],&feep);
        let bv_ata=ata(bv,token,wsol,atap);
        let dest_ata=ata(dest,token,wsol,atap);
        let rent=svm.minimum_balance_for_rent_exemption(208);
        svm.set_account(bv,Account{lamports:rent+1_000_000,data:bv_bytes(user),owner:feep,executable:false,rent_epoch:0}).unwrap();
        svm.set_account(bv_ata,Account{lamports:2_039_280,data:spl_tok165(wsol,bv,500_000),owner:token,executable:false,rent_epoch:0}).unwrap();
        svm.set_account(dest_ata,Account{lamports:2_039_280,data:spl_tok165(wsol,dest,0),owner:token,executable:false,rent_epoch:0}).unwrap();
        svm.set_account(dest,Account{lamports:1_000_000,data:vec![],owner:sys,executable:false,rent_epoch:0}).unwrap();
        let metas=vec![
            AccountMeta::new(dest,false),
            AccountMeta::new(user,true),
            AccountMeta::new(bv,false),
            AccountMeta::new(bv_ata,false),
            AccountMeta::new(dest_ata,false),
            AccountMeta::new_readonly(sys,false),
            AccountMeta::new_readonly(atap,false),
            AccountMeta::new_readonly(wsol,false),
            AccountMeta::new_readonly(token,false),
            AccountMeta::new_readonly(ev,false),
            AccountMeta::new_readonly(feep,false),
        ];
        let mut d=D_SWEEP.to_vec(); d.push(0);
        out.push(exec(&mut svm,"sweep_success_token1_wsol",user,metas,d,
            &[("buyback_vault",bv),("buyback_vault_ata",bv_ata),("destination_ata",dest_ata),("destination",dest)]));
    }
    // Case G: has_one authority mismatch -> expect 6016 NotAuthorized, matched rejection.
    {
        let (mut svm,user)=new_svm(fees_so);
        svm.set_account(mint,Account{lamports:1_000_000_000,data:spl_mint82(6),owner:token,executable:false,rent_epoch:0}).unwrap();
        let (bv,_b)=Pubkey::find_program_address(&[b"buyback-vault",&[0u8]],&feep);
        let bv_ata=ata(bv,token,mint,atap);
        let dest_ata=ata(dest,token,mint,atap);
        let rent=svm.minimum_balance_for_rent_exemption(208);
        let other=Pubkey::new_from_array([0x55u8;32]); // vault.authority != signer
        svm.set_account(bv,Account{lamports:rent+1_000_000,data:bv_bytes(other),owner:feep,executable:false,rent_epoch:0}).unwrap();
        svm.set_account(bv_ata,Account{lamports:2_039_280,data:spl_tok165(mint,bv,500_000),owner:token,executable:false,rent_epoch:0}).unwrap();
        svm.set_account(dest_ata,Account{lamports:2_039_280,data:spl_tok165(mint,dest,0),owner:token,executable:false,rent_epoch:0}).unwrap();
        svm.set_account(dest,Account{lamports:1_000_000,data:vec![],owner:sys,executable:false,rent_epoch:0}).unwrap();
        let metas=vec![
            AccountMeta::new(dest,false),
            AccountMeta::new(user,true),
            AccountMeta::new(bv,false),
            AccountMeta::new(bv_ata,false),
            AccountMeta::new(dest_ata,false),
            AccountMeta::new_readonly(sys,false),
            AccountMeta::new_readonly(atap,false),
            AccountMeta::new_readonly(mint,false),
            AccountMeta::new_readonly(token,false),
            AccountMeta::new_readonly(ev,false),
            AccountMeta::new_readonly(feep,false),
        ];
        let mut d=D_SWEEP.to_vec(); d.push(0);
        out.push(exec(&mut svm,"sweep_reject_notauth",user,metas,d,&[("buyback_vault",bv)]));
    }

    out
}

fn hx(v:&[u8])->String{v.iter().map(|b|format!("{:02x}",b)).collect()}

fn main(){
    let a:Vec<String>=std::env::args().collect();
    if a.len()<3 { eprintln!("usage: admin <deployed.so> <recovered.so>"); std::process::exit(2); }
    let o=run(&a[1]); let c=run(&a[2]);
    let mut all=true;
    for i in 0..o.len().min(c.len()){
        let okm=o[i].ok==c[i].ok;
        let em =o[i].err==c[i].err;
        // compare snapshots pairwise by label/order
        let mut snapm=true;
        let mut snapdetail=String::new();
        for (j,(lbl,od)) in o[i].snaps.iter().enumerate(){
            let cd=&c[i].snaps.get(j).map(|x|x.1.clone()).unwrap_or(None);
            let m = &od.as_ref().map(|x|(x.0,x.1.clone())) == cd || od==&c[i].snaps[j].1;
            let eq = od==&c[i].snaps[j].1;
            if !eq {
                snapm=false;
                let od_s=od.as_ref().map(|(l,d)|format!("lam={} len={} data={}",l,d.len(),hx(d))).unwrap_or("<none>".into());
                let cd_s=c[i].snaps[j].1.as_ref().map(|(l,d)|format!("lam={} len={} data={}",l,d.len(),hx(d))).unwrap_or("<none>".into());
                snapdetail.push_str(&format!("\n    SNAP[{}] DIVERGE\n      deployed:  {}\n      recovered: {}",lbl,od_s,cd_s));
            } else {
                let _=m;
                let tag=od.as_ref().map(|(l,d)|format!("lam={} len={}",l,d.len())).unwrap_or("<none>".into());
                snapdetail.push_str(&format!("\n    SNAP[{}] match ({})",lbl,tag));
            }
        }
        let logm_raw=o[i].logs==c[i].logs;
        let logm=canon(&o[i].logs)==canon(&c[i].logs); // behavioral log compare (source-loc canonicalized)
        let cosmetic = logm && !logm_raw;              // logs differ ONLY by compile-time source location
        let casem=okm&&em&&snapm&&logm;
        if !casem{all=false;}
        println!("{:<26} {}  ok:{}/{} err_match:{} snap_match:{} log_match:{}{}  cu:{} /{}",
            o[i].name, if casem{if cosmetic{"MATCH*  "}else{"MATCH   "}}else{"DIVERGE!"},
            o[i].ok,c[i].ok,em,snapm,logm,
            if cosmetic{" (raw log differs only by compile-time AnchorError src-location)"}else{""},
            o[i].cu,c[i].cu);
        if !o[i].err.is_empty()||!c[i].err.is_empty(){
            println!("    err deployed=[{}] recovered=[{}]",o[i].err,c[i].err);
        }
        print!("{}",snapdetail);
        if !snapdetail.is_empty(){println!();}
        if cosmetic{
            // surface the exact volatile lines so the cosmetic diff is auditable, not hidden
            for (dl,rl) in o[i].logs.iter().zip(c[i].logs.iter()){
                if dl!=rl{
                    println!("    COSMETIC src-location diff (behaviorally equal):");
                    println!("      D| {}",dl);
                    println!("      R| {}",rl);
                }
            }
        }
        if !logm{
            println!("    LOG DIVERGE:");
            println!("      deployed logs ({}):",o[i].logs.len());
            for l in &o[i].logs{println!("        D| {}",l);}
            println!("      recovered logs ({}):",c[i].logs.len());
            for l in &c[i].logs{println!("        R| {}",l);}
        }
    }
    // Decode a couple of key success snapshots for the report.
    for i in 0..o.len().min(c.len()){
        if o[i].name=="ifc_success_fixedadmin"{
            if let Some((lam,d))=&o[i].snaps[0].1{
                if d.len()>=41{
                    eprintln!("INFO ifc_success: fee_config lam={} len={} disc={} bump={} admin={}",
                        lam,d.len(),hx(&d[0..8]),d[8],bs58pk(&d[9..41]));
                }
            }
        }
        if o[i].name.starts_with("sweep_success"){
            if let Some((lam,d))=&o[i].snaps[0].1{
                if d.len()>=72{
                    let g=|n:usize| u64::from_le_bytes(d[n..n+8].try_into().unwrap());
                    eprintln!("INFO {}: vault lam={} total_claimed(40)={} token1(48)={} token2(56)={} last_claimed(64)={}",
                        o[i].name,lam,g(40),g(48),g(56),g(64));
                }
            }
        }
    }
    println!("\nADMIN_MATCH={}",all);
}

// minimal base58 for pubkey printing (debug only)
fn bs58pk(b:&[u8])->String{
    const A:&[u8]=b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
    let mut zeros=0; for &x in b{if x==0{zeros+=1}else{break}}
    let mut num=b.to_vec(); let mut out=vec![];
    while num.iter().any(|&x|x!=0){
        let mut rem=0u32; for x in num.iter_mut(){let cur=(rem<<8)|*x as u32; *x=(cur/58) as u8; rem=cur%58;}
        out.push(A[rem as usize]);
    }
    for _ in 0..zeros{out.push(A[0]);}
    out.reverse(); String::from_utf8(out).unwrap()
}
