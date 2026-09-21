"""Tiny Connect-compatible DEVELOPMENT STUB.

This is not the printer mock and not production backend code. It exists only so
that the printer simulator can be exercised end-to-end without your team's
backend being ready yet.
"""
from __future__ import annotations

import itertools
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Development Connect Stub")
ROOT = Path("./storage/connect-stub").resolve()
ROOT.mkdir(parents=True, exist_ok=True)
COMMAND_IDS = itertools.count(1)
COMMANDS: dict[str, deque[tuple[int, dict[str, Any]]]] = defaultdict(deque)
EVENTS: list[dict[str, Any]] = []
TELEMETRY: dict[str, dict[str, Any]] = {}


class QueueCommand(BaseModel):
    command: str
    args: list[Any] | None = None
    kwargs: dict[str, Any] | None = None


@app.post("/p/telemetry")
async def telemetry(
    request: Request,
    fingerprint: str = Header(alias="Fingerprint"),
):
    TELEMETRY[fingerprint] = await request.json()
    if not COMMANDS[fingerprint]:
        return Response(status_code=204)
    command_id, command = COMMANDS[fingerprint].popleft()
    return JSONResponse(
        command,
        status_code=200,
        headers={"Command-Id": str(command_id)},
    )


@app.post("/p/events", status_code=204)
async def events(
    request: Request,
    fingerprint: str = Header(alias="Fingerprint"),
):
    EVENTS.append({"fingerprint": fingerprint, "payload": await request.json()})
    return Response(status_code=204)


@app.get("/p/teams/{team_id}/files/{file_hash}/raw")
def raw_file(team_id: int, file_hash: str):
    path = ROOT / str(team_id) / file_hash
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return Response(content=path.read_bytes(), media_type="application/octet-stream")


@app.put("/dev/files/{team_id}/{file_hash}")
async def put_file(team_id: int, file_hash: str, request: Request):
    data = await request.body()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    directory = ROOT / str(team_id)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / file_hash
    path.write_bytes(data)
    return {"stored": True, "bytes": len(data)}


@app.post("/dev/printers/{fingerprint}/commands")
def queue_command(fingerprint: str, command: QueueCommand):
    command_id = next(COMMAND_IDS)
    payload: dict[str, Any] = {"command": command.command}
    if command.args is not None:
        payload["args"] = command.args
    if command.kwargs is not None:
        payload["kwargs"] = command.kwargs
    COMMANDS[fingerprint].append((command_id, payload))
    return {"command_id": command_id, "queued": payload}


@app.get("/dev/events")
def get_events():
    return EVENTS


@app.get("/dev/telemetry")
def get_telemetry():
    return TELEMETRY
