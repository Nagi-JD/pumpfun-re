use anchor_lang::prelude::*;
use anchor_spl::token_interface::{self, Mint, TokenAccount, TokenInterface, TransferChecked};
use crate::{Global, PumpError};
use crate::trade_types::{BondingCurve, FeeConfig, Fees, TradeEvent};
const FEE_PROGRAM: Pubkey = anchor_lang::solana_program::pubkey!("pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ");
const WSOL: Pubkey = anchor_lang::solana_program::pubkey!("So11111111111111111111111111111111111111112");
#[event_cpi]
#[derive(Accounts)]
pub struct SellV3<'info> {
    #[account(seeds=[b"global"],bump)]
    pub global: Box<Account<'info, Global>>,
    pub base_mint: Box<InterfaceAccount<'info, Mint>>,
    /// CHECK: recovered SOL/whitelisted-token quote checks validate this account.
    pub quote_mint: UncheckedAccount<'info>,
    pub base_token_program: Interface<'info, TokenInterface>,
    pub quote_token_program: Interface<'info, TokenInterface>,
    #[account(mut,seeds=[b"bonding-curve",base_mint.key().as_ref()],bump)]
    pub bonding_curve: Box<Account<'info, BondingCurve>>,
    #[account(mut,associated_token::mint=base_mint,associated_token::authority=bonding_curve,associated_token::token_program=base_token_program)]
    pub associated_base_bonding_curve: InterfaceAccount<'info, TokenAccount>,
    /// CHECK: token-quote checks validate owner, mint and relevant authority/address.
    #[account(mut)]
    pub associated_quote_bonding_curve: UncheckedAccount<'info>,
    #[account(mut)]
    pub user: Signer<'info>,
    #[account(mut,token::mint=base_mint,token::authority=user,token::token_program=base_token_program)]
    pub associated_base_user: InterfaceAccount<'info, TokenAccount>,
    /// CHECK: token-quote checks validate owner, mint and relevant authority/address.
    #[account(mut)]
    pub associated_quote_user: UncheckedAccount<'info>,
    /// CHECK: v3 rejects cashback; tested paths do not update volume accumulation.
    #[account(mut,seeds=[b"user_volume_accumulator",user.key().as_ref()],bump)]
    pub user_volume_accumulator: UncheckedAccount<'info>,
    /// CHECK: cross-program FeeConfig owner, address and serialization checked.
    #[account(owner=FEE_PROGRAM @ anchor_lang::error::ErrorCode::AccountOwnedByWrongProgram,seeds=[b"fee_config",crate::ID.as_ref()],bump,seeds::program=FEE_PROGRAM)]
    pub fee_config: UncheckedAccount<'info>,
    /// CHECK: membership in global buyback recipients is checked in handler.
    #[account(mut)]
    pub buyback_fee_recipient: UncheckedAccount<'info>,
    pub system_program: Program<'info, System>,
}
fn add(a:u64,b:u64)->Result<u64>{a.checked_add(b).ok_or_else(||error!(PumpError::Overflow))}
fn sub(a:u64,b:u64)->Result<u64>{a.checked_sub(b).ok_or_else(||error!(PumpError::Overflow))}
fn narrow(a:u128)->Result<u64>{u64::try_from(a).map_err(|_|error!(PumpError::Truncation))}
fn fee(a:u64,b:u64)->Result<u64>{narrow((a as u128*b as u128+9999)/10000)}
fn selected(config:&FeeConfig,cap:u128,stable:bool)->Fees{
    let tiers=if stable{&config.stable_fee_tiers}else{&config.fee_tiers};
    if cap<tiers[0].market_cap_lamports_threshold{return tiers[0].fees.clone()}
    tiers.iter().rev().find(|t|t.market_cap_lamports_threshold<=cap).unwrap_or(&tiers[0]).fees.clone()
}
pub fn sell(ctx:Context<SellV3>,amount:u64,min_sol_output:u64)->Result<()> {
    let a=&mut *ctx.accounts;
    crate::trade_types::prepare_bonding_curve(&a.bonding_curve, &a.system_program, &a.user)?;
    let quote_decimals=check_quote(a)?;
    let is_sol=quote_decimals.is_none();
    require!(!a.bonding_curve.is_cashback_coin,PumpError::CashbackCoinNotSupported);
    require!(!a.bonding_curve.complete,PumpError::BondingCurveComplete);
    require!(amount>0,PumpError::SellZeroAmount);
    require!(a.associated_base_user.amount>=amount,PumpError::NotEnoughTokensToSell);
    if is_sol{require!(a.global.buyback_fee_recipients.contains(&a.buyback_fee_recipient.key()),PumpError::BuybackFeeRecipientNotAuthorized);}
    let curve=&a.bonding_curve;
    let quote=narrow(amount as u128*curve.virtual_quote_reserves as u128/(curve.virtual_token_reserves as u128+amount as u128))?;
    let cap=curve.token_total_supply as u128*curve.virtual_quote_reserves as u128/curve.virtual_token_reserves as u128;
    let config_data=a.fee_config.try_borrow_data()?;
    let config=read_config(&config_data)?;
    drop(config_data);
    require!(!(if is_sol{&config.fee_tiers}else{&config.stable_fee_tiers}).is_empty(),PumpError::FeeTiersEmpty);
    let mut fees=selected(&config,cap,!is_sol);
    if curve.creator_fee_bps>0{fees.creator_fee_bps=curve.creator_fee_bps;}
    let creator_bps=if curve.creator==Pubkey::default(){0}else{fees.creator_fee_bps};
    let protocol_fee=fee(quote,fees.protocol_fee_bps)?;
    let creator_fee=fee(quote,creator_bps)?;
    let buyback_bps=if curve.is_mayhem_mode {0}else{a.global.buyback_basis_points};
    let buyback_fee=narrow(protocol_fee as u128*buyback_bps as u128/10000)?;
    let user_output=sub(sub(quote,protocol_fee)?,creator_fee)?;
    // Token-2022 net-accounting: the slippage bound is checked against what the user ACTUALLY
    // RECEIVES after the quote mint's transfer fee. The deployed sell body @0x29515 feeds the
    // output through amount_after_fee (@0x12a1c: net = amount - calculate_fee, via epoch_fee_params
    // @0x12921) and compares the NET against min_sol_output. Native (SOL) legs have no fee.
    let net_user_output=match quote_decimals{Some(_)=>crate::util::transfer_fee::amount_after_fee(&a.quote_mint.to_account_info(),user_output)?,None=>user_output};
    require!(net_user_output>=min_sol_output,PumpError::TooLittleSolReceived);
    let retained=sub(protocol_fee,buyback_fee)?;
    let next_base=add(curve.virtual_token_reserves,amount)?;
    let next_quote=sub(curve.virtual_quote_reserves,quote)?;
    let next_real_base=add(curve.real_token_reserves,amount)?;
    let next_real_quote=sub(curve.real_quote_reserves,quote)?;
    let next_creator=add(curve.creator_fee,creator_fee)?;
    let next_protocol=add(curve.protocol_fees,retained)?;
    token_interface::transfer_checked(CpiContext::new(a.base_token_program.to_account_info(),TransferChecked{
        from:a.associated_base_user.to_account_info(),mint:a.base_mint.to_account_info(),to:a.associated_base_bonding_curve.to_account_info(),authority:a.user.to_account_info()
    }),amount,a.base_mint.decimals)?;
    if let Some(decimals)=quote_decimals {
      let mint_key=a.base_mint.key();let bump=[ctx.bumps.bonding_curve];let seeds:&[&[u8]]=&[b"bonding-curve",mint_key.as_ref(),&bump];
      for (to,amount) in [(a.associated_quote_user.to_account_info(),user_output),(a.buyback_fee_recipient.to_account_info(),buyback_fee)] {
        if amount==0{continue}
        token_interface::transfer_checked(CpiContext::new_with_signer(a.quote_token_program.to_account_info(),TransferChecked{from:a.associated_quote_bonding_curve.to_account_info(),mint:a.quote_mint.to_account_info(),to,authority:a.bonding_curve.to_account_info()},&[seeds]),amount,decimals)?;
      }
    }else{
      a.bonding_curve.sub_lamports(add(user_output,buyback_fee)?)?;
      a.user.add_lamports(user_output)?;a.buyback_fee_recipient.add_lamports(buyback_fee)?;
    }
    let curve=&mut a.bonding_curve;
    curve.virtual_token_reserves=next_base;curve.virtual_quote_reserves=next_quote;
    curve.real_token_reserves=next_real_base;curve.real_quote_reserves=next_real_quote;
    curve.creator_fee=next_creator;curve.protocol_fees=next_protocol;
    let event=TradeEvent{
        mint:a.base_mint.key(),sol_amount:if is_sol{quote}else{0},token_amount:amount,is_buy:false,user:a.user.key(),timestamp:Clock::get()?.unix_timestamp,
        virtual_sol_reserves:if is_sol{next_quote}else{0},virtual_token_reserves:next_base,real_sol_reserves:if is_sol{next_real_quote}else{0},real_token_reserves:next_real_base,
        fee_recipient:Pubkey::default(),fee_basis_points:fees.protocol_fee_bps,fee:protocol_fee,creator:curve.creator,creator_fee_basis_points:fees.creator_fee_bps,creator_fee,
        track_volume:false,total_unclaimed_tokens:0,total_claimed_tokens:0,current_sol_volume:0,last_update_timestamp:0,ix_name:"sell".into(),mayhem_mode:curve.is_mayhem_mode,
        cashback_fee_basis_points:0,cashback:0,buyback_fee_basis_points:buyback_bps,buyback_fee,shareholders:vec![],quote_mint:curve.quote_mint,
        quote_amount:quote,virtual_quote_reserves:next_quote,real_quote_reserves:next_real_quote,holder_rewards_bps:if curve.is_holder_reward{fees.creator_fee_bps}else{0},holder_rewards:if curve.is_holder_reward{creator_fee}else{0},creator_fee_unclaimed:next_creator,
        unparsed_trailing_field:0,
    };
    emit!(event.clone());
    emit_cpi!(event);
    Ok(())
}

