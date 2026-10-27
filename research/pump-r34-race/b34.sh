#!/bin/bash
# usage: b34.sh LABEL SRCDIR(workspace root) [ORDER.ld]
set -e
L=$1; W=$2; R=/home/nagi/pumpround34; ORD=${3:-$R/repro/pump/main-contract-round34-20261027/ordered.ld}
P=$HOME/.cache/solana/v1.44/platform-tools; SC=$R/repro/pump/main-contract-round34-20261027/inputs/scripts
export PATH=$P/rust/bin:$HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin RUSTC=${RUSTC_SHIM:-$P/rust/bin/rustc} CC=$P/llvm/bin/clang AR=$P/llvm/bin/llvm-ar
export CARGO_HOME=${CH:-$HOME/.cargo} CARGO_TARGET_DIR=$R/target CARGO_BUILD_JOBS=2 CARGO_NET_OFFLINE=true CARGO_TARGET_SBF_SOLANA_SOLANA_RUSTFLAGS=-Zremap-cwd-prefix=
export RUSTC_WRAPPER=$SC/pump_text_layout_rustc.py PUMP_TEXT_ROOT_CRATE=pump_recovered PUMP_TEXT_PHYSICAL_WRAPPER=$SC/pump_physical_source_wrapper.py \
  PUMP_TEXT_LINKER=$P/rust/lib/rustlib/x86_64-unknown-linux-gnu/bin/rust-lld PUMP_TEXT_SCRIPT=$ORD PUMP_TEXT_RECORD_DIR=$R/link-$L PUMP_LOGICAL_REGISTRY_SRC=$CARGO_HOME/registry/src
rm -rf $R/link-$L; mkdir -p $R/out
cd $W
cargo build --manifest-path $W/programs/pump/Cargo.toml --release --target sbf-solana-solana --locked --offline --jobs 2 > $R/out/$L-build.log 2>&1 || { tail -30 $R/out/$L-build.log; exit 1; }
cp $R/target/sbf-solana-solana/release/pump_recovered.so $R/out/$L-symbols.so
$P/llvm/bin/llvm-objcopy --strip-all $R/out/$L-symbols.so $R/out/$L-candidate.so
sha256sum $R/out/$L-symbols.so $R/out/$L-candidate.so
python3 /home/nagi/pumpround34/metric/measure.py /home/nagi/pumpre/repo/evidence/original/pump/deployed.so $R/out/$L-candidate.so $R/out/$L-symbols.so --dump $R/out/$L-m.json | tail -1
