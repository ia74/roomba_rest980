### roomba::unjailed
## This script downloads the runjailed daemon.

. /opt/irobot/persistent/opt/runjailed/scripts/common.sh

WEB_PREFIX=https://raw.githubusercontent.com/ia74/roomba_rest980/refs/heads/main/runjailed

wget $WEB_PREFIX/jailbreak.py -O $RUNJAILED_DIR/jailbreak.py