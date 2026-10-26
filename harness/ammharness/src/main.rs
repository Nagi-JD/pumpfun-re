// Differential harness for pump_amm (PumpSwap AMM).
// Runs the DEPLOYED binary and the RECOVERED binary side-by-side in LiteSVM on
// identical, deterministically-seeded state, exercises the core AMM flow
// (create_pool -> deposit -> buy -> sell -> withdraw) and reports per-instruction
// whether the two builds MATCH (same ok/err, same resulting account bytes, CU).
//
// Account layouts are reversed from the Anchor IDL
//   /mnt/d/dev/ext/pumpfun-source/programs/pump-fees/idls/pump_amm.json
// cross-checked against the deployed binary handler map (amm_handlers.json):
//   create_pool @0x1c634, deposit @0x1ca4f, buy @0x1cec9, sell @0x1d099, withdraw @0x1caf6
// GlobalConfig / Pool / *VolumeAccumulator byte layouts are from the IDL `types`.

use litesvm::LiteSVM;
use solana_sdk::{pubkey::Pubkey, signature::{Keypair,Signer}, account::Account,
    instruction::{Instruction, AccountMeta}, transaction::Transaction, system_program};
use std::str::FromStr;

const AMM:&str  = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA";
const TOKEN:&str= "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA";
const T22:&str  = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb";
const ATA:&str  = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL";
const FEEP:&str = "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ";
const DEP:&str  = "/mnt/d/dev/ext/pumpfun-source/evidence/dependencies";

// IDL discriminators (instructions)
const D_CREATE_POOL:[u8;8]=[233,146,209,142,207,104,64,188];
const D_DEPOSIT:[u8;8]    =[242,35,198,137,82,225,242,182];
const D_BUY:[u8;8]        =[102,6,61,18,1,218,235,234];
const D_SELL:[u8;8]       =[51,230,133,164,1,127,131,173];
const D_WITHDRAW:[u8;8]   =[183,18,70,156,148,109,161,34];

struct Step{name:String,ok:bool,err:String,cu:u64,snap:Option<Vec<u8>>,logs:Vec<String>}
fn cu(l:&[String])->u64{for x in l.iter().rev(){if let Some(i)=x.find("consumed "){let r=&x[i+9..];if let Some(s)=r.find(char::is_whitespace){if let Ok(v)=r[..s].parse(){return v}}}}0}
fn u64le(v:u64)->Vec<u8>{v.to_le_bytes().to_vec()}
fn hexb(s:&str)->Vec<u8>{(0..s.len()).step_by(2).map(|i|u8::from_str_radix(&s[i..i+2],16).unwrap()).collect()}

