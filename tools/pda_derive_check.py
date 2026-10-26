#!/usr/bin/env python3
"""Offline PDA derivation + one round-trip check against mainnet.

Derives `find_program_address` candidates for the seed vectors recovered by
pda_catalog.py, then asks a public RPC whether the derived address exists and
what it is. This turns "the binary builds these seeds" into "these seeds produce
the account the program actually uses" for the checks that can be closed without
a mint or a creator key.

Read-only: no transaction is built or sent.
"""
import hashlib
import json
import sys
import urllib.request

ALPHA = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
P = 2 ** 255 - 19
D = (-121665 * pow(121666, P - 2, P)) % P
RPC = 'https://api.mainnet-beta.solana.com'
PDA_MARKER = b'ProgramDerivedAddress'


def b58d(s):
    n = 0
    for ch in s:
        n = n * 58 + ALPHA.index(ch)
    raw = n.to_bytes((n.bit_length() + 7) // 8, 'big')
    pad = len(s) - len(s.lstrip('1'))
    return b'\0' * pad + raw


def b58e(data):
    n = int.from_bytes(data, 'big')
    out = ''
    while n:
        n, r = divmod(n, 58)
        out = ALPHA[r] + out
    return '1' * (len(data) - len(data.lstrip(b'\0'))) + (out or '')


def on_curve(b):
    """ed25519: is this 32-byte string the y-coordinate of a curve point?"""
    y = int.from_bytes(b, 'little') & ((1 << 255) - 1)
    if y >= P:
        return False
    u = (y * y - 1) % P
    v = (D * y * y + 1) % P
    x2 = u * pow(v, P - 2, P) % P
    if x2 == 0:
        return True
    return pow(x2, (P - 1) // 2, P) == 1


def find_pda(seeds, program_id):
    for bump in range(255, -1, -1):
        h = hashlib.sha256(b''.join(seeds) + bytes([bump]) + program_id + PDA_MARKER).digest()
        if not on_curve(h):
            return b58e(h), bump
    return None, None


def rpc(method, params):
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    req = urllib.request.Request(RPC, data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def check(label, seeds, program_b58, program_name, want_disc=None, want_owner=None):
    pid = b58d(program_b58)
    addr, bump = find_pda(seeds, pid)
    got = rpc('getAccountInfo', [addr, {'encoding': 'base64'}])
    info = (got.get('result') or {}).get('value')
    if info is None:
        print(f'{label}: {addr} (bump {bump}) -> DOES NOT EXIST')
        return False
    import base64
    data = base64.b64decode(info['data'][0])
    disc = data[:8].hex()
    owner = info['owner']
    ok_owner = (owner == want_owner) if want_owner else True
    ok_disc = (disc == want_disc) if want_disc else True
    print(f'{label}: {addr} (bump {bump}) -> len={len(data)} owner={owner} '
          f'disc={disc} owner_ok={ok_owner} disc_ok={ok_disc}')
    return ok_owner and ok_disc


def main():
    pump = '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P'
    fees = 'pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ'
    mayhem = 'MAyhSmzXzV1pTf7LsNkrNwkWKTo4ougAJ1PPg47MD4e'
    results = []
    # G1: ["global"] under pump -> Global account (disc a7e8e8b1c86c727f)
    results.append(check('G1 ["global"] @pump', [b'global'], pump, 'pump',
                         want_disc='a7e8e8b1c86c727f', want_owner=pump))
    # G2: ["fee_config", pump_id, bump] under fees -> FeeConfig (disc 8f3492bbdb7b4c9b)
    results.append(check('G2 ["fee_config", pump] @fees', [b'fee_config', b58d(pump)], fees,
                         'fees', want_disc='8f3492bbdb7b4c9b', want_owner=fees))
    # G3: ["mayhem-state", pump_id] under mayhem -> negative control: the variable
    #     seed of that vector is not necessarily the pump id.
    addr, bump = find_pda([b'mayhem-state', b58d(pump)], b58d(mayhem))
    got = rpc('getAccountInfo', [addr, {'encoding': 'base64'}])
    info = (got.get('result') or {}).get('value')
    print(f'G3 ["mayhem-state", pump] @mayhem: {addr} (bump {bump}) -> '
          f'{"exists" if info else "DOES NOT EXIST (variable seed is not the pump id)"}')
    # G4: ["fee-program-global"] under fees (the recovered vector's only variable
    #     seed is the 1-byte bump) -> FeeProgramGlobal (disc a2a5f5311d2537f2)
    results.append(check('G4 ["fee-program-global"] @fees', [b'fee-program-global'], fees,
                         'fees', want_disc='a2a5f5311d2537f2', want_owner=fees))
    # G5: ["fee_config", amm_id] under fees -> the AMM's own FeeConfig
    amm = 'pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA'
    results.append(check('G5 ["fee_config", amm] @fees', [b'fee_config', b58d(amm)], fees,
                         'fees', want_disc='8f3492bbdb7b4c9b', want_owner=fees))
    print('\nall closed checks passed:', all(results))
    return 0 if all(results) else 1


if __name__ == '__main__':
    sys.exit(main())
