// Differential harness for the 12 pump_fees SHARING / SOCIAL / DONATION handlers.
// DEPLOYED (oracle pfeeUxB..) vs RECOVERED side-by-side in LiteSVM on identical seeded state.
// Same machinery as admin2.rs: two instances, {ok, exact error code, resulting account bytes,
// normalized+src-canonicalized logs} compared; sigverify OFF; fixed admin 8LWu.. impersonation.
// Account orders/args/PDA seeds/discs/error table from /mnt/d/dev/pumpfun-re/fees_sharing_source.md
// (entry table disc column; maps pump_fees_account_metas.json index == wire order).
use litesvm::LiteSVM;
use solana_sdk::{pubkey::Pubkey, signature::{Signer, Signature}, account::Account,
    instruction::{Instruction, AccountMeta}, message::Message, transaction::Transaction};
use std::str::FromStr;

const FEEP:&str="pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ";
const PUMP:&str="6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P";
const AMM:&str ="pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA";
const TOKEN:&str="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA";
const ATA:&str="ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL";
const RELAY:&str="RLAYHr9TRFcKB2ubYQhspcnXiaGpaVzNQvHytt47RZu";
const WSOL:&str="So11111111111111111111111111111111111111112";
const ADMIN:&str="8LWu7QM2dGR1G8nKDHthckea57bkCzXyBTAKPJUBDHo8";
const DEP:&str="/mnt/d/dev/ext/pumpfun-source/evidence/dependencies";
const EVO:&str="/mnt/d/dev/ext/pumpfun-source/evidence/original";

fn pk(s:&str)->Pubkey{Pubkey::from_str(s).unwrap()}
fn u16le(v:u16)->Vec<u8>{v.to_le_bytes().to_vec()}
fn u32le(v:u32)->Vec<u8>{v.to_le_bytes().to_vec()}
fn u64le(v:u64)->Vec<u8>{v.to_le_bytes().to_vec()}

// discriminators (sha256("global:"+name)[:8], entry table col)
fn d_create_fee_sharing_config()->Vec<u8>{vec![0xc3,0x4e,0x56,0x4c,0x6f,0x34,0xfb,0xd5]}
fn d_revoke()->Vec<u8>{vec![0x12,0xe9,0x9e,0x27,0xb9,0xcf,0x3a,0x68]}
fn d_transfer()->Vec<u8>{vec![0xca,0x0a,0x4b,0xc8,0xa4,0x22,0xd2,0x60]}
fn d_update_fee_shares()->Vec<u8>{vec![0xbd,0x0d,0x88,0x63,0xbb,0xa4,0xed,0x23]}
fn d_update_fee_shares_v2()->Vec<u8>{vec![0x6f,0xfb,0x31,0x06,0x4e,0x4e,0x6a,0x12]}
fn d_admin_cto()->Vec<u8>{vec![0x3c,0x64,0x90,0x9c,0x40,0x8a,0xb6,0x25]}
fn d_set_social_claim_authority()->Vec<u8>{vec![0x93,0x36,0xb8,0x9a,0x88,0xed,0xb9,0x99]}
fn d_create_social_fee_pda()->Vec<u8>{vec![0x90,0xe0,0x3b,0xd3,0x4e,0xf8,0xca,0xdc]}
fn d_claim_social_fee_pda()->Vec<u8>{vec![0xe1,0x15,0xfb,0x85,0xa1,0x1e,0xc7,0xe2]}
fn d_claim_social_fee_pda_v2()->Vec<u8>{vec![0x11,0x4d,0xf0,0x86,0x3a,0xbc,0x35,0x95]}
fn d_create_donation_fee_pda()->Vec<u8>{vec![0xf4,0x8b,0x10,0x58,0x0e,0xff,0x7a,0x1a]}
fn d_crank_donation_fee_pda()->Vec<u8>{vec![0xdc,0x0a,0xbd,0xa7,0xa9,0x11,0x19,0x45]}

const FPG_DISC:[u8;8]=[0xa2,0xa5,0xf5,0x31,0x1d,0x25,0x37,0xf2];
const SC_DISC:[u8;8] =[0xd8,0x4a,0x09,0x00,0x38,0x8c,0x5d,0x4b]; // SharingConfig
const SFP_DISC:[u8;8]=[0x8b,0x60,0x35,0x11,0x2a,0xa9,0xce,0x96]; // SocialFeePda
const DFP_DISC:[u8;8]=[0xf6,0xc5,0x60,0x09,0xc1,0x1e,0x5d,0x73]; // DonationFeePda
const GL_DISC:[u8;8] =[0xa7,0xe8,0xe8,0xb1,0xc8,0x6c,0x72,0x7f]; // pump Global

