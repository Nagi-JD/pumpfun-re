//! SPL Token-2022 transfer-fee math for the quote mint.
//!
//! This reconstructs the behavior of the deployed program's helper at
//! `deployed.so` offset `0x12a1c`: it reads the quote mint account's
//! Token-2022 `TransferFeeConfig` extension, resolves the fee that applies in
//! the current epoch, and computes the net amount (`NET = amount - fee`,
//! a checked `sub64` with error path) so the rest of the program can work in
//! net terms. It also provides the inverse gross-up
//! (`calculate_pre_fee_amount`) used when a desired net output must be grossed
//! up to the amount to send.
//!
//! The math is an original implementation of the public Token-2022
//! `TransferFeeConfig` specification (epoch-selected `{epoch, maximum_fee,
//! transfer_fee_basis_points}` pairs; `fee = min(ceil(amount * bps / 10000),
//! maximum_fee)`); only the extension *types* are reused to decode the raw
//! mint account data. Nothing is wired into a handler here.

use anchor_lang::prelude::*;
use anchor_spl::token_2022::spl_token_2022::{
    extension::{
        transfer_fee::TransferFeeConfig, BaseStateWithExtensions, StateWithExtensions,
    },
    state::Mint as SplMint,
};
use crate::PumpError;

/// Basis-point denominator used by the Token-2022 transfer-fee spec.
const ONE_IN_BASIS_POINTS: u64 = 10_000;

/// The epoch-resolved transfer-fee parameters pulled from a mint's
/// `TransferFeeConfig` extension: `(transfer_fee_basis_points, maximum_fee)`.
/// Returns `None` when the mint carries no transfer-fee extension (a plain
/// SPL mint, or a Token-2022 mint without the extension) — i.e. no fee applies.
///
/// `epoch` is the epoch to resolve against (normally `Clock::epoch`): the newer
/// schedule applies once `epoch >= newer_transfer_fee.epoch`, otherwise the
/// older schedule is used — matching the deployed `0x12a1c` selection.
pub fn epoch_fee_params(mint: &AccountInfo, epoch: u64) -> Result<Option<(u16, u64)>> {
    let data = mint.try_borrow_data()?;
    let state = match StateWithExtensions::<SplMint>::unpack(&data[..]) {
        Ok(state) => state,
        // Not a decodable Token-2022 mint (e.g. a legacy SPL mint): no fee.
        Err(_) => return Ok(None),
    };
    let config = match state.get_extension::<TransferFeeConfig>() {
        Ok(config) => config,
        // Mint has no transfer-fee extension: no fee applies.
        Err(_) => return Ok(None),
    };
    let fee = if epoch >= u64::from(config.newer_transfer_fee.epoch) {
        &config.newer_transfer_fee
    } else {
        &config.older_transfer_fee
    };
    let basis_points = u16::from(fee.transfer_fee_basis_points);
    let maximum_fee = u64::from(fee.maximum_fee);
    Ok(Some((basis_points, maximum_fee)))
}

/// Compute the Token-2022 transfer fee charged on a gross `amount` for `mint`
/// at the current epoch: `fee = min(ceil(amount * bps / 10000), maximum_fee)`.
/// Returns `0` when the mint has no transfer-fee extension.
pub fn transfer_fee(mint: &AccountInfo, amount: u64) -> Result<u64> {
    match epoch_fee_params(mint, Clock::get()?.epoch)? {
        Some((basis_points, maximum_fee)) => fee_from_bps(amount, basis_points, maximum_fee),
        None => Ok(0),
    }
}

/// Net amount the recipient receives after the transfer fee: `NET = amount - fee`.
/// This mirrors the `sub64` with error path at `0x12a1c`.
pub fn amount_after_fee(mint: &AccountInfo, amount: u64) -> Result<u64> {
    let fee = transfer_fee(mint, amount)?;
    amount.checked_sub(fee).ok_or_else(|| error!(PumpError::Overflow))
}

/// Inverse / gross-up: given a desired `net` the recipient must receive, return
/// the gross amount to send so that `amount_after_fee(mint, gross) == net`.
/// Standard Token-2022 `calculate_pre_fee_amount`. Returns `net` unchanged when
/// the mint has no transfer-fee extension.
pub fn pre_fee_amount(mint: &AccountInfo, net: u64) -> Result<u64> {
    match epoch_fee_params(mint, Clock::get()?.epoch)? {
        Some((basis_points, maximum_fee)) => pre_fee_from_net(net, basis_points, maximum_fee),
        None => Ok(net),
    }
}

