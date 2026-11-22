import argparse
import json
import os
import sys
import threading
import time

if extra := os.environ.get("SIM2WEB_R6_TRAME_LIB"):
    sys.path.append(extra)
import psutil

p=argparse.ArgumentParser()
p.add_argument("node",type=int)
p.add_argument("server",type=int)
a=p.parse_args()
root=psutil.Process(a.node)
server=psutil.Process(a.server) if a.server else None
lock=threading.Lock()
done=threading.Event()
peak=dict(chrome_rss=0,python_rss=0,chrome_max_processes=0,samples=0)
def read_server():
    if not server: return 0,0
    try:
        with server.oneshot():
            c=server.cpu_times()
            m=server.memory_info()
            return max(m.rss,getattr(m,"peak_wset",0)),c.user+c.system
    except psutil.Error: return 0,0
def sampling():
    target=time.perf_counter()
    while not done.is_set():
        rss=0
        count=0
        try: procs=root.children(recursive=True)
        except psutil.Error: procs=[]
        for proc in procs:
            try:
                with proc.oneshot():
                    if proc.name().lower() not in ("chrome.exe","chrome","chromium.exe","chromium"):continue
                    rss+=proc.memory_info().rss
                    count+=1
            except psutil.Error: pass
        py,_=read_server()
        with lock:
            peak["chrome_rss"]=max(peak["chrome_rss"],rss)
            peak["python_rss"]=max(peak["python_rss"],py)
            peak["chrome_max_processes"]=max(peak["chrome_max_processes"],count)
            peak["samples"]+=1
        target+=.1
        if target<time.perf_counter():target=time.perf_counter()
        done.wait(max(0,target-time.perf_counter()))
threading.Thread(target=sampling,daemon=True).start()
print("ready",flush=True)
for line in sys.stdin:
    command=line.strip()
    if command=="quit": break
    with lock: record=dict(peak)
    record["server_cpu_s"]=read_server()[1]
    print(json.dumps(record),flush=True)
done.set()
