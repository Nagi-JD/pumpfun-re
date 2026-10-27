use anchor_lang::prelude::*;
use crate::CollectCreatorFeeEvent;
#[event_cpi]
#[derive(Accounts)]
pub struct CollectCreatorFeeV2<'info>{
 /// CHECK: recipient only tied to vault/ATA seeds.
 #[account(mut)]pub creator:AccountInfo<'info>,
 /// CHECK: token program validates data only during positive token transfer.
 #[account(mut,seeds=[creator.key().as_ref(),quote_token_program.key().as_ref(),quote_mint.key().as_ref()],bump,seeds::program=associated_token_program.key())]pub creator_token_account:UncheckedAccount<'info>,
 /// CHECK: address constrained, native transfer defers owner/data checks.
 #[account(mut,seeds=[b"creator-vault",creator.key().as_ref()],bump)]pub creator_vault:AccountInfo<'info>,
 /// CHECK: address constrained, token program validates on transfer.
 #[account(mut,seeds=[creator_vault.key().as_ref(),quote_token_program.key().as_ref(),quote_mint.key().as_ref()],bump,seeds::program=associated_token_program.key())]pub creator_vault_token_account:UncheckedAccount<'info>,
 pub quote_mint:Box<InterfaceAccount<'info,anchor_spl::token_interface::Mint>>,
 pub quote_token_program:Interface<'info,anchor_spl::token_interface::TokenInterface>,
 pub associated_token_program:Program<'info,anchor_spl::associated_token::AssociatedToken>,
 pub system_program:Program<'info,System>,
}
pub fn execute(ctx:Context<CollectCreatorFeeV2>)->Result<()>{
 let a=&ctx.accounts;require!(*a.creator.owner!=crate::distribution::FEES,crate::PumpError::UnableToDistributeCreatorVaultMigratedToSharingConfig);if a.creator.executable{msg!("Creator account is executable, so it cannot receive lamports");return Ok(());}
 let native=a.quote_mint.key()==anchor_spl::token::spl_token::native_mint::ID;
 let amount=if native{
  let rent=Rent::get()?;
  let amount=a.creator_vault.lamports().saturating_sub(rent.minimum_balance(0));
  if amount>0 && a.creator.lamports().saturating_add(amount)<rent.minimum_balance(a.creator.data_len()){msg!("Creator account does not have enough rent-exemption lamports");return Ok(());}
  amount
 }else{
  let data=a.creator_vault_token_account.try_borrow_data()?;anchor_spl::token_interface::TokenAccount::try_deserialize(&mut &data[..])?.amount
 };
 if amount==0{msg!("No creator fee to collect");return Ok(());}
 let creator=a.creator.key();let bump=[ctx.bumps.creator_vault];let seeds:&[&[u8]]=&[b"creator-vault",creator.as_ref(),&bump];
 if native{anchor_lang::system_program::transfer(CpiContext::new_with_signer(a.system_program.to_account_info(),anchor_lang::system_program::Transfer{from:a.creator_vault.to_account_info(),to:a.creator.to_account_info()},&[seeds]),amount)?;}
 else{anchor_spl::token_interface::transfer_checked(CpiContext::new_with_signer(a.quote_token_program.to_account_info(),anchor_spl::token_interface::TransferChecked{from:a.creator_vault_token_account.to_account_info(),mint:a.quote_mint.to_account_info(),to:a.creator_token_account.to_account_info(),authority:a.creator_vault.to_account_info()},&[seeds]),amount,a.quote_mint.decimals)?;}
 let event=CollectCreatorFeeEvent{timestamp:Clock::get()?.unix_timestamp,creator,creator_fee:amount,quote_mint:if native{Pubkey::default()}else{a.quote_mint.key()}};emit!(event.clone());emit_cpi!(event);Ok(())
}
