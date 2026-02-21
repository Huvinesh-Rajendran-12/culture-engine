"""Example: create a Mind and stream a delegation run via SSE.

Usage:
    uv run python examples/mind_delegate_example.py
"""

from __future__ import annotations

import json

import httpx


def _iter_sse_events(response: httpx.Response):
    for line in response.iter_lines():
        if not line or not line.startswith("data: "):
            continue

        payload = line[6:].strip()
        if not payload:
            continue

        try:
            yield json.loads(payload)
        except json.JSONDecodeError:
            yield {"type": "raw", "content": payload}


def main() -> None:
    base_url = "http://localhost:8100"

    with httpx.Client(timeout=None) as client:
        create_resp = client.post(
            f"{base_url}/api/minds",
            json={
                "name": "Integration Mind",
                "personality": "practical, concise",
                "preferences": {"tone": "direct"},
            },
        )
        create_resp.raise_for_status()
        mind = create_resp.json()
        mind_id = mind["id"]
        print(f"Created mind: {mind_id}")

        events: list[dict] = []
        with client.stream(
            "POST",
            f"{base_url}/api/minds/{mind_id}/delegate",
            json={
                "description": (
                    "Draft a short onboarding checklist for a new backend engineer, "
                    "then summarize it in 3 bullets."
                ),
                "team": "default",
            },
        ) as response:
            response.raise_for_status()
            for event in _iter_sse_events(response):
                events.append(event)
                event_type = event.get("type")
                content = event.get("content")
                print(f"{event_type}: {content}")

        finished = next((e for e in events if e.get("type") == "task_finished"), None)
        if not finished:
            raise RuntimeError("Mind run did not emit task_finished")

        status = finished.get("content", {}).get("status")
        if status != "completed":
            raise RuntimeError(f"Mind run ended with status={status}")

        tasks_resp = client.get(f"{base_url}/api/minds/{mind_id}/tasks")
        tasks_resp.raise_for_status()
        tasks = tasks_resp.json()
        print(f"Persisted tasks: {len(tasks)}")

        memory_resp = client.get(f"{base_url}/api/minds/{mind_id}/memory")
        memory_resp.raise_for_status()
        memories = memory_resp.json()
        print(f"Persisted memories: {len(memories)}")


if __name__ == "__main__":
    main()
