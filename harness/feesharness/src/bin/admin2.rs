// Differential harness part 2 for pump_fees: the REMAINING 14 handlers. DEPLOYED (oracle) vs
// RECOVERED side-by-side in LiteSVM on identical seeded state. Same machinery as admin.rs:
//   two instances, {ok, exact error code, resulting account bytes, normalized logs} compare,
//   compile-time AnchorError src-path canonicalizer, sigverify-off + fixed-admin (8LWu..) impersonation.
// deployed.so is loaded ONLY as the pfeeUxB.. program for the oracle run; never a build input.
// Recovered comes solely from fees_recovered.so.
//
// Account order + args + PDA seeds reversed from the DEPLOYED binary (handler map fees_handlers.json)
// cross-checked against the upstream IDL evidence/upstream/pump_fees.json. Handler addrs cited inline.
// Shared seeded state:
//   FeeConfig PDA ["fee_config", config_program_id] stored bump 253, admin 8LWu.. (disc 8f3492bbdb7b4c9b),
//     seeds+bump=stored constraint proven by feesharness gfq_pump_badbump (2006).
//   FeeProgramGlobal PDA ["fee-program-global"] disc a2a5f5311d2537f2 (338B: bump@8, authority@9,
//     disable_flags@41, social_claim_authority@42, claim_rate_limit@74, _reserved@82..338).
//   BuybackVault PDA ["buyback-vault", index] disc 99a64790b3bd89fb (208B).
//   pump Global PDA ["global"] under 6EF8.. disc a7e8e8b1c86c727f (initialized@8, authority@9).
//   referral_vault SystemAccount PDA ["referral-vault", user].
// Fixed admin 8LWu7QM2dGR1G8nKDHthckea57bkCzXyBTAKPJUBDHo8 @ .rodata 0xc36e0.
//
// Handlers (disc @handler): update_fee_config 68b867f258976b14 @0x1319e; upsert_fee_tiers
// e317960c4d565e04 @0x13267; update_stable_fee_config 6ba964b3869b92dd @0x13329; upsert_stable_fee_tiers
// b5a0a2fc4a4ce0dd @0x133e0; extend_fee_config 44b3f45aad3811d9 @0x134a2; set_exotic_flat_fees
// 1eea958afce62749 @0x13541; update_buyback_authority 426271ca7925db6b @0x13ea6;
// update_buyback_claim_rate_limit ba5f87beffc789aa @0x13f80; withdraw b712469c946da122 @0x14121;
// initialize_fee_program_global 23d78254e9387ca7 @0x12e01; set_disable_flags c2d9702372de33be @0x12f8a;
// set_claim_rate_limit b9d39faed4315804 @0x13034; set_authority 85fa25156ea31a79 @0x130de;
// update_admin a1b028d53cb8b3e4 @0x135f3.
//
// Sigverify DISABLED (same justification as admin.rs): only skips the crypto sig check; runtime
// still sets the is_signer flag Anchor Signer/has_one/address constraints read. Both builds run
// under the identical setting, so it cannot introduce asymmetry.

use litesvm::LiteSVM;
use solana_sdk::{pubkey::Pubkey, signature::{Signer, Signature}, account::Account,
    instruction::{Instruction, AccountMeta}, message::Message, transaction::Transaction};
use std::str::FromStr;

const FEEP:&str = "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ";
const PUMP:&str = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P";
const AMM:&str  = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA";
const TOKEN:&str= "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA";
const ATA:&str  = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL";
const ADMIN:&str= "8LWu7QM2dGR1G8nKDHthckea57bkCzXyBTAKPJUBDHo8";
const DEP:&str  = "/mnt/d/dev/ext/pumpfun-source/evidence/dependencies";

