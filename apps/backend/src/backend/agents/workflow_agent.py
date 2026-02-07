"""Workflow agent that designs, builds, and tests workflows using Claude Agent SDK."""

import tempfile
from pathlib import Path
from typing import Any, AsyncGenerator

from .base import load_knowledge_base, run_agent

WORKFLOW_AGENT_SYSTEM_PROMPT = """You are FlowForge, an AI agent that builds and tests executable workflows from natural language descriptions.

You have access to an organization's knowledge base. Use it to create tailored workflows.

## Your Task

1. **Read** the knowledge base to understand systems, roles, and policies
2. **Write** executable Python code to `workflow.py` using the Write tool
3. **Run** the code with `python workflow.py` to test it
4. **Fix** any errors and re-run if needed
5. **Summarize** what the workflow does

## Critical Requirements
- ALWAYS use the Write tool to create `workflow.py` - DO NOT use bash/cat/echo to create files
- The Write tool automatically saves to the correct workspace directory
- Keep code simple with realistic outputs (e.g., "Created Slack channel #welcome-alice")
- Include a main() function with proper error handling
- DO NOT use task/todo management tools

## Organization Knowledge Base

{knowledge_base}
"""


async def generate_workflow(
    description: str,
    context: dict[str, Any] | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Generate, build, and test a workflow from natural language.

    Args:
        description: Natural language description of the desired workflow
        context: Optional additional context (employee name, department, etc.)

    Yields:
        Message dicts with type and content
    """
    kb = load_knowledge_base()
    system_prompt = WORKFLOW_AGENT_SYSTEM_PROMPT.format(knowledge_base=kb)
    workspace = tempfile.mkdtemp(prefix="flowforge-")

    prompt = f"Your workspace directory is: {workspace}\nWrite all files there using absolute paths (e.g., {workspace}/workflow.py).\n\nDesign, build, and test a workflow for the following request:\n\n{description}"

    if context:
        prompt += f"\n\nAdditional context:\n"
        for key, value in context.items():
            prompt += f"- {key}: {value}\n"

    async for message in run_agent(
        prompt=prompt,
        system_prompt=system_prompt,
        workspace_dir=workspace,
        allowed_tools=["Read", "Write", "Edit", "Bash", "Glob"],
        max_turns=30,
    ):
        yield message

    yield {
        "type": "workspace",
        "content": {"path": workspace},
    }
