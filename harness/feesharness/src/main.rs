// Differential harness for the pump_fees fee-query handlers (get_fees / get_fees_with_quote_mint).
//
// Runs the DEPLOYED pump_fees binary and the RECOVERED build side-by-side in LiteSVM on identical
// seeded state, invokes the two fee-query handlers that pump and pump_amm CPI into, and reports
// whether the serialized Fees RETURN DATA + ok/err + logs MATCH or DIVERGE byte-for-byte.
//
// Handler addresses (cited):
//   DEPLOYED  get_fees                 @0x136a0   get_fees_with_quote_mint @0x13763
//   RECOVERED get_fees                 @0xccb2    get_fees_with_quote_mint @0xccb6
//   DEPLOYED dispatcher @0x1240e; GetFeesWithQuoteMint arm matches disc u64 0xbba202a25c8aed9a
//     (bytes [154,237,138,92,162,2,162,187]) at insn 0x1245a.
//
// Account + arg layout reversed from the deployed binary, cross-checked with the upstream IDL
//   /mnt/d/dev/ext/pumpfun-source/evidence/upstream/pump_fees.json :
//   get_fees(fee_config: PDA[b"fee_config", config_program_id], config_program_id)
//     args: is_pump_pool:bool, market_cap_lamports:u128, trade_size_lamports:u64, is_new_quote_mint:OptionBool
//   get_fees_with_quote_mint(fee_config: PDA[b"fee_config", config_program_id], config_program_id)
//     args: is_pump_pool:bool, market_cap_lamports:u128, quote_mint:pubkey
//   The fee_config seed constant b"fee_config" lives in rodata at file offset 0xc3eb8.

use litesvm::LiteSVM;
use solana_sdk::{pubkey::Pubkey, signature::Signer, account::Account,
    instruction::{Instruction, AccountMeta}, transaction::Transaction};
use std::str::FromStr;

const PUMP:&str = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P";
const AMM:&str  = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA";
const FEEP:&str = "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ";
const WSOL:&str = "So11111111111111111111111111111111111111112";

// Anchor instruction discriminators (from pump_fees IDL / binary dispatcher).
const D_GET_FEES:[u8;8]      = [231,37,126,85,207,91,63,52];
const D_GET_FEES_QMINT:[u8;8]= [154,237,138,92,162,2,162,187];

struct Step{name:String, ok:bool, err:String, ret:Vec<u8>, logs:Vec<String>}

fn u64le(v:u64)->Vec<u8>{v.to_le_bytes().to_vec()}
fn u128le(v:u128)->Vec<u8>{v.to_le_bytes().to_vec()}

// Fees { lp_fee_bps, protocol_fee_bps, creator_fee_bps } — real mainnet values (0,95,30).
fn fees()->Vec<u8>{let mut v=u64le(0);v.extend(u64le(95));v.extend(u64le(30));v}

// Faithful replica of the live mainnet FeeConfig PDA (extended 4097-byte account).
// 8-byte disc, bump=253, real admin, flat_fees, 1 fee_tier (threshold 0), 1 stable_fee_tier,
// exotic_flat_fees, then zero-padded to 4097. Reused verbatim from the Pump harness so the
// GetFeesWithQuoteMint deserializer (which reads trailing fields present only in the extended
// account) does not under-run. Identical bytes seeded for every fee_config address.
fn feeconfig_bytes(bump:u8)->Vec<u8>{
    let admin:[u8;32]=[0xd3,0xbb,0x8c,0xab,0x34,0x1c,0xe0,0x52,0x84,0x57,0xf2,0xc3,0x81,0x7d,0x32,0x78,0x44,0x19,0x63,0xdc,0xd5,0x5f,0xed,0x58,0xba,0x24,0xc9,0x99,0xdd,0xac,0x02,0xaa];
    let mut d=vec![143,52,146,187,219,123,76,155u8];
    d.push(bump);
    d.extend_from_slice(&admin);
    d.extend(fees());                                                     // flat_fees
    d.extend(1u32.to_le_bytes()); d.extend(u128le(0)); d.extend(fees());  // fee_tiers[0]
    d.extend(1u32.to_le_bytes()); d.extend(u128le(0)); d.extend(fees());  // stable_fee_tiers[0]
    d.extend(fees());                                                     // exotic_flat_fees
    d.resize(4097,0);
    d
}

fn cu_logs(_l:&[String]){}