fn d_update_fee_config()->Vec<u8>{vec![0x68,0xb8,0x67,0xf2,0x58,0x97,0x6b,0x14]}
fn d_upsert_fee_tiers()->Vec<u8>{vec![0xe3,0x17,0x96,0x0c,0x4d,0x56,0x5e,0x04]}
fn d_update_stable_fee_config()->Vec<u8>{vec![0x6b,0xa9,0x64,0xb3,0x86,0x9b,0x92,0xdd]}
fn d_upsert_stable_fee_tiers()->Vec<u8>{vec![0xb5,0xa0,0xa2,0xfc,0x4a,0x4c,0xe0,0xdd]}
fn d_extend_fee_config()->Vec<u8>{vec![0x44,0xb3,0xf4,0x5a,0xad,0x38,0x11,0xd9]}
fn d_set_exotic_flat_fees()->Vec<u8>{vec![0x1e,0xea,0x95,0x8a,0xfc,0xe6,0x27,0x49]}
fn d_update_buyback_authority()->Vec<u8>{vec![0x42,0x62,0x71,0xca,0x79,0x25,0xdb,0x6b]}
fn d_update_buyback_claim_rate_limit()->Vec<u8>{vec![0xba,0x5f,0x87,0xbe,0xff,0xc7,0x89,0xaa]}
fn d_withdraw()->Vec<u8>{vec![0xb7,0x12,0x46,0x9c,0x94,0x6d,0xa1,0x22]}
fn d_initialize_fee_program_global()->Vec<u8>{vec![0x23,0xd7,0x82,0x54,0xe9,0x38,0x7c,0xa7]}
fn d_set_disable_flags()->Vec<u8>{vec![0xc2,0xd9,0x70,0x23,0x72,0xde,0x33,0xbe]}
fn d_set_claim_rate_limit()->Vec<u8>{vec![0xb9,0xd3,0x9f,0xae,0xd4,0x31,0x58,0x04]}
fn d_set_authority()->Vec<u8>{vec![0x85,0xfa,0x25,0x15,0x6e,0xa3,0x1a,0x79]}
fn d_update_admin()->Vec<u8>{vec![0xa1,0xb0,0x28,0xd5,0x3c,0xb8,0xb3,0xe4]}

const FC_DISC:[u8;8]  = [0x8f,0x34,0x92,0xbb,0xdb,0x7b,0x4c,0x9b]; // FeeConfig
const FPG_DISC:[u8;8] = [0xa2,0xa5,0xf5,0x31,0x1d,0x25,0x37,0xf2]; // FeeProgramGlobal
const BV_DISC:[u8;8]  = [0x99,0xa6,0x47,0x90,0xb3,0xbd,0x89,0xfb]; // BuybackVault
const GL_DISC:[u8;8]  = [0xa7,0xe8,0xe8,0xb1,0xc8,0x6c,0x72,0x7f]; // pump Global

fn pk(s:&str)->Pubkey{Pubkey::from_str(s).unwrap()}
fn u64le(v:u64)->Vec<u8>{v.to_le_bytes().to_vec()}
fn i64le(v:i64)->Vec<u8>{v.to_le_bytes().to_vec()}
fn u128le(v:u128)->Vec<u8>{v.to_le_bytes().to_vec()}
fn cu(l:&[String])->u64{for x in l.iter().rev(){if let Some(i)=x.find("consumed "){let r=&x[i+9..];if let Some(s)=r.find(char::is_whitespace){if let Ok(v)=r[..s].parse(){return v}}}}0}
fn norm(logs:&[String])->Vec<String>{logs.iter().filter(|l|!l.contains("compute units")&&!l.contains("consumed ")).cloned().collect()}
fn canon_line(l:&str)->String{
    if let Some(p)=l.find("AnchorError thrown in "){
        if let Some(q)=l[p..].find(". Error Code"){return format!("{}AnchorError thrown in <SRC>{}",&l[..p],&l[p+q..]);}
    }
    if let Some(p)=l.find("AnchorError occurred. Error Code"){let _=p;}
    l.to_string()
}
fn canon(logs:&[String])->Vec<String>{logs.iter().map(|l|canon_line(l)).collect()}