pub fn buy(ctx:Context<SellV3>,amount:u64,max_sol_cost:u64)->Result<()> {
    let a=&mut *ctx.accounts;
    crate::trade_types::prepare_bonding_curve(&a.bonding_curve, &a.system_program, &a.user)?;
    let quote_decimals=check_quote(a)?;
    let is_sol=quote_decimals.is_none();
    require!(!a.bonding_curve.complete,PumpError::BondingCurveComplete);
    require!(!a.bonding_curve.is_cashback_coin,PumpError::CashbackCoinNotSupported);
    require!(amount>0,PumpError::BuyZeroAmount);
    if is_sol{require!(a.global.buyback_fee_recipients.contains(&a.buyback_fee_recipient.key()),PumpError::BuybackFeeRecipientNotAuthorized);}
    let curve=&a.bonding_curve;
    let denominator=(curve.virtual_token_reserves as u128).checked_sub(amount as u128).ok_or_else(||error!(PumpError::Overflow))?;
    let quotient=(amount as u128*curve.virtual_quote_reserves as u128).checked_div(denominator).ok_or_else(||error!(PumpError::DivisionByZero))?;
    let quote=narrow(quotient.checked_add(1).ok_or_else(||error!(PumpError::Overflow))?)?;
    let cap=buy_fee_market_cap(curve, &a.base_mint)?;
    let config_data=a.fee_config.try_borrow_data()?;
    let config=read_config(&config_data)?;
    drop(config_data);
    require!(!(if is_sol{&config.fee_tiers}else{&config.stable_fee_tiers}).is_empty(),PumpError::FeeTiersEmpty);
    let mut fees=selected(&config,cap,!is_sol);
    if curve.creator_fee_bps>0{fees.creator_fee_bps=curve.creator_fee_bps;}
    let creator_bps=if curve.creator==Pubkey::default(){0}else{fees.creator_fee_bps};
    let protocol_fee=fee(quote,fees.protocol_fee_bps)?;
    let creator_fee=fee(quote,creator_bps)?;
    let buyback_bps=if curve.is_mayhem_mode {0}else{a.global.buyback_basis_points};
    let buyback_fee=narrow(protocol_fee as u128*buyback_bps as u128/10000)?;
    let user_output=add(add(quote,protocol_fee)?,creator_fee)?;
    require!(user_output<=max_sol_cost,PumpError::TooMuchSolRequired);
    let retained=sub(protocol_fee,buyback_fee)?;
    // Token-2022 net-accounting: the pool is credited with the quote that ACTUALLY ARRIVES at
    // the curve ATA after the quote mint's transfer fee, so reserves are not over-stated relative
    // to the ATA balance (deployed buy body @0x288a1 runs the quote legs through amount_after_fee
    // @0x12a1c). Native (SOL) legs have no transfer fee, so the credit is the gross `quote`.
    let credited_quote=match quote_decimals{Some(_)=>crate::util::transfer_fee::amount_after_fee(&a.quote_mint.to_account_info(),quote)?,None=>quote};
    let next_base=sub(curve.virtual_token_reserves,amount)?;
    let next_quote=add(curve.virtual_quote_reserves,credited_quote)?;
    let next_real_base=sub(curve.real_token_reserves,amount)?;
    let next_real_quote=add(curve.real_quote_reserves,credited_quote)?;
    let next_creator=add(curve.creator_fee,creator_fee)?;
    let next_protocol=add(curve.protocol_fees,retained)?;
    let mint_key=a.base_mint.key();let bump=[ctx.bumps.bonding_curve];
    let seeds:&[&[u8]]=&[b"bonding-curve",mint_key.as_ref(),&bump];
    token_interface::transfer_checked(CpiContext::new_with_signer(a.base_token_program.to_account_info(),TransferChecked{
        from:a.associated_base_bonding_curve.to_account_info(),mint:a.base_mint.to_account_info(),to:a.associated_base_user.to_account_info(),authority:a.bonding_curve.to_account_info()
    },&[seeds]),amount,a.base_mint.decimals)?;
    if let Some(decimals)=quote_decimals {
      for (to,amount) in [(a.associated_quote_bonding_curve.to_account_info(),sub(user_output,buyback_fee)?),(a.buyback_fee_recipient.to_account_info(),buyback_fee)] {
        if amount==0{continue}
        token_interface::transfer_checked(CpiContext::new(a.quote_token_program.to_account_info(),TransferChecked{from:a.associated_quote_user.to_account_info(),mint:a.quote_mint.to_account_info(),to,authority:a.user.to_account_info()}),amount,decimals)?;
      }
    }else{
      anchor_lang::system_program::transfer(CpiContext::new(a.system_program.to_account_info(),anchor_lang::system_program::Transfer{from:a.user.to_account_info(),to:a.bonding_curve.to_account_info()}),user_output)?;
      a.bonding_curve.sub_lamports(buyback_fee)?;a.buyback_fee_recipient.add_lamports(buyback_fee)?;
    }
    let curve=&mut a.bonding_curve;
    curve.virtual_token_reserves=next_base;curve.virtual_quote_reserves=next_quote;
    curve.real_token_reserves=next_real_base;curve.real_quote_reserves=next_real_quote;
    curve.creator_fee=next_creator;curve.protocol_fees=next_protocol;
    let event=TradeEvent{
        mint:a.base_mint.key(),sol_amount:if is_sol{quote}else{0},token_amount:amount,is_buy:true,user:a.user.key(),timestamp:Clock::get()?.unix_timestamp,
        virtual_sol_reserves:if is_sol{next_quote}else{0},virtual_token_reserves:next_base,real_sol_reserves:if is_sol{next_real_quote}else{0},real_token_reserves:next_real_base,
        fee_recipient:Pubkey::default(),fee_basis_points:fees.protocol_fee_bps,fee:protocol_fee,creator:curve.creator,creator_fee_basis_points:fees.creator_fee_bps,creator_fee,
        track_volume:false,total_unclaimed_tokens:0,total_claimed_tokens:0,current_sol_volume:0,last_update_timestamp:0,ix_name:"buy".into(),mayhem_mode:curve.is_mayhem_mode,
        cashback_fee_basis_points:0,cashback:0,buyback_fee_basis_points:buyback_bps,buyback_fee,shareholders:vec![],quote_mint:curve.quote_mint,
        quote_amount:quote,virtual_quote_reserves:next_quote,real_quote_reserves:next_real_quote,holder_rewards_bps:if curve.is_holder_reward{fees.creator_fee_bps}else{0},holder_rewards:if curve.is_holder_reward{creator_fee}else{0},creator_fee_unclaimed:next_creator,
        unparsed_trailing_field:0,
    };
    let completion=if next_real_base==0 {
        a.bonding_curve.complete=true;
        Some(crate::trade_types::CompleteEvent{user:a.user.key(),mint:a.base_mint.key(),bonding_curve:a.bonding_curve.key(),timestamp:Clock::get()?.unix_timestamp,quote_mint:a.bonding_curve.quote_mint})
    }else{None};
    emit!(event.clone());emit_cpi!(event);
    if let Some(completion)=completion {emit!(completion.clone());emit_cpi!(completion);}
    Ok(())
}

