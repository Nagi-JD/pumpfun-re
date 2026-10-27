#!/bin/bash
# usage: build.sh <label> <srcdir containing programs/pump-amm>  ; direct-path v1.44 (no cargo-build-sbf wrapper)
set -e
V=${TV:-v1.44}
P=$HOME/.cache/solana/$V/platform-tools
L=$1; S=$2; W=/home/nagi/ammresearch
export PATH=$P/rust/bin:/usr/local/bin:/usr/bin:/bin RUSTC=$P/rust/bin/rustc CC=$P/llvm/bin/clang AR=$P/llvm/bin/llvm-ar
export CARGO_HOME=$W/netcargo CARGO_TARGET_DIR=$W/target-$V CARGO_BUILD_JOBS=4 CARGO_NET_OFFLINE=true RUSTFLAGS=-Zremap-cwd-prefix=
cd $S
cargo rustc --manifest-path $S/programs/pump-amm/Cargo.toml --release --target sbpf-solana-solana --locked --offline --lib -- $EXTRA > $W/out/$L-build.log 2>&1 || { tail -30 $W/out/$L-build.log; exit 1; }
cp $W/target-$V/sbpf-solana-solana/release/pump_amm_recovered.so $W/out/$L-symbols.so
$HOME/.cache/solana/v1.52/platform-tools/llvm/bin/llvm-objcopy --strip-all $W/out/$L-symbols.so $W/out/$L-candidate.so
sha256sum $W/out/$L-candidate.so $W/out/$L-symbols.so
python3 $W/tools/measure.py $W/out/$L-symbols.so > $W/out/$L.json
python3 -c "import json;d=json.load(open(\"$W/out/$L.json\"));print(\"$L\",d[\"matched\"],d[\"raw\"],d[\"unique_pairs\"])"
