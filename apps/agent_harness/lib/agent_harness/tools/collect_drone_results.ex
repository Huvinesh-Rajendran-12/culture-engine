defmodule AgentHarness.Tools.CollectDroneResults do
  @moduledoc """
  Tool definition for consuming completed drone results.

  Execution is handled directly by the Agent loop because it needs access
  to the parent agent's runtime state.
  """
  @behaviour AgentHarness.Tool

  @impl true
  def name, do: "collect_drone_results"

  @impl true
  def description do
    "Collect completed drone results from async drones. Collected results are removed " <>
      "from the pending inbox so you can decide explicitly when to incorporate them."
  end

  @impl true
  def input_schema do
    %{
      "type" => "object",
      "properties" => %{
        "ids" => %{
          "type" => "array",
          "items" => %{"type" => "string"},
          "description" =>
            "Optional list of drone IDs to collect. Defaults to all completed drones."
        }
      },
      "required" => []
    }
  end

  @impl true
  def execute(_input) do
    {:error, "collect_drone_results must be executed within an agent context"}
  end
end
