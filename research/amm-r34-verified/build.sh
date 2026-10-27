#!/bin/bash
# usage: build_r34.sh <label> <srcdir containing programs/pump-amm> ; native direct-path v1.44
set -e
V=${TV:-v1.44}
P=$HOME/.cache/solana/$V/platform-tools
L=$1; S=$2; O=/home/nagi/ammr34/out
CH=${CH:-/home/nagi/ammr34/r34cargo}
export PATH=$P/rust/bin:/usr/local/bin:/usr/bin:/bin RUSTC=$P/rust/bin/rustc CC=$P/llvm/bin/clang AR=$P/llvm/bin/llvm-ar
export CARGO_HOME=$CH CARGO_TARGET_DIR=/home/nagi/ammr34/target-$V CARGO_BUILD_JOBS=${CARGO_BUILD_JOBS:-2} CARGO_NET_OFFLINE=true RUSTFLAGS=-Zremap-cwd-prefix=
cd $S
cargo rustc --manifest-path $S/programs/pump-amm/Cargo.toml --release --target sbpf-solana-solana --locked --offline --lib -- $EXTRA > $O/$L-build.log 2>&1 || { echo BUILD_FAILED; tail -40 $O/$L-build.log; exit 1; }
cp /home/nagi/ammr34/target-$V/sbpf-solana-solana/release/pump_amm_recovered.so $O/$L-symbols.so
$HOME/.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objcopy --strip-all $O/$L-symbols.so $O/$L-candidate.so
sha256sum $O/$L-candidate.so $O/$L-symbols.so
python3 /home/nagi/ammresearch/tools/measure.py $O/$L-symbols.so > $O/$L.json
python3 -c "import json;d=json.load(open('$O/$L.json'));print('RESULT',\"$L\",'matched',d['matched'],'raw',d['raw'],'uniq',d['unique_pairs'],'eqloc',d['equal_locations'])"