// FeeProgramGlobal: disc,bump@8,authority@9..41,disable_flags@41,social_claim_authority@42..74,claim_rate_limit@74..82, pad 338
fn fpg_bytes(bump:u8,authority:Pubkey,disable:u8,social:Pubkey,rate:u64)->Vec<u8>{
    let mut d=FPG_DISC.to_vec(); d.push(bump);
    d.extend_from_slice(&authority.to_bytes()); d.push(disable);
    d.extend_from_slice(&social.to_bytes()); d.extend(u64le(rate));
    d.resize(338,0); d
}
// SharingConfig serialized (Borsh declaration) order, section 3.1: disc,bump,version,status,mint,admin,admin_revoked,Vec<Shareholder>
fn sharing_config_bytes(bump:u8,status:u8,mint:Pubkey,admin:Pubkey,admin_revoked:u8,holders:&[(Pubkey,u16)],space:usize)->Vec<u8>{
    let mut d=SC_DISC.to_vec(); d.push(bump); d.push(2); d.push(status);
    d.extend_from_slice(&mint.to_bytes()); d.extend_from_slice(&admin.to_bytes()); d.push(admin_revoked);
    d.extend(u32le(holders.len() as u32));
    for (a,b) in holders{d.extend_from_slice(&a.to_bytes()); d.extend(u16le(*b));}
    d.resize(space,0); d
}
// SocialFeePda serialized section 3.2: disc,bump,version,user_id(4+n),platform,total_claimed,total_claimed_stable,last_claimed_at,_reserved[120]
fn social_fee_pda_bytes(bump:u8,version:u8,user_id:&[u8],platform:u8)->Vec<u8>{
    let mut d=SFP_DISC.to_vec(); d.push(bump); d.push(version);
    d.extend(u32le(user_id.len() as u32)); d.extend_from_slice(user_id); d.push(platform);
    d.extend(u64le(0)); d.extend(u64le(0)); d.extend(u64le(0)); let n=d.len(); d.resize(n+120,0); d
}
// DonationFeePda serialized section 3.3: disc,bump,version,config_id,base_mint,quote_mint,creator,total_donated,last_crank_ts,_reserved[64] = 218
fn donation_fee_pda_bytes(bump:u8,version:u8,config_id:Pubkey,base_mint:Pubkey,quote_mint:Pubkey,creator:Pubkey)->Vec<u8>{
    let mut d=DFP_DISC.to_vec(); d.push(bump); d.push(version);
    d.extend_from_slice(&config_id.to_bytes()); d.extend_from_slice(&base_mint.to_bytes());
    d.extend_from_slice(&quote_mint.to_bytes()); d.extend_from_slice(&creator.to_bytes());
    d.extend(u64le(0)); d.extend(u64le(0)); d.resize(218,0); d
}
fn global_bytes(authority:Pubkey)->Vec<u8>{let mut d=GL_DISC.to_vec();d.push(1);d.extend_from_slice(&authority.to_bytes());d.resize(1088,0);d}
fn spl_mint82(dec:u8)->Vec<u8>{let mut v=vec![0u8;82];v[44]=dec;v[45]=1;v}

fn cu(l:&[String])->u64{for x in l.iter().rev(){if let Some(i)=x.find("consumed "){let r=&x[i+9..];if let Some(s)=r.find(char::is_whitespace){if let Ok(v)=r[..s].parse(){return v}}}}0}
fn norm(logs:&[String])->Vec<String>{logs.iter().filter(|l|!l.contains("compute units")&&!l.contains("consumed ")).cloned().collect()}
fn canon_line(l:&str)->String{
    if let Some(p)=l.find("AnchorError thrown in "){ if let Some(q)=l[p..].find(". Error Code"){return format!("{}AnchorError thrown in <SRC>{}",&l[..p],&l[p+q..]);}}
    l.to_string()
}
fn canon(logs:&[String])->Vec<String>{logs.iter().map(|l|canon_line(l)).collect()}

struct Step{name:String,ok:bool,err:String,cu:u64,snaps:Vec<(String,Option<(u64,Vec<u8>)>)>,logs:Vec<String>}

