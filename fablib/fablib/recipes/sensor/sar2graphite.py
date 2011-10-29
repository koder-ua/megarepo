import os
import sys
import time
import socket
import signal
import subprocess

host, port = sys.argv[1].split(':')
prefix = sys.argv[2]
ctime = ""

def get_sock():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, int(port)))
    except socket.error:
        time.sleep(10)
        
def AMPMtoTimeStamp(st):
    tm, ampm = st.split(' ')
    h,m,s = tm.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)

os.environ['PATH'] = '.' + os.pathsep + os.environ['PATH']
sar = subprocess.Popen("sar -r -I SUM -B -R -b -S -W -u 1".split(),
                       stdout = subprocess.PIPE)


exit = False
def on_exit(sig, frame):
    global exit
    exit = True
    
signal.signal(signal.SIGINT, on_exit)

try:
    sarout = sar.stdout
    buff = []
    sock = get_sock()
    while not exit:
        try:
            ln = sarout.readline()
            if ln.strip() == '':
                sock.sendall("".join(buff))
                buff = []
            elif ln[0].isdigit():
                #ctime = AMPMtoTimeStamp(ln.strip())
                ctime = time.time()
            else:
                msg = "{0}.{1} {2}\n".format(prefix, ln.strip(), ctime)
                buff.append(msg)
        except socket.error:
            sock = get_sock()
finally:
    sar.kill()
    sar.wait()
