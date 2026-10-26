//! admin_update_token_incentives @ binary 0x25c54 (reconstructed from deployed.so).
//!
//! Authority-gated configuration of the global PumpSwap-style volume-reward
//! schedule: binds the incentive mint, sets the day length and the active
//! [start_time, end_time) window, resets the forward per-day sol-volume
//! buckets, and writes the per-day token-supply target. The only CPI is the
//! idempotent ATA create for the program's incentive vault; no value moves.
//!
//! Account order and the eight-guard schedule check are both verified against
//! the generated `__global` try_accounts (0x1e276) and the PumpError Display
//! table (0x2bd95). GlobalVolumeAccumulator field offsets (start@+0x00,
//! end@+0x08, seconds_in_a_day@+0x10, mint@+0x18, total_token_supply@+0x38,
//! sol_volumes@+0x128) match volume_sync::GlobalVolumeAccumulator.
use crate::*;
use anchor_spl::{associated_token::AssociatedToken, token_interface::{Mint, TokenAccount, TokenInterface}};
use crate::volume_sync::GlobalVolumeAccumulator;

#[event_cpi]
#[derive(Accounts)]
pub struct AdminUpdateTokenIncentives<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    #[account(seeds = [b"global"], bump, has_one = authority @ PumpError::NotAuthorized)]
    pub global: Box<Account<'info, Global>>,
    #[account(mut, seeds = [b"global_volume_accumulator"], bump)]
    pub global_volume_accumulator: Box<Account<'info, GlobalVolumeAccumulator>>,
    pub mint: InterfaceAccount<'info, Mint>,
    #[account(
        init_if_needed,
        payer = authority,
        associated_token::mint = mint,
        associated_token::authority = global_volume_accumulator,
        associated_token::token_program = token_program,
    )]
    pub global_incentive_token_account: InterfaceAccount<'info, TokenAccount>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    pub system_program: Program<'info, System>,
    pub token_program: Interface<'info, TokenInterface>,
}

pub fn admin_update_token_incentives(
    ctx: Context<AdminUpdateTokenIncentives>,
    start_time: i64,
    end_time: i64,
    seconds_in_a_day: i64,
    day_number: u64,
    pump_token_supply_per_day: u64,
) -> Result<()> {
    let now = Clock::get()?.unix_timestamp;
    let schedule = &mut ctx.accounts.global_volume_accumulator;

    // The mint binding and the day length are rewritten unconditionally on
    // every admin call (binary writes +0x18 and +0x10 before the guards).
    schedule.mint = ctx.accounts.mint.key();
    schedule.seconds_in_a_day = seconds_in_a_day;

    // A (0, 0) pair is a supply-only edit: the active window is left in place.
    if start_time != 0 && end_time != 0 {
        // Repositioning the window start wipes every per-day bucket.
        if start_time != schedule.start_time {
            require!(start_time > now, PumpError::StartTimeInThePast);
            schedule.start_time = start_time;
            schedule.total_token_supply = [0; 30];
            schedule.sol_volumes = [0; 30];
        }
        require!(end_time > now, PumpError::EndTimeInThePast);
        require!(end_time > start_time, PumpError::EndTimeBeforeStartTime);
        require!(end_time - start_time < seconds_in_a_day * 30, PumpError::TimeRangeTooLarge);
        schedule.end_time = end_time;

        // If the window has already opened, zero the volume of every day that
        // is still in the future so a reschedule cannot pay on stale buckets.
        if now > schedule.start_time {
            let current = day_index(now, schedule.start_time, seconds_in_a_day);
            let last = day_index(schedule.end_time, schedule.start_time, seconds_in_a_day);
            require!(last > current, PumpError::EndTimeBeforeCurrentDay);
            for day in (current + 1)..=last {
                schedule.sol_volumes[day] = 0;
            }
        }
    }

    // A positive supply targets one day (day_number < 30) or the entire
    // still-active range (day_number >= 30 sentinel).
    if pump_token_supply_per_day > 0 {
        require!(now <= schedule.end_time, PumpError::SupplyUpdateForFinishedRange);
        let current = if now < schedule.start_time {
            0
        } else {
            day_index(now, schedule.start_time, seconds_in_a_day)
        };
        let last = day_index(schedule.end_time, schedule.start_time, seconds_in_a_day);
        if day_number < 30 {
            let day = day_number as usize;
            require!(day <= last, PumpError::DayIndexAfterEndIndex);
            require!(day >= current, PumpError::DayInActiveRange);
            schedule.total_token_supply[day] = pump_token_supply_per_day;
        } else {
            for day in current..=last {
                schedule.total_token_supply[day] = pump_token_supply_per_day;
            }
        }
    }

    let event = AdminUpdateTokenIncentivesEvent {
        start_time,
        end_time,
        day_number,
        token_supply_per_day: pump_token_supply_per_day,
        mint: ctx.accounts.mint.key(),
        seconds_in_a_day,
        timestamp: now,
    };
    emit!(event.clone());
    emit_cpi!(event);
    Ok(())
}

// Whole-day offset of `point` from the window start. The surrounding guards
// (positive day length, non-negative offset) make the narrowing infallible,
// matching the binary's unchecked conversion.
fn day_index(point: i64, start: i64, day: i64) -> usize {
    usize::try_from((point - start) / day).unwrap()
}

#[event]
#[derive(Clone)]
pub struct AdminUpdateTokenIncentivesEvent {
    pub start_time: i64,
    pub end_time: i64,
    pub day_number: u64,
    pub token_supply_per_day: u64,
    pub mint: Pubkey,
    pub seconds_in_a_day: i64,
    pub timestamp: i64,
}
