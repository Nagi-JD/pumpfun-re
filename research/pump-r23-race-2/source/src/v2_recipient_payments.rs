use anchor_lang::prelude::*;

/// Transfer a native fee payment to a configured recipient.
#[inline(never)]
pub(super) fn transfer_native<'info>(
    system_program: &AccountInfo<'info>,
    recipient: &UncheckedAccount<'info>,
    payer: &AccountInfo<'info>,
    amount: u64,
) -> Result<()> {
    if amount == 0 {
        return Ok(());
    }
    anchor_lang::system_program::transfer(
        CpiContext::new(
            system_program.clone(),
            anchor_lang::system_program::Transfer {
                to: recipient.to_account_info(),
                from: payer.clone(),
            },
        ),
        amount,
    )
}

/// Split protocol fees after the curve payment, preserving the buyback invariants.
#[inline(never)]
pub(crate) fn split_protocol_fee(
    global: &crate::Global,
    protocol_fee: u64,
    is_mayhem_mode: bool,
) -> (u64, u64) {
    if is_mayhem_mode {
        return (0, protocol_fee);
    }
    let buyback_fee = u64::try_from(global.buyback_basis_points as u128 * protocol_fee as u128 / 10000)
        .expect("buyback fee is at most protocol_fee");
    let remaining = protocol_fee.checked_sub(buyback_fee)
        .expect("buyback_fee never exceeds protocol_fee");
    (buyback_fee, remaining)
}
