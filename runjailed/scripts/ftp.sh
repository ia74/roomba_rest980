### roomba::unjailed
## This script will start FTPd (temporarily on :21)

tcpsvd -vE 0.0.0.0 21 ftpd -w /