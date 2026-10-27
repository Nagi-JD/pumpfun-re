#!/bin/bash
# Reproduce lalalune/pumpfun-source's Fees checkpoint (research/fees-sharing-slice-recovery,
# MIT, upstream e57657de) natively, mirroring their build.py (podman) recipe.
# Verified output: stripped sha256 39b8fc901792a6fb67e3e10429e607788497eaf9d3d8848690f4ab0a4ded8cae
# (== claims.json candidate_sha256), 577/585 matched windows, 143 exact bodies.
# Recipe: platform-tools v1.44 rustc via direct `cargo rustc` (NOT cargo-build-sbf, which yields a
# different layout), anchor 0.31.1, cgu1/opt3, strip with v1.52 llvm-objcopy.
# Usage: R=<work dir> with <work dir>/<label> = decompressed checkpoint sources; ./fees_oracle_build.sh <label>
set -e
P=$HOME/.cache/solana/v1.44/platform-tools
L=${1:-sharing-577-joint}
R=${R:-$PWD}
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
