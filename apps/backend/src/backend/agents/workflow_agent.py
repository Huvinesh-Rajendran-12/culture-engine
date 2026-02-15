"""Unified FlowForge agent: conversational assistant that can also build workflows."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, AsyncGenerator

from ..simulator import create_simulator
from ..workflow.executor import WorkflowExecutor
from ..workflow.schema import Workflow
from ..workflow.store import WorkflowStore
from .base import run_agent
from .tools import DEFAULT_TOOL_NAMES

MAX_FIX_ATTEMPTS = 2

FLOWFORGE_SYSTEM_PROMPT = """\
You are FlowForge, an AI automation assistant.

You can converse with users, gather requirements, and produce executable workflow DAGs.
When asked to design or modify a workflow, write valid JSON to `workflow.json` using the `write_file` tool.

## Available tools
- file tools: read_file, write_file, edit_file
- discovery tools: search_apis, search_knowledge_base

## Workflow JSON contract
- Root keys: id, name, description, team, nodes, edges, parameters, version
- Every node must include: id, name, description, service, action, actor, parameters, depends_on, outputs
- Use {{param_name}} for global parameters
- Use {{node_id.output_key}} for upstream outputs
- edges must mirror depends_on relationships

## Design guidance
- Use search_knowledge_base to find required policy/process steps
- Use search_apis to validate service/action/parameter choices
- Keep dependencies valid and deterministic
- Always return at least one short natural-language text response per turn
"""

WORKFLOW_SCHEMA_DESCRIPTION = """\
The workflow JSON must conform to this schema:

