set -e
R=/home/nagi/pumpround23; S=/mnt/d/dev/tmp/claude/C--Users-jojod/320d21c7-3065-4245-af9c-7d59f1ee86fc/scratchpad
STEP=$1; PREV=$2
rm -rf $R/w_$STEP; cp -r $R/$PREV $R/w_$STEP
for x in ${3:-$STEP}; do python3 $S/edit.py $R/w_$STEP $x $4; done
grep -rc "err_at!" $R/w_$STEP/programs/pump/src | grep -v ":0" || true
bash $R/build.sh u$STEP $R/w_$STEP
python3 $R/gl.py s10 u$STEP
