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
    listed_agents = AgentHarness.Agent.list_agents()

    parent_ids =
      Map.new(listed_agents, fn {id, pid, _meta} -> {pid, id} end)

    agents =
      listed_agents
      |> Enum.map(fn {id, _pid, meta} ->
        parent =
          case meta[:parent] do
            pid when is_pid(pid) -> Map.get(parent_ids, pid, inspect(pid))
            other -> other
          end

        %{
          id: id,
          name: meta[:name] || "unknown",
          tier: to_string(meta[:tier] || :unknown),
          parent: parent
        }
      end)

    {:ok, Jason.encode!(agents, pretty: true)}
  end
end
