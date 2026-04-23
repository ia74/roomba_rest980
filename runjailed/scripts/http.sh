### roomba::unjailed
## This script creates the initial HTTP socket.

. /opt/irobot/persistent/opt/runjailed/scripts/common.sh

FILE="$SCRIPTS_DIR/http.socket"

if [ ! -f "$FILE" ]; then
  echo "$FILE does not exist."
  exit 1
fi

mount --bind $FILE /lib/systemd/system/http.socket
systemctl enable --now http.socket