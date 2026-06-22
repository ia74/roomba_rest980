### roomba::unjailed
## This sets up a roomba::unjailed environment to execute internal scripts with.

RUNJAILED_VERSION="1.0.0-dev"
RUNJAILED_DIR=/opt/irobot/persistent/opt/runjailed
SCRIPTS_DIR=$RUNJAILED_DIR/scripts

WEBROOT_PREF="https://raw.githubusercontent.com/ia74/roomba_rest980/refs/heads/main/runjailed"
WEBPREFIX=$WEBROOT_PREF/scripts

LIST="$WEBPREFIX/common.sh $WEBPREFIX/enableDevMode.sh $WEBPREFIX/ftp.sh $WEBPREFIX/sshd.sh $WEBPREFIX/sshd.socket $WEBROOT_PREF/jailbreak.py $WEBPREFIX/http.service"