pub fn buy_exact_quote(ctx:Context<SellV3>,spendable_quote_in:u64,min_tokens_out:u64,partial_fill:bool)->Result<()> {
    let a=&mut *ctx.accounts;
    crate::trade_types::prepare_bonding_curve(&a.bonding_curve, &a.system_program, &a.user)?;
    let quote_decimals=check_quote(a)?;
    let is_sol=quote_decimals.is_none();
    require!(!a.bonding_curve.is_cashback_coin,PumpError::CashbackCoinNotSupported);
    require!(!a.bonding_curve.complete,PumpError::BondingCurveComplete);
    require!(min_tokens_out>0,PumpError::BuyZeroAmount);
    require!(spendable_quote_in>0,PumpError::BuyNotEnoughSolToCoverFees);
    if is_sol{require!(a.global.buyback_fee_recipients.contains(&a.buyback_fee_recipient.key()),PumpError::BuybackFeeRecipientNotAuthorized);}
    let curve=&a.bonding_curve;
    let cap=buy_fee_market_cap(curve, &a.base_mint)?;
    let config_data=a.fee_config.try_borrow_data()?;
    if config_data.len()<8{return Err(error!(anchor_lang::error::ErrorCode::AccountDiscriminatorNotFound));}
    require!(config_data[..8]==[143,52,146,187,219,123,76,155],anchor_lang::error::ErrorCode::AccountDiscriminatorMismatch);
    let config=FeeConfig::deserialize(&mut &config_data[8..]).map_err(|_|error!(anchor_lang::error::ErrorCode::AccountDidNotDeserialize))?;
    require!(config_data.len()>=2512,PumpError::FeeConfigTooShort);
    drop(config_data);
    require!(!(if is_sol{&config.fee_tiers}else{&config.stable_fee_tiers}).is_empty(),PumpError::FeeTiersEmpty);
    let mut fees=selected(&config,cap,!is_sol);
    if curve.creator_fee_bps>0{fees.creator_fee_bps=curve.creator_fee_bps;}
    let creator_bps=if curve.creator==Pubkey::default(){0}else{fees.creator_fee_bps};
    let _=fee(spendable_quote_in,fees.protocol_fee_bps)?;
    let _=fee(spendable_quote_in,creator_bps)?;
    let quote_budget=net_quote(spendable_quote_in,fees.protocol_fee_bps,creator_bps)?;
    require!(spendable_quote_in as u128*10000/(10000u128+fees.protocol_fee_bps as u128+creator_bps as u128)>0,PumpError::BuyNotEnoughSolToCoverFees);
    let effective=quote_budget.saturating_sub(1);
    let computed_amount=narrow(curve.virtual_token_reserves as u128*effective as u128/(curve.virtual_quote_reserves as u128+effective as u128))?;
    let amount=computed_amount.min(curve.real_token_reserves);
    let exceeds=computed_amount>curve.real_token_reserves;
    require!(!exceeds || !curve.is_mayhem_mode || partial_fill,PumpError::NotEnoughTokensToBuy);
    let crossing=exceeds && !curve.is_mayhem_mode;
    let quote=if exceeds{narrow(curve.real_token_reserves as u128*curve.virtual_quote_reserves as u128/(curve.virtual_token_reserves as u128-curve.real_token_reserves as u128))?.checked_add(1).ok_or(error!(PumpError::Overflow))?}else{quote_budget};
    let fee_quote=if exceeds{quote}else{narrow(spendable_quote_in as u128*10000/(10000u128+fees.protocol_fee_bps as u128+creator_bps as u128))?};
    let protocol_fee=fee(fee_quote,fees.protocol_fee_bps)?;
    let creator_fee=fee(fee_quote,creator_bps)?;
    let buyback_bps=if curve.is_mayhem_mode {0}else{a.global.buyback_basis_points};
    let buyback_fee=narrow(protocol_fee as u128*buyback_bps as u128/10000)?;
    let first_cost=add(add(quote,protocol_fee)?,creator_fee)?;
    let pool_base_before=if crossing{sub(a.associated_base_bonding_curve.amount,amount)?}else{0};
    let pool_quote_before=if crossing{add(sub(add(curve.real_quote_reserves,quote)?,if is_sol{a.global.pool_migration_fee}else{0})?,curve.post_complete_quote_in)?}else{0};
    let post_quote=if crossing{net_quote(sub(spendable_quote_in,first_cost)?,fees.protocol_fee_bps,creator_bps)?}else{0};
    let post_base=if post_quote>0{narrow(pool_base_before as u128*(post_quote-1) as u128/(pool_quote_before as u128+(post_quote-1) as u128))?}else{0};
    let post_fee_quote=if crossing{narrow(sub(spendable_quote_in,first_cost)? as u128*10000/(10000u128+fees.protocol_fee_bps as u128+creator_bps as u128))?}else{0};
    let post_protocol=fee(post_fee_quote,fees.protocol_fee_bps)?;let post_creator=fee(post_fee_quote,creator_bps)?;
    let post_buyback=narrow(post_protocol as u128*buyback_bps as u128/10000)?;
    let transfer_base=add(amount,post_base)?;
    require!((exceeds && curve.is_mayhem_mode && partial_fill) || transfer_base>=min_tokens_out,PumpError::BuySlippageBelowMinTokensOut);
    let user_output=add(first_cost,add(add(post_quote,post_protocol)?,post_creator)?)?;

    let retained=sub(protocol_fee,buyback_fee)?;
    // Token-2022 net-accounting (see buy): credit the pool with the quote that actually arrives at
    // the curve ATA after the quote mint's transfer fee (deployed beq body @0x2913f applies
    // amount_after_fee @0x12a1c to the quote leg). Native (SOL) legs have no fee.
    let credited_quote=match quote_decimals{Some(_)=>crate::util::transfer_fee::amount_after_fee(&a.quote_mint.to_account_info(),quote)?,None=>quote};
    let next_base=sub(curve.virtual_token_reserves,amount)?;
    let next_quote=add(curve.virtual_quote_reserves,credited_quote)?;
    let next_real_base=sub(curve.real_token_reserves,amount)?;
    let next_real_quote=add(curve.real_quote_reserves,credited_quote)?;
    let next_creator=add(add(curve.creator_fee,creator_fee)?,post_creator)?;
    let next_protocol=add(add(curve.protocol_fees,retained)?,sub(post_protocol,post_buyback)?)?;
    let mint_key=a.base_mint.key();let bump=[ctx.bumps.bonding_curve];
    let seeds:&[&[u8]]=&[b"bonding-curve",mint_key.as_ref(),&bump];
    token_interface::transfer_checked(CpiContext::new_with_signer(a.base_token_program.to_account_info(),TransferChecked{
        from:a.associated_base_bonding_curve.to_account_info(),mint:a.base_mint.to_account_info(),to:a.associated_base_user.to_account_info(),authority:a.bonding_curve.to_account_info()
    },&[seeds]),transfer_base,a.base_mint.decimals)?;
    if let Some(decimals)=quote_decimals {
      for (to,amount) in [(a.associated_quote_bonding_curve.to_account_info(),sub(user_output,add(buyback_fee,post_buyback)?)?),(a.buyback_fee_recipient.to_account_info(),add(buyback_fee,post_buyback)?)] {
        if amount==0{continue}
        token_interface::transfer_checked(CpiContext::new(a.quote_token_program.to_account_info(),TransferChecked{from:a.associated_quote_user.to_account_info(),mint:a.quote_mint.to_account_info(),to,authority:a.user.to_account_info()}),amount,decimals)?;
      }
    }else{
      anchor_lang::system_program::transfer(CpiContext::new(a.system_program.to_account_info(),anchor_lang::system_program::Transfer{from:a.user.to_account_info(),to:a.bonding_curve.to_account_info()}),user_output)?;
      a.bonding_curve.sub_lamports(add(buyback_fee,post_buyback)?)?;a.buyback_fee_recipient.add_lamports(add(buyback_fee,post_buyback)?)?;
    }
    let curve=&mut a.bonding_curve;
    curve.virtual_token_reserves=next_base;curve.virtual_quote_reserves=next_quote;
    curve.real_token_reserves=next_real_base;curve.real_quote_reserves=next_real_quote;
    curve.creator_fee=next_creator;curve.protocol_fees=next_protocol;
    curve.post_complete_base_out=add(curve.post_complete_base_out,post_base)?;curve.post_complete_quote_in=add(curve.post_complete_quote_in,post_quote)?;
    let event=TradeEvent{
        mint:a.base_mint.key(),sol_amount:if is_sol{quote}else{0},token_amount:amount,is_buy:true,user:a.user.key(),timestamp:Clock::get()?.unix_timestamp,
        virtual_sol_reserves:if is_sol{next_quote}else{0},virtual_token_reserves:next_base,real_sol_reserves:if is_sol{next_real_quote}else{0},real_token_reserves:next_real_base,
        fee_recipient:Pubkey::default(),fee_basis_points:fees.protocol_fee_bps,fee:protocol_fee,creator:curve.creator,creator_fee_basis_points:fees.creator_fee_bps,creator_fee,
        track_volume:false,total_unclaimed_tokens:0,total_claimed_tokens:0,current_sol_volume:0,last_update_timestamp:0,ix_name:"buy_exact_quote_in".into(),mayhem_mode:curve.is_mayhem_mode,
        cashback_fee_basis_points:0,cashback:0,buyback_fee_basis_points:buyback_bps,buyback_fee,shareholders:vec![],quote_mint:curve.quote_mint,
        quote_amount:quote,virtual_quote_reserves:next_quote,real_quote_reserves:next_real_quote,holder_rewards_bps:if curve.is_holder_reward{fees.creator_fee_bps}else{0},holder_rewards:if curve.is_holder_reward{creator_fee}else{0},creator_fee_unclaimed:next_creator,
        unparsed_trailing_field:0,
    };
    let completion=if next_real_base==0 {
        a.bonding_curve.complete=true;
        Some(crate::trade_types::CompleteEvent{user:a.user.key(),mint:a.base_mint.key(),bonding_curve:a.bonding_curve.key(),timestamp:Clock::get()?.unix_timestamp,quote_mint:a.bonding_curve.quote_mint})
    }else{None};
    let post_event=if crossing && post_quote>0{Some(PostCompleteBuyEvent{user:a.user.key(),mint:a.base_mint.key(),bonding_curve:a.bonding_curve.key(),quote_mint:a.bonding_curve.quote_mint,timestamp:Clock::get()?.unix_timestamp,base_out:post_base,quote_in:post_quote,fee_basis_points:fees.protocol_fee_bps,fee:post_protocol,creator_fee_basis_points:fees.creator_fee_bps,creator_fee:post_creator,buyback_fee:post_buyback,pool_base_reserves_before:pool_base_before,pool_quote_reserves_before:pool_quote_before,pool_base_reserves_after:sub(pool_base_before,post_base)?,pool_quote_reserves_after:add(pool_quote_before,post_quote)?})}else{None};
    emit!(event.clone());emit_cpi!(event);
    if let Some(completion)=completion {emit!(completion.clone());emit_cpi!(completion);}
    if let Some(post_event)=post_event{emit!(post_event.clone());emit_cpi!(post_event);}
    Ok(())
}