/// Pure fee math: `fee = min(ceil(amount * bps / 10000), maximum_fee)`.
/// Overflow-checked; wide (`u128`) intermediate then narrowed to `u64`.
pub fn fee_from_bps(amount: u64, basis_points: u16, maximum_fee: u64) -> Result<u64> {
    if basis_points == 0 {
        return Ok(0);
    }
    let numerator = (amount as u128)
        .checked_mul(basis_points as u128)
        .ok_or_else(|| error!(PumpError::Overflow))?;
    // Ceiling division by 10_000.
    let scaled = numerator
        .checked_add((ONE_IN_BASIS_POINTS - 1) as u128)
        .ok_or_else(|| error!(PumpError::Overflow))?;
    let raw_fee = scaled / (ONE_IN_BASIS_POINTS as u128);
    let capped = raw_fee.min(maximum_fee as u128);
    u64::try_from(capped).map_err(|_| error!(PumpError::Truncation))
}

/// Pure net math: `NET = amount - fee`, overflow-checked.
pub fn net_from_fee(amount: u64, fee: u64) -> Result<u64> {
    amount.checked_sub(fee).ok_or_else(|| error!(PumpError::Overflow))
}

/// Pure inverse math (`calculate_pre_fee_amount`): smallest gross such that
/// `gross - min(ceil(gross * bps / 10000), maximum_fee) == net`.
pub fn pre_fee_from_net(net: u64, basis_points: u16, maximum_fee: u64) -> Result<u64> {
    if basis_points == 0 {
        return Ok(net);
    }
    if net == 0 {
        return Ok(0);
    }
    // A 100% (or higher, per spec clamp) fee rate caps at `maximum_fee`; the
    // only gross that nets `net` is `net + maximum_fee`. Guards the zero divisor.
    if basis_points as u64 >= ONE_IN_BASIS_POINTS {
        return net
            .checked_add(maximum_fee)
            .ok_or_else(|| error!(PumpError::Overflow));
    }
    let numerator = (net as u128)
        .checked_mul(ONE_IN_BASIS_POINTS as u128)
        .ok_or_else(|| error!(PumpError::Overflow))?;
    let denominator = (ONE_IN_BASIS_POINTS - basis_points as u64) as u128;
    // Ceiling division: (numerator + denominator - 1) / denominator.
    let scaled = numerator
        .checked_add(denominator - 1)
        .ok_or_else(|| error!(PumpError::Overflow))?;
    let raw_pre_fee = scaled / denominator;
    let implied_fee = raw_pre_fee
        .checked_sub(net as u128)
        .ok_or_else(|| error!(PumpError::Overflow))?;
    if implied_fee >= maximum_fee as u128 {
        net.checked_add(maximum_fee)
            .ok_or_else(|| error!(PumpError::Overflow))
    } else {
        u64::try_from(raw_pre_fee).map_err(|_| error!(PumpError::Truncation))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fee_is_ceil_capped() {
        // 100 bps (1%) of 10_001 = 100.01 -> ceil 101, under a high cap.
        assert_eq!(fee_from_bps(10_001, 100, u64::MAX).unwrap(), 101);
        // Cap binds.
        assert_eq!(fee_from_bps(1_000_000, 100, 50).unwrap(), 50);
        // Zero bps -> no fee.
        assert_eq!(fee_from_bps(1_000_000, 0, 50).unwrap(), 0);
    }

    #[test]
    fn net_round_trips_with_pre_fee() {
        let (bps, max) = (100u16, u64::MAX);
        let gross = 1_000_000u64;
        let fee = fee_from_bps(gross, bps, max).unwrap();
        let net = net_from_fee(gross, fee).unwrap();
        // Grossing the net back up never under-funds the recipient.
        let regrossed = pre_fee_from_net(net, bps, max).unwrap();
        assert!(regrossed >= gross);
        let refee = fee_from_bps(regrossed, bps, max).unwrap();
        assert!(net_from_fee(regrossed, refee).unwrap() >= net);
    }

    #[test]
    fn pre_fee_handles_cap_and_edges() {
        assert_eq!(pre_fee_from_net(0, 100, 1000).unwrap(), 0);
        assert_eq!(pre_fee_from_net(500, 0, 1000).unwrap(), 500);
        // Cap-bound region: gross = net + maximum_fee.
        assert_eq!(pre_fee_from_net(1_000_000, 100, 50).unwrap(), 1_000_050);
        // 100% rate clamps to net + max.
        assert_eq!(pre_fee_from_net(777, 10_000, 9).unwrap(), 786);
    }
}