fn run(fees_so:&str)->Vec<Step>{
    let pump=Pubkey::from_str(PUMP).unwrap();
    let amm =Pubkey::from_str(AMM).unwrap();
    let feep=Pubkey::from_str(FEEP).unwrap();
    let wsol=Pubkey::from_str(WSOL).unwrap();

    let mut svm=LiteSVM::new();
    svm.add_program_from_file(feep,fees_so).unwrap();
    let user=solana_sdk::signer::keypair::keypair_from_seed(&[7u8;32]).unwrap();
    svm.airdrop(&user.pubkey(),1_000_000_000_000).unwrap();

    // The two canonical fee_config addresses. The fee program re-derives fee_config as
    // PDA[b"fee_config", config_program_id] inside its Anchor try_accounts; pump passes
    // config_program_id = pump_id, pump_amm passes config_program_id = amm_id.
    let (feecfg_pump,bump_pump)=Pubkey::find_program_address(&[b"fee_config",pump.as_ref()],&feep);
    let (feecfg_amm ,bump_amm )=Pubkey::find_program_address(&[b"fee_config",amm.as_ref()],&feep);
    eprintln!("CANONICAL_BUMP fee_config[pump]={} fee_config[amm]={}",bump_pump,bump_amm);
    // Seed each address with FeeConfig bytes whose STORED bump field = that address's own canonical
    // bump. The handler's Anchor constraint is seeds=[b"fee_config", config_program_id], bump =
    // fee_config.bump (stored-bump), so the stored bump must match the canonical bump of the address.
    svm.set_account(feecfg_pump, Account{lamports:37_292_293,data:feeconfig_bytes(bump_pump),owner:feep,executable:false,rent_epoch:0}).unwrap();
    svm.set_account(feecfg_amm , Account{lamports:37_292_293,data:feeconfig_bytes(bump_amm ),owner:feep,executable:false,rent_epoch:0}).unwrap();

    let mut out=vec![];
    let send=|svm:&mut LiteSVM, name:&str, data:Vec<u8>, metas:Vec<AccountMeta>, out:&mut Vec<Step>|{
        let ix=Instruction{program_id:feep,accounts:metas,data};
        let bh=svm.latest_blockhash();
        let cbud=Pubkey::from_str("ComputeBudget111111111111111111111111111111").unwrap();
        let mut cbd=vec![2u8]; cbd.extend_from_slice(&1_400_000u32.to_le_bytes());
        let cbix=Instruction{program_id:cbud,accounts:vec![],data:cbd};
        let tx=Transaction::new_signed_with_payer(&[cbix,ix],Some(&user.pubkey()),&[&user],bh);
        let st=match svm.send_transaction(tx){
            Ok(m)=>{cu_logs(&m.logs); Step{name:name.into(),ok:true,err:String::new(),ret:m.return_data.data.clone(),logs:m.logs.clone()}},
            Err(e)=>Step{name:name.into(),ok:false,err:format!("{:?}",e.err),ret:e.meta.return_data.data.clone(),logs:e.meta.logs.clone()},
        };
        out.push(st);
    };

    // Account meta builder: [fee_config (ro), config_program_id (ro)].
    let metas=|feecfg:Pubkey, cfg_prog:Pubkey| vec![
        AccountMeta::new_readonly(feecfg,false),
        AccountMeta::new_readonly(cfg_prog,false),
    ];

    // ---- get_fees_with_quote_mint: PUMP caller path (config_program_id = pump) ----
    // is_pump_pool=true, market_cap=0 (flat/tier[0]), quote_mint=WSOL
    let mut d=D_GET_FEES_QMINT.to_vec();
    d.push(1); d.extend(u128le(0)); d.extend(wsol.to_bytes());
    send(&mut svm,"gfq_pump",d,metas(feecfg_pump,pump),&mut out);

    // ---- get_fees_with_quote_mint: AMM caller path (config_program_id = amm) ----
    let mut d=D_GET_FEES_QMINT.to_vec();
    d.push(0); d.extend(u128le(0)); d.extend(wsol.to_bytes());
    send(&mut svm,"gfq_amm",d,metas(feecfg_amm,amm),&mut out);

    // ---- get_fees_with_quote_mint: AMM config but PUMP's fee_config account (seed-mismatch probe) ----
    // Determines whether the enforced seed binds fee_config to config_program_id (expect reject).
    let mut d=D_GET_FEES_QMINT.to_vec();
    d.push(0); d.extend(u128le(0)); d.extend(wsol.to_bytes());
    send(&mut svm,"gfq_amm_wrongseed",d,metas(feecfg_pump,amm),&mut out);

    // ---- get_fees_with_quote_mint: PUMP, nonzero market cap (exercise tier selection) ----
    let mut d=D_GET_FEES_QMINT.to_vec();
    d.push(1); d.extend(u128le(5_000_000_000_000)); d.extend(wsol.to_bytes());
    send(&mut svm,"gfq_pump_cap",d,metas(feecfg_pump,pump),&mut out);

    // ---- get_fees: PUMP caller path ----
    // is_pump_pool=true, market_cap=0, trade_size=1_000_000_000, is_new_quote_mint=OptionBool(false)
    let mut d=D_GET_FEES.to_vec();
    d.push(1); d.extend(u128le(0)); d.extend(u64le(1_000_000_000)); d.push(0);
    send(&mut svm,"gf_pump",d,metas(feecfg_pump,pump),&mut out);

    // ---- get_fees: AMM caller path ----
    let mut d=D_GET_FEES.to_vec();
    d.push(0); d.extend(u128le(0)); d.extend(u64le(1_000_000_000)); d.push(0);
    send(&mut svm,"gf_amm",d,metas(feecfg_amm,amm),&mut out);

    // ---- get_fees: PUMP, is_new_quote_mint=true, nonzero cap (exotic/new-quote branch + tier) ----
    let mut d=D_GET_FEES.to_vec();
    d.push(1); d.extend(u128le(5_000_000_000_000)); d.extend(u64le(1_000_000_000)); d.push(1);
    send(&mut svm,"gf_pump_newq",d,metas(feecfg_pump,pump),&mut out);

    // ---- get_fees: AMM config but PUMP's fee_config account (seed-mismatch probe) ----
    let mut d=D_GET_FEES.to_vec();
    d.push(0); d.extend(u128le(0)); d.extend(u64le(1_000_000_000)); d.push(0);
    send(&mut svm,"gf_amm_wrongseed",d,metas(feecfg_pump,amm),&mut out);

    // ---- stored-bump gate probe: correct PUMP address + fee_config account storing the WRONG bump
    // (amm's canonical bump). If the constraint were plain seeds-only this would still pass; if it is
    // seeds + bump=fee_config.bump it must reject with 2006. Re-seed, call, restore. ----
    svm.set_account(feecfg_pump, Account{lamports:37_292_293,data:feeconfig_bytes(bump_amm),owner:feep,executable:false,rent_epoch:0}).unwrap();
    let mut d=D_GET_FEES_QMINT.to_vec();
    d.push(1); d.extend(u128le(1)); d.extend(wsol.to_bytes()); // cap=1 keeps this tx distinct from gfq_pump
    send(&mut svm,"gfq_pump_badbump",d,metas(feecfg_pump,pump),&mut out);
    svm.set_account(feecfg_pump, Account{lamports:37_292_293,data:feeconfig_bytes(bump_pump),owner:feep,executable:false,rent_epoch:0}).unwrap();

    out
}

