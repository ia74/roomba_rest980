### roomba::unjailed
## This script is meant to run initially to setup runjailed.

. /opt/irobot/persistent/opt/runjailed/scripts/common.sh

FILE="/opt/irobot/config/provisioning"
LOCAL_IP=$1

if [ ! -f "$FILE" ]; then
  echo "$FILE does not exist. What?!"
  exit 1
fi

sed -i 's/SYSTEM_ACCESS.*/SYSTEM_ACCESS="unlocked"/' /opt/irobot/config/provisioning

curl http://$LOCAL_IP:8883/done/unlocking

bash -c "$SCRIPTS_DIR/sshd.sh"

curl http://$LOCAL_IP:8883/done/ssh

python $SCRIPTS_DIR/jailbreak.py &

curl http://localhost:8080/ | echo $RUNJAILED_DIR

/usr/bin/play_opus.sh -f /opt/irobot/audio/songs/spot-clean-start.opus