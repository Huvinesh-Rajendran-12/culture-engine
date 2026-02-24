"""Simple agent runner API."""

import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .agents.base import run_agent

load_dotenv()

app = FastAPI(title="Agent Runner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_WORKSPACE = str(ROOT_DIR / "workspace")


class RunRequest(BaseModel):
    prompt: str
    system_prompt: str = ""
    team: str = "default"
    workspace_dir: Optional[str] = None
    allowed_tools: Optional[list[str]] = None
    max_turns: int = 50


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/run")
async def run(req: RunRequest):
    workspace = req.workspace_dir or DEFAULT_WORKSPACE

    async def event_generator():
        async for event in run_agent(
            prompt=req.prompt,
            system_prompt=req.system_prompt,
            workspace_dir=workspace,
            team=req.team,
            allowed_tools=req.allowed_tools,
            max_turns=req.max_turns,
        ):
            yield f"data: {event}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
