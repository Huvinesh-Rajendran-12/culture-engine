from __future__ import annotations

import json

from claude_agent_sdk import McpSdkServerConfig, create_sdk_mcp_server, tool

from .api_catalog import search_api_catalog
from .kb_search import search_knowledge_base


def create_flowforge_mcp_server(team: str = "default") -> McpSdkServerConfig:
    """Create an MCP server with FlowForge tools, capturing team via closure."""

    @tool(
        name="search_apis",
        description=(
            "Search available APIs by intent or keyword. "
            "Returns matching service actions with parameters and auth info. "
            "Use this to discover which APIs are available for building workflows."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query describing the API capability you need (e.g., 'send a message', 'create employee record', 'grant repository access')",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    )
    async def search_apis_tool(args: dict) -> dict:
        query = args["query"]
        top_k = args.get("top_k", 5)
        results = search_api_catalog(query, top_k=top_k)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        [entry.to_dict() for entry in results], indent=2
                    ),
                }
            ]
        }

    @tool(
        name="search_knowledge_base",
        description=(
            "Search the organization's knowledge base for policies, roles, systems, and procedures. "
            "Returns matching KB sections. "
            "Use this to find onboarding policies, role responsibilities, system details, and compliance requirements."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural language query describing the information you need (e.g., 'onboarding policy day 1', 'IT Admin responsibilities', 'benefits enrollment')",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    )
    async def search_kb_tool(args: dict) -> dict:
        query = args["query"]
        top_k = args.get("top_k", 5)
        results = search_knowledge_base(query, team=team, top_k=top_k)
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        [section.to_dict() for section in results], indent=2
                    ),
                }
            ]
        }

    return create_sdk_mcp_server(
        name="flowforge",
        tools=[search_apis_tool, search_kb_tool],
    )