```json
{
  "id": "string — unique workflow identifier (kebab-case)",
  "name": "string — human-readable name",
  "description": "string — what this workflow accomplishes",
  "team": "string — team whose KB was used (e.g., 'default', 'engineering')",
  "nodes": [
    {
      "id": "string — unique node ID (snake_case)",
      "name": "string — display name",
      "description": "string — what this step does",
      "service": "string — one of: slack, jira, google, hr, github",
      "action": "string — service method to call, e.g., create_channel, send_message, provision_account, create_employee, add_to_org, grant_repo_access, create_issue, create_epic, assign_issue, invite_user, send_email, create_calendar_event, enroll_benefits",
      "actor": "string — responsible role: hr_manager, it_admin, team_lead, new_employee",
      "parameters": [
        {
          "name": "string — parameter name matching the service method kwarg",
          "value": "any — the value; use {{param_name}} for global params, {{node_id.output_key}} for upstream outputs",
          "description": "string — human-readable description",
          "required": true
        }
      ],
      "depends_on": ["list of node IDs this step depends on"],
      "outputs": {"output_name": "description of what this output contains"}
    }
  ],
  "edges": [
    {"source": "node_id", "target": "node_id"}
  ],
  "parameters": {
    "employee_name": "Alice Chen",
    "role": "Software Engineer"
  },
  "version": 1
}
```
"""

EXAMPLE_WORKFLOW_JSON = """\
{
  "id": "day1-onboarding",
  "name": "Day 1 Onboarding",
  "description": "Provisions all accounts and sends welcome materials for a new hire's first day",
  "team": "default",
  "nodes": [
    {
      "id": "create_hr_record",
      "name": "Create Employee Record",
      "description": "Create the employee's HR record in the HR Portal",
      "service": "hr",
      "action": "create_employee",
      "actor": "hr_manager",
      "parameters": [
        {"name": "employee_name", "value": "{{employee_name}}", "description": "Full name of the new employee", "required": true},
        {"name": "role", "value": "{{role}}", "description": "Job title", "required": true},
        {"name": "department", "value": "{{department}}", "description": "Department", "required": false}
      ],
      "depends_on": [],
      "outputs": {"employee_id": "The created employee ID"}
    },
    {
      "id": "provision_google",
      "name": "Provision Google Workspace",
      "description": "Create Google Workspace account for email, calendar, and drive",
      "service": "google",
      "action": "provision_account",
      "actor": "it_admin",
      "parameters": [
        {"name": "employee_name", "value": "{{employee_name}}", "description": "Full name", "required": true},
        {"name": "email", "value": "{{employee_name}}.lowercase@company.com", "description": "Work email", "required": true}
      ],
      "depends_on": ["create_hr_record"],
      "outputs": {"email": "The provisioned email address"}
    },
    {
      "id": "invite_slack",
      "name": "Invite to Slack",
      "description": "Create Slack account and invite to required channels",
      "service": "slack",
      "action": "invite_user",
      "actor": "it_admin",
      "parameters": [
        {"name": "email", "value": "{{provision_google.email}}", "description": "User's email for Slack invite", "required": true},
        {"name": "channel_name", "value": "#general", "description": "Channel to invite to", "required": true}
      ],
      "depends_on": ["provision_google"],
      "outputs": {}
    }
  ],
  "edges": [
    {"source": "create_hr_record", "target": "provision_google"},
    {"source": "provision_google", "target": "invite_slack"}
  ],
  "parameters": {
    "employee_name": "Alice Chen",
    "role": "Software Engineer",
    "department": "Engineering"
  },
  "version": 1
}
"""

WORKFLOW_TOOLSET = DEFAULT_TOOL_NAMES


def _build_initial_prompt(
    *,
    workspace: str,
    description: str,
    context: dict[str, Any] | None,
    existing_workflow: Workflow | None,
) -> str:
    base = (
        f"Your workspace directory is: {workspace}\n"
        f"Write all files there using absolute paths (e.g., {workspace}/workflow.json).\n\n"
        f"Workflow schema reference:\n{WORKFLOW_SCHEMA_DESCRIPTION}\n\n"
        f"Example workflow JSON:\n{EXAMPLE_WORKFLOW_JSON}\n\n"
    )

    if existing_workflow:
        base += (
            "Modify this existing workflow based on the user request below.\n"
            f"Current workflow:\n{existing_workflow.model_dump_json(indent=2)}\n\n"
            "Update workflow.json and increment version by 1.\n\n"
        )
    else:
        base += "Design a workflow DAG for this request and write workflow.json.\n\n"

    base += f"User request:\n{description}"

    if context:
        base += "\n\nAdditional context:\n"
        for key, value in context.items():
            base += f"- {key}: {value}\n"

    return base


async def _run_fix_attempt(
    *,
    workspace: str,
    team: str,
    prompt: str,
) -> AsyncGenerator[dict[str, Any], None]:
    async for message in run_agent(
        prompt=prompt,
        system_prompt=FLOWFORGE_SYSTEM_PROMPT,
        workspace_dir=workspace,
        team=team,
        allowed_tools=WORKFLOW_TOOLSET,
        max_turns=10,
    ):
        yield message


async def generate_workflow(
    description: str,
    context: dict[str, Any] | None = None,
    team: str = "default",
    existing_workflow: Workflow | None = None,
    workflow_store: WorkflowStore | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Generate or modify a structured DAG workflow from natural language."""
    workspace = tempfile.mkdtemp(prefix="flowforge-")
    workflow_file = Path(workspace) / "workflow.json"

    async for message in run_agent(
        prompt=_build_initial_prompt(
            workspace=workspace,
            description=description,
            context=context,
            existing_workflow=existing_workflow,
        ),
        system_prompt=FLOWFORGE_SYSTEM_PROMPT,
        workspace_dir=workspace,
        team=team,
        allowed_tools=WORKFLOW_TOOLSET,
        max_turns=30,
    ):
        yield message

    if not workflow_file.exists():
        yield {"type": "error", "content": "Agent did not produce workflow.json"}
        yield {"type": "workspace", "content": {"path": workspace}}
        return

    report = None
    workflow = None

    for attempt in range(1, MAX_FIX_ATTEMPTS + 2):
        try:
            workflow_data = json.loads(workflow_file.read_text())
            workflow = Workflow.model_validate(workflow_data)
        except Exception as e:
            yield {
                "type": "error",
                "content": f"Failed to parse workflow.json (attempt {attempt}): {e}",
            }
            if attempt > MAX_FIX_ATTEMPTS:
                break

            async for message in _run_fix_attempt(
                workspace=workspace,
                team=team,
                prompt=(
                    f"The workflow.json file at {workflow_file} failed to parse "
                    f"with the following error:\n\n{e}\n\n"
                    f"Read the file, fix the JSON, and write it back."
                ),
            ):
                yield message
            continue

        yield {"type": "workflow", "content": workflow.model_dump()}

        state, trace, services, failure_config = create_simulator()
        executor = WorkflowExecutor(
            state=state,
            trace=trace,
            services=services,
            failure_config=failure_config,
        )
        report = await executor.execute(workflow)

        yield {
            "type": "execution_report",
            "content": {
                "report": report.to_dict(),
                "markdown": report.to_markdown(),
                "attempt": attempt,
            },
        }

        if report.failed == 0:
            break

        if attempt > MAX_FIX_ATTEMPTS:
            break

        yield {
            "type": "text",
            "content": f"Execution had {report.failed} failure(s). "
            f"Running self-correction (attempt {attempt}/{MAX_FIX_ATTEMPTS})...",
        }

        async for message in _run_fix_attempt(
            workspace=workspace,
            team=team,
            prompt=(
                f"The workflow at {workflow_file} was executed but had failures.\n\n"
                f"## Execution Report\n\n{report.to_markdown()}\n\n"
                f"Read the workflow.json, fix the issues described above, "
                f"and write the corrected file back."
            ),
        ):
            yield message

    if workflow_store and report and report.failed == 0 and workflow is not None:
        workflow_store.save(workflow)
        yield {
            "type": "workflow_saved",
            "content": {
                "workflow_id": workflow.id,
                "team": workflow.team,
                "version": workflow.version,
            },
        }

    yield {"type": "workspace", "content": {"path": workspace}}
