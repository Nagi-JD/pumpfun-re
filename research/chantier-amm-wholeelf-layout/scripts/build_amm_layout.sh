#!/bin/bash
# Build btree AMM through the text-layout shim; record link receipt + map; measure.
V=v1.44
P=$HOME/.cache/solana/$V/platform-tools
S=$HOME/chantier-matched/btree
SCR=$HOME/pumpround34/scripts
O=$HOME/ammlayout
L=amm_seed
mkdir -p "$O"
rm -rf "$O/link" "$HOME/chantier-matched/target-ammlayout-$V"
REMAP="--remap-path-prefix=src/=programs/pump-amm/src/ --remap-path-prefix=src/legacy_buy.rs=programs/pump-amm/src/instructions/swap/buy.rs --remap-path-prefix=src/legacy_sell.rs=programs/pump-amm/src/instructions/swap/sell.rs"
export PATH=$P/rust/bin:/usr/local/bin:/usr/bin:/bin RUSTC=$P/rust/bin/rustc CC=$P/llvm/bin/clang AR=$P/llvm/bin/llvm-ar
export CARGO_HOME=$HOME/.cargo CARGO_TARGET_DIR=$HOME/chantier-matched/target-ammlayout-$V CARGO_BUILD_JOBS=4 CARGO_NET_OFFLINE=true RUSTFLAGS=-Zremap-cwd-prefix=
export RUSTC_WRAPPER="$SCR/pump_text_layout_rustc.py"
export PUMP_TEXT_ROOT_CRATE=pump_amm_recovered
export PUMP_TEXT_PHYSICAL_WRAPPER="$SCR/pump_physical_source_wrapper.py"
export PUMP_TEXT_LINKER="$P/rust/lib/rustlib/x86_64-unknown-linux-gnu/bin/rust-lld"
export PUMP_TEXT_SCRIPT="$O/seed_text_only.ld"
export PUMP_TEXT_RECORD_DIR="$O/link"
echo "PUMP_TEXT_LINKER exists: $(ls -la "$PUMP_TEXT_LINKER" 2>&1 | head -1)"
cd "$S"
cargo rustc --manifest-path "$S/programs/pump-amm/Cargo.toml" --release --target sbpf-solana-solana --locked --offline --lib -- $REMAP > "$O/$L-build.log" 2>&1
rc=$?
echo "build rc=$rc"
if [ $rc -ne 0 ]; then echo "---build log tail---"; tail -35 "$O/$L-build.log"; exit $rc; fi
echo "=== link receipt present? ==="
ls -la "$O/link" 2>&1 | head
cp "$CARGO_TARGET_DIR/sbpf-solana-solana/release/pump_amm_recovered.so" "$O/$L-symbols.so"
python3 /home/nagi/ammresearch/tools/measure.py "$O/$L-symbols.so" > "$O/$L.json" 2>"$O/$L.err"
if [ -s "$O/$L.err" ]; then echo "measure err:"; tail -3 "$O/$L.err"; fi
python3 -c "import json;d=json.load(open('$O/$L.json'));print('RESULT $L matched',d['matched'],'raw',d['raw'],'unmatched',len(d['unmatched']))" 2>&1