// --- Borsh builders ---
fn fees_arg(lp:u64,proto:u64,creator:u64)->Vec<u8>{let mut v=u64le(lp);v.extend(u64le(proto));v.extend(u64le(creator));v}
// Vec<FeeTier> with a single tier {threshold, fees}
fn vec_feetier(threshold:u128,lp:u64,proto:u64,creator:u64)->Vec<u8>{
    let mut v=1u32.to_le_bytes().to_vec(); v.extend(u128le(threshold)); v.extend(fees_arg(lp,proto,creator)); v
}
// --- account byte builders ---
fn spl_mint82(dec:u8)->Vec<u8>{let mut v=vec![0u8;82];v[44]=dec;v[45]=1;v}
fn spl_tok165(mint:Pubkey,owner:Pubkey,amount:u64)->Vec<u8>{let mut v=vec![0u8;165];v[0..32].copy_from_slice(&mint.to_bytes());v[32..64].copy_from_slice(&owner.to_bytes());v[64..72].copy_from_slice(&amount.to_le_bytes());v[108]=1;v}
fn ata(owner:Pubkey,tok:Pubkey,mint:Pubkey,atap:Pubkey)->Pubkey{Pubkey::find_program_address(&[owner.as_ref(),tok.as_ref(),mint.as_ref()],&atap).0}
// FeeConfig: disc, bump, admin, flat_fees, fee_tiers(1), stable_fee_tiers(1), exotic_flat_fees; padded to size.
fn feeconfig(bump:u8,admin:Pubkey,size:usize)->Vec<u8>{
    let mut d=FC_DISC.to_vec();
    d.push(bump);
    d.extend_from_slice(&admin.to_bytes());
    d.extend(fees_arg(0,95,30));                                   // flat_fees
    d.extend(1u32.to_le_bytes()); d.extend(u128le(0)); d.extend(fees_arg(0,95,30)); // fee_tiers[0]
    d.extend(1u32.to_le_bytes()); d.extend(u128le(0)); d.extend(fees_arg(0,95,30)); // stable_fee_tiers[0]
    d.extend(fees_arg(0,95,30));                                   // exotic_flat_fees
    d.resize(size,0);
    d
}
fn fpg_bytes(bump:u8,authority:Pubkey)->Vec<u8>{
    let mut d=FPG_DISC.to_vec();
    d.push(bump);                       // bump@8
    d.extend_from_slice(&authority.to_bytes()); // authority@9..41
    d.push(0);                          // disable_flags@41
    d.extend_from_slice(&[0u8;32]);     // social_claim_authority@42..74
    d.extend(u64le(0));                 // claim_rate_limit@74..82
    d.resize(338,0);
    d
}
fn bv_bytes(authority:Pubkey)->Vec<u8>{let mut d=BV_DISC.to_vec();d.extend_from_slice(&authority.to_bytes());d.resize(208,0);d}
fn global_bytes(authority:Pubkey)->Vec<u8>{let mut d=GL_DISC.to_vec();d.push(1);d.extend_from_slice(&authority.to_bytes());d.resize(1088,0);d}

struct Step{name:String, ok:bool, err:String, cu:u64, snaps:Vec<(String,Option<(u64,Vec<u8>)>)>, logs:Vec<String>}

fn new_svm(fees_so:&str)->(LiteSVM,Pubkey){
    let mut svm=LiteSVM::new().with_sigverify(false);
    svm.add_program_from_file(pk(FEEP),fees_so).unwrap();
    svm.add_program_from_file(pk(TOKEN),format!("{}/spl_token/deployed.so",DEP)).unwrap();
    svm.add_program_from_file(pk(ATA),format!("{}/associated_token/deployed.so",DEP)).unwrap();
    let user=solana_sdk::signer::keypair::keypair_from_seed(&[7u8;32]).unwrap();
    svm.airdrop(&user.pubkey(),1_000_000_000_000).unwrap();
    (svm,user.pubkey())
}
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
    let snaps=snap.iter().map(|(lbl,p)|(lbl.to_string(),svm.get_account(p).map(|a|(a.lamports,a.data.clone())))).collect();
    Step{name:name.into(),ok,err,cu:cuv,snaps,logs:norm(&logs)}
}

