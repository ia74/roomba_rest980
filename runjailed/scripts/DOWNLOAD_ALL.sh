ROOT_PREF="https://raw.githubusercontent.com/ia74/roomba_rest980/refs/heads/main/runjailed"

PREFIX=$ROOT_PREF/scripts

RUNJAILED_DIR=/opt/irobot/persistent/opt/runjailed
SCRIPTS_DIR=$RUNJAILED_DIR/scripts
LOCAL_IP=$1

cd $SCRIPTS_DIR

rm *

LIST="$PREFIX/common.sh $PREFIX/enableDevMode.sh $PREFIX/ftp.sh $PREFIX/sshd.sh $PREFIX/sshd.socket $PREFIX/unlock.sh $ROOT_PREF/jailbreak.py"

for item in "${LIST[@]}"; do
    echo "Downloading $item..."
    wget $item
    chmod a+x $item
done

curl http://$LOCAL_IP:8883/done/downloading

# /usr/bin/play_opus.sh -f /opt/irobot/audio/songs/handoff.opus

bash -c "$SCRIPTS_DIR/unlock.sh $LOCAL_IP"