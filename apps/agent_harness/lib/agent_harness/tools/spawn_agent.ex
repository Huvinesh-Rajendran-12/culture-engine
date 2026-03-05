defmodule AgentHarness.Tools.SpawnAgent do
  @moduledoc """
  Tool definition for spawning a drone agent.

  Execution is handled directly by the Agent loop (not via this module's execute/1)
  because it needs access to the parent agent's state.
  """
  @behaviour AgentHarness.Tool

  @impl true
  def name, do: "spawn_agent"

  @impl true
  def description do
    "Spawn a drone agent to handle a subtask. The drone runs synchronously — " <>
      "you wait for its result like any other tool call. The drone has access to " <>
      "the same file tools but cannot spawn further agents or create tools. " <>
      "Use this to delegate focused subtasks (e.g., 'read and summarize file X', " <>
      "'search for all TODO comments')."
  end

  @impl true
  def input_schema do
    %{
      "type" => "object",
      "properties" => %{
        "task" => %{
          "type" => "string",
          "description" => "The task for the drone to complete. Be specific and self-contained."
        },
        "name" => %{
          "type" => "string",
          "description" => "Optional Culture-style name for the drone. Auto-generated if omitted."
        },
        "system" => %{
          "type" => "string",
          "description" => "Optional system prompt override for the drone."
        },
        "max_turns" => %{
          "type" => "integer",
          "description" => "Max tool-use turns for the drone (default: 5)."
        }
      },
      "required" => ["task"]
    }
  end

  @impl true
  def execute(_input) do
    # This is intercepted by Agent.execute_tool/3 — should never be called directly
    {:error, "spawn_agent must be executed within an agent context"}
  end
end
