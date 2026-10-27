#!/bin/bash
# build-exact.sh LABEL : their controller.py command, run natively (no podman)
L=$1; S=/work/next641/$L
cd $S
env -i HOME=$HOME PATH=/work/sdk/rust/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin RUSTC=/work/sdk/rust/bin/rustc CC=/work/sdk/llvm/bin/clang AR=/work/sdk/llvm/bin/llvm-ar CARGO_HOME=/cargo CARGO_TARGET_DIR=/work/target CARGO_BUILD_JOBS=1 CARGO_NET_OFFLINE=true RUSTFLAGS=-Zremap-cwd-prefix= \
 /work/sdk/rust/bin/cargo rustc --verbose --manifest-path $S/programs/pump-fees/Cargo.toml --release --target sbpf-solana-solana --locked --offline --jobs 1 --lib -- \
 --remap-path-prefix=$S/programs/pump-fees/src/../../../pump-fees-math/=pump-fees-math/ --remap-path-prefix=$S/pump-fees-math/=pump-fees-math/ --remap-path-prefix=programs/pump-fees/src/../../../pump-fees-math/=pump-fees-math/ \
 -C link-arg=-Map=/work/next641/$L.map -C linker=$S/linker.sh > /work/next641/$L-build.log 2>&1 || { tail -30 /work/next641/$L-build.log; exit 1; }
cp /work/target/sbpf-solana-solana/release/pump_fees_candidate.so /work/next641/$L-symbols.so
$HOME/.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objcopy --strip-all /work/next641/$L-symbols.so /work/next641/$L-candidate.so
sha256sum /work/next641/$L-symbols.so /work/next641/$L-candidate.so