fn new_svm(fees_so:&str)->(LiteSVM,Pubkey){
    let mut svm=LiteSVM::new().with_sigverify(false);
    svm.add_program_from_file(pk(FEEP),fees_so).unwrap();
    svm.add_program_from_file(pk(TOKEN),format!("{}/spl_token/deployed.so",DEP)).unwrap();
    svm.add_program_from_file(pk(ATA),format!("{}/associated_token/deployed.so",DEP)).unwrap();
    svm.add_program_from_file(pk(PUMP),format!("{}/pump/deployed.so",EVO)).unwrap();
    svm.add_program_from_file(pk(AMM),format!("{}/pump_amm/deployed.so",EVO)).unwrap();
    svm.add_program_from_file(pk(RELAY),format!("{}/donation_relay/deployed.so",DEP)).unwrap();
    let user=solana_sdk::signer::keypair::keypair_from_seed(&[7u8;32]).unwrap();
    svm.airdrop(&user.pubkey(),1_000_000_000_000).unwrap();
    (svm,user.pubkey())
}
fn exec(svm:&mut LiteSVM,name:&str,payer:Pubkey,metas:Vec<AccountMeta>,data:Vec<u8>,snap:&[(&str,Pubkey)])->Step{
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
    let snaps=snap.iter().map(|(lbl,p)|(lbl.to_string(),svm.get_account(p).map(|a|(a.lamports,a.data.clone())))).collect();
    Step{name:name.into(),ok,err,cu:cuv,snaps,logs:norm(&logs)}
}

// ---- deep.rs : drive the BODY of the 5 handlers that previously stopped at Anchor 3012 ----
// Layouts: pump Global / BondingCurve and pump_amm Pool from the pump/pump_amm IDLs bundled with the
// checkpoint sources (programs/pump-fees/idls/*.json); account constraints from the recovered
// sharing_admin.rs / sharing_update.rs / create_*.rs.
const BC_DISC:[u8;8]=[23,183,248,55,96,216,172,96];
fn pump_global(authority:Pubkey,admin_set_creator:Pubkey,set_creator:Pubkey)->Vec<u8>{
    let mut d=GL_DISC.to_vec(); d.push(1);                       // initialized@8
    d.extend_from_slice(&authority.to_bytes());                    // authority@9
    d.extend_from_slice(&[0x21;32]);                               // fee_recipient@41
    for v in [1_073_000_000_000_000u64,30_000_000_000,793_100_000_000_000,1_000_000_000_000_000,95]{d.extend(u64le(v));} // @73..113
    d.extend_from_slice(&[0x22;32]);                               // withdraw_authority@113
    d.push(1); d.extend(u64le(0)); d.extend(u64le(30));            // enable_migrate@145 pool_migration_fee@146 creator_fee_bps@154
    for _ in 0..7{d.extend_from_slice(&[0x23;32]);}                // fee_recipients@162..386
    d.extend_from_slice(&set_creator.to_bytes());                  // set_creator_authority@386
    d.extend_from_slice(&admin_set_creator.to_bytes());            // admin_set_creator_authority@418
    d.resize(1088,0); d
}
fn bonding_curve(creator:Pubkey,complete:bool,quote:Pubkey)->Vec<u8>{
    let mut d=BC_DISC.to_vec();
    for v in [1_000_000_000_000_000u64,30_000_000_000,700_000_000_000_000,1_000_000_000,1_000_000_000_000_000]{d.extend(u64le(v));}
    d.push(complete as u8); d.extend_from_slice(&creator.to_bytes()); d.push(0); d.push(0); // mayhem@81 cashback@82
    d.extend_from_slice(&quote.to_bytes());                        // quote_mint@83..115
    d.resize(151,0); d
}
fn acct(svm:&mut LiteSVM,k:Pubkey,lam:u64,data:Vec<u8>,owner:Pubkey){svm.set_account(k,Account{lamports:lam,data,owner,executable:false,rent_epoch:0}).unwrap();}