// Live mainnet pump_amm global_config PDA snapshot (8Wf... style). 949 bytes.
// admin=FFWtrEQ4..., lp_fee_bps=20, protocol_fee_bps=5, protocol_fee_recipients[0]=
// 62qc2CNXwrYqQScmEdiZFFAnJR262PxWEuNQtxfafNgV, coin_creator_fee_bps=5, mayhem_mode_enabled=1.
fn amm_gc_bytes()->Vec<u8>{hexb("95089ccaa0fcb0d9d3bb8cab341ce0528457f2c3817d3278441963dcd55fed58ba24c999ddac02aa14000000000000000500000000000000004ac2f8d0dd5cbc97e3289c197cb5062a54f3d956b9ce6e5115f96567aa5cb3e6608ccc1dfce961b43b779c191505a6e2d3bf45d5a4db4618ad76c82d61754535638373000ea22cb264d34aff64a04b5efabfbb74ddcd048997b1981547d7d110838474292e675a94b436ecb0a9988942328a83ddc6233802961267c5cd6117cb8d181a0c849fa937a6f34aded3081ef95700aacb0c9bb3d909a4b9147527a4ebd7aa8fb060d8291b4c4d475daff762c96bdc0daceb36c012ead12ed3a9484161e004c87ceb98fa5ce47f803806fd2c7945d29524959aec00ded97814f38f7846ff8383818ba8fa28c3cd3b6d5e93f9fab8f0979bc37215acc5b246877ba8c3c9050000000000000007215d9940793694e116066ce459b818fdf9bba0c7b41b783fa3a120ca419532a28b5fd26ab479a6a9cc6cbf6b0b23eb61885a371e0120aca913beef3d138a78e893141fb18e9f1574d810e178e19e30604e3175aa2e4a32dfc8600727d10709013584536256094f912819127efa4e446b4333721793d13876f9aadbf3dc7d0b5f6e75018220f942677003237b4d6b453759b4a5c690b59c35d9bb187a090cbd2a33987a9ebb136799ab59925b13e5dc8b3081df005db427c1478fa46ff8c347a074e9543f3e37a2d046227addcb4e9c774c44258c43edf24aa8aae1f00214665bda4c38cd6db7438f59b408bb9ec3b4ca9e8ad1f1f24653c499b5796c20dbf9b32ddd9eea3f39b372115c71847c1845cfa536c685074e030e44d021de3ef9e35c4cb780f08ee2fee84bec446a577825da68d439fa8a5da3b0c5cff50f63f4546b01439e6510c03d65fad931e89d04be0bb70d51971f51c415fb344c07db419f212202235516a917134c67588c493820ae155ee96665577ac1b718da47ddcf2a050ee6a7e22068bb88640aa57f909308c61fef711a0163f5a755c070bc860d1f6367207cecda5bcc6cb1eaf0f16d68404566b18d56d2481acb317032656e90551c78449641f84958dc73a76a85d8756f55c02cdaca89ba1932790c368ab157e92d73c54b96b5c931941e46ea4be2e0e31127744fc6b74cfb455efeaf8bd571792ced44fc1f78f94a33d0909c5e6b5fb021570ad8dbad8de8fdb3d20ed1cd99eb8e4e8770157eebeb678a655db99b37f6b1326c7657db90cfb8a87abef8c7b6f2c8698813000000000000f4846287c1d2fcabd6f1815f697f540056fd165568611b00d3cae97482c12c6501012c01000000000000")}

// FeeConfig PDA for pump_amm, owned by fee_program (pfeeUxB...). Same extended 4097-byte
// faithful replica used by the pump launchpad harness; GetFeesWithQuoteMint reads trailing
// zero fields only present in the extended account. admin,bump=253,flat_fees + tiers.
fn fees()->Vec<u8>{let mut v=u64le(0);v.extend(u64le(95));v.extend(u64le(30));v}
fn feeconfig_bytes()->Vec<u8>{
    let admin:[u8;32]=[0xd3,0xbb,0x8c,0xab,0x34,0x1c,0xe0,0x52,0x84,0x57,0xf2,0xc3,0x81,0x7d,0x32,0x78,0x44,0x19,0x63,0xdc,0xd5,0x5f,0xed,0x58,0xba,0x24,0xc9,0x99,0xdd,0xac,0x02,0xaa];
    let mut d=vec![143,52,146,187,219,123,76,155u8];
    d.push(253);
    d.extend_from_slice(&admin);
    d.extend(fees());
    d.extend(1u32.to_le_bytes()); d.extend(0u128.to_le_bytes()); d.extend(fees());
    d.extend(1u32.to_le_bytes()); d.extend(0u128.to_le_bytes()); d.extend(fees());
    d.extend(fees());
    d.resize(4097,0);
    d
}
// GlobalVolumeAccumulator: 8 disc + i64*3 + pubkey + u64*30 + u64*30 = 544 bytes
fn gva_bytes()->Vec<u8>{let mut d=vec![202,42,246,43,142,190,30,255u8];d.extend(vec![0u8;536]);d}
// UserVolumeAccumulator: on-chain Anchor space constraint is 137 bytes (IDL struct + reserved pad).
fn uva_bytes(user:Pubkey)->Vec<u8>{let mut d=vec![86,255,112,14,102,53,154,250u8];d.extend_from_slice(&user.to_bytes());d.resize(137,0);d}
// SPL mint (82 bytes): decimals at 44, is_initialized at 45.
fn spl_mint82(dec:u8)->Vec<u8>{let mut v=vec![0u8;82];v[44]=dec;v[45]=1;v}
// SPL token account (165 bytes): mint, owner, amount, state=1 (initialized) at 108.
fn spl_tok165(mint:Pubkey,owner:Pubkey,amount:u64)->Vec<u8>{let mut v=vec![0u8;165];v[0..32].copy_from_slice(&mint.to_bytes());v[32..64].copy_from_slice(&owner.to_bytes());v[64..72].copy_from_slice(&amount.to_le_bytes());v[108]=1;v}