fn read_config(data:&[u8])->Result<FeeConfig>{
 use anchor_lang::error::ErrorCode;
 if data.len()<8{return Err(error!(ErrorCode::AccountDiscriminatorNotFound))}
 if data[..8]!=[143,52,146,187,219,123,76,155]{return Err(error!(ErrorCode::AccountDiscriminatorMismatch))}
 let mut input=&data[8..];
 let decode=(||->std::io::Result<FeeConfig>{
  let bump=u8::deserialize(&mut input)?;let admin=Pubkey::deserialize(&mut input)?;
  let flat_fees=Fees::deserialize(&mut input)?;let fee_tiers=Vec::<crate::trade_types::FeeTier>::deserialize(&mut input)?;
  let stable_fee_tiers=if data.len()>=4073{Vec::<crate::trade_types::FeeTier>::deserialize(&mut input)?}else{vec![]};
  let exotic_flat_fees=if data.len()>=4097{Fees::deserialize(&mut input)?}else{Fees{lp_fee_bps:0,protocol_fee_bps:0,creator_fee_bps:0}};
  Ok(FeeConfig{bump,admin,flat_fees,fee_tiers,stable_fee_tiers,exotic_flat_fees})
 })().map_err(|_|error!(ErrorCode::AccountDidNotDeserialize))?;
 require!(data.len()>=2512,PumpError::FeeConfigTooShort);Ok(decode)
}

