defmodule AgentHarness.Tools.ListDrones do
  @moduledoc """
  Tool definition for listing the current drone lifecycle state.

  Execution is handled directly by the Agent loop because it needs access
  to the parent agent's runtime state.
  """
  @behaviour AgentHarness.Tool

  @impl true
  def name, do: "list_drones"

  @impl true
  def description do
    "List pending drones and any completed drone results that have not yet been collected. " <>
      "Use this to inspect drone state without consuming results."
  end

  @impl true
  def input_schema do
    %{
      "type" => "object",
      "properties" => %{
        "ids" => %{
          "type" => "array",
          "items" => %{"type" => "string"},
          "description" => "Optional list of drone IDs to limit the report to."
        }
      },
      "required" => []
    }
  end

  @impl true
  def execute(_input) do
    {:error, "list_drones must be executed within an agent context"}
  end
end
