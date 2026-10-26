//! create_v2.rs — Mayhem-branch reconstruction (replaces the ReconstructionBranchUnsupported stub).
//! Binary-pinned flow (pump create_v2 body, sites cited in create_v2_mayhem.md): gates CreateV2Disabled
//! (0x3e44)/MayhemModeDisabled(0x41e5) -> metadata init+update_authority -> mint_to #1 -> associated_bonding_curve
//! -> mayhem_token_vault ATA create -> init CPI @0x4267 initialize_mayhem_state (disc-only 8-byte 9dbd5e485545cc2d,
//! 10 accounts, order B) -> mint_to #2 @0x4274(->0x3910) mayhem_token_vault -> SetAuthority revoke @0x42a4
//! -> curve + CreateEvent{is_mayhem_mode:true}. VERIFIED: e2e differential create_v2(is_mayhem_mode=true),
//! deployed pump+mayhem vs recovered -> ALL accounts byte-identical incl. inner MayhemState (3d933eda). F2+F3 SEALED.
//! Note: bonding_curve boxed to clear a v1.52 CreateV2::try_accounts stack overflow (order/behavior-preserving).

use crate::*;
#[path = "nested_create.rs"]
mod nested_create;
use anchor_spl::{token_interface::{self,Mint,TokenAccount},token_2022::Token2022,associated_token::AssociatedToken};
use anchor_lang::solana_program::{instruction::{Instruction,AccountMeta},program::{invoke,invoke_signed}};
pub const MAYHEM_ID:Pubkey=anchor_lang::solana_program::pubkey!("MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e");
#[derive(AnchorSerialize,Clone)]
pub struct CreationOptionU64(pub u64);
impl AnchorDeserialize for CreationOptionU64 {
 fn deserialize_reader<R:std::io::Read>(reader:&mut R)->std::io::Result<Self>{let mut bytes=[0;8];match reader.read_exact(&mut bytes){Ok(())=>Ok(Self(u64::from_le_bytes(bytes))),Err(e) if e.kind()==std::io::ErrorKind::UnexpectedEof=>Ok(Self(0)),Err(e)=>Err(e)}}
}
#[event_cpi]
#[derive(Accounts)]
pub struct CreateV2<'info>{
 #[account(init,payer=user,mint::decimals=6,mint::authority=mint_authority,mint::token_program=token_program,extensions::metadata_pointer::metadata_address=mint)]
 pub mint:InterfaceAccount<'info,Mint>,
 /// CHECK: canonical mint authority.
 #[account(seeds=[b"mint-authority"],bump)]pub mint_authority:UncheckedAccount<'info>,
 #[account(init,payer=user,space=166,seeds=[b"bonding-curve",mint.key().as_ref()],bump)]pub bonding_curve:Box<Account<'info,trade_types::BondingCurve>>,
 #[account(init,payer=user,associated_token::mint=mint,associated_token::authority=bonding_curve,associated_token::token_program=token_program)]pub associated_bonding_curve:InterfaceAccount<'info,TokenAccount>,
 #[account(seeds=[b"global"],bump)]pub global:Box<Account<'info,Global>>,
 #[account(mut)]pub user:Signer<'info>,
 pub system_program:Program<'info,System>,
 pub token_program:Program<'info,Token2022>,
 pub associated_token_program:Program<'info,AssociatedToken>,
 /// CHECK: fixed CPI program; Mayhem invocation outside this bounded branch.
 #[account(mut,address=MAYHEM_ID)]pub mayhem_program_id:UncheckedAccount<'info>,
 /// CHECK: canonical Mayhem account, unused for normal creation.
 #[account(seeds=[b"global-params"],bump,seeds::program=MAYHEM_ID)]pub global_params:UncheckedAccount<'info>,
 /// CHECK: canonical Mayhem account, unused for normal creation.
 #[account(mut,seeds=[b"sol-vault"],bump,seeds::program=MAYHEM_ID)]pub sol_vault:UncheckedAccount<'info>,
 /// CHECK: canonical Mayhem account, unused for normal creation.
 #[account(mut,seeds=[b"mayhem-state",mint.key().as_ref()],bump,seeds::program=MAYHEM_ID)]pub mayhem_state:UncheckedAccount<'info>,
 /// CHECK: unused for normal creation.
 #[account(mut)]pub mayhem_token_vault:UncheckedAccount<'info>,
}
pub fn execute<'info>(ctx:Context<'_,'_,'_,'info,CreateV2<'info>>,name:String,symbol:String,uri:String,creator:Pubkey,is_mayhem_mode:bool,is_cashback_enabled:OptionBool,creator_fee_bps:CreationOptionU64,is_holder_reward:OptionBool)->Result<()>{
 // Other quote and Mayhem branches remain explicitly outside this reconstruction checkpoint.

 // === Mayhem branch reconstructed from the deployed create_v2 body (0x3cf8..0x4492).
 // init CPI @0x4267 -> initialize_mayhem_state, 2nd mint_to @0x4274, revoke/event @0x42a4. ===
 if is_mayhem_mode {
  let a=&ctx.accounts;
  require!(a.global.create_v2_enabled,PumpError::CreateV2Disabled);          // 0x3e44
  require!(a.global.mayhem_mode_enabled,PumpError::MayhemModeDisabled);      // 0x41e5
  require!(!is_cashback_enabled.0,PumpError::CashbackDeprecated);
  let creator=if is_holder_reward.0 {require!(a.global.is_holder_reward_enabled,PumpError::HolderRewardDisabled);Pubkey::find_program_address(&[b"holder-rewards",a.mint.key().as_ref()],&crate::ID).0}else{creator};
  require!(creator!=Pubkey::default(),PumpError::CreatorShouldNotBeZero);
  // Mayhem mode uses the native quote; a non-native quote is rejected (0x414b).
  require!(ctx.remaining_accounts.is_empty(),PumpError::MayhemModeQuoteMintNotAllowed);
  require!(name.len()<=32,PumpError::NameTooLong);require!(symbol.len()<=13,PumpError::SymbolTooLong);require!(uri.len()<=200,PumpError::UriTooLong);
  let bump=[ctx.bumps.mint_authority];let seeds:&[&[u8]]=&[b"mint-authority",&bump];
  let size=234+4+64+16+name.len()+symbol.len()+uri.len();
  let rent=Rent::get()?.minimum_balance(size).saturating_sub(a.mint.to_account_info().lamports());
  if rent>0 {anchor_lang::system_program::transfer(CpiContext::new(a.system_program.to_account_info(),anchor_lang::system_program::Transfer{from:a.user.to_account_info(),to:a.mint.to_account_info()}),rent)?;}
  // token_metadata_initialize
  let mut data=vec![210,225,30,162,88,184,77,141];name.serialize(&mut data)?;symbol.serialize(&mut data)?;uri.serialize(&mut data)?;
  let ix=Instruction{program_id:a.token_program.key(),accounts:vec![AccountMeta::new(a.mint.key(),false),AccountMeta::new_readonly(a.mint_authority.key(),false),AccountMeta::new_readonly(a.mint.key(),false),AccountMeta::new_readonly(a.mint_authority.key(),true)],data};
  invoke_signed(&ix,&[a.mint.to_account_info(),a.mint_authority.to_account_info(),a.mint.to_account_info(),a.mint_authority.to_account_info(),a.token_program.to_account_info()],&[seeds])?;
  // token_metadata_update_authority (clear)
  let mut data=vec![215,228,166,228,84,100,86,123];data.extend_from_slice(&[0;32]);
  let ix=Instruction{program_id:a.token_program.key(),accounts:vec![AccountMeta::new(a.mint.key(),false),AccountMeta::new_readonly(a.mint_authority.key(),true)],data};
  invoke_signed(&ix,&[a.mint.to_account_info(),a.mint_authority.to_account_info(),a.token_program.to_account_info()],&[seeds])?;
  // mint_to #1 -> associated_bonding_curve
  token_interface::mint_to(CpiContext::new_with_signer(a.token_program.to_account_info(),token_interface::MintTo{mint:a.mint.to_account_info(),to:a.associated_bonding_curve.to_account_info(),authority:a.mint_authority.to_account_info()},&[seeds]),a.global.token_total_supply)?;
  // create mayhem_token_vault ATA (authority = sol_vault); the deployed init creates it in-CPI.
  anchor_spl::associated_token::create(CpiContext::new(a.associated_token_program.to_account_info(),anchor_spl::associated_token::Create{payer:a.user.to_account_info(),associated_token:a.mayhem_token_vault.to_account_info(),authority:a.sol_vault.to_account_info(),mint:a.mint.to_account_info(),system_program:a.system_program.to_account_info(),token_program:a.token_program.to_account_info()}))?;
  // initialize_mayhem_state CPI: disc-only 8-byte payload (builder 0x23181), 10 accounts.
  let metas=vec![
   AccountMeta::new(a.user.key(),true),
   AccountMeta::new_readonly(a.global_params.key(),false),
   AccountMeta::new_readonly(a.mint.key(),false),
   AccountMeta::new(a.mayhem_state.key(),false),
   AccountMeta::new(a.mayhem_token_vault.key(),false),
   AccountMeta::new(a.sol_vault.key(),false),
   AccountMeta::new_readonly(a.bonding_curve.key(),false),
   AccountMeta::new_readonly(a.system_program.key(),false),
   AccountMeta::new_readonly(a.token_program.key(),false),
   AccountMeta::new_readonly(a.associated_token_program.key(),false),
  ];
  let ix=Instruction{program_id:MAYHEM_ID,accounts:metas,data:vec![0x9d,0xbd,0x5e,0x48,0x55,0x45,0xcc,0x2d]};
  invoke(&ix,&[a.user.to_account_info(),a.global_params.to_account_info(),a.mint.to_account_info(),a.mayhem_state.to_account_info(),a.mayhem_token_vault.to_account_info(),a.sol_vault.to_account_info(),a.bonding_curve.to_account_info(),a.system_program.to_account_info(),a.token_program.to_account_info(),a.associated_token_program.to_account_info(),a.mayhem_program_id.to_account_info()]).map_err(|_|error!(PumpError::CpitializeMayhemFailed))?;
  // mint_to #2 -> mayhem_token_vault (same amount, mint-authority signer), before revoke.
  token_interface::mint_to(CpiContext::new_with_signer(a.token_program.to_account_info(),token_interface::MintTo{mint:a.mint.to_account_info(),to:a.mayhem_token_vault.to_account_info(),authority:a.mint_authority.to_account_info()},&[seeds]),a.global.token_total_supply)?;
  // revoke mint authority
  token_interface::set_authority(CpiContext::new_with_signer(a.token_program.to_account_info(),token_interface::SetAuthority{current_authority:a.mint_authority.to_account_info(),account_or_mint:a.mint.to_account_info()},&[seeds]),token_interface::spl_token_2022::instruction::AuthorityType::MintTokens,None)?;
  // write curve + CreateEvent{is_mayhem_mode:true}
  let event=CreateEvent{name,symbol,uri,mint:a.mint.key(),bonding_curve:a.bonding_curve.key(),user:a.user.key(),creator,timestamp:Clock::get()?.unix_timestamp,virtual_token_reserves:a.global.initial_virtual_token_reserves,virtual_sol_reserves:a.global.initial_virtual_sol_reserves,real_token_reserves:a.global.initial_real_token_reserves,token_total_supply:a.global.token_total_supply,token_program:a.token_program.key(),is_mayhem_mode:true,is_cashback_enabled:false,quote_mint:Pubkey::default(),virtual_quote_reserves:a.global.initial_virtual_sol_reserves,creator_fee_bps:0,is_holder_reward:is_holder_reward.0,depth:0};
  let g=&ctx.accounts.global;let curve=&mut ctx.accounts.bonding_curve;curve.virtual_token_reserves=g.initial_virtual_token_reserves;curve.virtual_quote_reserves=g.initial_virtual_sol_reserves;curve.real_token_reserves=g.initial_real_token_reserves;curve.token_total_supply=g.token_total_supply;curve.creator=creator;curve.is_mayhem_mode=true;curve.quote_mint=Pubkey::default();curve.initial_virtual_quote_reserves=g.initial_virtual_sol_reserves;curve.depth=0;
  emit!(event.clone());emit_cpi!(event);
  return Ok(());
 }
 let a=&ctx.accounts;
 require!(a.global.create_v2_enabled,PumpError::CreateV2Disabled);
 require!(!is_cashback_enabled.0,PumpError::CashbackDeprecated);
 let creator=if is_holder_reward.0 {require!(a.global.is_holder_reward_enabled,PumpError::HolderRewardDisabled);Pubkey::find_program_address(&[b"holder-rewards",a.mint.key().as_ref()],&crate::ID).0}else{creator};
 require!(creator!=Pubkey::default(),PumpError::CreatorShouldNotBeZero);
 let mut depth=0u8;
 let (quote_mint,virtual_quote_reserves,can_configure_fee)=if ctx.remaining_accounts.is_empty(){(Pubkey::default(),a.global.initial_virtual_sol_reserves,false)}else{
  require!(ctx.remaining_accounts.len()>=3,PumpError::NotEnoughRemainingAccounts);
  let mint=&ctx.remaining_accounts[0];let ata=&ctx.remaining_accounts[1];let program=&ctx.remaining_accounts[2];
  require!(program.key()==anchor_spl::token::ID || program.key()==anchor_spl::token_2022::ID,PumpError::InvalidQuoteTokenProgram);
  require!(program.executable,PumpError::InvalidQuoteTokenProgram);
  if mint.key()==Pubkey::default() || mint.key()==anchor_spl::token::spl_token::native_mint::id() {
   (Pubkey::default(),a.global.initial_virtual_sol_reserves,false)
  } else {
  // Literal key rejection at 0x1f6a8, before whitelist/control selection.
  require!(mint.key()!=anchor_lang::solana_program::pubkey!("9pan9bMn5HatX4EJdBwg9VgCa7Uz5HL8N1m5D3NdXejP"),PumpError::UnsupportedQuoteMint);
  let (reserves,can_configure)=if a.global.whitelisted_quote_mints.contains(mint.key){(a.global.initial_virtual_quote_reserves,false)}else{
   require!(ctx.remaining_accounts.len()>=4,PumpError::UnsupportedQuoteMint);
   let control=&ctx.remaining_accounts[3];let expected=Pubkey::find_program_address(&[b"quote-control"],&crate::ID).0;
   require!(control.key()==expected && control.owner==&crate::ID,PumpError::InvalidQuoteControl);
   let entry={let data=control.try_borrow_data()?;nested_create::control_entry(&data,mint.key)?};
   if let Some(reserves)=entry {(reserves,true)} else {
    let (reserves,nested_depth)=nested_create::walk(&a.global,ctx.remaining_accounts)?;
    depth=nested_depth;
    (reserves,true)
   }
  };
  require!(mint.owner==program.key,PumpError::UnsupportedQuoteMint);
  if program.key()==anchor_spl::token_2022::ID {require!(quote_extensions_supported(&mint.try_borrow_data()?),PumpError::UnsupportedQuoteMint);}

  let expected=anchor_spl::associated_token::get_associated_token_address_with_program_id(&a.bonding_curve.key(),mint.key,program.key);
  require!(ata.key()==expected,PumpError::InvalidAssociatedQuoteBondingCurve);
  anchor_spl::associated_token::create(CpiContext::new(a.associated_token_program.to_account_info(),anchor_spl::associated_token::Create{payer:a.user.to_account_info(),associated_token:ata.clone(),authority:a.bonding_curve.to_account_info(),mint:mint.clone(),system_program:a.system_program.to_account_info(),token_program:program.clone()}))?;
  (mint.key(),reserves,can_configure)
  }
 };
 let fee=if can_configure_fee && creator_fee_bps.0>0 {
  require!(a.global.creator_fee_configurable,PumpError::CreatorFeeNotConfigurable);
  require!(creator_fee_bps.0<=a.global.max_configurable_creator_fee_bps,PumpError::CreatorFeeBpsOutOfRange);
  creator_fee_bps.0
 }else{0};
 require!(name.len()<=32,PumpError::NameTooLong);require!(symbol.len()<=13,PumpError::SymbolTooLong);require!(uri.len()<=200,PumpError::UriTooLong);
 let bump=[ctx.bumps.mint_authority];let seeds:&[&[u8]]=&[b"mint-authority",&bump];
 let size=234+4+64+16+name.len()+symbol.len()+uri.len();
 let rent=Rent::get()?.minimum_balance(size).saturating_sub(a.mint.to_account_info().lamports());
 if rent>0 {anchor_lang::system_program::transfer(CpiContext::new(a.system_program.to_account_info(),anchor_lang::system_program::Transfer{from:a.user.to_account_info(),to:a.mint.to_account_info()}),rent)?;}
 let mut data=vec![210,225,30,162,88,184,77,141];name.serialize(&mut data)?;symbol.serialize(&mut data)?;uri.serialize(&mut data)?;
 let ix=Instruction{program_id:a.token_program.key(),accounts:vec![AccountMeta::new(a.mint.key(),false),AccountMeta::new_readonly(a.mint_authority.key(),false),AccountMeta::new_readonly(a.mint.key(),false),AccountMeta::new_readonly(a.mint_authority.key(),true)],data};
 invoke_signed(&ix,&[a.mint.to_account_info(),a.mint_authority.to_account_info(),a.mint.to_account_info(),a.mint_authority.to_account_info(),a.token_program.to_account_info()],&[seeds])?;
 let mut data=vec![215,228,166,228,84,100,86,123];data.extend_from_slice(&[0;32]);
 let ix=Instruction{program_id:a.token_program.key(),accounts:vec![AccountMeta::new(a.mint.key(),false),AccountMeta::new_readonly(a.mint_authority.key(),true)],data};
 invoke_signed(&ix,&[a.mint.to_account_info(),a.mint_authority.to_account_info(),a.token_program.to_account_info()],&[seeds])?;
 token_interface::mint_to(CpiContext::new_with_signer(a.token_program.to_account_info(),token_interface::MintTo{mint:a.mint.to_account_info(),to:a.associated_bonding_curve.to_account_info(),authority:a.mint_authority.to_account_info()},&[seeds]),a.global.token_total_supply)?;
 token_interface::set_authority(CpiContext::new_with_signer(a.token_program.to_account_info(),token_interface::SetAuthority{current_authority:a.mint_authority.to_account_info(),account_or_mint:a.mint.to_account_info()},&[seeds]),token_interface::spl_token_2022::instruction::AuthorityType::MintTokens,None)?;
 let event=CreateEvent{name,symbol,uri,mint:a.mint.key(),bonding_curve:a.bonding_curve.key(),user:a.user.key(),creator,timestamp:Clock::get()?.unix_timestamp,virtual_token_reserves:a.global.initial_virtual_token_reserves,virtual_sol_reserves:virtual_quote_reserves,real_token_reserves:a.global.initial_real_token_reserves,token_total_supply:a.global.token_total_supply,token_program:a.token_program.key(),is_mayhem_mode:false,is_cashback_enabled:false,quote_mint,virtual_quote_reserves,creator_fee_bps:fee,is_holder_reward:is_holder_reward.0,depth};
 let g=&ctx.accounts.global;let curve=&mut ctx.accounts.bonding_curve;curve.virtual_token_reserves=g.initial_virtual_token_reserves;curve.virtual_quote_reserves=virtual_quote_reserves;curve.real_token_reserves=g.initial_real_token_reserves;curve.token_total_supply=g.token_total_supply;curve.creator=creator;curve.creator_fee_bps=fee;curve.is_holder_reward=is_holder_reward.0;curve.quote_mint=quote_mint;curve.initial_virtual_quote_reserves=virtual_quote_reserves;curve.depth=depth;
 emit!(event.clone());emit_cpi!(event);Ok(())
}

// The captured program accepts transfer-fee config as well as the operable
// metadata/delegate extensions; official IDL prose omits that observed case.
fn quote_extensions_supported(data:&[u8])->bool {
 if data.len()==82{return true;}
 if data.len()<166 || data.len()==355 || data[165]!=1{return false;}
 let mut at=166;
 while at<data.len(){
  if at+2>data.len(){return false;}let kind=u16::from_le_bytes([data[at],data[at+1]]);
  if kind==0{return true;}if at+4>data.len(){return false;}let size=u16::from_le_bytes([data[at+2],data[at+3]]) as usize;at+=4;
  if at+size>data.len(){return false;}let bytes=&data[at..at+size];
  match kind{4|12|16|18|19|25|26=>{},1=>if bytes.len()<108{return false;},6=>if bytes.is_empty() || bytes[0]!=1{return false;},14=>if bytes.len()<64 || bytes[32..64]!=[0;32]{return false;},_=>return false}
  at+=size;
 }
 true
}

