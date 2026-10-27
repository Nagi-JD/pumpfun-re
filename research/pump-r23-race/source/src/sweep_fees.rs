use anchor_lang::prelude::*;
use crate::{Global,PumpError};
use crate::trade_types::BondingCurve;
#[event_cpi]
#[derive(Accounts)]
pub struct SweepFees<'info>{
 #[account(mut)]pub payer:Signer<'info>,
 #[account(seeds=[b"global"],bump)]pub global:Box<Account<'info,Global>>,
 pub base_mint:Box<InterfaceAccount<'info,anchor_spl::token_interface::Mint>>,
 pub quote_mint:Box<InterfaceAccount<'info,anchor_spl::token_interface::Mint>>,
 pub quote_token_program:Interface<'info,anchor_spl::token_interface::TokenInterface>,
 pub associated_token_program:Program<'info,anchor_spl::associated_token::AssociatedToken>,
 pub system_program:Program<'info,System>,
 #[account(mut,seeds=[b"bonding-curve",base_mint.key().as_ref()],bump,constraint=quote_mint.key()==bonding_curve.quote_mint || (bonding_curve.quote_mint==Pubkey::default() && quote_mint.key()==anchor_spl::token::spl_token::native_mint::ID) @ PumpError::MintDoesNotMatchBondingCurve)]pub bonding_curve:Box<Account<'info,BondingCurve>>,
 /// CHECK: checked as token data only in the positive token branch.
 #[account(mut,seeds=[bonding_curve.key().as_ref(),quote_token_program.key().as_ref(),quote_mint.key().as_ref()],bump,seeds::program=anchor_spl::associated_token::ID)]pub associated_quote_bonding_curve:UncheckedAccount<'info>,
 /// CHECK: handler verifies fee recipient or creator vault.
 #[account(mut)]pub recipient:UncheckedAccount<'info>,
 /// CHECK: address checked; token branch creates or parses.
 #[account(mut,seeds=[recipient.key().as_ref(),quote_token_program.key().as_ref(),quote_mint.key().as_ref()],bump,seeds::program=anchor_spl::associated_token::ID)]pub associated_quote_recipient:UncheckedAccount<'info>,
}
#[event]
#[derive(Clone)]pub struct SweepBondingCurveFeeEvent{pub timestamp:i64,pub mint:Pubkey,pub bonding_curve:Pubkey,pub quote_mint:Pubkey,pub recipient:Pubkey,pub amount:u64,pub bucket:u8}
pub fn execute(ctx:Context<SweepFees>,creator:bool)->Result<()>{
 let a=&mut *ctx.accounts;
 crate::trade_types::prepare_bonding_curve(&a.bonding_curve,&a.system_program,&a.payer)?;
 let native=a.bonding_curve.quote_mint==Pubkey::default();let cf=a.bonding_curve.creator_fee;let pf=a.bonding_curve.protocol_fees;let info=a.bonding_curve.to_account_info();
 if creator{let expected=Pubkey::find_program_address(&[b"creator-vault",a.bonding_curve.creator.as_ref()],&crate::ID).0;require_keys_eq!(a.recipient.key(),expected,anchor_lang::error::ErrorCode::ConstraintSeeds);}
 else{crate::legacy_sell::fee_recipient::validate_fee_recipient(&a.recipient,&a.global,&a.bonding_curve)?;}
 let amount=if creator{cf}else{pf};if amount==0{return Ok(());}
 if native{a.bonding_curve.sub_lamports(amount)?;a.recipient.add_lamports(amount)?;}
 else{

  for (index,account) in [a.associated_quote_bonding_curve.to_account_info(),a.associated_quote_recipient.to_account_info()].into_iter().enumerate(){
  if index==1 && a.associated_quote_recipient.owner==&anchor_lang::system_program::ID{anchor_spl::associated_token::create_idempotent(CpiContext::new(a.associated_token_program.to_account_info(),anchor_spl::associated_token::Create{payer:a.payer.to_account_info(),associated_token:a.associated_quote_recipient.to_account_info(),authority:a.recipient.to_account_info(),mint:a.quote_mint.to_account_info(),system_program:a.system_program.to_account_info(),token_program:a.quote_token_program.to_account_info()}))?;}
   if account.owner==&anchor_lang::system_program::ID{return Err(error!(anchor_lang::error::ErrorCode::AccountNotInitialized));}
   if account.owner!=&anchor_spl::token::ID&&account.owner!=&anchor_spl::token_2022::ID{return Err(error!(anchor_lang::error::ErrorCode::AccountOwnedByWrongProgram));}
   let d=account.try_borrow_data()?;let token=anchor_spl::token_interface::TokenAccount::try_deserialize(&mut &d[..])?;require_keys_eq!(token.mint,a.quote_mint.key(),PumpError::MintDoesNotMatchBondingCurve);
  }
  let mint=a.base_mint.key();let bump=[ctx.bumps.bonding_curve];let seeds:&[&[u8]]=&[b"bonding-curve",mint.as_ref(),&bump];
  anchor_spl::token_interface::transfer_checked(CpiContext::new_with_signer(a.quote_token_program.to_account_info(),anchor_spl::token_interface::TransferChecked{from:a.associated_quote_bonding_curve.to_account_info(),mint:a.quote_mint.to_account_info(),to:a.associated_quote_recipient.to_account_info(),authority:info},&[seeds]),amount,a.quote_mint.decimals)?;
 }
 if creator{a.bonding_curve.creator_fee=0;}else{a.bonding_curve.protocol_fees=0;}
 let event=SweepBondingCurveFeeEvent{timestamp:Clock::get()?.unix_timestamp,mint:a.base_mint.key(),bonding_curve:a.bonding_curve.key(),quote_mint:a.bonding_curve.quote_mint,recipient:a.recipient.key(),amount,bucket:if creator{1}else{0}};emit!(event.clone());emit_cpi!(event);Ok(())
}

