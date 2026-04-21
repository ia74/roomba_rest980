# roomba::unjailed

These are the scripts for the roomba::unjailed project, a jailbreak for most `lewis` Roomba models (i,j series), with more support to come.

> Using this jailbreak will not make your Roomba less secure, unless you expose ports `1883` (internal MQTT broker) or `22` (runjailed SSH server). These allow unrestricted access to the `cleantrack` daemon, with no root password.

## Supported Versions

- 22.52.08+
- Everything else is untested!!

## Introduction

`runjailed.py` is the Python host script, as Roomba has Python 2.7 pre-installed.

`jailbreak.py` jailbreaks a Roomba, and downloads `runjailed.py` to it.

The exploit takes advantage of a MQTT input sanitization vulnerability, gaining ACE as the `apps` user.

Luckily for us, the Roomba is based on BusyBox, so it has `busybox.suid`, and it's one of the few commands `apps` is allowed to run.

We use the ACE vulnerability to gain root access and download the `runjailed` script, which performs the rest of the jailbreak with the included scripts.

## Features

| Feature | Status |
|---------|--------|
| Root ACE | ✅ |
| SSH, FTP | ✅ |
| Exfiltrate PMap data | ✅ |
| Expose new internal MQTT messages to the public | 🛠️ |
| Expose Timeline Report to the public | 🛠️ |
| Communication with mobility/auxiliary boards | 🛠️ |
| Downgrading | ⚠️ |

🛠️: WIP  
⚠️: WIP, risky  

## Scripts

> `runjailed` and these scripts assume you already have obtained root access. Note that you can perform most of the scripts anyways using the BusyBox SUID script, but it's better to have root anyway.

- `jailbreak.sh`: The initial script, only ran once by `jailbreak.py`, runs `sshd.sh` to begin an SSH server for a more stable connection.
- `enableDevMode.sh`: Sets the provisioning configuration key `DEV_MODE` to `enabled` from `disabled`.
- `ftp.sh`: Uses `tcpsvd` to host a simple FTPd server with write access from the `/` root on port 21.
- `sshd.sh`: Opens a SSH server on port 21.
- `unlock.sh`:  Sets the provisioning configuration key `SYSTEM_ACCESS` to `unlocked` from `locked`. This brings down the strict firewall rules.