fn main(){
    let a:Vec<String>=std::env::args().collect();
    if a.len()<3 { eprintln!("usage: feesharness <deployed.so> <recovered.so>"); std::process::exit(2); }
    let o=run(&a[1]); let c=run(&a[2]);
    let mut all=true;
    for i in 0..o.len().min(c.len()){
        let rm = o[i].ret==c[i].ret;
        let okm= o[i].ok==c[i].ok;
        let em = o[i].err==c[i].err;
        if !(rm&&okm&&em){all=false;}
        let hx=|v:&Vec<u8>| if v.is_empty(){"<none>".to_string()} else {v.iter().map(|b|format!("{:02x}",b)).collect::<String>()};
        println!("{:<20} ok:{}/{} returndata_match:{} ret_d={} ret_r={}{}",
            o[i].name,o[i].ok,c[i].ok,rm,hx(&o[i].ret),hx(&c[i].ret),
            if o[i].err.is_empty()&&c[i].err.is_empty(){String::new()}
            else{format!("  err d=[{}] r=[{}]",o[i].err,c[i].err)});
    }
    // Decode the Fees return data for any matched, successful call (3 u64 LE = lp/protocol/creator bps).
    for i in 0..o.len().min(c.len()){
        if o[i].ok && o[i].ret.len()==24 {
            let g=|b:&[u8],n:usize| u64::from_le_bytes(b[n*8..n*8+8].try_into().unwrap());
            eprintln!("FEES {:<20} lp={} protocol={} creator={}",o[i].name,g(&o[i].ret,0),g(&o[i].ret,1),g(&o[i].ret,2));
        }
    }
    if std::env::var("LOGS").is_ok(){
        for i in 0..o.len().min(c.len()){
            eprintln!("=== {} DEPLOYED ok={} ===",o[i].name,o[i].ok); for l in &o[i].logs{eprintln!("{}",l);}
            eprintln!("=== {} RECOVERED ok={} ===",c[i].name,c[i].ok); for l in &c[i].logs{eprintln!("{}",l);}
        }
    }
    println!("\nFEES_MATCH={}",all);
}
