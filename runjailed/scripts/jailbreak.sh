### roomba::unjailed
## This script will perform a minimal jailbreak by unlocking the system and enabling SSH access.
## This assumes the roomba::unjailed binary has been delivered, as it handles everything else.

RUNJAILED_DIR=/opt/irobot/persistent/opt/runjailed
SCRIPTS_DIR=$RUNJAILED_DIR/scripts

$RUNJAILED_DIR/runjailed --download-scripts $SCRIPTS_DIR

sh $SCRIPTS_DIR/sshd.sh