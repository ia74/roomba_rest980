### roomba::unjailed
## This script enables Developer mode

FILE="/opt/irobot/config/provisioning"

if [ ! -f "$FILE" ]; then
  echo "$FILE does not exist. What?!"
  exit 1
fi

sed -i 's/DEV_MODE.*/DEV_MODE="enabled"/' /opt/irobot/config/provisioning