fn check_quote(a:&SellV3)->Result<Option<u8>>{
 // Native (SOL) quote is gated SOLELY by the WSOL sentinel. This matches the deployed v3
 // core check_quote @0x204af, whose only mint-constant comparison is a 32-byte memcmp of the
 // quote mint key against the WSOL native-mint constant (@0x20891, rodata 0x1b5cc8).
 if a.quote_mint.key()==WSOL||a.quote_mint.key()==Pubkey::default(){
  require!(a.bonding_curve.quote_mint==WSOL||a.bonding_curve.quote_mint==Pubkey::default(),crate::ReconstructionError::ReconstructionBranchUnsupported);return Ok(None)
 }
 // Non-native quote: accept ANY whitelisted quote mint, identified by the curve's own
 // bonding_curve.quote_mint (the whitelist is enforced at curve-creation time via quote_control,
 // exactly as buy_v2.rs's account constraint already does). The deployed program does NOT
 // hardcode USDC: the USDC byte-constant (rodata 0x1b5d28) is referenced exactly once in all of
 // .text, at 0x11425 (function 0x113d9), which is outside every v3 core function
 // (0x204af / 0x28f74 / 0x2913f). Verified via full-.text scan of the deployed binary.
 let expected_quote=a.bonding_curve.quote_mint;
 require!(expected_quote!=WSOL && expected_quote!=Pubkey::default(),crate::ReconstructionError::ReconstructionBranchUnsupported);
 require_keys_eq!(a.quote_mint.key(),expected_quote,PumpError::MintDoesNotMatchBondingCurve);
 require!(a.quote_mint.owner==&a.quote_token_program.key(),anchor_lang::error::ErrorCode::AccountOwnedByWrongProgram);
 let mint=Mint::try_deserialize(&mut &a.quote_mint.try_borrow_data()?[..])?;
 for (role,info) in [(0,a.associated_quote_bonding_curve.to_account_info()),(1,a.associated_quote_user.to_account_info()),(2,a.buyback_fee_recipient.to_account_info())]{
  require!(info.owner==&a.quote_token_program.key(),PumpError::AccountTypeNotSupported);
  let token=TokenAccount::try_deserialize(&mut &info.try_borrow_data()?[..])?;
  require_keys_eq!(token.mint,expected_quote,PumpError::MintDoesNotMatchBondingCurve);
  if role==1{require_keys_eq!(token.owner,a.user.key(),PumpError::AccountTypeNotSupported)}
  if role==2{require!(a.global.buyback_fee_recipients.contains(&token.owner),PumpError::BuybackFeeRecipientNotAuthorized)}
  if role!=1 {
   let authority=if role==0{a.bonding_curve.key()}else{token.owner};
   let expected=anchor_spl::associated_token::get_associated_token_address_with_program_id(&authority,&expected_quote,&a.quote_token_program.key());
   require_keys_eq!(info.key(),expected,anchor_lang::error::ErrorCode::ConstraintSeeds);
  }
 }
 Ok(Some(mint.decimals))
}

