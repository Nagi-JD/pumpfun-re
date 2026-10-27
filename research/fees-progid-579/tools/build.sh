#!/bin/bash
# Mirrors research/fees-sharing-slice-recovery/build.py (native instead of podman).
set -e
P=$HOME/.cache/solana/v1.44/platform-tools
L=${1:-sharing-577-joint}
R=/home/nagi/pumpre/feesbuild
B=$R/$L
export PATH=$P/rust/bin:/usr/local/bin:/usr/bin:/bin RUSTC=$P/rust/bin/rustc CC=$P/llvm/bin/clang AR=$P/llvm/bin/llvm-ar
export CARGO_HOME=$R/cargo CARGO_TARGET_DIR=$R/target CARGO_BUILD_JOBS=1 CARGO_NET_OFFLINE=true RUSTFLAGS=-Zremap-cwd-prefix=
cd $B
cargo rustc --verbose --manifest-path $B/programs/pump-fees/Cargo.toml --release --target sbpf-solana-solana --locked --offline --jobs 1 --lib -- \
 --remap-path-prefix=$B/programs/pump-fees/src/../../../pump-fees-math/=pump-fees-math/ \
 --remap-path-prefix=$B/pump-fees-math/=pump-fees-math/ \
 --remap-path-prefix=programs/pump-fees/src/../../../pump-fees-math/=pump-fees-math/ > $R/$L-build.log 2>&1 || { tail -30 $R/$L-build.log; exit 1; }
cp $R/target/sbpf-solana-solana/release/pump_fees_candidate.so $R/$L-symbols.so
$HOME/.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objcopy --strip-all $R/$L-symbols.so $R/$L-candidate.so
sha256sum $R/$L-symbols.so $R/$L-candidate.so
