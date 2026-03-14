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
    max = AgentHarness.Agent.max_depth()

    "Spawn a drone agent to handle a subtask. By default the drone runs synchronously — " <>
      "you wait for its result like any other tool call. Set async: true to dispatch " <>
      "the drone in the background; the result stays available until you explicitly " <>
      "inspect, collect, or cancel it with the drone lifecycle tools. Drones can spawn their " <>
      "own sub-drones up to a maximum nesting depth of #{max}. " <>
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
        "max_turns" => %{
          "type" => "integer",
          "description" =>
            "Max tool-use turns for the drone (default: 15). " <>
              "Set higher for complex analytical tasks. " <>
              "The drone will summarize partial progress if it hits this limit."
        },
        "async" => %{
          "type" => "boolean",
          "description" =>
            "If true, the drone runs asynchronously and reports back when done. " <>
              "The mind continues immediately without waiting. Default: false."
        },
        "tool_timeout" => %{
          "type" => "integer",
          "description" =>
            "Timeout in seconds for the drone's custom tool scripts (default: 120). " <>
              "Set higher for tools that do heavy computation or network calls."
        },
        "max_output_bytes" => %{
          "type" => "integer",
          "description" =>
            "Max output size in bytes for the drone's tool results (default: 200000). " <>
              "Increase for tools that produce large outputs."
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
