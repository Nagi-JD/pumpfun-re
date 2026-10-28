#!/bin/bash
# 03: build an AMM candidate tree. usage: 03-build-amm.sh <label> <srcdir>
# direct-path v1.44 (no cargo-build-sbf wrapper), exactly research/amm-race/build.sh
# with local paths. EXTRA comes from research/amm-race/remap-path-prefix.txt.
set -e
V=${TV:-v1.44}
P=$HOME/.cache/solana/$V/platform-tools
W=$HOME/pumpwork
L=$1; S=$2
PKT=/mnt/c/Users/arzfeqsdeidm/Desktop/yop/AA/pumpfun-re/research
EXTRA=$(tr -d '\r' < "$PKT/amm-race/remap-path-prefix.txt")

export PATH=$P/rust/bin:/usr/local/bin:/usr/bin:/bin
export RUSTC=$P/rust/bin/rustc CC=$P/llvm/bin/clang AR=$P/llvm/bin/llvm-ar
export CARGO_HOME=$W/netcargo CARGO_TARGET_DIR=$W/target-$V CARGO_BUILD_JOBS=4
export RUSTFLAGS=-Zremap-cwd-prefix=

if [ "$3" = "online" ]; then
  unset CARGO_NET_OFFLINE
  (cd "$S" && cargo fetch --manifest-path "$S/programs/pump-amm/Cargo.toml" --locked) \
    > "$W/out/$L-fetch.log" 2>&1 || { tail -20 "$W/out/$L-fetch.log"; exit 1; }
  export CARGO_NET_OFFLINE=true
else
  export CARGO_NET_OFFLINE=true
fi

cd "$S"
cargo rustc --manifest-path "$S/programs/pump-amm/Cargo.toml" --release \
  --target sbpf-solana-solana --locked --offline --lib -- $EXTRA \
  > "$W/out/$L-build.log" 2>&1 || { tail -30 "$W/out/$L-build.log"; exit 1; }

cp "$W/target-$V/sbpf-solana-solana/release/pump_amm_recovered.so" "$W/out/$L-symbols.so"
$HOME/.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objcopy --strip-all \
  "$W/out/$L-symbols.so" "$W/out/$L-candidate.so"
sha256sum "$W/out/$L-candidate.so" "$W/out/$L-symbols.so"

python3 "$W/measure.py" "$W/out/$L-symbols.so" > "$W/out/$L.json"
python3 -c "import json;d=json.load(open('$W/out/$L.json'));print('$L', d['matched'], d['raw'], d['unique_pairs'])"
