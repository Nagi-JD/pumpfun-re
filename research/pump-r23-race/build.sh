#!/bin/bash
# usage: build.sh LABEL [srcdir]   ; EXTRA env = extra rustc flags for the pump crate only
set -e
P=$HOME/.cache/solana/v1.44/platform-tools
L=${1:-base}; R=/home/nagi/pumpround23; B=${2:-$R/src}
export PATH=$P/rust/bin:$HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin RUSTC=$P/rust/bin/rustc CC=$P/llvm/bin/clang AR=$P/llvm/bin/llvm-ar
export CARGO_HOME=/home/nagi/pumpround23/cargo CARGO_TARGET_DIR=$R/target CARGO_BUILD_JOBS=3 CARGO_NET_OFFLINE=true CARGO_TARGET_SBF_SOLANA_SOLANA_RUSTFLAGS=-Zremap-cwd-prefix=
mkdir -p $R/out
cd $B
$P/rust/bin/cargo rustc -p pump-recovered --release --target sbf-solana-solana --locked --offline --lib --jobs 3 -- $EXTRA > $R/out/$L-build.log 2>&1 || { tail -30 $R/out/$L-build.log; exit 1; }
cp $R/target/sbf-solana-solana/release/pump_recovered.so $R/out/$L-symbols.so
$P/llvm/bin/llvm-objcopy --strip-all $R/out/$L-symbols.so $R/out/$L-candidate.so
sha256sum $R/out/$L-symbols.so $R/out/$L-candidate.so
python3 /home/nagi/pumpresearch/metric/measure.py /home/nagi/pumpre/repo/evidence/original/pump/deployed.so $R/out/$L-candidate.so $R/out/$L-symbols.so --dump $R/out/$L-m.json | tail -5