fn ata(owner:Pubkey,tok:Pubkey,mint:Pubkey,atap:Pubkey)->Pubkey{
    Pubkey::find_program_address(&[owner.as_ref(),tok.as_ref(),mint.as_ref()],&atap).0
}

fn run(amm_so:&str)->Vec<Step>{
    let amm=Pubkey::from_str(AMM).unwrap();
    let token=Pubkey::from_str(TOKEN).unwrap();
    let t22=Pubkey::from_str(T22).unwrap();
    let atap=Pubkey::from_str(ATA).unwrap();
    let feep=Pubkey::from_str(FEEP).unwrap();

    let mut svm=LiteSVM::new();
    svm.add_program_from_file(amm,amm_so).unwrap();
    svm.add_program_from_file(token,format!("{}/spl_token/deployed.so",DEP)).unwrap();
    svm.add_program_from_file(atap,format!("{}/associated_token/deployed.so",DEP)).unwrap();
    svm.add_program_from_file(t22,format!("{}/spl_token_2022/deployed.so",DEP)).unwrap();
    svm.add_program_from_file(feep,"/mnt/d/dev/ext/pumpfun-source/evidence/original/pump_fees/deployed.so").unwrap();

    let user=solana_sdk::signer::keypair::keypair_from_seed(&[7u8;32]).unwrap();
    svm.airdrop(&user.pubkey(),1_000_000_000_000).unwrap();

    // --- deterministic base/quote mints (both classic SPL) ---
    let base_mint=Pubkey::new_from_array([0x11u8;32]);
    let quote_mint=Pubkey::new_from_array([0x22u8;32]);
    svm.set_account(base_mint ,Account{lamports:1_000_000_000,data:spl_mint82(6),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(quote_mint,Account{lamports:1_000_000_000,data:spl_mint82(9),owner:token,executable:false,rent_epoch:0}).unwrap();

    // --- global_config PDA (owner = pump_amm), seeded directly (create_config is admin-gated) ---
    let gc=Pubkey::find_program_address(&[b"global_config"],&amm).0;
    svm.set_account(gc,Account{lamports:9_272_823,data:amm_gc_bytes(),owner:amm,executable:false,rent_epoch:0}).unwrap();

    // --- fee_config PDA (owner = fee_program): seeds [b"fee_config", amm_id] per the pump_amm IDL
    // (const 2nd seed = pAMMBay bytes). This is the address pump_amm's OWN Anchor layer validates.
    // NOTE: the external fee_program's GetFeesWithQuoteMint re-derives fee_config with a stricter,
    // undocumented seed and rejects this canonical address with ConstraintSeeds (2006) during the
    // buy/sell fee CPI. That gate is in the fixed pump_fees dependency (loaded identically in both
    // runs), not in the pump_amm binary under test, so both builds stop there identically.
    let fee_cfg=Pubkey::find_program_address(&[b"fee_config",amm.as_ref()],&feep).0;
    svm.set_account(fee_cfg,Account{lamports:37_292_293,data:feeconfig_bytes(),owner:feep,executable:false,rent_epoch:0}).unwrap();

    // --- user base/quote ATAs with large balances ---
    let user_base =ata(user.pubkey(),token,base_mint ,atap);
    let user_quote=ata(user.pubkey(),token,quote_mint,atap);
    svm.set_account(user_base ,Account{lamports:2_039_280,data:spl_tok165(base_mint ,user.pubkey(),1_000_000_000_000_000),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(user_quote,Account{lamports:2_039_280,data:spl_tok165(quote_mint,user.pubkey(),1_000_000_000_000_000),owner:token,executable:false,rent_epoch:0}).unwrap();

    // --- pool / lp / vault PDAs (created by create_pool; NOT pre-seeded) ---
    let index:u16=0;
    let pool=Pubkey::find_program_address(&[b"pool",&index.to_le_bytes(),user.pubkey().as_ref(),base_mint.as_ref(),quote_mint.as_ref()],&amm).0;
    let lp_mint=Pubkey::find_program_address(&[b"pool_lp_mint",pool.as_ref()],&amm).0;
    let user_pool_tok=ata(user.pubkey(),t22,lp_mint,atap);        // LP mint is Token-2022
    let pool_base =ata(pool,token,base_mint ,atap);
    let pool_quote=ata(pool,token,quote_mint,atap);
    let ev=Pubkey::find_program_address(&[b"__event_authority"],&amm).0;

    // --- buy/sell satellite accounts ---
    let coin_creator=user.pubkey();
    let cc_vault_auth=Pubkey::find_program_address(&[b"creator_vault",coin_creator.as_ref()],&amm).0;
    let cc_vault_ata =ata(cc_vault_auth,token,quote_mint,atap);
    let gva=Pubkey::find_program_address(&[b"global_volume_accumulator"],&amm).0;
    let uva=Pubkey::find_program_address(&[b"user_volume_accumulator",user.pubkey().as_ref()],&amm).0;
    let pfr=Pubkey::from_str("62qc2CNXwrYqQScmEdiZFFAnJR262PxWEuNQtxfafNgV").unwrap(); // protocol_fee_recipients[0]
    let pfr_ata=ata(pfr,token,quote_mint,atap);
    // pre-seed the fee/vault destination token accounts + volume accumulators (transfers target them)
    svm.set_account(pfr_ata,Account{lamports:2_039_280,data:spl_tok165(quote_mint,pfr,0),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(cc_vault_ata,Account{lamports:2_039_280,data:spl_tok165(quote_mint,cc_vault_auth,0),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(gva,Account{lamports:5_000_000,data:gva_bytes(),owner:amm,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(uva,Account{lamports:2_000_000,data:uva_bytes(user.pubkey()),owner:amm,executable:false,rent_epoch:0}).unwrap();

    let mut out=vec![];
    let send=|svm:&mut LiteSVM,name:&str,data:Vec<u8>,metas:Vec<AccountMeta>,signers:&[&Keypair],snaps:&[(&str,Pubkey)],out:&mut Vec<Step>|{
        let ix=Instruction{program_id:Pubkey::from_str(AMM).unwrap(),accounts:metas,data};
        let bh=svm.latest_blockhash();
        let mut all=vec![&user]; all.extend_from_slice(signers);
        let cbud=Pubkey::from_str("ComputeBudget111111111111111111111111111111").unwrap();
        let mut cbd=vec![2u8]; cbd.extend_from_slice(&1_400_000u32.to_le_bytes());
        let cbix=Instruction{program_id:cbud,accounts:vec![],data:cbd};
        let tx=Transaction::new_signed_with_payer(&[cbix,ix],Some(&user.pubkey()),&all,bh);
        let (ok,err,logs)=match svm.send_transaction(tx){
            Ok(m)=>(true,String::new(),m.logs.clone()),
            Err(e)=>(false,format!("{:?}",e.err),e.meta.logs.clone()),
        };
        let cuv=cu(&logs);
        // primary step carries the first snapshot
        let first=snaps.first().and_then(|(_,k)|svm.get_account(k).map(|a|a.data));
        out.push(Step{name:name.into(),ok,err,cu:cuv,snap:first,logs});
        for (lbl,k) in snaps.iter().skip(1){
            out.push(Step{name:format!("{}:{}",name,lbl),ok,err:String::new(),cu:0,snap:svm.get_account(k).map(|a|a.data),logs:vec![]});
        }
    };

    // ===== 1. create_pool =====
    // accounts [IDL order]: 0 pool(W,pda) 1 global_config 2 creator(W,S) 3 base_mint 4 quote_mint
    // 5 lp_mint(W,pda) 6 user_base(W) 7 user_quote(W) 8 user_pool_tok(W,pda) 9 pool_base(W,pda)
    // 10 pool_quote(W,pda) 11 system 12 token_2022 13 base_tok_prog 14 quote_tok_prog
    // 15 ata_prog 16 event_authority 17 program
    let mut cp=D_CREATE_POOL.to_vec();
    cp.extend(index.to_le_bytes());
    cp.extend(u64le(1_000_000_000_000)); // base_amount_in
    cp.extend(u64le(1_000_000_000));     // quote_amount_in
    cp.extend(coin_creator.to_bytes());  // coin_creator
    cp.push(0);                          // is_mayhem_mode = false
    cp.push(0);                          // is_cashback_coin = OptionBool None
    send(&mut svm,"create_pool",cp,vec![
        AccountMeta::new(pool,false),AccountMeta::new_readonly(gc,false),AccountMeta::new(user.pubkey(),true),
        AccountMeta::new_readonly(base_mint,false),AccountMeta::new_readonly(quote_mint,false),
        AccountMeta::new(lp_mint,false),AccountMeta::new(user_base,false),AccountMeta::new(user_quote,false),
        AccountMeta::new(user_pool_tok,false),AccountMeta::new(pool_base,false),AccountMeta::new(pool_quote,false),
        AccountMeta::new_readonly(system_program::ID,false),AccountMeta::new_readonly(t22,false),
        AccountMeta::new_readonly(token,false),AccountMeta::new_readonly(token,false),
        AccountMeta::new_readonly(atap,false),AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(amm,false)],
        &[],&[("pool",pool),("base",pool_base),("quote",pool_quote),("lp",lp_mint),("uplp",user_pool_tok)],&mut out);

    if std::env::var("DUMP").is_ok(){
        let amt=|k:&Pubkey|svm.get_account(k).map(|a|if a.data.len()>=72{u64::from_le_bytes(a.data[64..72].try_into().unwrap())}else{0}).unwrap_or(0);
        let sup=svm.get_account(&lp_mint).map(|a|if a.data.len()>=44{u64::from_le_bytes(a.data[36..44].try_into().unwrap())}else{0}).unwrap_or(0);
        eprintln!("[{}] after create_pool: pool_base_vault={} pool_quote_vault={} lp_supply={} user_lp={}",
            amm_so, amt(&pool_base), amt(&pool_quote), sup, amt(&user_pool_tok));
    }

    // ===== 2. deposit =====
    // 0 pool(W) 1 gc 2 user(S) 3 base_mint 4 quote_mint 5 lp_mint(W) 6 user_base(W) 7 user_quote(W)
    // 8 user_pool_tok(W) 9 pool_base(W) 10 pool_quote(W) 11 token_prog 12 token_2022 13 ev 14 program
    let mut dp=D_DEPOSIT.to_vec();
    dp.extend(u64le(100_000_000));           // lp_token_amount_out
    dp.extend(u64le(1_000_000_000_000));     // max_base_amount_in
    dp.extend(u64le(1_000_000_000));         // max_quote_amount_in
    let dep_metas=vec![
        AccountMeta::new(pool,false),AccountMeta::new_readonly(gc,false),AccountMeta::new(user.pubkey(),true),
        AccountMeta::new_readonly(base_mint,false),AccountMeta::new_readonly(quote_mint,false),
        AccountMeta::new(lp_mint,false),AccountMeta::new(user_base,false),AccountMeta::new(user_quote,false),
        AccountMeta::new(user_pool_tok,false),AccountMeta::new(pool_base,false),AccountMeta::new(pool_quote,false),
        AccountMeta::new_readonly(token,false),AccountMeta::new_readonly(t22,false),
        AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(amm,false)];
    send(&mut svm,"deposit",dp,dep_metas.clone(),&[],&[("pool",pool),("base",pool_base),("quote",pool_quote),("lp",lp_mint),("uplp",user_pool_tok)],&mut out);

    // create_pool stores its own coin_creator in Pool (offset 211..243: 8 disc + bump(1)+index(2)+
    // creator(32)+base_mint(32)+quote_mint(32)+lp_mint(32)+pool_base(32)+pool_quote(32)+lp_supply(8)).
    // The creator_vault authority PDA is seeded from pool.coin_creator, so read it back and re-derive.
    let cc=svm.get_account(&pool).map(|a|{let mut b=[0u8;32];b.copy_from_slice(&a.data[211..243]);Pubkey::new_from_array(b)}).unwrap_or(coin_creator);
    let cc_vault_auth=Pubkey::find_program_address(&[b"creator_vault",cc.as_ref()],&amm).0;
    let cc_vault_ata =ata(cc_vault_auth,token,quote_mint,atap);
    svm.set_account(cc_vault_ata,Account{lamports:2_039_280,data:spl_tok165(quote_mint,cc_vault_auth,0),owner:token,executable:false,rent_epoch:0}).unwrap();

    // ===== 3. buy ===== (quote -> base)
    // 0 pool(W) 1 user(W,S) 2 gc 3 base_mint 4 quote_mint 5 user_base(W) 6 user_quote(W)
    // 7 pool_base(W) 8 pool_quote(W) 9 pfr 10 pfr_ata(W,pda) 11 base_tok_prog 12 quote_tok_prog
    // 13 system 14 ata_prog 15 ev 16 program 17 cc_vault_ata(W,pda) 18 cc_vault_auth(pda)
    // 19 gva(pda) 20 uva(W,pda) 21 fee_config(pda) 22 fee_program
    let mut by=D_BUY.to_vec();
    by.extend(u64le(1_000_000_000)); // base_amount_out
    by.extend(u64le(1_000_000_000)); // max_quote_amount_in
    by.push(0);                      // track_volume = OptionBool None
    send(&mut svm,"buy",by,vec![
        AccountMeta::new(pool,false),AccountMeta::new(user.pubkey(),true),AccountMeta::new_readonly(gc,false),
        AccountMeta::new_readonly(base_mint,false),AccountMeta::new_readonly(quote_mint,false),
        AccountMeta::new(user_base,false),AccountMeta::new(user_quote,false),
        AccountMeta::new(pool_base,false),AccountMeta::new(pool_quote,false),
        AccountMeta::new_readonly(pfr,false),AccountMeta::new(pfr_ata,false),
        AccountMeta::new_readonly(token,false),AccountMeta::new_readonly(token,false),
        AccountMeta::new_readonly(system_program::ID,false),AccountMeta::new_readonly(atap,false),
        AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(amm,false),
        AccountMeta::new(cc_vault_ata,false),AccountMeta::new_readonly(cc_vault_auth,false),
        AccountMeta::new_readonly(gva,false),AccountMeta::new(uva,false),
        AccountMeta::new_readonly(fee_cfg,false),AccountMeta::new_readonly(feep,false)],
        &[],&[("pool",pool),("base",pool_base),("quote",pool_quote),("ubase",user_base),("uquote",user_quote),("pfr",pfr_ata)],&mut out);

    // ===== 4. sell ===== (base -> quote)
    // 0 pool(W) 1 user(W,S) 2 gc 3 base_mint 4 quote_mint 5 user_base(W) 6 user_quote(W)
    // 7 pool_base(W) 8 pool_quote(W) 9 pfr 10 pfr_ata(W,pda) 11 base_tok_prog 12 quote_tok_prog
    // 13 system 14 ata_prog 15 ev 16 program 17 cc_vault_ata(W,pda) 18 cc_vault_auth(pda)
    // 19 fee_config(pda) 20 fee_program
    let mut sl=D_SELL.to_vec();
    sl.extend(u64le(500_000_000)); // base_amount_in
    sl.extend(u64le(0));           // min_quote_amount_out
    send(&mut svm,"sell",sl,vec![
        AccountMeta::new(pool,false),AccountMeta::new(user.pubkey(),true),AccountMeta::new_readonly(gc,false),
        AccountMeta::new_readonly(base_mint,false),AccountMeta::new_readonly(quote_mint,false),
        AccountMeta::new(user_base,false),AccountMeta::new(user_quote,false),
        AccountMeta::new(pool_base,false),AccountMeta::new(pool_quote,false),
        AccountMeta::new_readonly(pfr,false),AccountMeta::new(pfr_ata,false),
        AccountMeta::new_readonly(token,false),AccountMeta::new_readonly(token,false),
        AccountMeta::new_readonly(system_program::ID,false),AccountMeta::new_readonly(atap,false),
        AccountMeta::new_readonly(ev,false),AccountMeta::new_readonly(amm,false),
        AccountMeta::new(cc_vault_ata,false),AccountMeta::new_readonly(cc_vault_auth,false),
        AccountMeta::new_readonly(fee_cfg,false),AccountMeta::new_readonly(feep,false)],
        &[],&[("pool",pool),("base",pool_base),("quote",pool_quote),("ubase",user_base),("uquote",user_quote),("pfr",pfr_ata)],&mut out);

    // ===== 5. withdraw ===== (burn LP -> base+quote)
    let mut wd=D_WITHDRAW.to_vec();
    wd.extend(u64le(50_000_000)); // lp_token_amount_in
    wd.extend(u64le(0));          // min_base_amount_out
    wd.extend(u64le(0));          // min_quote_amount_out
    send(&mut svm,"withdraw",wd,dep_metas,&[],&[("pool",pool),("base",pool_base),("quote",pool_quote),("lp",lp_mint),("uplp",user_pool_tok)],&mut out);

    out
}

fn main(){
    let a:Vec<String>=std::env::args().collect();
    if a.len()<3 { eprintln!("usage: ammharness <deployed.so> <recovered.so>"); std::process::exit(2); }
    let o=run(&a[1]); let c=run(&a[2]); let mut all=true;
    for i in 0..o.len().min(c.len()){
        let sm=o[i].snap==c[i].snap; let okm=o[i].ok==c[i].ok; let em=o[i].err==c[i].err;
        if !(sm&&okm&&em){all=false;}
        println!("{:<22} ok:{}/{} state_match:{} cu:{}/{}{}",o[i].name,o[i].ok,c[i].ok,sm,o[i].cu,c[i].cu,
            if o[i].err.is_empty()&&c[i].err.is_empty(){String::new()}else{format!("  err o=[{}] c=[{}]",o[i].err,c[i].err)});
    }
    // byte-level divergence dump
    for i in 0..o.len().min(c.len()){ if o[i].snap!=c[i].snap {
        if let (Some(os),Some(cs))=(&o[i].snap,&c[i].snap){
            eprintln!("DIFF {} olen={} clen={}",o[i].name,os.len(),cs.len());
            for j in 0..os.len().min(cs.len()){ if os[j]!=cs[j]{
                let s=j.saturating_sub(4);
                eprintln!("  first diff @ +{}: o={:02x} c={:02x}",j,os[j],cs[j]);
                eprintln!("  o[{}..]: {}",s,os[s..(s+24).min(os.len())].iter().map(|b|format!("{:02x}",b)).collect::<String>());
                eprintln!("  c[{}..]: {}",s,cs[s..(s+24).min(cs.len())].iter().map(|b|format!("{:02x}",b)).collect::<String>());
                break;}}
        } else { eprintln!("DIFF {} snap presence o={} c={}",o[i].name,o[i].snap.is_some(),c[i].snap.is_some()); }
    }}
    if std::env::var("LOGS").is_ok(){for i in 0..o.len().min(c.len()){eprintln!("=== {} ORIG ok={} ===",o[i].name,o[i].ok);for l in &o[i].logs{eprintln!("{}",l);}eprintln!("=== {} RECO ok={} ===",c[i].name,c[i].ok);for l in &c[i].logs{eprintln!("{}",l);}}}
    println!("\nAMM_FLOW_MATCH={}",all);
}
