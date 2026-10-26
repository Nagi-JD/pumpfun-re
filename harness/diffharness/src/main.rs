use litesvm::LiteSVM;
use solana_sdk::{pubkey::Pubkey, signature::{Keypair,Signer}, account::Account,
    instruction::{Instruction, AccountMeta}, transaction::Transaction, system_program, sysvar};
use std::str::FromStr;

const PUMP:&str="6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P";
const TOKEN:&str="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA";
const ATA:&str="ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL";
const META:&str="metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s";
const FEEP:&str="pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ";
const INIT:[u8;8]=[0xaf,0xaf,0x6d,0x1f,0x0d,0x98,0x9b,0xed];
const SETP:[u8;8]=[0x1b,0xea,0xb2,0x34,0x93,0x02,0xbb,0x8d];
const CREATE:[u8;8]=[0x18,0x1e,0xc8,0x28,0x05,0x1c,0x07,0x77];
const BUY:[u8;8]=[102,6,61,18,1,218,235,234];
const SELL:[u8;8]=[51,230,133,164,1,127,131,173];
const DEP:&str="/mnt/d/dev/ext/pumpfun-source/evidence/dependencies";
const ORIG_FEES:&str="/mnt/d/dev/ext/pumpfun-source/evidence/original/pump_fees/deployed.so";

struct Step{name:String,ok:bool,err:String,cu:u64,snap:Option<Vec<u8>>,logs:Vec<String>}
fn cu(l:&[String])->u64{for x in l.iter().rev(){if let Some(i)=x.find("consumed "){let r=&x[i+9..];if let Some(s)=r.find(char::is_whitespace){if let Ok(v)=r[..s].parse(){return v}}}}0}
fn u64le(v:u64)->Vec<u8>{v.to_le_bytes().to_vec()}
fn u128le(v:u128)->Vec<u8>{v.to_le_bytes().to_vec()}
fn strb(s:&str)->Vec<u8>{let mut o=(s.len() as u32).to_le_bytes().to_vec();o.extend_from_slice(s.as_bytes());o}
// Fees { lp_fee_bps, protocol_fee_bps, creator_fee_bps } — real mainnet values (0,95,30).
fn fees()->Vec<u8>{let mut v=u64le(0);v.extend(u64le(95));v.extend(u64le(30));v}

// Faithful replica of the live mainnet FeeConfig PDA (8Wf5TiAheLUqBrKXeYg2JtAFFMWtKdG2BSFgqUcPVwTt):
// 8-byte disc, bump=253, real admin, flat_fees, 1 fee_tier, 1 stable_fee_tier, exotic_flat_fees
// (177 canonical bytes) then zero-padded to the real extended size of 4097 bytes. The deployed
// pump_fees GetFeesWithQuoteMint deserializer reads trailing fields that are only present (as zeros)
// in the extended account, so a tight buffer under-ran ("failed to fill whole buffer").
fn feeconfig_bytes()->Vec<u8>{
    let admin:[u8;32]=[0xd3,0xbb,0x8c,0xab,0x34,0x1c,0xe0,0x52,0x84,0x57,0xf2,0xc3,0x81,0x7d,0x32,0x78,0x44,0x19,0x63,0xdc,0xd5,0x5f,0xed,0x58,0xba,0x24,0xc9,0x99,0xdd,0xac,0x02,0xaa];
    let mut d=vec![143,52,146,187,219,123,76,155u8];
    d.push(253);
    d.extend_from_slice(&admin);
    d.extend(fees());
    d.extend(1u32.to_le_bytes()); d.extend(u128le(0)); d.extend(fees()); // fee_tiers[0]
    d.extend(1u32.to_le_bytes()); d.extend(u128le(0)); d.extend(fees()); // stable_fee_tiers[0]
    d.extend(fees());                                                     // exotic_flat_fees
    d.resize(4097,0);
    d
}
fn gva_bytes()->Vec<u8>{let mut d=vec![202,42,246,43,142,190,30,255u8];d.extend(vec![0u8;536]);d}
fn hexb(s:&str)->Vec<u8>{(0..s.len()).step_by(2).map(|i|u8::from_str_radix(&s[i..i+2],16).unwrap()).collect()}
fn amm_gc_bytes()->Vec<u8>{hexb("95089ccaa0fcb0d9d3bb8cab341ce0528457f2c3817d3278441963dcd55fed58ba24c999ddac02aa14000000000000000500000000000000004ac2f8d0dd5cbc97e3289c197cb5062a54f3d956b9ce6e5115f96567aa5cb3e6608ccc1dfce961b43b779c191505a6e2d3bf45d5a4db4618ad76c82d61754535638373000ea22cb264d34aff64a04b5efabfbb74ddcd048997b1981547d7d110838474292e675a94b436ecb0a9988942328a83ddc6233802961267c5cd6117cb8d181a0c849fa937a6f34aded3081ef95700aacb0c9bb3d909a4b9147527a4ebd7aa8fb060d8291b4c4d475daff762c96bdc0daceb36c012ead12ed3a9484161e004c87ceb98fa5ce47f803806fd2c7945d29524959aec00ded97814f38f7846ff8383818ba8fa28c3cd3b6d5e93f9fab8f0979bc37215acc5b246877ba8c3c9050000000000000007215d9940793694e116066ce459b818fdf9bba0c7b41b783fa3a120ca419532a28b5fd26ab479a6a9cc6cbf6b0b23eb61885a371e0120aca913beef3d138a78e893141fb18e9f1574d810e178e19e30604e3175aa2e4a32dfc8600727d10709013584536256094f912819127efa4e446b4333721793d13876f9aadbf3dc7d0b5f6e75018220f942677003237b4d6b453759b4a5c690b59c35d9bb187a090cbd2a33987a9ebb136799ab59925b13e5dc8b3081df005db427c1478fa46ff8c347a074e9543f3e37a2d046227addcb4e9c774c44258c43edf24aa8aae1f00214665bda4c38cd6db7438f59b408bb9ec3b4ca9e8ad1f1f24653c499b5796c20dbf9b32ddd9eea3f39b372115c71847c1845cfa536c685074e030e44d021de3ef9e35c4cb780f08ee2fee84bec446a577825da68d439fa8a5da3b0c5cff50f63f4546b01439e6510c03d65fad931e89d04be0bb70d51971f51c415fb344c07db419f212202235516a917134c67588c493820ae155ee96665577ac1b718da47ddcf2a050ee6a7e22068bb88640aa57f909308c61fef711a0163f5a755c070bc860d1f6367207cecda5bcc6cb1eaf0f16d68404566b18d56d2481acb317032656e90551c78449641f84958dc73a76a85d8756f55c02cdaca89ba1932790c368ab157e92d73c54b96b5c931941e46ea4be2e0e31127744fc6b74cfb455efeaf8bd571792ced44fc1f78f94a33d0909c5e6b5fb021570ad8dbad8de8fdb3d20ed1cd99eb8e4e8770157eebeb678a655db99b37f6b1326c7657db90cfb8a87abef8c7b6f2c8698813000000000000f4846287c1d2fcabd6f1815f697f540056fd165568611b00d3cae97482c12c6501012c01000000000000")}
fn mayhem_gp_bytes()->Vec<u8>{hexb("79c1f857c3384c0b401f00000000000000c817a80400000000c817a80400000000203d88792d000000203d88792d000000d3bb8cab341ce0528457f2c3817d3278441963dcd55fed58ba24c999ddac02aaed64bf8d93a251ab472128330eb846b797063f07befd741dcefff0142d7d57ab303722b496150000000000000000000080f0fa02000000001800000000000000000000000000000000100e0000000000000a000000085101000000000000204aa9d101000000105e5f0000000000409452a303000000409452a30300006cbfd4f62c000000000000000000000000093d0000000000100e00000000000000000000000000000040be402500000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000")}
fn spl_mint82(dec:u8)->Vec<u8>{let mut v=vec![0u8;82];v[44]=dec;v[45]=1;v}
fn spl_tok165(mint:Pubkey,owner:Pubkey,amount:u64)->Vec<u8>{let mut v=vec![0u8;165];v[0..32].copy_from_slice(&mint.to_bytes());v[32..64].copy_from_slice(&owner.to_bytes());v[64..72].copy_from_slice(&amount.to_le_bytes());v[108]=1;v}
fn t22_mint_tfee(dec:u8,bps:u16,max_fee:u64)->Vec<u8>{let mut v=vec![0u8;278];v[44]=dec;v[45]=1;v[165]=1;v[166..168].copy_from_slice(&1u16.to_le_bytes());v[168..170].copy_from_slice(&108u16.to_le_bytes());v[250..258].copy_from_slice(&max_fee.to_le_bytes());v[258..260].copy_from_slice(&bps.to_le_bytes());v[268..276].copy_from_slice(&max_fee.to_le_bytes());v[276..278].copy_from_slice(&bps.to_le_bytes());v}
fn t22_tok_tfee(mint:Pubkey,owner:Pubkey,amount:u64)->Vec<u8>{let mut v=vec![0u8;178];v[0..32].copy_from_slice(&mint.to_bytes());v[32..64].copy_from_slice(&owner.to_bytes());v[64..72].copy_from_slice(&amount.to_le_bytes());v[108]=1;v[165]=2;v[166..168].copy_from_slice(&2u16.to_le_bytes());v[168..170].copy_from_slice(&8u16.to_le_bytes());v}

