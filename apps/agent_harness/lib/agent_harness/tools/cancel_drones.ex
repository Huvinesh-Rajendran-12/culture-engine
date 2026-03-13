defmodule AgentHarness.Tools.CancelDrones do
  @moduledoc """
  Tool definition for cancelling pending drones.

  Execution is handled directly by the Agent loop because it needs access
  to the parent agent's runtime state.
  """
  @behaviour AgentHarness.Tool

  @impl true
  def name, do: "cancel_drones"

  @impl true
  def description do
    "Cancel one or more pending async drones. Cancelled drones are removed from the " <>
      "pending set and recorded as cancelled results."
  end

  @impl true
  def input_schema do
    %{
      "type" => "object",
      "properties" => %{
        "ids" => %{
          "type" => "array",
          "items" => %{"type" => "string"},
          "description" => "Optional list of drone IDs to cancel. Defaults to all pending drones."
        }
      },
      "required" => []
    }
  end

  @impl true
  def execute(_input) do
    {:error, "cancel_drones must be executed within an agent context"}
  end
end