fn net_quote(spend:u64,pb:u64,cb:u64)->Result<u64>{let total=add(pb,cb)?;let mut quote=narrow(spend as u128*10000/(10000u128+total as u128))?;if quote>0 && add(add(quote,fee(quote,pb)?)?,fee(quote,cb)?)?>spend{quote-=1;}Ok(quote)}
#[event]
#[derive(Clone)]pub struct PostCompleteBuyEvent{pub user:Pubkey,pub mint:Pubkey,pub bonding_curve:Pubkey,pub quote_mint:Pubkey,pub timestamp:i64,pub base_out:u64,pub quote_in:u64,pub fee_basis_points:u64,pub fee:u64,pub creator_fee_basis_points:u64,pub creator_fee:u64,pub buyback_fee:u64,pub pool_base_reserves_before:u64,pub pool_quote_reserves_before:u64,pub pool_base_reserves_after:u64,pub pool_quote_reserves_after:u64}

// Buy-side pretrade fee basis recovered from the original mode selector.
fn buy_fee_market_cap(curve: &BondingCurve, mint: &Mint) -> Result<u128> {
    require!(curve.virtual_token_reserves != 0, PumpError::DivisionByZero);
    let selected_supply = if curve.is_mayhem_mode {
        curve.token_total_supply
    } else {
        mint.supply
    };
    Ok(u128::from(selected_supply) * u128::from(curve.virtual_quote_reserves)
        / u128::from(curve.virtual_token_reserves))
}
