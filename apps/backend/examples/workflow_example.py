"""Example: stream a workflow generation request against the FlowForge API."""

import httpx


def main():
    url = "http://localhost:8000/api/workflows/generate"
    payload = {
        "description": (
            "Create an employee onboarding workflow that sends a welcome email, "
            "creates accounts in Slack and JIRA, assigns mandatory training, "
            "and schedules a meeting with the new hire's manager."
        ),
        "context": {
            "company": "TechCorp",
            "systems": ["Slack", "JIRA", "HR Portal", "Training Platform"],
            "team": "Engineering",
        },
    }

    with httpx.Client(timeout=None) as client:
        with client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.startswith("data: "):
                    print(line[len("data: "):])


if __name__ == "__main__":
    main()
