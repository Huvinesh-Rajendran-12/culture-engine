#!/usr/bin/env python3
"""Test script for the workflow agent."""
import asyncio
from pathlib import Path

from backend.agents import generate_workflow


async def test_workflow_generation():
    """Test workflow generation with a realistic scenario."""
    print("Testing Workflow Agent\n")
    print("=" * 60)

    # Test case: Simple onboarding workflow
    description = "Create a Day 1 onboarding workflow for a new engineer"
    context = {
        "employee_name": "Alice Chen",
        "role": "Software Engineer"
    }

    print(f"Request: {description}")
    print(f"Context: {context}\n")
    print("=" * 60)
    print()

    workspace_path = None
    has_error = False

    try:
        async for message in generate_workflow(description, context):
            msg_type = message["type"]
            content = message["content"]

            if msg_type == "text":
                print(f"[agent] {content}")
            elif msg_type == "tool_use":
                tool = content["tool"]
                inp = content.get("input", {})
                detail = inp.get("file_path") or inp.get("command", "")
                if detail:
                    print(f"[tool]  {tool}: {detail[:120]}")
                else:
                    print(f"[tool]  {tool}")
            elif msg_type == "result":
                cost = content.get("cost_usd", 0)
                print(f"\n[done]  Completed | Cost: ${cost:.4f}")
            elif msg_type == "workspace":
                workspace_path = content["path"]
                print(f"[info]  Workspace: {workspace_path}")
            elif msg_type == "error":
                print(f"[error] {content}")
                has_error = True

    except Exception as e:
        print(f"[error] Exception: {e}")
        has_error = True

    print("\n" + "=" * 60)

    # Check if workflow.py was generated
    if workspace_path:
        workflow_file = Path(workspace_path) / "workflow.py"
        if workflow_file.exists():
            print(f"[pass]  Generated workflow at: {workflow_file}")
            print(f"\nWorkflow code preview:")
            print("-" * 60)
            code = workflow_file.read_text()
            lines = code.split("\n")[:20]
            print("\n".join(lines))
            if len(code.split("\n")) > 20:
                print("...")
        else:
            print("[fail]  workflow.py not found in workspace")

    return not has_error


if __name__ == "__main__":
    success = asyncio.run(test_workflow_generation())
    exit(0 if success else 1)
