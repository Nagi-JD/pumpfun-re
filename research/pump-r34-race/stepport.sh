#!/bin/bash
# stepport.sh NEWSTEP PREVSTEP FILE... : copy our w_F version of each FILE, port R23->R34 changes, build, compare
SP=/mnt/d/dev/tmp/claude/C--Users-jojod/320d21c7-3065-4245-af9c-7d59f1ee86fc/scratchpad; R=/home/nagi/pumpround34
O=/home/nagi/pumpround23/src/programs/pump/src; F=/home/nagi/pumpround23/w_F/programs/pump/src
NS=$1; PS=$2; shift 2
rm -rf $R/$NS; cp -r $R/$PS $R/$NS; N=$R/$NS/programs/pump/src
for f in "$@"; do cp $F/$f $N/$f; python3 $SP/port.py $O/$f $R/w0/programs/pump/src/$f $N/$f --write || exit 1; done
python3 $SP/sites.py $R/$NS | tail -1
bash $R/step.sh $NS $R/$NS $PS
