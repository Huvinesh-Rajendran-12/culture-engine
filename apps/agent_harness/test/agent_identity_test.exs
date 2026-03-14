defmodule AgentHarness.AgentIdentityTest do
  use ExUnit.Case, async: false

  alias AgentHarness.Agent

  test "start_supervised creates agent with identity" do
    {:ok, pid} = Agent.start_supervised(system: "test")
    identity = Agent.get_identity(pid)

    assert is_binary(identity.id)
    assert is_binary(identity.name)
    assert identity.tier == :mind
    assert identity.parent == nil

    DynamicSupervisor.terminate_child(AgentHarness.AgentSupervisor, pid)
  end

  test "agent appears in list_agents" do
    {:ok, pid} = Agent.start_supervised(system: "test")
    identity = Agent.get_identity(pid)

    agents = Agent.list_agents()
    ids = Enum.map(agents, fn {id, _pid, _meta} -> id end)
    assert identity.id in ids

    DynamicSupervisor.terminate_child(AgentHarness.AgentSupervisor, pid)
  end

  test "drone agent has correct tier and parent" do
    {:ok, parent_pid} = Agent.start_supervised(system: "test")

    {:ok, drone_pid} =
      Agent.start_supervised(
        system: "test",
        tier: :drone,
        parent: parent_pid
      )

    drone_identity = Agent.get_identity(drone_pid)
    assert drone_identity.tier == :drone
    assert drone_identity.parent == parent_pid

    DynamicSupervisor.terminate_child(AgentHarness.AgentSupervisor, drone_pid)
    DynamicSupervisor.terminate_child(AgentHarness.AgentSupervisor, parent_pid)
  end

  test "custom agent name is used" do
    {:ok, pid} = Agent.start_supervised(system: "test", agent_name: "Gravely Mistaken Pedagogy")
    identity = Agent.get_identity(pid)
    assert identity.name == "Gravely Mistaken Pedagogy"

    DynamicSupervisor.terminate_child(AgentHarness.AgentSupervisor, pid)
  end

  test "events use 3-tuple format" do
    {:ok, pid} = Agent.start_supervised(system: "test", max_turns: 0)
    Agent.chat_async(pid, "hello")
    identity = Agent.get_identity(pid)

    # With max_turns: 0, continuation protocol kicks in — we get a partial text, not an error
    assert_receive {:agent_event, agent_id, {:text, text}}, 5000
    assert agent_id == identity.id
    assert text =~ "[partial"

    DynamicSupervisor.terminate_child(AgentHarness.AgentSupervisor, pid)
  end

  test "synchronous chat broadcasts events to PubSub" do
    {:ok, pid} = Agent.start_supervised(system: "test", max_turns: 0)
    identity = Agent.get_identity(pid)
    Phoenix.PubSub.subscribe(AgentHarness.PubSub, "agent:#{identity.id}")

    assert {:ok, text} = Agent.chat(pid, "hello")
    assert text =~ "[partial"

    assert_receive {:agent_event, agent_id, {:text, _}}, 5000
    assert agent_id == identity.id
    assert_receive {:agent_event, agent_id, :done}, 5000
    assert agent_id == identity.id

    DynamicSupervisor.terminate_child(AgentHarness.AgentSupervisor, pid)
  end
end
