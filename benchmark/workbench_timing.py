"""Time the workbench steps on a project through its HTTP API.

    python benchmark/workbench_timing.py PROJECT_DIR [--out timing.json]

PROJECT_DIR must hold a valid case.yaml.  Runs read model, preview, build and
validate (every 5th section) as the interface does, and measures how quickly
the server answers interface requests while each task runs.
"""
import argparse
import http.client
import json
import platform
import threading
import time

from sim2web import __version__
from sim2web.workbench import make_server

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--out")
args = ap.parse_args()
srv = make_server(args.project, port=0)
threading.Thread(target=srv.serve_forever, daemon=True).start()
port = srv.server_address[1]

def call(method, path, body=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=600)
    c.request(method, path, body=json.dumps(body).encode() if body is not None else None,
              headers={"Host": f"127.0.0.1:{port}", "Content-Type": "application/json"})
    r = c.getresponse(); d = r.read(); c.close()
    return json.loads(d) if d[:1] in b"{[" else d

def job(kind, params=None):
    t = time.perf_counter()
    j = call("POST", "/api/jobs", {"kind": kind, "params": params or {}})
    lat = []
    while True:
        t0 = time.perf_counter(); v = call("GET", f"/api/jobs/{j['id']}"); t1 = time.perf_counter()
        t2 = time.perf_counter(); call("GET", "/api/project"); lat.append(max(t1 - t0, time.perf_counter() - t2))
        if v["state"] != "running":
            break
        time.sleep(0.4)
    assert v["state"] == "done", v["error"]
    return time.perf_counter() - t, max(lat), sorted(lat)[len(lat) // 2]

state = call("GET", "/api/project")
files = [s["file"] for s in state["config"]["input"]["stages"]]
res = {}
res["read_model (inspect)"] = job("inspect", {"files": files, "keep_settings": True})
res["preview (surfaces)"] = job("preview")
res["build (full)"] = job("build")
res["validate (every 5th section)"] = job("validate", {"sections": 5})
st = call("GET", "/api/project")
for k, (t, worst, median) in res.items():
    print(f"{k:32s} {t:7.1f} s   UI request latency: median {median*1000:5.0f} ms, worst {worst*1000:6.0f} ms")
print("errors:", st["errors"], "validation passed:", st["validation"]["passed"])
r = st["build_report"]["stages"][0]
print("primary bytes", r["primary_bytes"], "sections", r["section_count"])
if args.out:
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"sim2web": __version__, "platform": platform.platform(), "python": platform.python_version(),
                   "inputs": files, "validation_passed": st["validation"]["passed"],
                   "primary_bytes": r["primary_bytes"], "sections": r["section_count"],
                   "steps": {k: {"seconds": t, "ui_latency_median_s": m, "ui_latency_worst_s": w}
                             for k, (t, w, m) in res.items()},
                   "note": "client and server in one process; latency covers job status and project state"},
                  fh, indent=2)
srv.shutdown()
