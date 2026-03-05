defmodule AgentHarness.Tools.ListAgents do
  @moduledoc """
  Tool that returns all currently running agents with their identity info.
  """
  @behaviour AgentHarness.Tool

  @impl true
  def name, do: "list_agents"

  @impl true
  def description do
    "List all currently running agents with their ID, name, tier (mind/drone), and parent."
  end

  @impl true
  def input_schema do
    %{
      "type" => "object",
      "properties" => %{},
      "required" => []
    }
  end

  @impl true
  def execute(_input) do
    agents =
      AgentHarness.Agent.list_agents()
      |> Enum.map(fn {id, _pid, meta} ->
        %{
          id: id,
          name: meta[:name] || "unknown",
          tier: meta[:tier] || :unknown,
          parent: meta[:parent]
        }
      end)

    {:ok, Jason.encode!(agents, pretty: true)}
  end
end
