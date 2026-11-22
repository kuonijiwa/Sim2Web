"""The workbench server, driven over HTTP as the browser interface drives it."""
import http.client
import io
import json
import threading
import time
import zipfile

import numpy as np
import pytest
import yaml

from sim2web.workbench import make_server

from conftest import make_block_model


@pytest.fixture
def server(tmp_path):
    grid, _ = make_block_model()
    model = tmp_path / "models" / "block.vtu"
    model.parent.mkdir()
    grid.save(model)
    project = tmp_path / "project"
    srv = make_server(project, port=0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv, model, project
    srv.shutdown()
    srv.server_close()


def _call(srv, method, path, body=None, host="127.0.0.1"):
    conn = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=60)
    headers = {"Host": f"{host}:{srv.server_address[1]}"}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    conn.request(method, path, body=data, headers=headers)
    res = conn.getresponse()
    raw = res.read()
    conn.close()
    if res.getheader("Content-Type", "").startswith("application/json"):
        return res.status, json.loads(raw)
    return res.status, raw


def _job(srv, kind, params=None):
    status, job = _call(srv, "POST", "/api/jobs", {"kind": kind, "params": params or {}})
    assert status == 202, job
    for _ in range(600):
        status, view = _call(srv, "GET", f"/api/jobs/{job['id']}")
        if view["state"] != "running":
            assert view["state"] == "done", view["error"] + "\n" + "\n".join(view["log"])
            return view
        time.sleep(0.05)
    raise TimeoutError(kind)


def test_open_edit_build_validate_export(server):
    srv, model, project = server
    status, state = _call(srv, "GET", "/api/project")
    assert status == 200 and state["config"] is None and state["errors"]

    view = _job(srv, "inspect", {"files": [str(model)], "names": ["step1"]})
    assert view["result"]["inspection"]["cells"] == 1000
    status, state = _call(srv, "GET", "/api/project")
    cfg = state["config"]
    assert cfg["input"]["stages"] == [{"file": str(model.resolve()), "name": "step1"}]
    assert cfg["fields"]["stress"]["order"] == "from_file"            # the file names its components
    assert (project / "case.yaml").is_file()

    # edit as the forms do: the configuration is validated and saved
    cfg["fields"]["stress"]["unit"] = "kPa"
    cfg["geometry"]["excavation"].update({"enabled": True, "strategy": "labels_then_stress"})
    cfg["sections"].update({"spacing": 2, "placement": "interior", "min_points": 0})
    cfg["output"]["viewer"] = False
    status, state = _call(srv, "PUT", "/api/config", {"config": cfg})
    assert status == 200 and state["errors"] == []
    saved = yaml.safe_load((project / "case.yaml").read_text())
    assert saved["fields"]["stress"]["unit"] == "kPa"

    bad = json.loads(json.dumps(cfg))
    bad["geometry"]["primary"] = "nonsense"
    status, state = _call(srv, "PUT", "/api/config", {"config": bad})
    assert any("geometry.primary" in e for e in state["errors"])
    _call(srv, "PUT", "/api/config", {"config": cfg})

    _job(srv, "preview")
    assert (project / ".sim2web" / "preview" / "model_cache" / "index.json").is_file()
    _job(srv, "build")
    _job(srv, "validate")
    status, state = _call(srv, "GET", "/api/project")
    assert state["built"] and state["validation"]["passed"], state["validation"]
    assert state["build_report"]["stages"][0]["section_count"] > 0

    assert (project / "site" / "validation" / "validation_summary.json").is_file()   # as `sim2web validate`
    _job(srv, "build")                                                                  # a rebuild clears it
    status, state = _call(srv, "GET", "/api/project")
    assert state["validation"] is None
    _job(srv, "validate", {"sections": 2})

    status, index = _call(srv, "GET", "/site/model_cache/index.json")
    assert status == 200 and index["schema"] == "sim2web-index/2"
    # same provenance as `sim2web build case.yaml`: the hash of the saved file
    import hashlib
    text = (project / "case.yaml").read_text(encoding="utf-8")
    assert index["config_sha256"] == hashlib.sha256(text.encode("utf-8")).hexdigest()
    status, raw = _call(srv, "GET", "/api/export")
    names = zipfile.ZipFile(io.BytesIO(raw)).namelist()
    assert "case.yaml" in names and "site/model_cache/index.json" in names


def test_only_one_task_runs_at_a_time(server):
    srv, model, _ = server
    status, first = _call(srv, "POST", "/api/jobs", {"kind": "inspect", "params": {"files": [str(model)]}})
    status2, second = _call(srv, "POST", "/api/jobs", {"kind": "inspect", "params": {"files": [str(model)]}})
    assert status == 202
    assert status2 in (202, 409)          # 409 while the first one is still running
    while _call(srv, "GET", f"/api/jobs/{first['id']}")[1]["state"] == "running":
        time.sleep(0.05)


def test_failures_are_reported_not_raised(server):
    srv, model, _ = server
    status, job = _call(srv, "POST", "/api/jobs", {"kind": "inspect", "params": {"files": [str(model) + ".missing"]}})
    while True:
        view = _call(srv, "GET", f"/api/jobs/{job['id']}")[1]
        if view["state"] != "running":
            break
        time.sleep(0.05)
    assert view["state"] == "failed" and "does not exist" in view["error"]
    assert _call(srv, "POST", "/api/jobs", {"kind": "format_disk"})[0] == 400


def test_requests_for_other_host_names_are_refused(server):
    srv, _, _ = server
    status, body = _call(srv, "GET", "/api/project", host="attacker.example")
    assert status == 403
    with pytest.raises(ValueError):
        make_server(".", host="0.0.0.0", port=0)


def test_file_listing_offers_folders_and_model_files(server, tmp_path):
    srv, model, _ = server
    (model.parent / "notes.txt").write_text("x")
    status, listing = _call(srv, "GET", f"/api/browse?path={model.parent}")
    names = [e["name"] for e in listing["entries"]]
    assert "block.vtu" in names and "notes.txt" not in names


def test_unnamed_stress_components_must_be_chosen(server):
    srv, model, project = server
    import pyvista as pv

    mesh = pv.read(model)
    values = np.array(mesh.cell_data["Stress"], copy=True)        # copy before removing (see convert._take)
    mesh.cell_data.remove("Stress")
    mesh.cell_data["S"] = values                                   # same values, no component names
    unnamed = model.parent / "unnamed.vtu"
    mesh.save(unnamed)
    _job(srv, "inspect", {"files": [str(unnamed)]})
    status, state = _call(srv, "GET", "/api/project")
    assert state["config"]["fields"]["stress"]["order"] == "from_file"
    assert any("does not name the components" in e for e in state["errors"])
    cfg = state["config"]
    cfg["fields"]["stress"]["order"] = "XX,YY,ZZ,XY,YZ,XZ"
    status, state = _call(srv, "PUT", "/api/config", {"config": cfg})
    assert state["errors"] == []
