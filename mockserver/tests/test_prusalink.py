"""PrusaLink facade tests with a stub worker (the real SDK worker needs Linux inotify)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.prusalink import USERNAME, build_router


class StubSimulator:
    def __init__(self) -> None:
        self.running = False
        self.calls: list[str] = []

    def stop(self) -> None:
        self.calls.append("stop")
        self.running = False

    def pause(self) -> None:
        self.calls.append("pause")

    def resume(self) -> None:
        self.calls.append("resume")


class StubWorker:
    def __init__(self, root: Path) -> None:
        self.config = SimpleNamespace(token="secret-token", gcode_printer_model="COREONE")
        self.root = root
        self.simulator = StubSimulator()
        self.valid = True
        self.state = "READY"

    def storage_path(self, relative_path: str) -> Path:
        target = (self.root / relative_path).resolve()
        if self.root.resolve() not in target.parents:
            raise ValueError("Path escapes printer storage")
        return target

    def status(self):
        tool = SimpleNamespace(slot=0, temperature_c=214.9, target_temperature_c=215.0)
        return SimpleNamespace(
            state=self.state,
            progress_percent=12.5 if self.simulator.running else 0.0,
            time_remaining_s=3000.4,
            elapsed_s=400.2,
            toolheads=[tool],
            active_tool=0,
            temp_bed_c=59.5,
            target_bed_c=60.0,
        )

    def handle_upload(self, relative_path: str, print_after_upload: bool) -> None:
        if not self.valid:
            self.state = "ATTENTION"
            return
        self.state = "READY"
        if print_after_upload:
            self.simulator.running = True
            self.state = "PRINTING"


class StubManager:
    def __init__(self, worker: StubWorker) -> None:
        self.worker = worker

    def get(self, printer_id: str) -> StubWorker:
        if printer_id != "mock-1":
            raise KeyError(printer_id)
        return self.worker


@pytest.fixture()
def env(tmp_path: Path):
    worker = StubWorker(tmp_path)
    app = FastAPI()
    app.include_router(build_router(StubManager(worker)))
    client = TestClient(app, base_url="http://mock", follow_redirects=False)
    auth = httpx.DigestAuth(USERNAME, "secret-token")
    return client, worker, auth, "/prusalink/mock-1"


def test_requires_digest_auth(env) -> None:
    client, _, _, base = env
    resp = client.get(f"{base}/api/v1/status")
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"].startswith("Digest ")
    bad = client.get(f"{base}/api/v1/status", auth=httpx.DigestAuth(USERNAME, "wrong"))
    assert bad.status_code == 401


def test_unknown_printer_is_404(env) -> None:
    client, _, auth, _ = env
    assert client.get("/prusalink/nope/api/v1/status", auth=auth).status_code == 404


def test_status_idle_then_printing(env) -> None:
    client, worker, auth, base = env
    body = client.get(f"{base}/api/v1/status", auth=auth).json()
    assert body["printer"]["state"] == "READY" and "job" not in body
    assert client.get(f"{base}/api/v1/job", auth=auth).status_code == 204

    worker.simulator.running, worker.state = True, "PRINTING"
    body = client.get(f"{base}/api/v1/status", auth=auth).json()
    assert body["printer"]["state"] == "PRINTING"
    assert body["job"] == {"id": 1, "progress": 12.5, "time_remaining": 3000, "time_printing": 400}
    assert client.get(f"{base}/api/v1/job", auth=auth).json()["id"] == 1


def test_upload_and_print_then_stop(env) -> None:
    client, worker, auth, base = env
    resp = client.put(
        f"{base}/api/v1/files/usb/job.gcode",
        content=b"G28\n",
        headers={"Print-After-Upload": "?1", "Overwrite": "?1"},
        auth=auth,
    )
    assert resp.status_code == 201
    assert worker.storage_path("job.gcode").read_bytes() == b"G28\n"
    job = client.get(f"{base}/api/v1/job", auth=auth).json()
    assert job["id"] == 1

    # A second print while busy is refused.
    busy = client.put(f"{base}/api/v1/files/usb/b.gcode", content=b"x",
                      headers={"Print-After-Upload": "?1"}, auth=auth)
    assert busy.status_code == 409

    assert client.delete(f"{base}/api/v1/job/999", auth=auth).status_code == 404
    assert client.put(f"{base}/api/v1/job/{job['id']}/pause", auth=auth).status_code == 204
    assert client.delete(f"{base}/api/v1/job/{job['id']}", auth=auth).status_code == 204
    assert worker.simulator.calls == ["pause", "stop"]

    # The next print gets a new job id.
    client.put(f"{base}/api/v1/files/usb/c.gcode", content=b"x",
               headers={"Print-After-Upload": "?1"}, auth=auth)
    assert client.get(f"{base}/api/v1/job", auth=auth).json()["id"] == 2


def test_invalid_file_puts_printer_in_attention(env) -> None:
    client, worker, auth, base = env
    worker.valid = False
    resp = client.put(f"{base}/api/v1/files/usb/bad.gcode", content=b"x",
                      headers={"Print-After-Upload": "?1"}, auth=auth)
    assert resp.status_code == 201
    assert client.get(f"{base}/api/v1/status", auth=auth).json()["printer"]["state"] == "ATTENTION"
    assert client.get(f"{base}/api/v1/job", auth=auth).status_code == 204


def test_overwrite_and_start_missing_file(env) -> None:
    client, _, auth, base = env
    url = f"{base}/api/v1/files/usb/a.gcode"
    assert client.put(url, content=b"1", auth=auth).status_code == 201
    assert client.put(url, content=b"2", auth=auth).status_code == 409
    assert client.put(url, content=b"2", headers={"Overwrite": "?1"}, auth=auth).status_code == 201
    assert client.post(f"{base}/api/v1/files/usb/missing.gcode", auth=auth).status_code == 404
    assert client.post(url, auth=auth).status_code == 204


def test_rejects_unknown_storage_and_path_traversal(env) -> None:
    client, _, auth, base = env
    assert client.put(f"{base}/api/v1/files/sdcard/a.gcode", content=b"x", auth=auth).status_code == 404
    assert client.put(f"{base}/api/v1/files/usb/../../evil.gcode", content=b"x", auth=auth).status_code in (400, 404)