fn run(fees_so:&str)->Vec<Step>{
    let feep=pk(FEEP); let pump=pk(PUMP); let amm=pk(AMM); let token=pk(TOKEN); let atap=pk(ATA);
    let admin=pk(ADMIN); let sys=solana_sdk::system_program::id();
    let ev=Pubkey::find_program_address(&[b"__event_authority"],&feep).0;
    let (fc_pump,fc_bump)=Pubkey::find_program_address(&[b"fee_config",pump.as_ref()],&feep); // bump 253
    let (fpg,fpg_bump)=Pubkey::find_program_address(&[b"fee-program-global"],&feep);
    let (bv0,_bv_bump)=Pubkey::find_program_address(&[b"buyback-vault",&[0u8]],&feep);
    let gl=Pubkey::find_program_address(&[b"global"],&pump).0;
    let new_admin=Pubkey::new_from_array([0x66u8;32]);
    let new_auth =Pubkey::new_from_array([0x77u8;32]);
    let social   =Pubkey::new_from_array([0x88u8;32]);
    let mut out=vec![];

    // Common FeeConfig admin-gated setter metas: [fee_config(mut), admin(signer), config_program_id, event, program]
    let fc_setter_metas=|signer:Pubkey, admin_mut:bool|->Vec<AccountMeta>{vec![
        AccountMeta::new(fc_pump,false),
        if admin_mut{AccountMeta::new(signer,true)}else{AccountMeta::new_readonly(signer,true)},
        AccountMeta::new_readonly(pump,false),
        AccountMeta::new_readonly(ev,false),
        AccountMeta::new_readonly(feep,false),
    ]};
    // seed a fresh FeeConfig (size) at fc_pump for a case
    let seed_fc=|svm:&mut LiteSVM, size:usize|{svm.set_account(fc_pump,Account{lamports:50_000_000,data:feeconfig(fc_bump,admin,size),owner:feep,executable:false,rent_epoch:0}).unwrap();};

    // ---- update_fee_config @0x1319e : args fee_tiers:Vec<FeeTier>, flat_fees:Fees ----
    for (nm,signer,payer) in [("update_fee_config_success",admin,admin),("update_fee_config_reject_wrongadmin",pk("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"),pk("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"))]{
        // (use a non-admin signer = pump pubkey for the reject; any key != 8LWu triggers 6001)
        let (mut svm,user)=new_svm(fees_so);
        let (signer,payer)= if nm.contains("reject"){(user,user)}else{(signer,payer)};
        svm.airdrop(&signer,1_000_000_000).unwrap(); seed_fc(&mut svm,4097);
        let mut data=d_update_fee_config(); data.extend(vec_feetier(0,1,2,3)); data.extend(fees_arg(7,8,9));
        out.push(exec(&mut svm,nm,payer,fc_setter_metas(signer,false),data,&[("fee_config",fc_pump)]));
    }
    // ---- upsert_fee_tiers @0x13267 : args fee_tiers:Vec<FeeTier>, offset:u8 ----
    for reject in [false,true]{
        let (mut svm,user)=new_svm(fees_so);
        let signer= if reject{user}else{admin}; svm.airdrop(&signer,1_000_000_000).unwrap(); seed_fc(&mut svm,4097);
        let mut data=d_upsert_fee_tiers(); data.extend(vec_feetier(1000,4,5,6)); data.push(0);
        let nm= if reject{"upsert_fee_tiers_reject_wrongadmin"}else{"upsert_fee_tiers_success"};
        out.push(exec(&mut svm,nm,signer,fc_setter_metas(signer,false),data,&[("fee_config",fc_pump)]));
    }
    // ---- update_stable_fee_config @0x13329 : args fee_tiers:Vec<FeeTier> ----
    for reject in [false,true]{
        let (mut svm,user)=new_svm(fees_so);
        let signer= if reject{user}else{admin}; svm.airdrop(&signer,1_000_000_000).unwrap(); seed_fc(&mut svm,4097);
        let mut data=d_update_stable_fee_config(); data.extend(vec_feetier(0,11,12,13));
        let nm= if reject{"update_stable_fee_config_reject_wrongadmin"}else{"update_stable_fee_config_success"};
        out.push(exec(&mut svm,nm,signer,fc_setter_metas(signer,false),data,&[("fee_config",fc_pump)]));
    }
    // ---- upsert_stable_fee_tiers @0x133e0 : args fee_tiers:Vec<FeeTier>, offset:u8 ----
    for reject in [false,true]{
        let (mut svm,user)=new_svm(fees_so);
        let signer= if reject{user}else{admin}; svm.airdrop(&signer,1_000_000_000).unwrap(); seed_fc(&mut svm,4097);
        let mut data=d_upsert_stable_fee_tiers(); data.extend(vec_feetier(2000,14,15,16)); data.push(0);
        let nm= if reject{"upsert_stable_fee_tiers_reject_wrongadmin"}else{"upsert_stable_fee_tiers_success"};
        out.push(exec(&mut svm,nm,signer,fc_setter_metas(signer,false),data,&[("fee_config",fc_pump)]));
    }
    // ---- set_exotic_flat_fees @0x13541 : [fee_config(mut), admin(mut signer), config_prog, system, event, program] arg Fees ----
    for reject in [false,true]{
        let (mut svm,user)=new_svm(fees_so);
        let signer= if reject{user}else{admin}; svm.airdrop(&signer,1_000_000_000).unwrap(); seed_fc(&mut svm,2512); // 2512 to exercise any grow-to-4097
        let metas=vec![
            AccountMeta::new(fc_pump,false), AccountMeta::new(signer,true),
            AccountMeta::new_readonly(pump,false), AccountMeta::new_readonly(sys,false),
            AccountMeta::new_readonly(ev,false), AccountMeta::new_readonly(feep,false),
        ];
        let mut data=d_set_exotic_flat_fees(); data.extend(fees_arg(21,22,23));
        let nm= if reject{"set_exotic_flat_fees_reject_wrongadmin"}else{"set_exotic_flat_fees_success"};
        out.push(exec(&mut svm,nm,signer,metas,data,&[("fee_config",fc_pump)]));
    }
    // ---- extend_fee_config @0x134a2 : [fee_config(mut unchecked), user(signer), config_prog, system, event, program] no args ----
    {   // success: seed 2512 at fc_pump, config_program_id=pump, any signer -> realloc to 4097
        let (mut svm,user)=new_svm(fees_so); seed_fc(&mut svm,2512);
        let metas=vec![AccountMeta::new(fc_pump,false),AccountMeta::new_readonly(user,true),
            AccountMeta::new_readonly(pump,false),AccountMeta::new_readonly(sys,false),
            AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false)];
        out.push(exec(&mut svm,"extend_fee_config_success",user,metas,d_extend_fee_config(),&[("fee_config",fc_pump)]));
    }
    {   // reject: fee_config seeded for pump but config_program_id=amm -> PDA mismatch 6028
        let (mut svm,user)=new_svm(fees_so); seed_fc(&mut svm,2512);
        let metas=vec![AccountMeta::new(fc_pump,false),AccountMeta::new_readonly(user,true),
            AccountMeta::new_readonly(amm,false),AccountMeta::new_readonly(sys,false),
            AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false)];
        out.push(exec(&mut svm,"extend_fee_config_reject_badpda",user,metas,d_extend_fee_config(),&[("fee_config",fc_pump)]));
    }
    // ---- update_admin @0x135f3 : [admin(signer), fee_config(mut), new_admin, config_prog, event, program] no args ----
    for reject in [false,true]{
        let (mut svm,user)=new_svm(fees_so);
        let signer= if reject{user}else{admin}; svm.airdrop(&signer,1_000_000_000).unwrap(); seed_fc(&mut svm,4097);
        let metas=vec![
            AccountMeta::new_readonly(signer,true), AccountMeta::new(fc_pump,false),
            AccountMeta::new_readonly(new_admin,false), AccountMeta::new_readonly(pump,false),
            AccountMeta::new_readonly(ev,false), AccountMeta::new_readonly(feep,false),
        ];
        let nm= if reject{"update_admin_reject_wrongadmin"}else{"update_admin_success"};
        out.push(exec(&mut svm,nm,signer,metas,d_update_admin(),&[("fee_config",fc_pump)]));
    }

    // ---- fee_program_global-gated setters: [authority(mut signer), fee_program_global(mut), event, program] ----
    let fpg_setter=|svm:&mut LiteSVM, authority:Pubkey|{svm.set_account(fpg,Account{lamports:5_000_000,data:fpg_bytes(fpg_bump,admin),owner:feep,executable:false,rent_epoch:0}).unwrap(); let _=authority;};
    // set_disable_flags @0x12f8a arg disable_flags:u8
    for reject in [false,true]{
        let (mut svm,user)=new_svm(fees_so);
        let signer= if reject{user}else{admin}; svm.airdrop(&signer,1_000_000_000).unwrap(); fpg_setter(&mut svm,signer);
        let metas=vec![AccountMeta::new(signer,true),AccountMeta::new(fpg,false),AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false)];
        let mut data=d_set_disable_flags(); data.push(3);
        let nm= if reject{"set_disable_flags_reject_wrongauth"}else{"set_disable_flags_success"};
        out.push(exec(&mut svm,nm,signer,metas,data,&[("fee_program_global",fpg)]));
    }
    // set_claim_rate_limit @0x13034 arg claim_rate_limit:u64
    for reject in [false,true]{
        let (mut svm,user)=new_svm(fees_so);
        let signer= if reject{user}else{admin}; svm.airdrop(&signer,1_000_000_000).unwrap(); fpg_setter(&mut svm,signer);
        let metas=vec![AccountMeta::new(signer,true),AccountMeta::new(fpg,false),AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false)];
        let mut data=d_set_claim_rate_limit(); data.extend(u64le(86400));
        let nm= if reject{"set_claim_rate_limit_reject_wrongauth"}else{"set_claim_rate_limit_success"};
        out.push(exec(&mut svm,nm,signer,metas,data,&[("fee_program_global",fpg)]));
    }
    // set_authority @0x130de arg new_authority:pubkey
    for reject in [false,true]{
        let (mut svm,user)=new_svm(fees_so);
        let signer= if reject{user}else{admin}; svm.airdrop(&signer,1_000_000_000).unwrap(); fpg_setter(&mut svm,signer);
        let metas=vec![AccountMeta::new(signer,true),AccountMeta::new(fpg,false),AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false)];
        let mut data=d_set_authority(); data.extend_from_slice(&new_auth.to_bytes());
        let nm= if reject{"set_authority_reject_wrongauth"}else{"set_authority_success"};
        out.push(exec(&mut svm,nm,signer,metas,data,&[("fee_program_global",fpg)]));
    }

    // ---- update_buyback_authority @0x13ea6 : [authority(mut signer), fee_program_global(mut), buyback_vault(mut), event, program] args index:u8,new_authority:pubkey ----
    for reject in [false,true]{
        let (mut svm,user)=new_svm(fees_so);
        let signer= if reject{user}else{admin}; svm.airdrop(&signer,1_000_000_000).unwrap();
        svm.set_account(fpg,Account{lamports:5_000_000,data:fpg_bytes(fpg_bump,admin),owner:feep,executable:false,rent_epoch:0}).unwrap();
        svm.set_account(bv0,Account{lamports:2_338_560,data:bv_bytes(Pubkey::new_from_array([0x55u8;32])),owner:feep,executable:false,rent_epoch:0}).unwrap();
        let metas=vec![AccountMeta::new(signer,true),AccountMeta::new(fpg,false),AccountMeta::new(bv0,false),AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false)];
        let mut data=d_update_buyback_authority(); data.push(0); data.extend_from_slice(&new_auth.to_bytes());
        let nm= if reject{"update_buyback_authority_reject_wrongauth"}else{"update_buyback_authority_success"};
        out.push(exec(&mut svm,nm,signer,metas,data,&[("buyback_vault",bv0)]));
    }
    // ---- update_buyback_claim_rate_limit @0x13f80 : args index:u8,claim_rate_limit:i64 ----
    for reject in [false,true]{
        let (mut svm,user)=new_svm(fees_so);
        let signer= if reject{user}else{admin}; svm.airdrop(&signer,1_000_000_000).unwrap();
        svm.set_account(fpg,Account{lamports:5_000_000,data:fpg_bytes(fpg_bump,admin),owner:feep,executable:false,rent_epoch:0}).unwrap();
        svm.set_account(bv0,Account{lamports:2_338_560,data:bv_bytes(Pubkey::new_from_array([0x55u8;32])),owner:feep,executable:false,rent_epoch:0}).unwrap();
        let metas=vec![AccountMeta::new(signer,true),AccountMeta::new(fpg,false),AccountMeta::new(bv0,false),AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false)];
        let mut data=d_update_buyback_claim_rate_limit(); data.push(0); data.extend(i64le(3600));
        let nm= if reject{"update_buyback_claim_rate_limit_reject_wrongauth"}else{"update_buyback_claim_rate_limit_success"};
        out.push(exec(&mut svm,nm,signer,metas,data,&[("buyback_vault",bv0)]));
    }

    // ---- initialize_fee_program_global @0x12e01 : [authority(mut signer), pump_global(["global"]@pump, has_one authority), fee_program_global(init), system, event, program] args social:pubkey,disable:u8,rate:u64 ----
    for reject in [false,true]{
        let (mut svm,user)=new_svm(fees_so);
        let signer= if reject{user}else{admin}; svm.airdrop(&signer,1_000_000_000).unwrap();
        svm.set_account(gl,Account{lamports:50_000_000,data:global_bytes(admin),owner:pump,executable:false,rent_epoch:0}).unwrap();
        // fee_program_global NOT pre-seeded (init)
        let metas=vec![AccountMeta::new(signer,true),AccountMeta::new_readonly(gl,false),AccountMeta::new(fpg,false),
            AccountMeta::new_readonly(sys,false),AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false)];
        let mut data=d_initialize_fee_program_global(); data.extend_from_slice(&social.to_bytes()); data.push(5); data.extend(u64le(7200));
        let nm= if reject{"initialize_fee_program_global_reject_wrongauth"}else{"initialize_fee_program_global_success"};
        out.push(exec(&mut svm,nm,signer,metas,data,&[("fee_program_global",fpg)]));
    }

    // ---- withdraw @0x14121 : [user(signer), referral_vault(SystemAccount ["referral-vault",user]), quote_mint, vault_ata, user_ata, token_program, system, event, program] no args ----
    let qmint=Pubkey::new_from_array([0x3au8;32]);
    {   // success token path: referral_vault SystemAccount, vault_ata with balance -> transfer to user_ata
        let (mut svm,user)=new_svm(fees_so);
        let rv=Pubkey::find_program_address(&[b"referral-vault",user.as_ref()],&feep).0;
        svm.set_account(qmint,Account{lamports:1_000_000_000,data:spl_mint82(6),owner:token,executable:false,rent_epoch:0}).unwrap();
        svm.set_account(rv,Account{lamports:3_000_000,data:vec![],owner:sys,executable:false,rent_epoch:0}).unwrap();
        let vault_ata=ata(rv,token,qmint,atap); let user_ata=ata(user,token,qmint,atap);
        svm.set_account(vault_ata,Account{lamports:2_039_280,data:spl_tok165(qmint,rv,500_000),owner:token,executable:false,rent_epoch:0}).unwrap();
        svm.set_account(user_ata ,Account{lamports:2_039_280,data:spl_tok165(qmint,user,0),owner:token,executable:false,rent_epoch:0}).unwrap();
        let metas=vec![AccountMeta::new(user,true),AccountMeta::new(rv,false),AccountMeta::new_readonly(qmint,false),
            AccountMeta::new(vault_ata,false),AccountMeta::new(user_ata,false),AccountMeta::new_readonly(token,false),
            AccountMeta::new_readonly(sys,false),AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false)];
        out.push(exec(&mut svm,"withdraw_success_token",user,metas,d_withdraw(),&[("vault_ata",vault_ata),("user_ata",user_ata),("referral_vault",rv)]));
    }
    {   // reject: vault_ata balance 0 -> NothingToWithdraw (6036)
        let (mut svm,user)=new_svm(fees_so);
        let rv=Pubkey::find_program_address(&[b"referral-vault",user.as_ref()],&feep).0;
        svm.set_account(qmint,Account{lamports:1_000_000_000,data:spl_mint82(6),owner:token,executable:false,rent_epoch:0}).unwrap();
        svm.set_account(rv,Account{lamports:3_000_000,data:vec![],owner:sys,executable:false,rent_epoch:0}).unwrap();
        let vault_ata=ata(rv,token,qmint,atap); let user_ata=ata(user,token,qmint,atap);
        svm.set_account(vault_ata,Account{lamports:2_039_280,data:spl_tok165(qmint,rv,0),owner:token,executable:false,rent_epoch:0}).unwrap();
        svm.set_account(user_ata ,Account{lamports:2_039_280,data:spl_tok165(qmint,user,0),owner:token,executable:false,rent_epoch:0}).unwrap();
        let metas=vec![AccountMeta::new(user,true),AccountMeta::new(rv,false),AccountMeta::new_readonly(qmint,false),
            AccountMeta::new(vault_ata,false),AccountMeta::new(user_ata,false),AccountMeta::new_readonly(token,false),
            AccountMeta::new_readonly(sys,false),AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(feep,false)];
        out.push(exec(&mut svm,"withdraw_reject_nothing",user,metas,d_withdraw(),&[("vault_ata",vault_ata),("user_ata",user_ata)]));
    }

    out
}

