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
    "Spawn a drone agent to handle a subtask. By default the drone runs synchronously — " <>
      "you wait for its result like any other tool call. Set async: true to dispatch " <>
      "the drone in the background; it will report back when done. Drones can spawn their " <>
      "own sub-drones up to a maximum nesting depth of 3. " <>
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
        },
        "async" => %{
          "type" => "boolean",
          "description" =>
            "If true, the drone runs asynchronously and reports back when done. " <>
              "The mind continues immediately without waiting. Default: false."
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
