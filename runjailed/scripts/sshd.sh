### roomba::unjailed
## This script creates the initial SSH socket.

. /opt/irobot/persistent/opt/runjailed/scripts/common.sh

FILE="$SCRIPTS_DIR/sshd.socket"

if [ ! -f "$FILE" ]; then
  echo "$FILE does not exist."
  exit 1
fi

mount --bind $SCRIPTS_DIR/sshd.socket /lib/systemd/system/sshd.socket
systemctl start sshd.socket