#!/bin/bash
# CLEAN build of btree (dedicated cold target dir) -> true composite measure
V=v1.44
P=$HOME/.cache/solana/$V/platform-tools
S=$HOME/chantier-matched/btree
O=$HOME/chantier-matched/out
L=btree_clean
mkdir -p "$O"
rm -rf "$HOME/chantier-matched/target-btclean-$V"
REMAP="--remap-path-prefix=src/=programs/pump-amm/src/ --remap-path-prefix=src/legacy_buy.rs=programs/pump-amm/src/instructions/swap/buy.rs --remap-path-prefix=src/legacy_sell.rs=programs/pump-amm/src/instructions/swap/sell.rs"
export PATH=$P/rust/bin:/usr/local/bin:/usr/bin:/bin RUSTC=$P/rust/bin/rustc CC=$P/llvm/bin/clang AR=$P/llvm/bin/llvm-ar
export CARGO_HOME=$HOME/.cargo CARGO_TARGET_DIR=$HOME/chantier-matched/target-btclean-$V CARGO_BUILD_JOBS=4 CARGO_NET_OFFLINE=true RUSTFLAGS=-Zremap-cwd-prefix=
cd "$S"
cargo rustc --manifest-path "$S/programs/pump-amm/Cargo.toml" --release --target sbpf-solana-solana --locked --offline --lib -- $REMAP > "$O/$L-build.log" 2>&1
rc=$?
if [ $rc -ne 0 ]; then echo "BUILD_FAILED rc=$rc"; tail -25 "$O/$L-build.log"; exit $rc; fi
cp "$CARGO_TARGET_DIR/sbpf-solana-solana/release/pump_amm_recovered.so" "$O/$L-symbols.so"
python3 /home/nagi/ammresearch/tools/measure.py "$O/$L-symbols.so" > "$O/$L.json"
python3 -c "import json;d=json.load(open('$O/$L.json'));print('RESULT $L matched',d['matched'],'raw',d['raw'],'uniq',d['unique_pairs'],'eqloc',d.get('equal_locations'),'unmatched',len(d['unmatched']))"
