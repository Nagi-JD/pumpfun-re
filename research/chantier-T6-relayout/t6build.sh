#!/bin/bash
# t6build.sh LABEL WORKDIR ORDERED_LD [EXTRA_RUSTFLAGS]
# Mirrors pumpround34/b34-merge.sh but writes to an isolated /home/nagi/t6work area.
set -e
L="$1"; W="$2"; ORD="$3"; EXTRA="${4:- -C passes=mergefunc}"
R=/home/nagi/pumpround34
R2=/home/nagi/t6work
P=$HOME/.cache/solana/v1.44/platform-tools
SC=$R/repro/pump/main-contract-round34-20261027/inputs/scripts
DEP=/home/nagi/pumpre/repo/evidence/original/pump/deployed.so
export PATH=$P/rust/bin:$HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin
export RUSTC=${RUSTC_SHIM:-$P/rust/bin/rustc} CC=$P/llvm/bin/clang AR=$P/llvm/bin/llvm-ar
export CARGO_HOME=$HOME/.cargo CARGO_TARGET_DIR=$R2/target CARGO_BUILD_JOBS=2 CARGO_NET_OFFLINE=true
export CARGO_TARGET_SBF_SOLANA_SOLANA_RUSTFLAGS="-Zremap-cwd-prefix=$EXTRA"
export RUSTC_WRAPPER=$SC/pump_text_layout_rustc.py PUMP_TEXT_ROOT_CRATE=pump_recovered PUMP_TEXT_PHYSICAL_WRAPPER=$SC/pump_physical_source_wrapper.py
export PUMP_TEXT_LINKER=$P/rust/lib/rustlib/x86_64-unknown-linux-gnu/bin/rust-lld PUMP_TEXT_SCRIPT=$ORD PUMP_TEXT_RECORD_DIR=$R2/link-$L PUMP_LOGICAL_REGISTRY_SRC=$CARGO_HOME/registry/src
rm -rf $R2/link-$L; mkdir -p $R2/out
cd $W
cargo build --manifest-path $W/programs/pump/Cargo.toml --release --target sbf-solana-solana --locked --offline --jobs 2 > $R2/out/$L-build.log 2>&1 || { tail -30 $R2/out/$L-build.log; exit 1; }
cp $R2/target/sbf-solana-solana/release/pump_recovered.so $R2/out/$L-symbols.so
$P/llvm/bin/llvm-objcopy --strip-all $R2/out/$L-symbols.so $R2/out/$L-candidate.so
echo -n "SHA "; sha256sum $R2/out/$L-candidate.so | cut -d' ' -f1
python3 $R/metric/measure.py $DEP $R2/out/$L-candidate.so $R2/out/$L-symbols.so --dump $R2/out/$L-m.json | tail -1