fn run(fees_so:&str)->Vec<Step>{
    let feep=pk(FEEP); let pump=pk(PUMP); let amm=pk(AMM); let token=pk(TOKEN); let atap=pk(ATA);
    let wsol=pk(WSOL); let admin=pk(ADMIN); let sys=solana_sdk::system_program::id();
    let ev=Pubkey::find_program_address(&[b"__event_authority"],&feep).0;
    let pump_ev=Pubkey::find_program_address(&[b"__event_authority"],&pump).0;
    let amm_ev=Pubkey::find_program_address(&[b"__event_authority"],&amm).0;
    let (fpg,fpg_bump)=Pubkey::find_program_address(&[b"fee-program-global"],&feep);
    let gl=Pubkey::find_program_address(&[b"global"],&pump).0;
    let mint=Pubkey::new_from_array([0x4d;32]);
    let (sc,sc_bump)=Pubkey::find_program_address(&[b"sharing-config",mint.as_ref()],&feep);
    let bc=Pubkey::find_program_address(&[b"bonding-curve",mint.as_ref()],&pump).0;
    let pool_auth=Pubkey::find_program_address(&[b"pool-authority",mint.as_ref()],&pump).0;
    let pcv=Pubkey::find_program_address(&[b"creator-vault",sc.as_ref()],&pump).0;
    let ccva=Pubkey::find_program_address(&[b"creator_vault",sc.as_ref()],&amm).0;
    let ccva_ata=Pubkey::find_program_address(&[ccva.as_ref(),token.as_ref(),wsol.as_ref()],&atap).0;
    let pcv_ata=Pubkey::find_program_address(&[pcv.as_ref(),token.as_ref(),wsol.as_ref()],&atap).0;
    let creator=solana_sdk::signer::keypair::keypair_from_seed(&[7u8;32]).unwrap().pubkey(); // == harness user
    let mut out=vec![];
    // common upstream state
    let base=|svm:&mut LiteSVM, sc_admin:Pubkey, sc_status:u8, sc_seed:bool|{
        svm.airdrop(&admin,10_000_000_000).unwrap();
        acct(svm,mint,1_461_600,spl_mint82(6),token);
        acct(svm,wsol,1_000_000_000,spl_mint82(9),token);
        acct(svm,gl,50_000_000,pump_global(admin,admin,admin),pump);
        acct(svm,bc,1_500_000_000,bonding_curve(creator,false,wsol),pump);
        if sc_seed{acct(svm,sc,8_000_000,sharing_config_bytes(sc_bump,sc_status,mint,sc_admin,0,&[(sc_admin,10000)],1024),feep);}
    };

    // ===== admin_cto_sharing_config : pool_authority=PDA["pool-authority",mint]@pump, global.admin_set_creator_authority==authority =====
    for (nm,auth,arg) in [
        ("admin_cto_success_set_new_admin",admin,Some([0x66u8;32])),
        ("admin_cto_success_none_pause",admin,None),
        ("admin_cto_reject_zero_admin_6001",admin,Some([0u8;32])),
        ("admin_cto_reject_wrong_authority",creator,Some([0x66u8;32]))]{
        let (mut svm,_u)=new_svm(fees_so); base(&mut svm,creator,1,true);
        let metas=vec![AccountMeta::new_readonly(pool_auth,true),AccountMeta::new_readonly(auth,true),AccountMeta::new_readonly(gl,false),
            AccountMeta::new_readonly(mint,false),AccountMeta::new(sc,false),AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false)];
        let mut data=d_admin_cto(); match arg{Some(k)=>{data.push(1);data.extend_from_slice(&k);},None=>data.push(0)}
        out.push(exec(&mut svm,nm,admin,metas,data,&[("sharing_config",sc)]));
    }

    // ===== update_fee_shares (v1) : authority must be sharing_config.admin; remaining = shareholder accounts =====
    let new_holder=Pubkey::new_from_array([0x5a;32]);
    for (nm,signer,holders) in [
        ("update_fee_shares_success",creator,vec![(creator,6000u16),(new_holder,4000u16)]),
        ("update_fee_shares_reject_wrong_authority",admin,vec![(creator,10000u16)]),
        ("update_fee_shares_reject_bad_total",creator,vec![(creator,5000u16)])]{
        let (mut svm,_u)=new_svm(fees_so); base(&mut svm,creator,1,true);
        acct(&mut svm,new_holder,1_000_000,vec![],sys);
        acct(&mut svm,bc,1_500_000_000,bonding_curve(sc,false,Pubkey::default()),pump);
        let mut metas=vec![
            AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false),
            AccountMeta::new_readonly(signer,true),AccountMeta::new_readonly(gl,false),AccountMeta::new_readonly(mint,false),
            AccountMeta::new(sc,false),AccountMeta::new_readonly(bc,false),AccountMeta::new(pcv,false),
            AccountMeta::new_readonly(sys,false),AccountMeta::new_readonly(pump,false),AccountMeta::new_readonly(pump_ev,false),
            AccountMeta::new_readonly(amm,false),AccountMeta::new_readonly(amm_ev,false),AccountMeta::new_readonly(wsol,false),
            AccountMeta::new_readonly(token,false),AccountMeta::new_readonly(atap,false),AccountMeta::new(ccva,false),AccountMeta::new(ccva_ata,false)];
        for (h,_) in &holders{metas.push(AccountMeta::new(*h,false));}
        let mut data=d_update_fee_shares(); data.extend(u32le(holders.len() as u32));
        for (h,b) in &holders{data.extend_from_slice(&h.to_bytes()); data.extend(u16le(*b));}
        out.push(exec(&mut svm,nm,creator,metas,data,&[("sharing_config",sc),("pump_creator_vault",pcv)]));
    }

    // ===== update_fee_shares_v2 =====
    for (nm,signer,holders) in [
        ("update_fee_shares_v2_success",creator,vec![(creator,6000u16),(new_holder,4000u16)]),
        ("update_fee_shares_v2_reject_wrong_authority",admin,vec![(creator,10000u16)]),
        ("update_fee_shares_v2_reject_zero_share",creator,vec![(creator,10000u16),(new_holder,0u16)])]{
        let (mut svm,_u)=new_svm(fees_so); base(&mut svm,creator,1,true);
        acct(&mut svm,new_holder,1_000_000,vec![],sys);
        acct(&mut svm,bc,1_500_000_000,bonding_curve(sc,false,wsol),pump);
        let mut metas=vec![
            AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false),
            AccountMeta::new(signer,true),AccountMeta::new_readonly(gl,false),AccountMeta::new_readonly(mint,false),
            AccountMeta::new(sc,false),AccountMeta::new_readonly(bc,false),AccountMeta::new(pcv,false),AccountMeta::new(pcv_ata,false),
            AccountMeta::new_readonly(sys,false),AccountMeta::new_readonly(pump,false),AccountMeta::new_readonly(pump_ev,false),
            AccountMeta::new_readonly(amm,false),AccountMeta::new_readonly(amm_ev,false),AccountMeta::new_readonly(wsol,false),
            AccountMeta::new_readonly(token,false),AccountMeta::new_readonly(atap,false),AccountMeta::new(ccva,false),AccountMeta::new(ccva_ata,false)];
        for (h,_) in &holders{metas.push(AccountMeta::new(*h,false));}
        let mut data=d_update_fee_shares_v2(); data.extend(u32le(holders.len() as u32));
        for (h,b) in &holders{data.extend_from_slice(&h.to_bytes()); data.extend(u16le(*b));}
        out.push(exec(&mut svm,nm,creator,metas,data,&[("sharing_config",sc),("pump_creator_vault",pcv)]));
    }

    // ===== create_fee_sharing_config : curve not complete -> pool/amm Option accounts = None (program id) =====
    for (nm,payer,curve_creator) in [
        ("create_fee_sharing_config_success",creator,creator),
        ("create_fee_sharing_config_success_payer_not_creator",admin,creator)]{
        let (mut svm,_u)=new_svm(fees_so); base(&mut svm,creator,1,false);
        acct(&mut svm,bc,1_500_000_000,bonding_curve(curve_creator,false,wsol),pump);
        let metas=vec![
            AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false),
            AccountMeta::new(payer,true),AccountMeta::new_readonly(gl,false),AccountMeta::new_readonly(mint,false),
            AccountMeta::new(sc,false),AccountMeta::new_readonly(sys,false),AccountMeta::new(bc,false),
            AccountMeta::new_readonly(pump,false),AccountMeta::new_readonly(pump_ev,false),
            AccountMeta::new_readonly(feep,false),AccountMeta::new_readonly(feep,false),AccountMeta::new_readonly(feep,false)];
        out.push(exec(&mut svm,nm,payer,metas,d_create_fee_sharing_config(),&[("sharing_config",sc),("bonding_curve",bc)]));
    }

    // ===== create_donation_fee_pda : flags 0, curve not complete, sharing_config owned by feep =====
    let config_id=Pubkey::new_from_array([0xc1;32]);
    let dfp=Pubkey::find_program_address(&[b"donation-fee-pda",mint.as_ref(),config_id.as_ref()],&feep).0;
    for (nm,payer,sc_admin,sc_status,sc_seed) in [
        ("create_donation_fee_pda_success",creator,creator,1u8,true),
        ("create_donation_fee_pda_reject_not_admin",admin,creator,1u8,true),
        ("create_donation_fee_pda_reject_paused",creator,creator,0u8,true),
        ("create_donation_fee_pda_no_sharing_config",creator,creator,1u8,false)]{
        let (mut svm,_u)=new_svm(fees_so); base(&mut svm,sc_admin,sc_status,sc_seed);
        acct(&mut svm,fpg,5_000_000,fpg_bytes(fpg_bump,admin,0,Pubkey::new_from_array([0;32]),0),feep);
        let metas=vec![
            AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false),
            AccountMeta::new(payer,true),AccountMeta::new_readonly(sys,false),AccountMeta::new_readonly(fpg,false),
            AccountMeta::new(dfp,false),AccountMeta::new_readonly(config_id,false),AccountMeta::new_readonly(mint,false),
            AccountMeta::new_readonly(bc,false),AccountMeta::new_readonly(Pubkey::new_from_array([0x7a;32]),false),AccountMeta::new_readonly(sc,false)];
        out.push(exec(&mut svm,nm,payer,metas,d_create_donation_fee_pda(),&[("donation_fee_pda",dfp)]));
    }
    out
}

