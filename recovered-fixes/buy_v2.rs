use anchor_lang::prelude::*;
use anchor_spl::token_interface::{self,Mint,TokenAccount,TokenInterface,TransferChecked};
use crate::{Global,PumpError};
use crate::trade_types::{TradeEvent,Fees};
use crate::legacy_sell::{LegacyCurve,LegacyFeeConfig,LegacyFeesProgram};
const FEE_PROGRAM:Pubkey=anchor_lang::solana_program::pubkey!("pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ");
const WSOL:Pubkey=anchor_lang::solana_program::pubkey!("So11111111111111111111111111111111111111112");
#[derive(Accounts)]
pub struct BuyV2<'info>{
 #[account(seeds=[b"global"],bump)]pub global:Box<Account<'info,Global>>,
 pub base_mint:Box<InterfaceAccount<'info,Mint>>,
 pub quote_mint:Box<InterfaceAccount<'info,Mint>>,
 pub base_token_program:Interface<'info,TokenInterface>,
 pub quote_token_program:Interface<'info,TokenInterface>,
 pub associated_token_program:Program<'info,anchor_spl::associated_token::AssociatedToken>,
 /// CHECK: handler checks membership.
 #[account(mut)]pub fee_recipient:UncheckedAccount<'info>,
 /// CHECK: quote ATA.
 #[account(mut,seeds=[fee_recipient.key().as_ref(),quote_token_program.key().as_ref(),quote_mint.key().as_ref()],bump,seeds::program=associated_token_program.key())]pub associated_quote_fee_recipient:UncheckedAccount<'info>,
 /// CHECK: handler checks membership.
 #[account(mut)]pub buyback_fee_recipient:UncheckedAccount<'info>,
 /// CHECK: quote ATA.
 #[account(mut,seeds=[buyback_fee_recipient.key().as_ref(),quote_token_program.key().as_ref(),quote_mint.key().as_ref()],bump,seeds::program=associated_token_program.key())]pub associated_quote_buyback_fee_recipient:UncheckedAccount<'info>,
 #[account(mut,seeds=[b"bonding-curve",base_mint.key().as_ref()],bump,constraint=quote_mint.key()==if bonding_curve.quote_mint==Pubkey::default(){WSOL}else{bonding_curve.quote_mint} @ PumpError::UnsupportedQuoteMint)]pub bonding_curve:Box<Account<'info,LegacyCurve>>,
 #[account(mut,associated_token::mint=base_mint,associated_token::authority=bonding_curve,associated_token::token_program=base_token_program)]pub associated_base_bonding_curve:Box<InterfaceAccount<'info,TokenAccount>>,
 /// CHECK: quote ATA.
 #[account(mut,seeds=[bonding_curve.key().as_ref(),quote_token_program.key().as_ref(),quote_mint.key().as_ref()],bump,seeds::program=associated_token_program.key())]pub associated_quote_bonding_curve:UncheckedAccount<'info>,
 #[account(mut)]pub user:Signer<'info>,
 #[account(mut,token::mint=base_mint,token::authority=user,token::token_program=base_token_program)]pub associated_base_user:Box<InterfaceAccount<'info,TokenAccount>>,
 /// CHECK: quote ATA.
 #[account(mut)]pub associated_quote_user:UncheckedAccount<'info>,
 /// CHECK: PDA.
 #[account(mut,seeds=[b"creator-vault",bonding_curve.creator.as_ref()],bump)]pub creator_vault:UncheckedAccount<'info>,
 /// CHECK: quote ATA.
 #[account(mut,seeds=[creator_vault.key().as_ref(),quote_token_program.key().as_ref(),quote_mint.key().as_ref()],bump,seeds::program=associated_token_program.key())]pub associated_creator_vault:UncheckedAccount<'info>,
 /// CHECK: sharing validation later.
 #[account(seeds=[b"sharing-config",base_mint.key().as_ref()],bump,seeds::program=FEE_PROGRAM)]pub sharing_config:UncheckedAccount<'info>,
 #[account(seeds=[b"global_volume_accumulator"],bump)]pub global_volume_accumulator:Box<Account<'info,crate::GlobalVolumeAccumulator>>,
 /// CHECK: volume state validated when used.
 #[account(init_if_needed,payer=user,space=137,seeds=[b"user_volume_accumulator",user.key().as_ref()],bump)]pub user_volume_accumulator:Box<Account<'info,crate::UserVolumeAccumulator>>,
 /// CHECK: quote ATA.
 #[account(mut,seeds=[user_volume_accumulator.key().as_ref(),quote_token_program.key().as_ref(),quote_mint.key().as_ref()],bump,seeds::program=associated_token_program.key())]pub associated_user_volume_accumulator:UncheckedAccount<'info>,
 #[account(seeds=[b"fee_config",crate::ID.as_ref()],bump,seeds::program=FEE_PROGRAM)]pub fee_config:Account<'info,LegacyFeeConfig>,
 pub fee_program:Program<'info,LegacyFeesProgram>,
 pub system_program:Program<'info,System>,
 /// CHECK: event PDA.
 #[account(seeds=[b"__event_authority"],bump)]pub event_authority:AccountInfo<'info>,
 pub program:Program<'info,crate::program::PumpRecovered>,
}
fn add(a:u64,b:u64)->Result<u64>{a.checked_add(b).ok_or_else(||error!(PumpError::Overflow))}
fn sub(a:u64,b:u64)->Result<u64>{a.checked_sub(b).ok_or_else(||error!(PumpError::Overflow))}
fn narrow(a:u128)->Result<u64>{u64::try_from(a).map_err(|_|error!(PumpError::Truncation))}
pub fn execute<'info>(ctx:Context<'_,'_,'_,'info,BuyV2<'info>>,input:u64,limit:u64,partial:bool,exact:bool)->Result<()>{
 let a=&mut *ctx.accounts;
 if a.user_volume_accumulator.user==Pubkey::default(){a.user_volume_accumulator.user=a.user.key();}
 if a.bonding_curve.quote_mint!=Pubkey::default(){
  require!(a.associated_quote_bonding_curve.owner!=&anchor_lang::system_program::ID,anchor_lang::error::ErrorCode::AccountNotInitialized);
  check_token(&a.associated_quote_bonding_curve,a.quote_mint.key(),a.bonding_curve.key())?;
  require!(a.associated_quote_user.owner!=&anchor_lang::system_program::ID,PumpError::AccountTypeNotSupported);
  check_token(&a.associated_quote_user,a.quote_mint.key(),a.user.key())?;{let d=a.associated_quote_user.try_borrow_data()?;let t=TokenAccount::try_deserialize(&mut &d[..])?;require!(t.owner==a.user.key(),PumpError::AccountTypeNotSupported);}
  for (destination,authority) in [(a.associated_quote_fee_recipient.to_account_info(),a.fee_recipient.to_account_info()),(a.associated_quote_buyback_fee_recipient.to_account_info(),a.buyback_fee_recipient.to_account_info()),(a.associated_creator_vault.to_account_info(),a.creator_vault.to_account_info()),(a.associated_user_volume_accumulator.to_account_info(),a.user_volume_accumulator.to_account_info())]{
   if destination.owner==&anchor_lang::system_program::ID{anchor_spl::associated_token::create_idempotent(CpiContext::new(a.associated_token_program.to_account_info(),anchor_spl::associated_token::Create{payer:a.user.to_account_info(),associated_token:destination.clone(),authority:authority.clone(),mint:a.quote_mint.to_account_info(),system_program:a.system_program.to_account_info(),token_program:a.quote_token_program.to_account_info()}))?;}
   check_token(&destination,a.quote_mint.key(),authority.key())?;
  }
 }




 let c=&a.bonding_curve;let native=c.quote_mint==Pubkey::default();
 require!(if c.is_mayhem_mode{a.fee_recipient.key()==a.global.reserved_fee_recipient||a.global.reserved_fee_recipients.contains(&a.fee_recipient.key())}else{a.fee_recipient.key()==a.global.fee_recipient||a.global.fee_recipients.contains(&a.fee_recipient.key())},PumpError::NotAuthorized);
 require!(!c.complete,PumpError::BondingCurveComplete);
 if exact{require!(limit>0,PumpError::BuyZeroAmount);require!(input>0,PumpError::BuyNotEnoughSolToCoverFees);}else{require!(input>0,PumpError::BuyZeroAmount);}
 if !exact{require!(input<=c.real_token_reserves||partial,PumpError::NotEnoughTokensToBuy);}
 let cap=c.token_total_supply as u128*c.virtual_quote_reserves as u128/c.virtual_token_reserves as u128;
 let mut data=vec![154,237,138,92,162,2,162,187,1];data.extend_from_slice(&cap.to_le_bytes());data.extend_from_slice(c.quote_mint.as_ref());
 let ix=anchor_lang::solana_program::instruction::Instruction{program_id:FEE_PROGRAM,accounts:vec![anchor_lang::solana_program::instruction::AccountMeta::new_readonly(a.fee_config.key(),false),anchor_lang::solana_program::instruction::AccountMeta::new_readonly(crate::ID,false)],data};
 anchor_lang::solana_program::program::invoke(&ix,&[a.fee_config.to_account_info(),a.program.to_account_info(),a.fee_program.to_account_info()])?;
 let (_,ret)=anchor_lang::solana_program::program::get_return_data().unwrap();let mut fees=Fees::deserialize(&mut ret.as_slice())?;if c.creator_fee_bps>0{fees.creator_fee_bps=c.creator_fee_bps;}
 let cb=if c.creator==Pubkey::default(){0}else{fees.creator_fee_bps};
 let raw_quote=if exact{let _=ceil_fee(input,fees.protocol_fee_bps)?;let _=ceil_fee(input,cb)?;let total_bps=add(fees.protocol_fee_bps,cb)?;let denominator=10000u128+total_bps as u128;narrow(input as u128*10000/denominator)?}else{0};
 let adjusted=if exact && add(add(raw_quote,ceil_fee(raw_quote,fees.protocol_fee_bps)?)?,ceil_fee(raw_quote,cb)?)?>input{sub(raw_quote,1)?}else{raw_quote};
 let computed=if exact{require!(raw_quote>0,PumpError::BuyNotEnoughSolToCoverFees);let e=adjusted.saturating_sub(1);narrow(c.virtual_token_reserves as u128*e as u128/(c.virtual_quote_reserves as u128+e as u128))?}else{input};
 require!(computed<=c.real_token_reserves||partial,PumpError::NotEnoughTokensToBuy);let amount=computed.min(c.real_token_reserves);
 let quote=if exact && computed<=c.real_token_reserves{adjusted}else{add(narrow(amount as u128*c.virtual_quote_reserves as u128/(c.virtual_token_reserves as u128-amount as u128))?,1)?};
 let fq=if exact && computed<=c.real_token_reserves{raw_quote}else{quote};let pf=ceil_fee(fq,fees.protocol_fee_bps)?;let cf=ceil_fee(fq,cb)?;
 if exact{require!((partial && computed>c.real_token_reserves)||amount>=limit,PumpError::BuySlippageBelowMinTokensOut);}else{require!(add(add(quote,pf)?,cf)?<=limit,PumpError::TooMuchSolRequired);}
 // Token-2022 net-accounting: in v2 the pool deposit leg carries exactly `quote` (protocol/
 // creator/buyback fees go to SEPARATE recipient ATAs), so the curve ATA receives `quote` MINUS
 // the quote mint's transfer fee. Credit the pool with that net so reserves are not over-stated
 // vs the ATA balance (deployed buy_v2 body @0x27737 applies amount_after_fee @0x12a1c to the one
 // curve quote leg). Native (SOL) legs have no transfer fee: credit the gross `quote`.
 let credited_quote=if native{quote}else{crate::util::transfer_fee::amount_after_fee(&a.quote_mint.to_account_info(),quote)?};
 let vb=sub(c.virtual_token_reserves,amount)?;let vq=add(c.virtual_quote_reserves,credited_quote)?;let rb=sub(c.real_token_reserves,amount)?;let rq=add(c.real_quote_reserves,credited_quote)?;
 let mint=a.base_mint.key();let bump=[ctx.bumps.bonding_curve];let seeds:&[&[u8]]=&[b"bonding-curve",mint.as_ref(),&bump];
 token_interface::transfer_checked(CpiContext::new_with_signer(a.base_token_program.to_account_info(),TransferChecked{from:a.associated_base_bonding_curve.to_account_info(),mint:a.base_mint.to_account_info(),to:a.associated_base_user.to_account_info(),authority:a.bonding_curve.to_account_info()},&[seeds]),amount,a.base_mint.decimals)?;
 let bb=&a.buyback_fee_recipient;require!(a.global.buyback_fee_recipients.contains(bb.key),PumpError::BuybackFeeRecipientNotAuthorized);
 let bbps=if c.is_mayhem_mode{0}else{a.global.buyback_basis_points};let bf=narrow(pf as u128*bbps as u128/10000)?;
 let shareholders={let d=a.sharing_config.try_borrow_data()?;crate::SharingConfig::try_deserialize(&mut &d[..]).map(|s|s.shareholders).unwrap_or_default()};
 let ev=TradeEvent{mint:a.base_mint.key(),sol_amount:if native{quote}else{0},token_amount:amount,is_buy:true,user:a.user.key(),timestamp:Clock::get()?.unix_timestamp,virtual_sol_reserves:if native{vq}else{0},virtual_token_reserves:vb,real_sol_reserves:if native{rq}else{0},real_token_reserves:rb,fee_recipient:a.fee_recipient.key(),fee_basis_points:fees.protocol_fee_bps,fee:pf,creator:c.creator,creator_fee_basis_points:if c.is_cashback_coin{0}else{fees.creator_fee_bps},creator_fee:if c.is_cashback_coin{0}else{cf},track_volume:false,total_unclaimed_tokens:a.user_volume_accumulator.total_unclaimed_tokens,total_claimed_tokens:a.user_volume_accumulator.total_claimed_tokens,current_sol_volume:a.user_volume_accumulator.current_sol_volume,last_update_timestamp:a.user_volume_accumulator.last_update_timestamp,ix_name:if exact{"buy_exact_quote_in".into()}else{"buy".into()},mayhem_mode:c.is_mayhem_mode,cashback_fee_basis_points:if c.is_cashback_coin{cb}else{0},cashback:if c.is_cashback_coin{cf}else{0},buyback_fee_basis_points:bbps,buyback_fee:bf,shareholders,quote_mint:c.quote_mint,quote_amount:quote,virtual_quote_reserves:vq,real_quote_reserves:rq,holder_rewards_bps:if c.is_holder_reward{cb}else{0},holder_rewards:if c.is_holder_reward{cf}else{0},creator_fee_unclaimed:c.creator_fee,unparsed_trailing_field:0};
 let cashback_coin=c.is_cashback_coin;
 if native{
 let creator_destination=if cashback_coin{a.user_volume_accumulator.to_account_info()}else{a.creator_vault.to_account_info()};
 for (to,n) in [(creator_destination,cf),(a.bonding_curve.to_account_info(),quote),(a.fee_recipient.to_account_info(),sub(pf,bf)?),(bb.to_account_info(),bf)]{if n>0{anchor_lang::system_program::transfer(CpiContext::new(a.system_program.to_account_info(),anchor_lang::system_program::Transfer{from:a.user.to_account_info(),to}),n)?;}}
 if cashback_coin{a.user_volume_accumulator.cashback_earned=add(a.user_volume_accumulator.cashback_earned,cf)?;}
 }else{
 for (to,n) in [(if cashback_coin{a.associated_user_volume_accumulator.to_account_info()}else{a.associated_creator_vault.to_account_info()},cf),(a.associated_quote_bonding_curve.to_account_info(),quote),(a.associated_quote_fee_recipient.to_account_info(),sub(pf,bf)?),(a.associated_quote_buyback_fee_recipient.to_account_info(),bf)]{if n>0{token_interface::transfer_checked(CpiContext::new(a.quote_token_program.to_account_info(),TransferChecked{from:a.associated_quote_user.to_account_info(),mint:a.quote_mint.to_account_info(),to,authority:a.user.to_account_info()}),n,a.quote_mint.decimals)?;}}
 if cashback_coin{a.user_volume_accumulator.stable_cashback_earned=add(a.user_volume_accumulator.stable_cashback_earned,cf)?;}
 }
 let c=&mut a.bonding_curve;c.virtual_token_reserves=vb;c.virtual_quote_reserves=vq;c.real_token_reserves=rb;c.real_quote_reserves=rq;
 let complete=if rb==0{c.complete=true;Some(crate::trade_types::CompleteEvent{user:a.user.key(),mint:a.base_mint.key(),bonding_curve:a.bonding_curve.key(),timestamp:Clock::get()?.unix_timestamp,quote_mint:ev.quote_mint})}else{None};
 emit!(ev.clone());emit_cpi!(ev);if let Some(event)=complete{emit!(event.clone());emit_cpi!(event);}
 let a=&mut *ctx.accounts;
 {let info=a.bonding_curve.to_account_info();let reserve=if a.bonding_curve.quote_mint==Pubkey::default(){add(add(a.bonding_curve.real_quote_reserves,a.bonding_curve.creator_fee)?,a.bonding_curve.protocol_fees)?}else{0};let target=add(Rent::get()?.minimum_balance(info.data_len().max(166)),reserve)?;let deficit=target.saturating_sub(info.lamports());if deficit>0{anchor_lang::system_program::transfer(CpiContext::new(a.system_program.to_account_info(),anchor_lang::system_program::Transfer{from:a.user.to_account_info(),to:info.clone()}),deficit)?;}if info.data_len()<166{info.realloc(166,false)?;a.bonding_curve.1=166;}}
Ok(())
}
fn ceil_fee(q:u64,b:u64)->Result<u64>{narrow((q as u128*b as u128+9999)/10000)}

fn check_token(info:&AccountInfo,mint:Pubkey,owner:Pubkey)->Result<()>{let d=info.try_borrow_data()?;let t=TokenAccount::try_deserialize(&mut &d[..])?;require!(t.mint==mint,PumpError::MintDoesNotMatchBondingCurve);let _=owner;Ok(())}
