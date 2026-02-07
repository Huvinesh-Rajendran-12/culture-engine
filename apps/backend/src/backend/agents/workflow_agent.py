"""Workflow agent that designs, builds, and tests workflows using Claude Agent SDK."""

import tempfile
from pathlib import Path
from typing import Any, AsyncGenerator

from .base import load_knowledge_base, run_agent

WORKFLOW_AGENT_SYSTEM_PROMPT = """You are FlowForge, an AI agent that designs, builds, and runs executable workflows from natural language descriptions.

You have access to an organization's knowledge base which describes their systems, roles, and policies. Use this context to create workflows that are tailored to the organization.

## Your Process

1. **Discover**: Read the organization's knowledge base to understand available systems, roles, and policies.
2. **Design**: Create a structured workflow plan with steps, actors, dependencies, and integrations.
3. **Build**: Write executable Python code that implements the workflow. The code should:
   - Define each workflow step as a function
   - Include proper error handling and logging
   - Simulate API calls to the organization's systems (since we don't have real credentials)
   - Print clear status messages showing what each step does
   - Include a main() function that runs the full workflow
4. **Test**: Run the generated code using the Bash tool. If there are errors, fix them and re-run.
5. **Report**: After the code runs successfully, provide a clear summary including:
   - What the workflow does (in plain English for non-technical users)
   - The steps involved and their order
   - Which systems are integrated
   - The test results

## Rules
- Always write code to a file called `workflow.py` in the workspace
- Always run the code after writing it to verify it works
- If the code fails, fix it and re-run (up to 3 attempts)
- Keep the code simple and well-structured
- Include realistic simulated outputs (e.g., "Created Slack channel #welcome-jane-doe")
- The final code should be self-contained and runnable with just `python workflow.py`

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

    prompt = f"Design, build, and test a workflow for the following request:\n\n{description}"

    if context:
        prompt += f"\n\nAdditional context:\n"
        for key, value in context.items():
            prompt += f"- {key}: {value}\n"

    workspace = tempfile.mkdtemp(prefix="flowforge-")

    async for message in run_agent(
        prompt=prompt,
        system_prompt=system_prompt,
        workspace_dir=workspace,
        max_turns=50,
    ):
        yield message

    yield {
        "type": "workspace",
        "content": {"path": workspace},
    }
