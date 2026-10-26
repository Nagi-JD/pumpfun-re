//! claim_token_incentives @ binary 0x25d0e (reconstructed from deployed.so).
//!
//! Settles a user's accrued volume reward. It rolls the user volume
//! accumulator forward against the read-only global schedule (crediting the
//! previous day's pro-rata token reward into `total_unclaimed_tokens`), then
//! transfers the full unclaimed balance from the program's incentive vault to
//! the user's ATA, signed by the global_volume_accumulator PDA.
//!
//! Account set and the `has_one = mint` / InvalidIncentiveMint guard are
//! verified against try_accounts 0x1e986; the zero-reward "No tokens to claim"
//! early return is verified live at insn 0xe41d; the PDA-signed
//! transfer_checked is the only value-moving CPI (plus the idempotent user_ata
//! create on the init_if_needed path).
use crate::*;
use anchor_spl::{associated_token::AssociatedToken, token_interface::{self, Mint, TokenAccount, TokenInterface, TransferChecked}};
use crate::volume_sync::GlobalVolumeAccumulator;

#[derive(Accounts)]
pub struct ClaimTokenIncentives<'info> {
    /// CHECK: authority of the destination ATA and seed of the user accumulator.
    pub user: AccountInfo<'info>,
    #[account(
        init_if_needed,
        payer = payer,
        associated_token::mint = mint,
        associated_token::authority = user,
        associated_token::token_program = token_program,
    )]
    pub user_ata: InterfaceAccount<'info, TokenAccount>,
    #[account(seeds = [b"global_volume_accumulator"], bump, has_one = mint @ PumpError::InvalidIncentiveMint)]
    pub global_volume_accumulator: Account<'info, GlobalVolumeAccumulator>,
    #[account(
        mut,
        associated_token::mint = mint,
        associated_token::authority = global_volume_accumulator,
        associated_token::token_program = token_program,
    )]
    pub global_incentive_token_account: InterfaceAccount<'info, TokenAccount>,
    #[account(mut, seeds = [b"user_volume_accumulator", user.key().as_ref()], bump)]
    pub user_volume_accumulator: Account<'info, UserVolumeAccumulator>,
    pub mint: InterfaceAccount<'info, Mint>,
    pub token_program: Interface<'info, TokenInterface>,
    pub system_program: Program<'info, System>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    /// CHECK: Anchor event authority PDA (verified-order account, so declared
    /// manually rather than via #[event_cpi] since `payer` trails it).
    #[account(seeds = [b"__event_authority"], bump)]
    pub event_authority: AccountInfo<'info>,
    pub program: Program<'info, crate::program::PumpRecovered>,
    #[account(mut)]
    pub payer: Signer<'info>,
}

pub fn claim_token_incentives(ctx: Context<ClaimTokenIncentives>) -> Result<()> {
    let now = Clock::get()?.unix_timestamp;
    let schedule = &ctx.accounts.global_volume_accumulator;
    let account = &mut ctx.accounts.user_volume_accumulator;
    account.user = ctx.accounts.user.key();

    // A claim landing before a freshly-scheduled window opens discards any
    // total carried over from a previous, now-superseded schedule.
    if now < schedule.start_time && account.last_update_timestamp < schedule.start_time {
        account.total_claimed_tokens = 0;
        account.has_total_claimed_tokens = false;
    }

    roll_forward(schedule, account, now)?;

    let amount = account.total_unclaimed_tokens;
    if amount == 0 {
        msg!("No tokens to claim");
        return Ok(());
    }

    // The global_volume_accumulator PDA is the authority of the incentive
    // vault and signs the payout.
    let bump = [ctx.bumps.global_volume_accumulator];
    let signer: &[&[u8]] = &[b"global_volume_accumulator", &bump];
    token_interface::transfer_checked(
        CpiContext::new_with_signer(
            ctx.accounts.token_program.to_account_info(),
            TransferChecked {
                from: ctx.accounts.global_incentive_token_account.to_account_info(),
                mint: ctx.accounts.mint.to_account_info(),
                to: ctx.accounts.user_ata.to_account_info(),
                authority: schedule.to_account_info(),
            },
            &[signer],
        ),
        amount,
        ctx.accounts.mint.decimals,
    )?;

    account.total_unclaimed_tokens = 0;
    account.total_claimed_tokens += amount;
    account.has_total_claimed_tokens = true;
    account.needs_claim = account.current_sol_volume > 0;
    account.last_update_timestamp = now;

    let event = ClaimTokenIncentivesEvent {
        user: ctx.accounts.user.key(),
        mint: ctx.accounts.mint.key(),
        amount,
        timestamp: now,
        total_claimed_tokens: account.total_claimed_tokens,
        current_sol_volume: account.current_sol_volume,
    };
    emit!(event.clone());
    emit_cpi!(event);
    Ok(())
}

// Shared volume-accumulator roll-forward (original updater at binary 0x6d408):
// credit the previous whole day's pro-rata reward into the unclaimed balance
// (consuming the user's current volume), then refresh the claim bookkeeping
// against the current day while the window is still active.
fn roll_forward(
    schedule: &GlobalVolumeAccumulator,
    account: &mut UserVolumeAccumulator,
    now: i64,
) -> Result<()> {
    let now_index = usize::try_from(now).expect("SVM is 64-bit");
    let start_index = usize::try_from(schedule.start_time).expect("SVM is 64-bit");
    if now_index < start_index || schedule.seconds_in_a_day == 0 {
        return Ok(());
    }
    let period = usize::try_from(schedule.seconds_in_a_day).expect("SVM is 64-bit");
    let last_index = usize::try_from(account.last_update_timestamp).expect("SVM is 64-bit");
    let today = (now_index - start_index) / period;

    if last_index >= start_index {
        let previous_day = (last_index - start_index) / period;
        let end_index = usize::try_from(schedule.end_time).expect("SVM is 64-bit");
        let end_day = end_index
            .checked_sub(start_index)
            .expect("end_time should be bigger than start_time")
            / period;
        if previous_day < today
            && previous_day <= end_day
            && schedule.sol_volumes[previous_day] > 0
            && account.current_sol_volume > 0
        {
            // reward = current_volume * supply[prev] / sol_volumes[prev], in
            // u128 then narrowed; a value exceeding u64 is Truncation.
            let reward = u64::try_from(
                (account.current_sol_volume as u128)
                    * (schedule.total_token_supply[previous_day] as u128)
                    / (schedule.sol_volumes[previous_day] as u128),
            )
            .map_err(|_| error!(PumpError::Truncation))?;
            account.total_unclaimed_tokens = account
                .total_unclaimed_tokens
                .checked_add(reward)
                .expect("Unexpected overflow");
            account.current_sol_volume = 0;
            account.last_update_timestamp = now;
            account.needs_claim = account.total_unclaimed_tokens > 0;
        }
    }

    if now <= schedule.end_time {
        // The original updater touches today's bucket even on a zero-volume
        // pass; the window guards keep `today` inside the 30-day arrays.
        let _ = schedule.sol_volumes[today];
        account.last_update_timestamp = now;
        account.needs_claim = account.total_unclaimed_tokens > 0 || account.current_sol_volume > 0;
    }
    Ok(())
}

#[event]
#[derive(Clone)]
pub struct ClaimTokenIncentivesEvent {
    pub user: Pubkey,
    pub mint: Pubkey,
    pub amount: u64,
    pub timestamp: i64,
    pub total_claimed_tokens: u64,
    pub current_sol_volume: u64,
}
