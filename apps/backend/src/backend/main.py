import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from .agents import generate_workflow
from .models import HealthResponse, WorkflowRequest

load_dotenv()

app = FastAPI(
    title="FlowForge API",
    description="AI agents that design, build, and run workflows from natural language",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok")


@app.post("/api/workflows/generate")
async def create_workflow(request: WorkflowRequest):
    """Generate a workflow from natural language description.

    Streams Server-Sent Events with agent progress:
    - text: Agent's reasoning and explanations
    - tool_use: Tools being called (Write, Bash, etc.)
    - result: Final result with cost/usage
    - error: Any errors encountered
    """

    async def event_stream():
        async for message in generate_workflow(
            description=request.description,
            context=request.context,
        ):
            yield f"data: {json.dumps(message)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
