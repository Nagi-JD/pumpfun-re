use crate::*;
#[path = "nested_create.rs"]
mod nested_create;
use anchor_spl::{token_interface::{self,Mint,TokenAccount},token_2022::Token2022,associated_token::AssociatedToken};
use anchor_lang::solana_program::{instruction::{Instruction,AccountMeta},program::invoke_signed};
pub const MAYHEM_ID:Pubkey=anchor_lang::solana_program::pubkey!("MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e");

// =============================================================================
// Mayhem create-v2 branch — binary-derived reconstruction
// -----------------------------------------------------------------------------
// Binary map (evidence/original/pump/deployed.so):
//   * create_v2 global handler        @0x24d15  (logs "Instruction: CreateV2",
//                                       21 bytes @ rodata 0x1b7d7b; disc d6904cec5f8b31b4)
//   * the `callx r2` @0x24d58 is NOT the body — it is tagged-pointer Drop glue on
//     the arg-deserialize error path (r8&0x3 tag dispatch -> [r8+7]->[r2+0]).
//   * Anchor try_accounts (account-context build) @0x158d9  (call @0x24dfd):
//     derives/validates the 5 Mayhem PDAs under MAYHEM_ID. It loads the Mayhem id
//     inline (immediates 0x24a7daa7d7e52a05 / 0x4c67601667a0d45a @0x15e0c.. =
//     the 32 id bytes) and the seeds "global-params"@0x1b753a, "sol-vault"@0x1b7547,
//     "mayhem-state"@0x1b7559; field names "sol_vault"/"mayhem_state"/
//     "mayhem_token_vault"/"global_params" @0x1b7550.. .
//   * create_v2::execute body          @0x3cf8..0x4492  (call 0x3cf8 @0x24e57).
//     Mayhem gate errors raised here:
//        6046 CreateV2Disabled               (stw 0x179e @0x3e44)
//        6048 MayhemModeDisabled             (stw 0x17a0 @0x41e5)
//        6071 MayhemModeQuoteMintNotAllowed  (stw 0x17b7 @0x414b)
//     6047 CpitializeMayhemFailed is NEVER a raw immediate anywhere in .text — it
//     wraps the InitializeMayhemState CPI *result* (map_err), hence modelled that way.
//
// Mayhem-init CPI:
//   * target program : MAYHEM_ID (MAyhSmz…MD4e, bytes verified @rodata 0x1b7aa7;
//     the `mayhem_program_id` account is address-constrained to it).
//   * target instruction : InitializeMayhemState — recovered from the Mayhem
//     program's log string "Instruction: InitializeMayhemStateInstruction"
//     (mayhem/deployed.so @712971). The error name "C(pi)tializeMayhemFailed"
//     corroborates a CPI-initialize.
//   * the body's only DIRECT invoke_signed (@0x431e) is emit_cpi! — proven by its
//     data discriminator e445a52e51cb9a1d ("anchor:event") + program_id =
//     pump's own id (6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P @0x1b79df) +
//     the "__event_authority" meta (@0x1b6807). So the Mayhem CPI itself is issued
//     from an indirect-dispatch helper (anchor CpiContext path), not inline.
//
// UNVERIFIED (flagged; could not be resolved statically in-budget):
//   (1) CPI selector/discriminator. No sha256("global:initialize_mayhem_state")
//       8-byte discriminator (9dbd5e485545cc2d) appears in EITHER binary, and every
//       Mayhem instruction name carries an "Instruction" suffix — i.e. the Mayhem
//       program is a custom (non-standard-Anchor) dispatcher whose selector is a
//       borsh instruction-enum tag, NOT an 8-byte Anchor hash. MAYHEM_INITIALIZE_STATE_SELECTOR
//       below is a PLACEHOLDER and must be replaced with the real Mayhem enum tag.
//   (2) exact CPI argument layout and account order/metas (helper is indirect-dispatch).
// VERIFIED and modelled below: program id, call site (is_mayhem_mode branch of
// execute 0x3cf8), the mint-authority PDA signer (shared with the sibling mint CPIs),
// and the failure mapping Err -> CpitializeMayhemFailed (6047).
// -----------------------------------------------------------------------------
// UNVERIFIED selector placeholder: Anchor sha256("global:initialize_mayhem_state")[..8].
// The real Mayhem program is non-Anchor; its true selector is a small borsh enum tag.
// Replace once the Mayhem dispatcher tag is recovered. (No CPI will succeed until then.)
const MAYHEM_INITIALIZE_STATE_SELECTOR:[u8;8]=[0x9d,0xbd,0x5e,0x48,0x55,0x45,0xcc,0x2d];
// =============================================================================

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
 #[account(init,payer=user,space=166,seeds=[b"bonding-curve",mint.key().as_ref()],bump)]pub bonding_curve:Account<'info,trade_types::BondingCurve>,
 #[account(init,payer=user,associated_token::mint=mint,associated_token::authority=bonding_curve,associated_token::token_program=token_program)]pub associated_bonding_curve:InterfaceAccount<'info,TokenAccount>,
 #[account(seeds=[b"global"],bump)]pub global:Box<Account<'info,Global>>,
 #[account(mut)]pub user:Signer<'info>,
 pub system_program:Program<'info,System>,
 pub token_program:Program<'info,Token2022>,
 pub associated_token_program:Program<'info,AssociatedToken>,
 /// CHECK: fixed Mayhem CPI program; address-constrained to MAYHEM_ID. Validated by Anchor try_accounts @0x158d9.
 #[account(mut,address=MAYHEM_ID)]pub mayhem_program_id:UncheckedAccount<'info>,
 /// CHECK: Mayhem PDA ["global-params"] under MAYHEM_ID (seed @rodata 0x1b753a). Unused on the non-mayhem path.
 #[account(seeds=[b"global-params"],bump,seeds::program=MAYHEM_ID)]pub global_params:UncheckedAccount<'info>,
 /// CHECK: Mayhem PDA ["sol-vault"] under MAYHEM_ID (seed @rodata 0x1b7547). Unused on the non-mayhem path.
 #[account(mut,seeds=[b"sol-vault"],bump,seeds::program=MAYHEM_ID)]pub sol_vault:UncheckedAccount<'info>,
 /// CHECK: Mayhem PDA ["mayhem-state", mint] under MAYHEM_ID (seed @rodata 0x1b7559). Unused on the non-mayhem path.
 #[account(mut,seeds=[b"mayhem-state",mint.key().as_ref()],bump,seeds::program=MAYHEM_ID)]pub mayhem_state:UncheckedAccount<'info>,
 /// CHECK: Mayhem token vault (field name @rodata 0x1b7571). Unused on the non-mayhem path.
 #[account(mut)]pub mayhem_token_vault:UncheckedAccount<'info>,
}
pub fn execute<'info>(ctx:Context<'_,'_,'_,'info,CreateV2<'info>>,name:String,symbol:String,uri:String,creator:Pubkey,is_mayhem_mode:bool,is_cashback_enabled:OptionBool,creator_fee_bps:CreationOptionU64,is_holder_reward:OptionBool)->Result<()>{
 let a=&ctx.accounts;
 require!(a.global.create_v2_enabled,PumpError::CreateV2Disabled);
 // ===== Mayhem-mode gate (binary body 0x3cf8; see header note) =====
 if is_mayhem_mode {
  // 6048 MayhemModeDisabled (stw 0x17a0 @0x41e5): mayhem must be globally enabled.
  require!(a.global.mayhem_mode_enabled,PumpError::MayhemModeDisabled);
  // 6071 MayhemModeQuoteMintNotAllowed (stw 0x17b7 @0x414b): mayhem coins are SOL-quoted
  // only — any non-default quote leg (remaining_accounts) is rejected. [INFERRED semantic]
  require!(ctx.remaining_accounts.is_empty(),PumpError::MayhemModeQuoteMintNotAllowed);
 }
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
 // ===== Mayhem state initialization CPI (into MAYHEM_ID; failure -> 6047 CpitializeMayhemFailed) =====
 // Target: InitializeMayhemState. Selector + arg layout + account order are UNVERIFIED (see header).
 if is_mayhem_mode {
  let mut mayhem_data:Vec<u8>=MAYHEM_INITIALIZE_STATE_SELECTOR.to_vec();
  // UNVERIFIED args — modelled from mayhem_state ["mayhem-state", mint] semantics.
  a.mint.key().serialize(&mut mayhem_data)?;
  creator.serialize(&mut mayhem_data)?;
  a.global.initial_virtual_token_reserves.serialize(&mut mayhem_data)?;
  virtual_quote_reserves.serialize(&mut mayhem_data)?;
  // UNVERIFIED account order/metas for the Mayhem CPI.
  let mayhem_ix=Instruction{
   program_id:a.mayhem_program_id.key(), // address-constrained to MAYHEM_ID
   accounts:vec![
    AccountMeta::new_readonly(a.global_params.key(),false),
    AccountMeta::new(a.sol_vault.key(),false),
    AccountMeta::new(a.mayhem_state.key(),false),
    AccountMeta::new(a.mayhem_token_vault.key(),false),
    AccountMeta::new(a.mint.key(),false),
    AccountMeta::new(a.bonding_curve.key(),false),
    AccountMeta::new(a.user.key(),true),
    AccountMeta::new_readonly(a.system_program.key(),false),
    AccountMeta::new_readonly(a.token_program.key(),false),
   ],
   data:mayhem_data,
  };
  invoke_signed(
   &mayhem_ix,
   &[
    a.mayhem_program_id.to_account_info(),
    a.global_params.to_account_info(),
    a.sol_vault.to_account_info(),
    a.mayhem_state.to_account_info(),
    a.mayhem_token_vault.to_account_info(),
    a.mint.to_account_info(),
    a.bonding_curve.to_account_info(),
    a.user.to_account_info(),
    a.system_program.to_account_info(),
    a.token_program.to_account_info(),
   ],
   &[seeds], // mint-authority PDA signer (b"mint-authority"), shared with the mint CPIs above
  ).map_err(|_|error!(PumpError::CpitializeMayhemFailed))?; // 6047 (CPI-result wrap; never a raw immediate in .text)
 }
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