fn run(pump_so:&str)->Vec<Step>{
    let pump=Pubkey::from_str(PUMP).unwrap();
    let token=Pubkey::from_str(TOKEN).unwrap();
    let ata=Pubkey::from_str(ATA).unwrap();
    let meta=Pubkey::from_str(META).unwrap();
    let feep=Pubkey::from_str(FEEP).unwrap();
    let mut svm=LiteSVM::new();
    svm.add_program_from_file(pump,pump_so).unwrap();
    svm.add_program_from_file(token,format!("{}/spl_token/deployed.so",DEP)).unwrap();
    svm.add_program_from_file(ata,format!("{}/associated_token/deployed.so",DEP)).unwrap();
    svm.add_program_from_file(meta,format!("{}/token_metadata/deployed.so",DEP)).unwrap();
    svm.add_program_from_file(feep,ORIG_FEES).unwrap();
    svm.add_program_from_file(Pubkey::from_str("pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA").unwrap(),"/mnt/d/dev/ext/pumpfun-source/evidence/original/pump_amm/deployed.so").unwrap();
    svm.add_program_from_file(Pubkey::from_str("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb").unwrap(),format!("{}/spl_token_2022/deployed.so",DEP)).unwrap();
    svm.add_program_from_file(Pubkey::from_str("MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e").unwrap(),"/mnt/d/dev/ext/pumpfun-source/evidence/original/mayhem/deployed.so").unwrap();
    let user=solana_sdk::signer::keypair::keypair_from_seed(&[7u8;32]).unwrap();
    svm.airdrop(&user.pubkey(),1_000_000_000_000).unwrap();
    let (global,_)=Pubkey::find_program_address(&[b"global"],&pump);
    let (mint_auth,_)=Pubkey::find_program_address(&[b"mint-authority"],&pump);
    let (evauth,_)=Pubkey::find_program_address(&[b"__event_authority"],&pump);
    let (gva,_)=Pubkey::find_program_address(&[b"global_volume_accumulator"],&pump);
    let (feecfg,_)=Pubkey::find_program_address(&[b"fee_config",pump.as_ref()],&feep);
    let mut out=vec![];
    let send=|svm:&mut LiteSVM,name:&str,prog:Pubkey,data:Vec<u8>,metas:Vec<AccountMeta>,signers:&[&Keypair],snap:Option<Pubkey>,out:&mut Vec<Step>|{
        let ix=Instruction{program_id:prog,accounts:metas,data};
        let bh=svm.latest_blockhash();
        let mut all=vec![&user]; all.extend_from_slice(signers);
        let cbud=Pubkey::from_str("ComputeBudget111111111111111111111111111111").unwrap();
        let mut cbd=vec![2u8]; cbd.extend_from_slice(&1_400_000u32.to_le_bytes());
        let cbix=Instruction{program_id:cbud,accounts:vec![],data:cbd};
        let tx=Transaction::new_signed_with_payer(&[cbix,ix],Some(&user.pubkey()),&all,bh);
        let st=match svm.send_transaction(tx){
            Ok(m)=>Step{name:name.into(),ok:true,err:String::new(),cu:cu(&m.logs),snap:snap.and_then(|k|svm.get_account(&k).map(|a|a.data)),logs:m.logs.clone()},
            Err(e)=>Step{name:name.into(),ok:false,err:format!("{:?}",e.err),cu:cu(&e.meta.logs),snap:snap.and_then(|k|svm.get_account(&k).map(|a|a.data)),logs:e.meta.logs.clone()},
        };
        out.push(st);
    };
    send(&mut svm,"initialize",pump,INIT.to_vec(),
        vec![AccountMeta::new(global,false),AccountMeta::new(user.pubkey(),true),AccountMeta::new_readonly(system_program::ID,false)],&[],Some(global),&mut out);
    let mut d=SETP.to_vec();
    d.extend(u64le(1_073_000_000_000_000)); d.extend(u64le(30_000_000_000));
    d.extend(u64le(793_100_000_000_000));   d.extend(u64le(1_000_000_000_000_000));
    d.extend(u64le(100)); d.extend(user.pubkey().to_bytes()); d.push(1); d.extend(u64le(15_000_000_000));
    d.extend(u64le(0)); d.extend(user.pubkey().to_bytes()); d.extend(user.pubkey().to_bytes());
    let mut sm=vec![AccountMeta::new(global,false),AccountMeta::new(user.pubkey(),true),AccountMeta::new_readonly(evauth,false),AccountMeta::new_readonly(pump,false)];
    for i in 1u8..=8 {let r=Pubkey::new_from_array([i;32]); svm.airdrop(&r,1_000_000_000).unwrap(); sm.push(AccountMeta::new_readonly(r,false));}
    send(&mut svm,"set_params",pump,d,sm,&[],Some(global),&mut out);
    if std::env::var("DUMPG").is_ok(){if let Some(g)=svm.get_account(&global){eprintln!("GLOBAL[{}] len={}",pump_so,g.data.len());for (i,ch) in g.data.chunks(32).enumerate(){let off=i*32;eprintln!("  +{:#05x}: {}",off,ch.iter().map(|b|format!("{:02x}",b)).collect::<String>());}}}
    // Inject an authorized buyback fee recipient into Global.buyback_fee_recipients[0].
    // Stored Global data is byte-identical across both programs; buyback_fee_recipients[0]
    // begins at raw offset 741 (8-byte Anchor disc + borsh offset 733). buyback_basis_points
    // (raw 997) is left zero so no buyback transfer is required during the trade.
    if std::env::var("PDAS").is_ok(){eprintln!("FEECFG={}",feecfg);}
    let bbrecip=Pubkey::new_from_array([0x42u8;32]);
    if let Some(mut g)=svm.get_account(&global){ g.data[741..773].copy_from_slice(&bbrecip.to_bytes()); g.data[450]=1; g.data[515]=1; svm.set_account(global,g).unwrap(); }
    let mint=solana_sdk::signer::keypair::keypair_from_seed(&[0x11u8;32]).unwrap();
    let (bc,_)=Pubkey::find_program_address(&[b"bonding-curve",mint.pubkey().as_ref()],&pump);
    let (abc,_)=Pubkey::find_program_address(&[bc.as_ref(),token.as_ref(),mint.pubkey().as_ref()],&ata);
    let (mdpda,_)=Pubkey::find_program_address(&[b"metadata",meta.as_ref(),mint.pubkey().as_ref()],&meta);
    let mut cd=CREATE.to_vec(); cd.extend(strb("T")); cd.extend(strb("T")); cd.extend(strb("u")); cd.extend(user.pubkey().to_bytes());
    send(&mut svm,"create",pump,cd,vec![
        AccountMeta::new(mint.pubkey(),true),AccountMeta::new_readonly(mint_auth,false),
        AccountMeta::new(bc,false),AccountMeta::new(abc,false),AccountMeta::new_readonly(global,false),
        AccountMeta::new_readonly(meta,false),AccountMeta::new(mdpda,false),AccountMeta::new(user.pubkey(),true),
        AccountMeta::new_readonly(system_program::ID,false),AccountMeta::new_readonly(token,false),
        AccountMeta::new_readonly(ata,false),AccountMeta::new_readonly(sysvar::rent::ID,false),
        AccountMeta::new_readonly(evauth,false),AccountMeta::new_readonly(pump,false)],&[&mint],Some(bc),&mut out);
    let fresh_curve=svm.get_account(&bc).map(|x|x.data.clone()).unwrap_or_default();
    if std::env::var("FCDUMP").is_ok(){eprintln!("FRESHCURVE {}",fresh_curve.iter().take(120).map(|b|format!("{:02x}",b)).collect::<String>());}
    svm.set_account(feecfg, Account{lamports:37_292_293,data:feeconfig_bytes(),owner:feep,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(gva, Account{lamports:5_000_000,data:gva_bytes(),owner:pump,executable:false,rent_epoch:0}).unwrap();
    let (auser,_)=Pubkey::find_program_address(&[user.pubkey().as_ref(),token.as_ref(),mint.pubkey().as_ref()],&ata);
    send(&mut svm,"create_user_ata",ata,vec![1u8],vec![
        AccountMeta::new(user.pubkey(),true),AccountMeta::new(auser,false),AccountMeta::new_readonly(user.pubkey(),false),
        AccountMeta::new_readonly(mint.pubkey(),false),AccountMeta::new_readonly(system_program::ID,false),AccountMeta::new_readonly(token,false)],&[],None,&mut out);
    let recip=Pubkey::new_from_array([1u8;32]);
    let (cvault,_)=Pubkey::find_program_address(&[b"creator-vault",user.pubkey().as_ref()],&pump);
    let (uva,_)=Pubkey::find_program_address(&[b"user_volume_accumulator",user.pubkey().as_ref()],&pump);
    let mut bd=BUY.to_vec(); bd.extend(u64le(1_000_000_000)); bd.extend(u64le(1_000_000_000_000)); bd.push(0); bd.push(0);
    send(&mut svm,"buy",pump,bd,vec![
        AccountMeta::new_readonly(global,false),AccountMeta::new(recip,false),AccountMeta::new_readonly(mint.pubkey(),false),
        AccountMeta::new(bc,false),AccountMeta::new(abc,false),AccountMeta::new(auser,false),AccountMeta::new(user.pubkey(),true),
        AccountMeta::new_readonly(system_program::ID,false),AccountMeta::new_readonly(token,false),
        AccountMeta::new(cvault,false),AccountMeta::new_readonly(evauth,false),AccountMeta::new_readonly(pump,false),
        AccountMeta::new_readonly(gva,false),AccountMeta::new(uva,false),
        AccountMeta::new_readonly(feecfg,false),AccountMeta::new_readonly(feep,false),
        AccountMeta::new_readonly(Pubkey::find_program_address(&[b"bonding-curve-v2",mint.pubkey().as_ref()],&pump).0,false),
        AccountMeta::new(bbrecip,false)],&[],Some(bc),&mut out);
    // Verify the user's token balance is byte-identical across original vs clone after the buy.
    if let Some(a)=svm.get_account(&auser){out.push(Step{name:"buy_user_tokens".into(),ok:true,err:String::new(),cu:0,snap:Some(a.data),logs:vec![]});}
    // --- sell: the user (now holding tokens) sells half of them back to the curve ---
    let bcv2=Pubkey::find_program_address(&[b"bonding-curve-v2",mint.pubkey().as_ref()],&pump).0;
    let mut sd=SELL.to_vec(); sd.extend(u64le(500_000_000)); sd.extend(u64le(0)); // amount, min_sol_output
    send(&mut svm,"sell",pump,sd,vec![
        AccountMeta::new_readonly(global,false),AccountMeta::new(recip,false),AccountMeta::new_readonly(mint.pubkey(),false),
        AccountMeta::new(bc,false),AccountMeta::new(abc,false),AccountMeta::new(auser,false),AccountMeta::new(user.pubkey(),true),
        AccountMeta::new_readonly(system_program::ID,false),AccountMeta::new(cvault,false),AccountMeta::new_readonly(token,false),
        AccountMeta::new_readonly(evauth,false),AccountMeta::new_readonly(pump,false),
        AccountMeta::new_readonly(feecfg,false),AccountMeta::new_readonly(feep,false),
        AccountMeta::new_readonly(bcv2,false),AccountMeta::new(bbrecip,false)],&[],Some(bc),&mut out);
    if let Some(a)=svm.get_account(&auser){out.push(Step{name:"sell_user_tokens".into(),ok:true,err:String::new(),cu:0,snap:Some(a.data),logs:vec![]});}
    // --- v3 native-SOL trades: SellV3 context (17 accts incl. event_cpi), WSOL/default quote → native branch ---
    let wsol=Pubkey::from_str("So11111111111111111111111111111111111111112").unwrap();
    // Deployed SellV3 types quote_mint as InterfaceAccount<Mint> (fails with AccountNotInitialized/3012
    // if absent). Seed a real SPL WSOL mint (82 bytes, owner=spl-token, decimals=9, initialized) so the
    // native branch's quote_mint deserializes on both original and clone.
    { let mut wm=vec![0u8;82]; wm[44]=9; wm[45]=1;
      svm.set_account(wsol, Account{lamports:1_000_000_000,data:wm,owner:token,executable:false,rent_epoch:0}).unwrap(); }
    // Original SellV3 enforces an associated_token ADDRESS constraint on the quote ATAs even on the
    // native branch (ConstraintSeeds/2006 otherwise): ATA(authority, quote_token_program, quote_mint).
    let qbc=Pubkey::find_program_address(&[bc.as_ref(),token.as_ref(),wsol.as_ref()],&ata).0; // assoc_quote_bonding_curve = ATA(bc,WSOL)
    let qu =Pubkey::find_program_address(&[user.pubkey().as_ref(),token.as_ref(),wsol.as_ref()],&ata).0; // assoc_quote_user = ATA(user,WSOL)
    // SellV3 account order from IDL (buy_v3/sell_v3/buy_exact_quote_in_v3 share it):
    // 0 global,1 base_mint,2 quote_mint,3 base_tok_prog,4 quote_tok_prog,5 bonding_curve,
    // 6 abc,7 aqbc,8 user,9 abu,10 aqu,11 uva,12 fee_config,13 buyback_recipient,14 system,15 ev_auth,16 program
    let v3_metas=|| vec![
        AccountMeta::new_readonly(global,false),AccountMeta::new_readonly(mint.pubkey(),false),AccountMeta::new_readonly(wsol,false),
        AccountMeta::new_readonly(token,false),AccountMeta::new_readonly(token,false),AccountMeta::new(bc,false),
        AccountMeta::new(abc,false),AccountMeta::new(qbc,false),AccountMeta::new(user.pubkey(),true),
        AccountMeta::new(auser,false),AccountMeta::new(qu,false),AccountMeta::new(uva,false),
        AccountMeta::new_readonly(feecfg,false),AccountMeta::new(bbrecip,false),AccountMeta::new_readonly(system_program::ID,false),
        AccountMeta::new_readonly(evauth,false),AccountMeta::new_readonly(pump,false)];
    // buy_v3 disc [7,5,29,196,245,23,101,80] + amount:u64 + max_sol_cost:u64 + partial_fill:OptionBool(1 byte)
    let mut b3=vec![7u8,5,29,196,245,23,101,80]; b3.extend(u64le(100_000_000)); b3.extend(u64le(1_000_000_000_000)); b3.push(0);
    send(&mut svm,"buy_v3",pump,b3,v3_metas(),&[],Some(bc),&mut out);
    if let Some(a)=svm.get_account(&auser){out.push(Step{name:"buy_v3_tokens".into(),ok:true,err:String::new(),cu:0,snap:Some(a.data),logs:vec![]});}
    // sell_v3 disc [28,146,222,119,38,196,105,213] + amount:u64 + min_sol_output:u64
    let mut s3=vec![28u8,146,222,119,38,196,105,213]; s3.extend(u64le(100_000_000)); s3.extend(u64le(0));
    send(&mut svm,"sell_v3",pump,s3,v3_metas(),&[],Some(bc),&mut out);
    if let Some(a)=svm.get_account(&auser){out.push(Step{name:"sell_v3_tokens".into(),ok:true,err:String::new(),cu:0,snap:Some(a.data),logs:vec![]});}
    // --- non-SOL quote route: buy_v3 on a curve whose quote_mint is a plain SPL token ---
    let mint2=Pubkey::new_from_array([0x22u8;32]);
    let qmint=Pubkey::new_from_array([0x33u8;32]);
    svm.set_account(mint2,Account{lamports:1_000_000_000,data:spl_mint82(9),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(qmint,Account{lamports:1_000_000_000,data:spl_mint82(6),owner:token,executable:false,rent_epoch:0}).unwrap();
    let bc2=Pubkey::find_program_address(&[b"bonding-curve",mint2.as_ref()],&pump).0;
    { let mut cd2=fresh_curve.clone(); if cd2.len()>=115 { cd2[83..115].copy_from_slice(&qmint.to_bytes()); } svm.set_account(bc2,Account{lamports:1_000_000_000,data:cd2,owner:pump,executable:false,rent_epoch:0}).unwrap(); }
    let abc2=Pubkey::find_program_address(&[bc2.as_ref(),token.as_ref(),mint2.as_ref()],&ata).0;
    let abu2=Pubkey::find_program_address(&[user.pubkey().as_ref(),token.as_ref(),mint2.as_ref()],&ata).0;
    let abqc=Pubkey::find_program_address(&[bc2.as_ref(),token.as_ref(),qmint.as_ref()],&ata).0;
    let aqu2=Pubkey::find_program_address(&[user.pubkey().as_ref(),token.as_ref(),qmint.as_ref()],&ata).0;
    let bb_q=Pubkey::find_program_address(&[bbrecip.as_ref(),token.as_ref(),qmint.as_ref()],&ata).0;
    svm.set_account(abc2,Account{lamports:2_039_280,data:spl_tok165(mint2,bc2,1_000_000_000_000_000),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(abu2,Account{lamports:2_039_280,data:spl_tok165(mint2,user.pubkey(),0),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(abqc,Account{lamports:2_039_280,data:spl_tok165(qmint,bc2,0),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(aqu2,Account{lamports:2_039_280,data:spl_tok165(qmint,user.pubkey(),1_000_000_000_000_000),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(bb_q,Account{lamports:2_039_280,data:spl_tok165(qmint,bbrecip,0),owner:token,executable:false,rent_epoch:0}).unwrap();
    let mut qb3=vec![7u8,5,29,196,245,23,101,80]; qb3.extend(u64le(1_000_000_000)); qb3.extend(u64le(1_000_000_000_000_000)); qb3.push(0);
    send(&mut svm,"buy_v3_spl",pump,qb3,vec![
        AccountMeta::new_readonly(global,false),AccountMeta::new_readonly(mint2,false),AccountMeta::new_readonly(qmint,false),
        AccountMeta::new_readonly(token,false),AccountMeta::new_readonly(token,false),AccountMeta::new(bc2,false),
        AccountMeta::new(abc2,false),AccountMeta::new(abqc,false),AccountMeta::new(user.pubkey(),true),
        AccountMeta::new(abu2,false),AccountMeta::new(aqu2,false),AccountMeta::new(uva,false),
        AccountMeta::new_readonly(feecfg,false),AccountMeta::new(bb_q,false),AccountMeta::new_readonly(system_program::ID,false),
        AccountMeta::new_readonly(evauth,false),AccountMeta::new_readonly(pump,false)],&[],Some(bc2),&mut out);
    if let Some(a)=svm.get_account(&abqc){out.push(Step{name:"buy_v3_spl_quote".into(),ok:true,err:String::new(),cu:0,snap:Some(a.data),logs:vec![]});}
    // --- non-SOL quote route (Token-2022 w/ TransferFeeConfig): exercises inferred amount_after_fee ---
    let t22=Pubkey::from_str("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb").unwrap();
    let mint3=Pubkey::new_from_array([0x55u8;32]);
    let qmint2=Pubkey::new_from_array([0x44u8;32]);
    svm.set_account(mint3,Account{lamports:1_000_000_000,data:spl_mint82(9),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(qmint2,Account{lamports:1_000_000_000,data:t22_mint_tfee(6,100,1_000_000_000_000_000_000),owner:t22,executable:false,rent_epoch:0}).unwrap();
    let bc3=Pubkey::find_program_address(&[b"bonding-curve",mint3.as_ref()],&pump).0;
    { let mut cd3=fresh_curve.clone(); if cd3.len()>=115 { cd3[83..115].copy_from_slice(&qmint2.to_bytes()); } svm.set_account(bc3,Account{lamports:1_000_000_000,data:cd3,owner:pump,executable:false,rent_epoch:0}).unwrap(); }
    let abc3=Pubkey::find_program_address(&[bc3.as_ref(),token.as_ref(),mint3.as_ref()],&ata).0;
    let abu3=Pubkey::find_program_address(&[user.pubkey().as_ref(),token.as_ref(),mint3.as_ref()],&ata).0;
    let abqc2=Pubkey::find_program_address(&[bc3.as_ref(),t22.as_ref(),qmint2.as_ref()],&ata).0;
    let aqu3=Pubkey::find_program_address(&[user.pubkey().as_ref(),t22.as_ref(),qmint2.as_ref()],&ata).0;
    let bb_q2=Pubkey::find_program_address(&[bbrecip.as_ref(),t22.as_ref(),qmint2.as_ref()],&ata).0;
    svm.set_account(abc3,Account{lamports:2_039_280,data:spl_tok165(mint3,bc3,1_000_000_000_000_000),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(abu3,Account{lamports:2_039_280,data:spl_tok165(mint3,user.pubkey(),0),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(abqc2,Account{lamports:2_039_280,data:t22_tok_tfee(qmint2,bc3,0),owner:t22,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(aqu3,Account{lamports:2_039_280,data:t22_tok_tfee(qmint2,user.pubkey(),1_000_000_000_000_000),owner:t22,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(bb_q2,Account{lamports:2_039_280,data:t22_tok_tfee(qmint2,bbrecip,0),owner:t22,executable:false,rent_epoch:0}).unwrap();
    let mut tb3=vec![7u8,5,29,196,245,23,101,80]; tb3.extend(u64le(1_000_000_000)); tb3.extend(u64le(1_000_000_000_000_000)); tb3.push(0);
    send(&mut svm,"buy_v3_t22",pump,tb3,vec![
        AccountMeta::new_readonly(global,false),AccountMeta::new_readonly(mint3,false),AccountMeta::new_readonly(qmint2,false),
        AccountMeta::new_readonly(token,false),AccountMeta::new_readonly(t22,false),AccountMeta::new(bc3,false),
        AccountMeta::new(abc3,false),AccountMeta::new(abqc2,false),AccountMeta::new(user.pubkey(),true),
        AccountMeta::new(abu3,false),AccountMeta::new(aqu3,false),AccountMeta::new(uva,false),
        AccountMeta::new_readonly(feecfg,false),AccountMeta::new(bb_q2,false),AccountMeta::new_readonly(system_program::ID,false),
        AccountMeta::new_readonly(evauth,false),AccountMeta::new_readonly(pump,false)],&[],Some(bc3),&mut out);
    if let Some(a)=svm.get_account(&abqc2){out.push(Step{name:"buy_v3_t22_quote".into(),ok:true,err:String::new(),cu:0,snap:Some(a.data),logs:vec![]});}
    if let Some(a)=svm.get_account(&aqu3){out.push(Step{name:"buy_v3_t22_user".into(),ok:true,err:String::new(),cu:0,snap:Some(a.data),logs:vec![]});}
    // --- sell_v3 on a Token-2022-quote curve (characterize sell-side fee handling) ---
    let mint4=Pubkey::new_from_array([0x66u8;32]);
    let qmint3=Pubkey::new_from_array([0x77u8;32]);
    svm.set_account(mint4,Account{lamports:1_000_000_000,data:spl_mint82(9),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(qmint3,Account{lamports:1_000_000_000,data:t22_mint_tfee(6,100,1_000_000_000_000_000_000),owner:t22,executable:false,rent_epoch:0}).unwrap();
    let bc4=Pubkey::find_program_address(&[b"bonding-curve",mint4.as_ref()],&pump).0;
    { let mut cd=fresh_curve.clone(); if cd.len()>=115 { cd[83..115].copy_from_slice(&qmint3.to_bytes()); } cd[32..40].copy_from_slice(&10_000_000u64.to_le_bytes()); cd[16..24].copy_from_slice(&30_010_000_000u64.to_le_bytes()); svm.set_account(bc4,Account{lamports:1_000_000_000,data:cd,owner:pump,executable:false,rent_epoch:0}).unwrap(); }
    let abc4=Pubkey::find_program_address(&[bc4.as_ref(),token.as_ref(),mint4.as_ref()],&ata).0;
    let abu4=Pubkey::find_program_address(&[user.pubkey().as_ref(),token.as_ref(),mint4.as_ref()],&ata).0;
    let abqc4=Pubkey::find_program_address(&[bc4.as_ref(),t22.as_ref(),qmint3.as_ref()],&ata).0;
    let aqu4=Pubkey::find_program_address(&[user.pubkey().as_ref(),t22.as_ref(),qmint3.as_ref()],&ata).0;
    let bb_q3=Pubkey::find_program_address(&[bbrecip.as_ref(),t22.as_ref(),qmint3.as_ref()],&ata).0;
    svm.set_account(abc4,Account{lamports:2_039_280,data:spl_tok165(mint4,bc4,1_000_000_000_000_000),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(abu4,Account{lamports:2_039_280,data:spl_tok165(mint4,user.pubkey(),1_000_000_000),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(abqc4,Account{lamports:2_039_280,data:t22_tok_tfee(qmint3,bc4,1_000_000_000),owner:t22,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(aqu4,Account{lamports:2_039_280,data:t22_tok_tfee(qmint3,user.pubkey(),0),owner:t22,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(bb_q3,Account{lamports:2_039_280,data:t22_tok_tfee(qmint3,bbrecip,0),owner:t22,executable:false,rent_epoch:0}).unwrap();
    let mut ts3=vec![28u8,146,222,119,38,196,105,213]; ts3.extend(u64le(500_000_000)); ts3.extend(u64le(0));
    send(&mut svm,"sell_v3_t22",pump,ts3,vec![
        AccountMeta::new_readonly(global,false),AccountMeta::new_readonly(mint4,false),AccountMeta::new_readonly(qmint3,false),
        AccountMeta::new_readonly(token,false),AccountMeta::new_readonly(t22,false),AccountMeta::new(bc4,false),
        AccountMeta::new(abc4,false),AccountMeta::new(abqc4,false),AccountMeta::new(user.pubkey(),true),
        AccountMeta::new(abu4,false),AccountMeta::new(aqu4,false),AccountMeta::new(uva,false),
        AccountMeta::new_readonly(feecfg,false),AccountMeta::new(bb_q3,false),AccountMeta::new_readonly(system_program::ID,false),
        AccountMeta::new_readonly(evauth,false),AccountMeta::new_readonly(pump,false)],&[],Some(bc4),&mut out);
    if let Some(a)=svm.get_account(&aqu4){out.push(Step{name:"sell_v3_t22_user".into(),ok:true,err:String::new(),cu:0,snap:Some(a.data),logs:vec![]});}
    if let Some(a)=svm.get_account(&abqc4){out.push(Step{name:"sell_v3_t22_curveq".into(),ok:true,err:String::new(),cu:0,snap:Some(a.data),logs:vec![]});}
    // --- buy_exact_quote_in_v3 on a Token-2022-quote curve (characterize) ---
    let mint5=Pubkey::new_from_array([0x88u8;32]);
    let qmint4=Pubkey::new_from_array([0x99u8;32]);
    svm.set_account(mint5,Account{lamports:1_000_000_000,data:spl_mint82(9),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(qmint4,Account{lamports:1_000_000_000,data:t22_mint_tfee(6,100,1_000_000_000_000_000_000),owner:t22,executable:false,rent_epoch:0}).unwrap();
    let bc5=Pubkey::find_program_address(&[b"bonding-curve",mint5.as_ref()],&pump).0;
    { let mut cd=fresh_curve.clone(); if cd.len()>=115 { cd[83..115].copy_from_slice(&qmint4.to_bytes()); } svm.set_account(bc5,Account{lamports:1_000_000_000,data:cd,owner:pump,executable:false,rent_epoch:0}).unwrap(); }
    let abc5=Pubkey::find_program_address(&[bc5.as_ref(),token.as_ref(),mint5.as_ref()],&ata).0;
    let abu5=Pubkey::find_program_address(&[user.pubkey().as_ref(),token.as_ref(),mint5.as_ref()],&ata).0;
    let abqc5=Pubkey::find_program_address(&[bc5.as_ref(),t22.as_ref(),qmint4.as_ref()],&ata).0;
    let aqu5=Pubkey::find_program_address(&[user.pubkey().as_ref(),t22.as_ref(),qmint4.as_ref()],&ata).0;
    let bb_q4=Pubkey::find_program_address(&[bbrecip.as_ref(),t22.as_ref(),qmint4.as_ref()],&ata).0;
    svm.set_account(abc5,Account{lamports:2_039_280,data:spl_tok165(mint5,bc5,1_000_000_000_000_000),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(abu5,Account{lamports:2_039_280,data:spl_tok165(mint5,user.pubkey(),0),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(abqc5,Account{lamports:2_039_280,data:t22_tok_tfee(qmint4,bc5,0),owner:t22,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(aqu5,Account{lamports:2_039_280,data:t22_tok_tfee(qmint4,user.pubkey(),1_000_000_000_000_000),owner:t22,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(bb_q4,Account{lamports:2_039_280,data:t22_tok_tfee(qmint4,bbrecip,0),owner:t22,executable:false,rent_epoch:0}).unwrap();
    let mut be3=vec![225u8,247,80,30,213,179,132,136]; be3.extend(u64le(1_000_000)); be3.extend(u64le(1)); be3.push(0);
    send(&mut svm,"bexact_v3_t22",pump,be3,vec![
        AccountMeta::new_readonly(global,false),AccountMeta::new_readonly(mint5,false),AccountMeta::new_readonly(qmint4,false),
        AccountMeta::new_readonly(token,false),AccountMeta::new_readonly(t22,false),AccountMeta::new(bc5,false),
        AccountMeta::new(abc5,false),AccountMeta::new(abqc5,false),AccountMeta::new(user.pubkey(),true),
        AccountMeta::new(abu5,false),AccountMeta::new(aqu5,false),AccountMeta::new(uva,false),
        AccountMeta::new_readonly(feecfg,false),AccountMeta::new(bb_q4,false),AccountMeta::new_readonly(system_program::ID,false),
        AccountMeta::new_readonly(evauth,false),AccountMeta::new_readonly(pump,false)],&[],Some(bc5),&mut out);
    if let Some(a)=svm.get_account(&abqc5){out.push(Step{name:"bexact_v3_t22_curveq".into(),ok:true,err:String::new(),cu:0,snap:Some(a.data),logs:vec![]});}
    // --- buy_exact_quote_in_v2 on a Token-2022-quote curve (BuyV2 ctx: 27 accounts, GetFeesWithQuoteMint CPI) ---
    // Verifies whether the LEGACY v2 exact-quote path shares buy_v3's input-netting fee-direction bug.
    let mint6=Pubkey::new_from_array([0xaau8;32]);
    let qmint5=Pubkey::new_from_array([0xbbu8;32]);
    svm.set_account(mint6,Account{lamports:1_000_000_000,data:spl_mint82(9),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(qmint5,Account{lamports:1_000_000_000,data:t22_mint_tfee(6,100,1_000_000_000_000_000_000),owner:t22,executable:false,rent_epoch:0}).unwrap();
    let bc6=Pubkey::find_program_address(&[b"bonding-curve",mint6.as_ref()],&pump).0;
    { let mut cd=fresh_curve.clone(); if cd.len()>=115 { cd[83..115].copy_from_slice(&qmint5.to_bytes()); } svm.set_account(bc6,Account{lamports:1_000_000_000,data:cd,owner:pump,executable:false,rent_epoch:0}).unwrap(); }
    let abc6=Pubkey::find_program_address(&[bc6.as_ref(),token.as_ref(),mint6.as_ref()],&ata).0;
    let abu6=Pubkey::find_program_address(&[user.pubkey().as_ref(),token.as_ref(),mint6.as_ref()],&ata).0;
    let aqbc6=Pubkey::find_program_address(&[bc6.as_ref(),t22.as_ref(),qmint5.as_ref()],&ata).0;
    let aqu6=Pubkey::find_program_address(&[user.pubkey().as_ref(),t22.as_ref(),qmint5.as_ref()],&ata).0;
    let aqfr=Pubkey::find_program_address(&[recip.as_ref(),t22.as_ref(),qmint5.as_ref()],&ata).0;
    let aqbb=Pubkey::find_program_address(&[bbrecip.as_ref(),t22.as_ref(),qmint5.as_ref()],&ata).0;
    let aqcv=Pubkey::find_program_address(&[cvault.as_ref(),t22.as_ref(),qmint5.as_ref()],&ata).0;
    let aquva=Pubkey::find_program_address(&[uva.as_ref(),t22.as_ref(),qmint5.as_ref()],&ata).0;
    let scfg=Pubkey::find_program_address(&[b"sharing-config",mint6.as_ref()],&feep).0;
    svm.set_account(abc6,Account{lamports:2_039_280,data:spl_tok165(mint6,bc6,1_000_000_000_000_000),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(abu6,Account{lamports:2_039_280,data:spl_tok165(mint6,user.pubkey(),0),owner:token,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(aqbc6,Account{lamports:2_039_280,data:t22_tok_tfee(qmint5,bc6,0),owner:t22,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(aqu6,Account{lamports:2_039_280,data:t22_tok_tfee(qmint5,user.pubkey(),1_000_000_000_000_000),owner:t22,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(aqfr,Account{lamports:2_039_280,data:t22_tok_tfee(qmint5,recip,0),owner:t22,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(aqbb,Account{lamports:2_039_280,data:t22_tok_tfee(qmint5,bbrecip,0),owner:t22,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(aqcv,Account{lamports:2_039_280,data:t22_tok_tfee(qmint5,cvault,0),owner:t22,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(aquva,Account{lamports:2_039_280,data:t22_tok_tfee(qmint5,uva,0),owner:t22,executable:false,rent_epoch:0}).unwrap();
    let mut bv2=vec![194u8,171,28,70,104,77,91,47]; bv2.extend(u64le(1_000_000)); bv2.extend(u64le(1)); bv2.push(0);
    send(&mut svm,"beq_v2_t22",pump,bv2,vec![
        AccountMeta::new_readonly(global,false),AccountMeta::new_readonly(mint6,false),AccountMeta::new_readonly(qmint5,false),
        AccountMeta::new_readonly(token,false),AccountMeta::new_readonly(t22,false),AccountMeta::new_readonly(ata,false),
        AccountMeta::new(recip,false),AccountMeta::new(aqfr,false),AccountMeta::new(bbrecip,false),AccountMeta::new(aqbb,false),
        AccountMeta::new(bc6,false),AccountMeta::new(abc6,false),AccountMeta::new(aqbc6,false),
        AccountMeta::new(user.pubkey(),true),AccountMeta::new(abu6,false),AccountMeta::new(aqu6,false),
        AccountMeta::new(cvault,false),AccountMeta::new(aqcv,false),AccountMeta::new_readonly(scfg,false),
        AccountMeta::new_readonly(gva,false),AccountMeta::new(uva,false),AccountMeta::new(aquva,false),
        AccountMeta::new_readonly(feecfg,false),AccountMeta::new_readonly(feep,false),AccountMeta::new_readonly(system_program::ID,false),
        AccountMeta::new_readonly(evauth,false),AccountMeta::new_readonly(pump,false)],&[],Some(bc6),&mut out);
    if let Some(a)=svm.get_account(&aqbc6){out.push(Step{name:"beq_v2_t22_curveq".into(),ok:true,err:String::new(),cu:0,snap:Some(a.data),logs:vec![]});}
    if let Some(a)=svm.get_account(&aqu6){out.push(Step{name:"beq_v2_t22_user".into(),ok:true,err:String::new(),cu:0,snap:Some(a.data),logs:vec![]});}
    // --- create_v2 (Mayhem full flow): is_mayhem_mode=true, SOL-quoted (no remaining accounts) ---
    let mayhem=Pubkey::from_str("MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e").unwrap();
    let t22c=Pubkey::from_str("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb").unwrap();
    let (m_gp,_)=Pubkey::find_program_address(&[b"global-params"],&mayhem);
    svm.set_account(m_gp,Account{lamports:3_104_160,data:mayhem_gp_bytes(),owner:mayhem,executable:false,rent_epoch:0}).unwrap();
    let mintv2=solana_sdk::signer::keypair::keypair_from_seed(&[0x5au8;32]).unwrap();
    let (bcv2c,_)=Pubkey::find_program_address(&[b"bonding-curve",mintv2.pubkey().as_ref()],&pump);
    let (abcv2,_)=Pubkey::find_program_address(&[bcv2c.as_ref(),t22c.as_ref(),mintv2.pubkey().as_ref()],&ata);
    let (m_solvault,_)=Pubkey::find_program_address(&[b"sol-vault"],&mayhem);
    let (m_state,_)=Pubkey::find_program_address(&[b"mayhem-state",mintv2.pubkey().as_ref()],&mayhem);
    let (m_tokvault,_)=Pubkey::find_program_address(&[m_solvault.as_ref(),t22c.as_ref(),mintv2.pubkey().as_ref()],&ata);
    let mut cv2=vec![214u8,144,76,236,95,139,49,180];
    cv2.extend(strb("M")); cv2.extend(strb("M")); cv2.extend(strb("u"));
    cv2.extend(user.pubkey().to_bytes());
    cv2.push(1); cv2.push(0); cv2.extend(u64le(0)); cv2.push(0);
    send(&mut svm,"create_v2",pump,cv2,vec![
        AccountMeta::new(mintv2.pubkey(),true),AccountMeta::new_readonly(mint_auth,false),
        AccountMeta::new(bcv2c,false),AccountMeta::new(abcv2,false),AccountMeta::new_readonly(global,false),
        AccountMeta::new(user.pubkey(),true),AccountMeta::new_readonly(system_program::ID,false),
        AccountMeta::new_readonly(t22c,false),AccountMeta::new_readonly(ata,false),
        AccountMeta::new(mayhem,false),AccountMeta::new_readonly(m_gp,false),AccountMeta::new(m_solvault,false),
        AccountMeta::new(m_state,false),AccountMeta::new(m_tokvault,false),
        AccountMeta::new_readonly(evauth,false),AccountMeta::new_readonly(pump,false)],&[&mintv2],Some(bcv2c),&mut out);
    if let Some(a)=svm.get_account(&m_state){out.push(Step{name:"create_v2_mstate".into(),ok:true,err:String::new(),cu:0,snap:Some(a.data),logs:vec![]});}
    if let Some(a)=svm.get_account(&bcv2c){out.push(Step{name:"create_v2_curve".into(),ok:true,err:String::new(),cu:0,snap:Some(a.data),logs:vec![]});}
    if let Some(a)=svm.get_account(&m_tokvault){out.push(Step{name:"create_v2_tokvault".into(),ok:true,err:String::new(),cu:0,snap:Some(a.data),logs:vec![]});}
    if let Some(a)=svm.get_account(&abcv2){out.push(Step{name:"create_v2_abc".into(),ok:true,err:String::new(),cu:0,snap:Some(a.data),logs:vec![]});}
    // --- migrate: graduate a COMPLETED native curve to PumpSwap (pump_amm CPI) ---
    let amm=Pubkey::from_str("pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA").unwrap();
    let t22=Pubkey::from_str("TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb").unwrap();
    if let Some(mut g)=svm.get_account(&bc){ g.data[48]=1; g.data[32..40].copy_from_slice(&85_000_000_000u64.to_le_bytes()); g.lamports=300_000_000_000; svm.set_account(bc,g).unwrap(); }
    let pool_auth=Pubkey::find_program_address(&[b"pool-authority",mint.pubkey().as_ref()],&pump).0;
    let pool=Pubkey::find_program_address(&[b"pool",&0u16.to_le_bytes(),pool_auth.as_ref(),mint.pubkey().as_ref(),wsol.as_ref()],&amm).0;
    let amm_cfg=Pubkey::find_program_address(&[b"global_config"],&amm).0;
    let lp_mint=Pubkey::find_program_address(&[b"pool_lp_mint",pool.as_ref()],&amm).0;
    let amm_ev=Pubkey::find_program_address(&[b"__event_authority"],&amm).0;
    let pa_mint_acct=Pubkey::find_program_address(&[pool_auth.as_ref(),token.as_ref(),mint.pubkey().as_ref()],&ata).0;
    let pa_wsol_acct=Pubkey::find_program_address(&[pool_auth.as_ref(),token.as_ref(),wsol.as_ref()],&ata).0;
    let user_pool_tok=Pubkey::find_program_address(&[pool_auth.as_ref(),t22.as_ref(),lp_mint.as_ref()],&ata).0;
    let pool_base=Pubkey::find_program_address(&[pool.as_ref(),token.as_ref(),mint.pubkey().as_ref()],&ata).0;
    let pool_quote=Pubkey::find_program_address(&[pool.as_ref(),token.as_ref(),wsol.as_ref()],&ata).0;
    // init_boost PDAs (migrate non-mayhem boost branch, 2 remaining accounts)
    let boost_auth=Pubkey::find_program_address(&[b"boost_vault",pool.as_ref()],&amm).0;
    let boost_vault=Pubkey::find_program_address(&[boost_auth.as_ref(),token.as_ref(),wsol.as_ref()],&ata).0;
    svm.set_account(amm_cfg, Account{lamports:9_272_823,data:amm_gc_bytes(),owner:amm,executable:false,rent_epoch:0}).unwrap();
    let mig=vec![155u8,234,231,146,236,158,162,30];
    send(&mut svm,"migrate",pump,mig,vec![
        AccountMeta::new_readonly(global,false),AccountMeta::new(user.pubkey(),false),AccountMeta::new_readonly(mint.pubkey(),false),
        AccountMeta::new(bc,false),AccountMeta::new(abc,false),AccountMeta::new(user.pubkey(),true),
        AccountMeta::new_readonly(system_program::ID,false),AccountMeta::new_readonly(token,false),AccountMeta::new_readonly(amm,false),
        AccountMeta::new(pool,false),AccountMeta::new(pool_auth,false),AccountMeta::new(pa_mint_acct,false),AccountMeta::new(pa_wsol_acct,false),
        AccountMeta::new_readonly(amm_cfg,false),AccountMeta::new_readonly(wsol,false),AccountMeta::new(lp_mint,false),
        AccountMeta::new(user_pool_tok,false),AccountMeta::new(pool_base,false),AccountMeta::new(pool_quote,false),
        AccountMeta::new_readonly(t22,false),AccountMeta::new_readonly(ata,false),AccountMeta::new_readonly(amm_ev,false),
        AccountMeta::new_readonly(evauth,false),AccountMeta::new_readonly(pump,false),AccountMeta::new_readonly(sysvar::rent::ID,false),AccountMeta::new_readonly(boost_auth,false),AccountMeta::new(boost_vault,false)],&[],Some(bc),&mut out);
    // --- migrate_v2: generalized graduation (base/quote mints). Native curve reuses migrate PDAs. ---
    let migv2=vec![187u8,203,18,31,206,237,254,41];
    send(&mut svm,"migrate_v2",pump,migv2,vec![
        AccountMeta::new_readonly(global,false),AccountMeta::new(user.pubkey(),false),AccountMeta::new_readonly(mint.pubkey(),false),
        AccountMeta::new_readonly(wsol,false),AccountMeta::new(bc,false),AccountMeta::new(abc,false),AccountMeta::new(qbc,false),
        AccountMeta::new(user.pubkey(),true),AccountMeta::new_readonly(system_program::ID,false),AccountMeta::new_readonly(amm,false),
        AccountMeta::new(pool,false),AccountMeta::new(pool_auth,false),AccountMeta::new(pa_mint_acct,false),AccountMeta::new(pa_wsol_acct,false),
        AccountMeta::new_readonly(amm_cfg,false),AccountMeta::new(lp_mint,false),AccountMeta::new(user_pool_tok,false),
        AccountMeta::new(pool_base,false),AccountMeta::new(pool_quote,false),
        AccountMeta::new_readonly(token,false),AccountMeta::new_readonly(token,false),AccountMeta::new_readonly(t22,false),AccountMeta::new_readonly(ata,false),
        AccountMeta::new_readonly(amm_ev,false),AccountMeta::new_readonly(sysvar::rent::ID,false),AccountMeta::new_readonly(evauth,false),AccountMeta::new_readonly(pump,false),AccountMeta::new_readonly(boost_auth,false),AccountMeta::new(boost_vault,false)],&[],Some(bc),&mut out);
    out
}
fn main(){
    let a:Vec<String>=std::env::args().collect();
    let o=run(&a[1]); let c=run(&a[2]); let mut all=true;
    for i in 0..o.len(){let sm=o[i].snap==c[i].snap; let okm=o[i].ok==c[i].ok; let em=o[i].err==c[i].err; if !(sm&&okm&&em){all=false;}
        println!("{:<16} ok:{}/{} state_match:{} cu:{}/{}{}",o[i].name,o[i].ok,c[i].ok,sm,o[i].cu,c[i].cu,
            if o[i].err.is_empty()&&c[i].err.is_empty(){String::new()}else{format!("  err o=[{}] c=[{}]",o[i].err,c[i].err)});}
    for i in 0..o.len(){ if o[i].snap!=c[i].snap { if let (Some(os),Some(cs))=(&o[i].snap,&c[i].snap){ eprintln!("DIFF {} olen={} clen={}",o[i].name,os.len(),cs.len()); for j in 0..os.len().min(cs.len()){ if os[j]!=cs[j]{eprintln!("  first diff @ +{}: o={:02x} c={:02x}",j,os[j],cs[j]); let s=j.saturating_sub(4); eprintln!("  o[{}..]: {}",s,os[s..(s+24).min(os.len())].iter().map(|b|format!("{:02x}",b)).collect::<String>()); eprintln!("  c[{}..]: {}",s,cs[s..(s+24).min(cs.len())].iter().map(|b|format!("{:02x}",b)).collect::<String>()); break;}}}}}
    if std::env::var("T22DUMP").is_ok(){for i in 0..o.len(){if o[i].name.starts_with("buy_v3_t22")||o[i].name.starts_with("sell_v3_t22")||o[i].name.starts_with("bexact_v3_t22")||o[i].name.starts_with("beq_v2_t22"){eprintln!("{} O {}",o[i].name,o[i].snap.as_ref().map(|d|d.iter().map(|b|format!("{:02x}",b)).collect::<String>()).unwrap_or_default());eprintln!("{} C {}",c[i].name,c[i].snap.as_ref().map(|d|d.iter().map(|b|format!("{:02x}",b)).collect::<String>()).unwrap_or_default());}}}
    if std::env::var("LOGS").is_ok(){for i in 0..o.len(){eprintln!("=== {} ORIG ===",o[i].name);for l in &o[i].logs{eprintln!("{}",l);}eprintln!("=== {} CLONE ===",c[i].name);for l in &c[i].logs{eprintln!("{}",l);}}}
    println!("\nLAUNCHPAD_FLOW_MATCH={}",all);
}