fn hx(v:&[u8])->String{v.iter().map(|b|format!("{:02x}",b)).collect()}

fn main(){
    let a:Vec<String>=std::env::args().collect();
    if a.len()<3 { eprintln!("usage: admin2 <deployed.so> <recovered.so>"); std::process::exit(2); }
    let o=run(&a[1]); let c=run(&a[2]);
    let mut all=true;
    for i in 0..o.len().min(c.len()){
        let okm=o[i].ok==c[i].ok;
        let em =o[i].err==c[i].err;
        let mut snapm=true; let mut sd=String::new();
        for (j,(lbl,od)) in o[i].snaps.iter().enumerate(){
            let eq = od==&c[i].snaps[j].1;
            if !eq{
                snapm=false;
                let f=|x:&Option<(u64,Vec<u8>)>| x.as_ref().map(|(l,d)|format!("lam={} len={} data={}",l,d.len(),hx(d))).unwrap_or("<none>".into());
                sd.push_str(&format!("\n    SNAP[{}] DIVERGE\n      D: {}\n      R: {}",lbl,f(od),f(&c[i].snaps[j].1)));
            } else {
                let t=od.as_ref().map(|(l,d)|format!("lam={} len={}",l,d.len())).unwrap_or("<none>".into());
                sd.push_str(&format!("\n    SNAP[{}] match ({})",lbl,t));
            }
        }
        let logm_raw=o[i].logs==c[i].logs;
        let logm=canon(&o[i].logs)==canon(&c[i].logs);
        let cosmetic=logm&&!logm_raw;
        let casem=okm&&em&&snapm&&logm;
        if !casem{all=false;}
        println!("{:<48} {}  ok:{}/{} err_match:{} snap_match:{} log_match:{}{}  cu:{}/{}",
            o[i].name, if casem{if cosmetic{"MATCH*  "}else{"MATCH   "}}else{"DIVERGE!"},
            o[i].ok,c[i].ok,em,snapm,logm,
            if cosmetic{" (raw log differs only by compile-time src-location)"}else{""},o[i].cu,c[i].cu);
        if !o[i].err.is_empty()||!c[i].err.is_empty(){println!("    err D=[{}] R=[{}]",o[i].err,c[i].err);}
        print!("{}",sd); if !sd.is_empty(){println!();}
        if cosmetic{
            for (dl,rl) in o[i].logs.iter().zip(c[i].logs.iter()){ if dl!=rl{println!("    COSMETIC src-location diff (behaviorally equal):\n      D| {}\n      R| {}",dl,rl);} }
        }
        if !logm{
            println!("    LOG DIVERGE:");
            println!("      D logs ({}):",o[i].logs.len()); for l in &o[i].logs{println!("        D| {}",l);}
            println!("      R logs ({}):",c[i].logs.len()); for l in &c[i].logs{println!("        R| {}",l);}
        }
    }
    println!("\nFEES_ADMIN2_MATCH={}",all);
}
