#!/bin/bash
# direct-path native build (mirrors feesbuild/build.sh). usage: build.sh LABEL [srcdir] [tools]
set -e
T=${3:-v1.44}
P=$HOME/.cache/solana/$T/platform-tools
L=${1:-base}; R=/home/nagi/pumpresearch; B=${2:-$R/src}
export PATH=$P/rust/bin:$HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin RUSTC=$P/rust/bin/rustc CC=$P/llvm/bin/clang AR=$P/llvm/bin/llvm-ar
export CARGO_HOME=$R/cargo CARGO_TARGET_DIR=$R/target-$T CARGO_BUILD_JOBS=4 CARGO_NET_OFFLINE=true RUSTFLAGS=-Zremap-cwd-prefix=
mkdir -p $R/out
cd $B/programs/pump
$P/rust/bin/cargo rustc --manifest-path $B/programs/pump/Cargo.toml --release --target sbpf-solana-solana --locked --offline --lib -- $EXTRA > $R/out/$L-build.log 2>&1 || { tail -30 $R/out/$L-build.log; exit 1; }
cp $R/target-$T/sbpf-solana-solana/release/pump_recovered.so $R/out/$L-symbols.so
$HOME/.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objcopy --strip-all $R/out/$L-symbols.so $R/out/$L-candidate.so
sha256sum $R/out/$L-symbols.so $R/out/$L-candidate.so
python3 $R/metric/measure.py /home/nagi/pumpre/repo/evidence/original/pump/deployed.so $R/out/$L-candidate.so $R/out/$L-symbols.so --dump $R/out/$L-m.json
