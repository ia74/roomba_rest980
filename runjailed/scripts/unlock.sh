### roomba::unjailed
## This script unlocks the firewall.

FILE="/opt/irobot/config/provisioning"

if [ ! -f "$FILE" ]; then
  echo "$FILE does not exist. What?!"
  exit 1
fi

sed -i 's/SYSTEM_ACCESS.*/SYSTEM_ACCESS="unlocked"/' /opt/irobot/config/provisioning