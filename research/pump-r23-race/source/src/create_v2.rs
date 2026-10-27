use crate::*;
use spl_type_length_value::variable_len_pack::VariableLenPack;
#[path = "nested_create.rs"]
mod nested_create;
use anchor_spl::{token_interface::{self,Mint,TokenAccount},token_2022::Token2022,associated_token::AssociatedToken};
use anchor_lang::solana_program::{instruction::{Instruction,AccountMeta},program::invoke_signed};
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
 #[account(init,payer=user,associated_token::mint=mint,associated_token::authority=bonding_curve,associated_token::token_program=token_program)]pub associated_bonding_curve:Box<InterfaceAccount<'info,TokenAccount>>,
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
 let a=&ctx.accounts;
 require_eq!(a.global.create_v2_enabled,true,PumpError::CreateV2Disabled);
 require!(!is_cashback_enabled.0,PumpError::CashbackDeprecated);
 // Mayhem-mode gate: requires the admin flag and rejects any quote-mint remaining accounts.
 if is_mayhem_mode {
  require!(a.global.mayhem_mode_enabled,PumpError::MayhemModeDisabled);
  require!(ctx.remaining_accounts.is_empty(),PumpError::MayhemModeQuoteMintNotAllowed);
 }
 let creator=if is_holder_reward.0 {require!(a.global.is_holder_reward_enabled,PumpError::HolderRewardDisabled);Pubkey::find_program_address(&[b"holder-rewards",a.mint.key().as_ref()],&crate::ID).0}else{creator};
 require_keys_neq!(creator,Pubkey::default(),PumpError::CreatorShouldNotBeZero);
 let mut depth=0u8;
 let (quote_mint,virtual_quote_reserves,can_configure_fee)=if ctx.remaining_accounts.is_empty(){(Pubkey::default(),a.global.initial_virtual_sol_reserves,false)}else{
  require_gte!(ctx.remaining_accounts.len(),3,PumpError::NotEnoughRemainingAccounts);
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
   require_keys_eq!(control.key(),expected,PumpError::InvalidQuoteControl);
   require_keys_eq!(*control.owner,crate::ID,PumpError::InvalidQuoteControl);
   let entry={let data=control.try_borrow_data()?;nested_create::control_entry(&data,mint.key)?};
   if let Some(reserves)=entry {(reserves,true)} else {
    let (reserves,nested_depth)=nested_create::walk(&a.global,ctx.remaining_accounts)?;
    depth=nested_depth;
    (reserves,true)
   }
  };
  require_keys_eq!(*mint.owner,program.key(),PumpError::UnsupportedQuoteMint);
  if program.key()==anchor_spl::token_2022::ID {require!(quote_extensions_supported(&mint.try_borrow_data()?),PumpError::UnsupportedQuoteMint);}

  let expected=anchor_spl::associated_token::get_associated_token_address_with_program_id(&a.bonding_curve.key(),mint.key,program.key);
  require_keys_eq!(ata.key(),expected,PumpError::InvalidAssociatedQuoteBondingCurve);
  anchor_spl::associated_token::create(CpiContext::new(a.associated_token_program.to_account_info(),anchor_spl::associated_token::Create{payer:a.user.to_account_info(),associated_token:ata.clone(),authority:a.bonding_curve.to_account_info(),mint:mint.clone(),system_program:a.system_program.to_account_info(),token_program:program.clone()}))?;
  (mint.key(),reserves,can_configure)
  }
 };
 let fee=if can_configure_fee && creator_fee_bps.0>0 {
  require!(a.global.creator_fee_configurable,PumpError::CreatorFeeNotConfigurable);
  require!(creator_fee_bps.0<=a.global.max_configurable_creator_fee_bps,PumpError::CreatorFeeBpsOutOfRange);
  creator_fee_bps.0
 }else{0};
 require_gte!(32,name.len(),PumpError::NameTooLong);require_gte!(13,symbol.len(),PumpError::SymbolTooLong);require_gte!(200,uri.len(),PumpError::UriTooLong);
 let bump=[ctx.bumps.mint_authority];let seeds:&[&[u8]]=&[b"mint-authority",&bump];
 let metadata=anchor_spl::token_2022_extensions::spl_token_metadata_interface::state::TokenMetadata{
  name:name.clone(),symbol:symbol.clone(),uri:uri.clone(),..Default::default()
 };
 let rent_sysvar=Rent::get()?;
 let mint_info=a.mint.to_account_info();
 let base_size=mint_info.data_len().checked_add(4).ok_or_else(|| error!(PumpError::Overflow))?;
 let metadata_size=metadata.get_packed_len()?;
 let size=base_size.checked_add(metadata_size).ok_or_else(|| error!(PumpError::Overflow))?;
 let rent=rent_sysvar.minimum_balance(size).saturating_sub(mint_info.lamports());
 if rent>0 {anchor_lang::system_program::transfer(CpiContext::new(a.system_program.to_account_info(),anchor_lang::system_program::Transfer{from:a.user.to_account_info(),to:a.mint.to_account_info()}),rent)?;}
 anchor_spl::token_2022_extensions::token_metadata_initialize(
  CpiContext::new_with_signer(a.token_program.to_account_info(),anchor_spl::token_2022_extensions::TokenMetadataInitialize{
   program_id:a.token_program.to_account_info(),metadata:a.mint.to_account_info(),update_authority:a.mint_authority.to_account_info(),mint_authority:a.mint_authority.to_account_info(),mint:a.mint.to_account_info(),
  },&[seeds]),name.clone(),symbol.clone(),uri.clone(),
 )?;
 let new_authority:anchor_spl::token_2022_extensions::spl_pod::optional_keys::OptionalNonZeroPubkey=None::<Pubkey>.try_into()?;
 anchor_spl::token_2022_extensions::token_metadata_update_authority(
  CpiContext::new_with_signer(a.token_program.to_account_info(),anchor_spl::token_2022_extensions::TokenMetadataUpdateAuthority{
   program_id:a.token_program.to_account_info(),metadata:a.mint.to_account_info(),current_authority:a.mint_authority.to_account_info(),new_authority:a.system_program.to_account_info(),
  },&[seeds]),new_authority,
 )?;
 // Mayhem-creation CPI: pump signs the ["mint-authority"] PDA into mayhem's
 // initialize_mayhem_state (disc 0x2dcc4555485ebd9d, no args). Mayhem derives the
 // mint from account #4, derives/inits mayhem_state["mayhem-state",mint] and the
 // sol-vault token vault, and sets end_timestamp=now+reset_middle[0]*3600.
 if is_mayhem_mode {
  let mdata=vec![157u8,189,94,72,85,69,204,45];
  let mix=Instruction{program_id:MAYHEM_ID,accounts:vec![AccountMeta::new(a.user.key(),true),AccountMeta::new_readonly(a.global_params.key(),false),AccountMeta::new_readonly(a.mint_authority.key(),true),AccountMeta::new(a.sol_vault.key(),false),AccountMeta::new_readonly(a.mint.key(),false),AccountMeta::new(a.mayhem_token_vault.key(),false),AccountMeta::new(a.mayhem_state.key(),false),AccountMeta::new_readonly(a.system_program.key(),false),AccountMeta::new_readonly(a.token_program.key(),false),AccountMeta::new_readonly(a.associated_token_program.key(),false)],data:mdata};
  invoke_signed(&mix,&[a.user.to_account_info(),a.global_params.to_account_info(),a.mint_authority.to_account_info(),a.sol_vault.to_account_info(),a.mint.to_account_info(),a.mayhem_token_vault.to_account_info(),a.mayhem_state.to_account_info(),a.system_program.to_account_info(),a.token_program.to_account_info(),a.associated_token_program.to_account_info()],&[seeds])?;
 }
 token_interface::mint_to(CpiContext::new_with_signer(a.token_program.to_account_info(),token_interface::MintTo{mint:a.mint.to_account_info(),to:a.associated_bonding_curve.to_account_info(),authority:a.mint_authority.to_account_info()},&[seeds]),a.global.token_total_supply)?;
 if is_mayhem_mode {
  // Mayhem mints the full supply to the sol-vault token vault as well.
  token_interface::mint_to(CpiContext::new_with_signer(a.token_program.to_account_info(),token_interface::MintTo{mint:a.mint.to_account_info(),to:a.mayhem_token_vault.to_account_info(),authority:a.mint_authority.to_account_info()},&[seeds]),a.global.token_total_supply)?;
 }
 token_interface::set_authority(CpiContext::new_with_signer(a.token_program.to_account_info(),token_interface::SetAuthority{current_authority:a.mint_authority.to_account_info(),account_or_mint:a.mint.to_account_info()},&[seeds]),token_interface::spl_token_2022::instruction::AuthorityType::MintTokens,None)?;
 let event=CreateEvent{name,symbol,uri,mint:a.mint.key(),bonding_curve:a.bonding_curve.key(),user:a.user.key(),creator,timestamp:Clock::get()?.unix_timestamp,virtual_token_reserves:a.global.initial_virtual_token_reserves,virtual_sol_reserves:virtual_quote_reserves,real_token_reserves:a.global.initial_real_token_reserves,token_total_supply:a.global.token_total_supply,token_program:a.token_program.key(),is_mayhem_mode,is_cashback_enabled:false,quote_mint,virtual_quote_reserves,creator_fee_bps:fee,is_holder_reward:is_holder_reward.0,depth};
 let g=&ctx.accounts.global;let curve=&mut ctx.accounts.bonding_curve;curve.virtual_token_reserves=g.initial_virtual_token_reserves;curve.virtual_quote_reserves=virtual_quote_reserves;curve.real_token_reserves=g.initial_real_token_reserves;curve.token_total_supply=g.token_total_supply;curve.creator=creator;curve.creator_fee_bps=fee;curve.is_holder_reward=is_holder_reward.0;curve.quote_mint=quote_mint;curve.initial_virtual_quote_reserves=virtual_quote_reserves;curve.depth=depth;curve.is_mayhem_mode=is_mayhem_mode;
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

