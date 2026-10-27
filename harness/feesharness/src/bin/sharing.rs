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

fn run(fees_so:&str)->Vec<Step>{
    let feep=pk(FEEP); let pump=pk(PUMP); let amm=pk(AMM); let token=pk(TOKEN); let atap=pk(ATA);
    let relay=pk(RELAY); let wsol=pk(WSOL); let admin=pk(ADMIN); let sys=solana_sdk::system_program::id();
    let rent=pk("SysvarRent111111111111111111111111111111111");
    let ev=Pubkey::find_program_address(&[b"__event_authority"],&feep).0;
    let (fpg,fpg_bump)=Pubkey::find_program_address(&[b"fee-program-global"],&feep);
    let gl=Pubkey::find_program_address(&[b"global"],&pump).0;
    let mint=Pubkey::new_from_array([0x4d;32]);
    let (sc,sc_bump)=Pubkey::find_program_address(&[b"sharing-config",mint.as_ref()],&feep);
    let mut out=vec![];

    // ===== 1. revoke_fee_sharing_authority (deprecated stub, no accounts) -> 6023 =====
    { let (mut svm,user)=new_svm(fees_so);
      out.push(exec(&mut svm,"revoke_fee_sharing_authority",user,vec![],d_revoke(),&[])); }
    // ===== 2. transfer_fee_sharing_authority (deprecated stub) -> 6023 =====
    { let (mut svm,user)=new_svm(fees_so);
      out.push(exec(&mut svm,"transfer_fee_sharing_authority",user,vec![],d_transfer(),&[])); }

    // ===== 7. set_social_claim_authority : [authority(signer,w), fpg(w), event, program] arg pubkey =====
    let new_social=Pubkey::new_from_array([0x99;32]);
    for reject in [false,true]{
        let (mut svm,user)=new_svm(fees_so);
        let signer= if reject{user}else{admin}; svm.airdrop(&signer,1_000_000_000).unwrap();
        svm.set_account(fpg,Account{lamports:5_000_000,data:fpg_bytes(fpg_bump,admin,0,Pubkey::new_from_array([0;32]),0),owner:feep,executable:false,rent_epoch:0}).unwrap();
        let metas=vec![AccountMeta::new(signer,true),AccountMeta::new(fpg,false),AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false)];
        let mut data=d_set_social_claim_authority(); data.extend_from_slice(&new_social.to_bytes());
        let nm= if reject{"set_social_claim_authority_reject_wrongauth"}else{"set_social_claim_authority_success"};
        out.push(exec(&mut svm,nm,signer,metas,data,&[("fee_program_global",fpg)]));
    }

    // ===== 8. create_social_fee_pda : [payer(signer,w), social_fee_pda(w), system, fpg, event, program] args user_id:String, platform:u8 =====
    for (nm,user_id,platform) in [("create_social_fee_pda_success","u1",0u8),("create_social_fee_pda_reject_useridtoolong","abcdefghijklmnopqrstuvwxyz",0u8)]{
        let (mut svm,user)=new_svm(fees_so);
        let (sfp,_sfp_bump)=Pubkey::find_program_address(&[b"social-fee-pda",user_id.as_bytes(),&[platform]],&feep);
        svm.set_account(fpg,Account{lamports:5_000_000,data:fpg_bytes(fpg_bump,admin,0,Pubkey::new_from_array([0;32]),0),owner:feep,executable:false,rent_epoch:0}).unwrap();
        let metas=vec![AccountMeta::new(user,true),AccountMeta::new(sfp,false),AccountMeta::new_readonly(sys,false),AccountMeta::new_readonly(fpg,false),AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false)];
        let mut data=d_create_social_fee_pda(); data.extend(u32le(user_id.len() as u32)); data.extend_from_slice(user_id.as_bytes()); data.push(platform);
        out.push(exec(&mut svm,nm,user,metas,data,&[("social_fee_pda",sfp)]));
    }

    // ===== 4. claim_social_fee_pda : [recipient(w), social_fee_pda(w), fpg, social_claim_authority(signer), event, program] args user_id,platform =====
    { let (mut svm,_user)=new_svm(fees_so);
      let user_id="u1"; let platform=0u8;
      let (sfp,sfp_bump)=Pubkey::find_program_address(&[b"social-fee-pda",user_id.as_bytes(),&[platform]],&feep);
      let recipient=Pubkey::new_from_array([0x3c;32]);
      // disable_flags bit1 (=2) disables claim -> body 6021; social_claim_authority == admin (has_one)
      svm.set_account(fpg,Account{lamports:5_000_000,data:fpg_bytes(fpg_bump,admin,2,admin,0),owner:feep,executable:false,rent_epoch:0}).unwrap();
      svm.set_account(sfp,Account{lamports:3_000_000,data:social_fee_pda_bytes(sfp_bump,1,user_id.as_bytes(),platform),owner:feep,executable:false,rent_epoch:0}).unwrap();
      svm.set_account(recipient,Account{lamports:1_000_000,data:vec![],owner:sys,executable:false,rent_epoch:0}).unwrap();
      svm.airdrop(&admin,1_000_000_000).unwrap();
      let metas=vec![AccountMeta::new(recipient,false),AccountMeta::new(sfp,false),AccountMeta::new_readonly(fpg,false),AccountMeta::new_readonly(admin,true),AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false)];
      let mut data=d_claim_social_fee_pda(); data.extend(u32le(user_id.len() as u32)); data.extend_from_slice(user_id.as_bytes()); data.push(platform);
      out.push(exec(&mut svm,"claim_social_fee_pda_disabled",admin,metas,data,&[("social_fee_pda",sfp)])); }

    // ===== 5. claim_social_fee_pda_v2 : [recipient(w), social_fee_pda(w), quote_mint(w), assoc_sfp(w), assoc_recipient(w), quote_token_program, ata_program, fpg, social_claim_authority(signer), system, event, program] =====
    { let (mut svm,_user)=new_svm(fees_so);
      let user_id="u1"; let platform=0u8;
      let (sfp,sfp_bump)=Pubkey::find_program_address(&[b"social-fee-pda",user_id.as_bytes(),&[platform]],&feep);
      let recipient=Pubkey::new_from_array([0x3c;32]);
      svm.set_account(fpg,Account{lamports:5_000_000,data:fpg_bytes(fpg_bump,admin,2,admin,0),owner:feep,executable:false,rent_epoch:0}).unwrap();
      svm.set_account(sfp,Account{lamports:3_000_000,data:social_fee_pda_bytes(sfp_bump,1,user_id.as_bytes(),platform),owner:feep,executable:false,rent_epoch:0}).unwrap();
      svm.set_account(recipient,Account{lamports:1_000_000,data:vec![],owner:sys,executable:false,rent_epoch:0}).unwrap();
      svm.set_account(wsol,Account{lamports:1_000_000_000,data:spl_mint82(9),owner:token,executable:false,rent_epoch:0}).unwrap();
      let assoc_sfp=Pubkey::find_program_address(&[sfp.as_ref(),token.as_ref(),wsol.as_ref()],&atap).0;
      let assoc_rec=Pubkey::find_program_address(&[recipient.as_ref(),token.as_ref(),wsol.as_ref()],&atap).0;
      svm.airdrop(&admin,1_000_000_000).unwrap();
      let metas=vec![AccountMeta::new(recipient,false),AccountMeta::new(sfp,false),AccountMeta::new(wsol,false),AccountMeta::new(assoc_sfp,false),AccountMeta::new(assoc_rec,false),AccountMeta::new_readonly(token,false),AccountMeta::new_readonly(atap,false),AccountMeta::new_readonly(fpg,false),AccountMeta::new_readonly(admin,true),AccountMeta::new_readonly(sys,false),AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false)];
      let mut data=d_claim_social_fee_pda_v2(); data.extend(u32le(user_id.len() as u32)); data.extend_from_slice(user_id.as_bytes()); data.push(platform);
      out.push(exec(&mut svm,"claim_social_fee_pda_v2_disabled",admin,metas,data,&[("social_fee_pda",sfp)])); }

    // ===== 6. admin_cto_sharing_config : [pool_authority(signer), authority(signer), global, mint, sharing_config(w), event, program] arg Option<Pubkey> =====
    let pool_auth=Pubkey::find_program_address(&[b"pool-authority",mint.as_ref()],&feep).0;
    for (nm,some,key) in [("admin_cto_sharing_config_reject_zeroadmin",true,[0u8;32]),("admin_cto_sharing_config_setadmin",true,[0x66u8;32])]{
        let (mut svm,_user)=new_svm(fees_so);
        svm.airdrop(&admin,1_000_000_000).unwrap();
        svm.set_account(gl,Account{lamports:50_000_000,data:global_bytes(admin),owner:pump,executable:false,rent_epoch:0}).unwrap();
        svm.set_account(sc,Account{lamports:50_000_000,data:sharing_config_bytes(sc_bump,1,mint,admin,0,&[(admin,10000)],1024),owner:feep,executable:false,rent_epoch:0}).unwrap();
        let metas=vec![AccountMeta::new_readonly(pool_auth,true),AccountMeta::new_readonly(admin,true),AccountMeta::new_readonly(gl,false),AccountMeta::new_readonly(mint,false),AccountMeta::new(sc,false),AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false)];
        let mut data=d_admin_cto(); if some {data.push(1); data.extend_from_slice(&key);} else {data.push(0);}
        out.push(exec(&mut svm,nm,admin,metas,data,&[("sharing_config",sc)]));
    }

    // ===== 3. update_fee_shares : wrong authority -> gate reject. metas from map index order =====
    { let (mut svm,user)=new_svm(fees_so);
      let bc=Pubkey::find_program_address(&[b"bonding-curve",mint.as_ref()],&pump).0;
      let pcv=Pubkey::find_program_address(&[b"creator-vault",sc.as_ref()],&pump).0;
      let ccva=Pubkey::find_program_address(&[b"creator_vault",sc.as_ref()],&amm).0;
      svm.set_account(gl,Account{lamports:50_000_000,data:global_bytes(admin),owner:pump,executable:false,rent_epoch:0}).unwrap();
      svm.set_account(sc,Account{lamports:50_000_000,data:sharing_config_bytes(sc_bump,1,mint,admin,0,&[(admin,10000)],1024),owner:feep,executable:false,rent_epoch:0}).unwrap();
      let ccva_ata=Pubkey::new_from_array([0x11;32]);
      let metas=vec![
        AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false),
        AccountMeta::new_readonly(user,true),AccountMeta::new_readonly(gl,false),AccountMeta::new_readonly(mint,false),
        AccountMeta::new(sc,false),AccountMeta::new_readonly(bc,false),AccountMeta::new(pcv,false),
        AccountMeta::new_readonly(sys,false),AccountMeta::new_readonly(pump,false),AccountMeta::new_readonly(ev,false),
        AccountMeta::new_readonly(amm,false),AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(wsol,false),
        AccountMeta::new_readonly(token,false),AccountMeta::new_readonly(atap,false),AccountMeta::new(ccva,false),AccountMeta::new(ccva_ata,false)];
      let mut data=d_update_fee_shares(); data.extend(u32le(1)); data.extend_from_slice(&admin.to_bytes()); data.extend(u16le(10000));
      out.push(exec(&mut svm,"update_fee_shares_wrongauth",user,metas,data,&[("sharing_config",sc)])); }

    // ===== update_fee_shares_v2 : wrong authority -> gate reject =====
    { let (mut svm,user)=new_svm(fees_so);
      let bc=Pubkey::find_program_address(&[b"bonding-curve",mint.as_ref()],&pump).0;
      let pcv=Pubkey::find_program_address(&[b"creator-vault",sc.as_ref()],&pump).0;
      let ccva=Pubkey::find_program_address(&[b"creator_vault",sc.as_ref()],&amm).0;
      let pcv_ata=Pubkey::find_program_address(&[pcv.as_ref(),token.as_ref(),wsol.as_ref()],&atap).0;
      let ccva_ata=Pubkey::find_program_address(&[ccva.as_ref(),token.as_ref(),wsol.as_ref()],&atap).0;
      svm.set_account(gl,Account{lamports:50_000_000,data:global_bytes(admin),owner:pump,executable:false,rent_epoch:0}).unwrap();
      svm.set_account(sc,Account{lamports:50_000_000,data:sharing_config_bytes(sc_bump,1,mint,admin,0,&[(admin,10000)],1024),owner:feep,executable:false,rent_epoch:0}).unwrap();
      let metas=vec![
        AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false),
        AccountMeta::new(user,true),AccountMeta::new_readonly(gl,false),AccountMeta::new_readonly(mint,false),
        AccountMeta::new(sc,false),AccountMeta::new_readonly(bc,false),AccountMeta::new(pcv,false),AccountMeta::new(pcv_ata,false),
        AccountMeta::new_readonly(sys,false),AccountMeta::new_readonly(pump,false),AccountMeta::new_readonly(ev,false),
        AccountMeta::new_readonly(amm,false),AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(wsol,false),
        AccountMeta::new_readonly(token,false),AccountMeta::new_readonly(atap,false),AccountMeta::new(ccva,false),AccountMeta::new(ccva_ata,false)];
      let mut data=d_update_fee_shares_v2(); data.extend(u32le(1)); data.extend_from_slice(&admin.to_bytes()); data.extend(u16le(10000));
      out.push(exec(&mut svm,"update_fee_shares_v2_wrongauth",user,metas,data,&[("sharing_config",sc)])); }

    // ===== 1(create). create_fee_sharing_config : metas from map index order. complex CPI; expect matched early reject =====
    { let (mut svm,user)=new_svm(fees_so);
      let bc=Pubkey::find_program_address(&[b"bonding-curve",mint.as_ref()],&pump).0;
      let pool=Pubkey::new_from_array([0x7a;32]);
      svm.set_account(gl,Account{lamports:50_000_000,data:global_bytes(admin),owner:pump,executable:false,rent_epoch:0}).unwrap();
      let metas=vec![
        AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false),
        AccountMeta::new(user,true),AccountMeta::new_readonly(gl,false),AccountMeta::new_readonly(mint,false),
        AccountMeta::new(sc,false),AccountMeta::new_readonly(sys,false),AccountMeta::new(bc,false),
        AccountMeta::new_readonly(pump,false),AccountMeta::new_readonly(ev,false),AccountMeta::new(pool,false),
        AccountMeta::new_readonly(amm,false),AccountMeta::new_readonly(ev,false)];
      out.push(exec(&mut svm,"create_fee_sharing_config_earlygate",user,metas,d_create_fee_sharing_config(),&[("sharing_config",sc)])); }

    // ===== 11. create_donation_fee_pda : disable_flags set -> 6021 at body entry. metas from map =====
    let config_id=Pubkey::new_from_array([0xc1;32]); let base_mint=mint;
    let (dfp,dfp_bump)=Pubkey::find_program_address(&[b"donation-fee-pda",base_mint.as_ref(),config_id.as_ref()],&feep);
    { let (mut svm,user)=new_svm(fees_so);
      let bc=Pubkey::find_program_address(&[b"bonding-curve",base_mint.as_ref()],&pump).0;
      let pool=Pubkey::new_from_array([0x7a;32]);
      svm.set_account(fpg,Account{lamports:5_000_000,data:fpg_bytes(fpg_bump,admin,0xff,Pubkey::new_from_array([0;32]),0),owner:feep,executable:false,rent_epoch:0}).unwrap();
      svm.set_account(dfp,Account{lamports:3_000_000,data:donation_fee_pda_bytes(dfp_bump,0,config_id,base_mint,wsol,admin),owner:feep,executable:false,rent_epoch:0}).unwrap();
      let metas=vec![
        AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false),
        AccountMeta::new(user,true),AccountMeta::new_readonly(sys,false),AccountMeta::new_readonly(fpg,false),
        AccountMeta::new(dfp,false),AccountMeta::new_readonly(config_id,false),AccountMeta::new_readonly(base_mint,false),
        AccountMeta::new_readonly(bc,false),AccountMeta::new_readonly(pool,false),AccountMeta::new_readonly(sc,false)];
      out.push(exec(&mut svm,"create_donation_fee_pda_disabled",user,metas,d_create_donation_fee_pda(),&[("donation_fee_pda",dfp)])); }

    // ===== 12. crank_donation_fee_pda : disable_flags set -> 6021 at body entry. metas from map =====
    { let (mut svm,user)=new_svm(fees_so);
      svm.set_account(fpg,Account{lamports:5_000_000,data:fpg_bytes(fpg_bump,admin,0xff,Pubkey::new_from_array([0;32]),0),owner:feep,executable:false,rent_epoch:0}).unwrap();
      svm.set_account(dfp,Account{lamports:3_000_000,data:donation_fee_pda_bytes(dfp_bump,1,config_id,base_mint,wsol,admin),owner:feep,executable:false,rent_epoch:0}).unwrap();
      svm.set_account(wsol,Account{lamports:1_000_000_000,data:spl_mint82(9),owner:token,executable:false,rent_epoch:0}).unwrap();
      let dfp_ata=Pubkey::find_program_address(&[dfp.as_ref(),token.as_ref(),wsol.as_ref()],&atap).0;
      let relay_ev=Pubkey::find_program_address(&[b"__event_authority"],&relay).0;
      let whitelist=Pubkey::new_from_array([0xa1;32]); let epoch=Pubkey::new_from_array([0xa2;32]);
      let deb=Pubkey::new_from_array([0xa3;32]); let deb_ata=Pubkey::new_from_array([0xa4;32]);
      let metas=vec![
        AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false),
        AccountMeta::new(user,true),AccountMeta::new_readonly(sys,false),AccountMeta::new_readonly(token,false),
        AccountMeta::new_readonly(atap,false),AccountMeta::new_readonly(rent,false),AccountMeta::new_readonly(fpg,false),
        AccountMeta::new(dfp,false),AccountMeta::new(wsol,false),AccountMeta::new(dfp_ata,false),
        AccountMeta::new_readonly(relay,false),AccountMeta::new_readonly(relay_ev,false),AccountMeta::new_readonly(whitelist,false),
        AccountMeta::new(epoch,false),AccountMeta::new(deb,false),AccountMeta::new(deb_ata,false)];
      out.push(exec(&mut svm,"crank_donation_fee_pda_disabled",user,metas,d_crank_donation_fee_pda(),&[("donation_fee_pda",dfp)])); }

    out
}

fn hx(v:&[u8])->String{v.iter().map(|b|format!("{:02x}",b)).collect()}
fn main(){
    let a:Vec<String>=std::env::args().collect();
    if a.len()<3 { eprintln!("usage: sharing <deployed.so> <recovered.so>"); std::process::exit(2); }
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
        if !logm{println!("    LOG DIVERGE:");
            println!("      D({}):",o[i].logs.len()); for l in &o[i].logs{println!("        D| {}",l);}
            println!("      R({}):",c[i].logs.len()); for l in &c[i].logs{println!("        R| {}",l);} }
    }
    println!("\nFEES_SHARING_MATCH={}",all);
}
