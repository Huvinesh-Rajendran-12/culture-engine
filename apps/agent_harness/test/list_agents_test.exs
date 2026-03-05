defmodule AgentHarness.Tools.ListAgentsTest do
  use ExUnit.Case, async: false

  alias AgentHarness.Agent
  alias AgentHarness.Tools.ListAgents

  test "execute serializes drone parent as the parent agent id" do
    {:ok, parent_pid} = Agent.start_supervised(system: "test")
    parent_identity = Agent.get_identity(parent_pid)

    {:ok, drone_pid} =
      Agent.start_supervised(
        system: "test",
        tier: :drone,
        parent: parent_pid
      )

    drone_identity = Agent.get_identity(drone_pid)

    {:ok, json} = ListAgents.execute(%{})
    agents = Jason.decode!(json)

    assert %{
             "id" => id,
             "tier" => "drone",
             "parent" => parent
           } = Enum.find(agents, &(&1["id"] == drone_identity.id))
    assert id == drone_identity.id
    assert parent == parent_identity.id

    DynamicSupervisor.terminate_child(AgentHarness.AgentSupervisor, drone_pid)
    DynamicSupervisor.terminate_child(AgentHarness.AgentSupervisor, parent_pid)
  end
end
