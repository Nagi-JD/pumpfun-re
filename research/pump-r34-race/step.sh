#!/bin/bash
# step.sh LABEL DIR PREVLABEL : build+measure with spoofed host, compare matched AND raw sets to PREVLABEL
R=/home/nagi/pumpround34
CH=$(cat $R/CH_PATH) RUSTC_SHIM=$R/shim/rustc bash $R/b34.sh $1 $2 | tail -1
python3 $R/cmp2.py $R/out/$3-m.json $R/out/$1-m.json