fn hx(v:&[u8])->String{v.iter().map(|b|format!("{:02x}",b)).collect()}
fn main(){
    let a:Vec<String>=std::env::args().collect();
    if a.len()<3 { eprintln!("usage: deep <deployed.so> <recovered.so>"); std::process::exit(2); }
    let o=run(&a[1]); let c=run(&a[2]);
    let mut all=true;
    for i in 0..o.len().min(c.len()){
        let okm=o[i].ok==c[i].ok; let em=o[i].err==c[i].err;
        let mut snapm=true; let mut sd=String::new();
        for (j,(lbl,od)) in o[i].snaps.iter().enumerate(){
            let eq=od==&c[i].snaps[j].1;
            if !eq{snapm=false;
                let f=|x:&Option<(u64,Vec<u8>)>| x.as_ref().map(|(l,d)|format!("lam={} len={} data={}",l,d.len(),hx(d))).unwrap_or("<none>".into());
                sd.push_str(&format!("\n    SNAP[{}] DIVERGE\n      D: {}\n      R: {}",lbl,f(od),f(&c[i].snaps[j].1)));
            } else {
                let t=od.as_ref().map(|(l,d)|format!("lam={} len={}",l,d.len())).unwrap_or("<none>".into());
                sd.push_str(&format!("\n    SNAP[{}] match ({})",lbl,t));
            }
        }
        let logm_raw=o[i].logs==c[i].logs; let logm=canon(&o[i].logs)==canon(&c[i].logs);
        let cosmetic=logm&&!logm_raw; let casem=okm&&em&&snapm&&logm;
        if !casem{all=false;}
        println!("{:<46} {}  ok:{}/{} err:{} snap:{} log:{}{}  cu:{}/{}",
            o[i].name, if casem{if cosmetic{"MATCH*  "}else{"MATCH   "}}else{"DIVERGE!"},
            o[i].ok,c[i].ok,em,snapm,logm,if cosmetic{" (src-loc only)"}else{""},o[i].cu,c[i].cu);
        if !o[i].err.is_empty()||!c[i].err.is_empty(){println!("    err D=[{}] R=[{}]",o[i].err,c[i].err);}
        print!("{}",sd); if !sd.is_empty(){println!();}
        if cosmetic{for (dl,rl) in o[i].logs.iter().zip(c[i].logs.iter()){ if dl!=rl{println!("    COSMETIC: D| {}\n              R| {}",dl,rl);} }}
        if std::env::var("LOGS").is_ok(){for l in &o[i].logs{println!("      D| {}",l);}}
        if !logm{println!("    LOG DIVERGE:");
            println!("      D({}):",o[i].logs.len()); for l in &o[i].logs{println!("        D| {}",l);}
            println!("      R({}):",c[i].logs.len()); for l in &c[i].logs{println!("        R| {}",l);} }
    }
    println!("\nFEES_DEEP_MATCH={}",all);
}
