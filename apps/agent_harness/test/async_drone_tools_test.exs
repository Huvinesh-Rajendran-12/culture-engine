defmodule AgentHarness.AsyncDroneToolsTest do
  use ExUnit.Case, async: false

  alias AgentHarness.Agent

  defmodule StubHelpers do
    def drone_system?(opts) do
      opts[:system]
      |> to_string()
      |> String.contains?("You are a Drone")
    end

    def has_tool_result?(messages, tool_name) do
      Enum.any?(messages, fn
        %{"role" => "user", "content" => content} when is_list(content) ->
          Enum.any?(content, fn
            %{"type" => "tool_result", "tool_use_id" => _id, "content" => _content} = result ->
              tool_result_for?(messages, tool_name, result)

            _ ->
              false
          end)

        _ ->
          false
      end)
    end

    def text_response(text) do
      %{"content" => [%{"type" => "text", "text" => text}]}
    end

    def tool_response(id, name, input) do
      %{"content" => [%{"type" => "tool_use", "id" => id, "name" => name, "input" => input}]}
    end

    defp tool_result_for?(messages, tool_name, %{"tool_use_id" => tool_use_id}) do
      Enum.any?(messages, fn
        %{"role" => "assistant", "content" => content} ->
          Enum.any?(content, fn
            %{"type" => "tool_use", "id" => ^tool_use_id, "name" => ^tool_name} -> true
            _ -> false
          end)

        _ ->
          false
      end)
    end
  end

  defmodule NoResumeAPI do
    def chat(messages, _tools, opts) do
      if StubHelpers.drone_system?(opts) do
        Process.sleep(50)
        {:ok, StubHelpers.text_response("drone finished late")}
      else
        cond do
          StubHelpers.has_tool_result?(messages, "spawn_agent") ->
            {:ok, StubHelpers.text_response("mind finished before the drone")}

          true ->
            {:ok,
             StubHelpers.tool_response("spawn-1", "spawn_agent", %{
               "task" => "drone task",
               "async" => true
             })}
        end
      end
    end
  end

  defmodule CollectVisibleAPI do
    def chat(messages, _tools, opts) do
      if StubHelpers.drone_system?(opts) do
        {:ok, StubHelpers.text_response("drone result ready")}
      else
        cond do
          StubHelpers.has_tool_result?(messages, "collect_drone_results") ->
            {:ok, StubHelpers.text_response("mind collected the drone result")}

          StubHelpers.has_tool_result?(messages, "spawn_agent") ->
            Process.sleep(50)
            {:ok, StubHelpers.tool_response("collect-1", "collect_drone_results", %{})}

          true ->
            {:ok,
             StubHelpers.tool_response("spawn-1", "spawn_agent", %{
               "task" => "drone task",
               "async" => true
             })}
        end
      end
    end
  end

  defmodule CancelDroneAPI do
    def chat(messages, _tools, opts) do
      if StubHelpers.drone_system?(opts) do
        Process.sleep(200)
        {:ok, StubHelpers.text_response("too late")}
      else
        cond do
          StubHelpers.has_tool_result?(messages, "cancel_drones") ->
            {:ok, StubHelpers.text_response("mind cancelled the drone")}

          StubHelpers.has_tool_result?(messages, "spawn_agent") ->
            {:ok, StubHelpers.tool_response("cancel-1", "cancel_drones", %{})}

          true ->
            {:ok,
             StubHelpers.tool_response("spawn-1", "spawn_agent", %{
               "task" => "drone task",
               "async" => true
             })}
        end
      end
    end
  end

  defmodule SlowNoResumeAPI do
    def chat(messages, _tools, opts) do
      if StubHelpers.drone_system?(opts) do
        Process.sleep(500)
        {:ok, StubHelpers.text_response("drone would have finished later")}
      else
        cond do
          StubHelpers.has_tool_result?(messages, "spawn_agent") ->
            {:ok, StubHelpers.text_response("mind finished before the slow drone")}

          true ->
            {:ok,
             StubHelpers.tool_response("spawn-1", "spawn_agent", %{
               "task" => "drone task",
               "async" => true
             })}
        end
      end
    end
  end

  setup do
    on_exit(fn ->
      Agent.list_agents()
      |> Enum.each(fn {_id, pid, _meta} ->
        DynamicSupervisor.terminate_child(AgentHarness.AgentSupervisor, pid)
      end)
    end)

    :ok
  end

  test "async drone completion does not emit a second post-done event wave" do
    {:ok, pid} =
      Agent.start_supervised(
        api_module: NoResumeAPI,
        system: AgentHarness.Prompts.default(:mind)
      )

    Agent.chat_async(pid, "start")

    assert_receive {:agent_event, _id, {:tool_use, "spawn_agent", _}}, 1_000
    assert_receive {:agent_event, _id, {:tool_result, "spawn_agent", _}}, 1_000
    assert_receive {:agent_event, _id, {:text, "mind finished before the drone"}}, 1_000
    assert_receive {:agent_event, _id, :done}, 1_000
    refute_receive {:agent_event, _id, _event}, 200

    Process.sleep(100)
    refute_receive {:agent_event, _id, _event}, 200

    state = :sys.get_state(pid)
    assert state.pending_drones == %{}
    assert [%{status: :completed, result: {:ok, "drone finished late"}}] = state.completed_drones
  end

  test "collect_drone_results sees completions that arrived while the turn was busy" do
    {:ok, pid} =
      Agent.start_supervised(
        api_module: CollectVisibleAPI,
        system: AgentHarness.Prompts.default(:mind)
      )

    Agent.chat_async(pid, "start")

    assert_receive {:agent_event, _id, {:tool_use, "spawn_agent", _}}, 1_000
    assert_receive {:agent_event, _id, {:tool_result, "spawn_agent", _}}, 1_000
    assert_receive {:agent_event, _id, {:tool_use, "collect_drone_results", %{}}}, 1_000

    assert_receive {:agent_event, _id, {:tool_result, "collect_drone_results", output}}, 1_000
    assert output =~ "drone result ready"

    assert_receive {:agent_event, _id, {:text, "mind collected the drone result"}}, 1_000
    assert_receive {:agent_event, _id, :done}, 1_000

    state = :sys.get_state(pid)
    assert state.pending_drones == %{}
    assert state.completed_drones == []
  end

  test "cancel_drones removes pending drones and records the cancellation" do
    {:ok, pid} =
      Agent.start_supervised(
        api_module: CancelDroneAPI,
        system: AgentHarness.Prompts.default(:mind)
      )

    Agent.chat_async(pid, "start")

    assert_receive {:agent_event, _id, {:tool_use, "spawn_agent", _}}, 1_000
    assert_receive {:agent_event, _id, {:tool_result, "spawn_agent", _}}, 1_000
    assert_receive {:agent_event, _id, {:tool_use, "cancel_drones", %{}}}, 1_000
    assert_receive {:agent_event, _id, {:tool_result, "cancel_drones", output}}, 1_000
    assert output =~ "Cancelled drones:"
    assert_receive {:agent_event, _id, {:text, "mind cancelled the drone"}}, 1_000
    assert_receive {:agent_event, _id, :done}, 1_000

    state = :sys.get_state(pid)
    assert state.pending_drones == %{}
    assert [%{status: :cancelled}] = state.completed_drones

    Process.sleep(250)
    refute_receive {:agent_event, _id, _event}, 200
  end

  test "reset clears completed drone results and stops pending drones" do
    {:ok, pid} =
      Agent.start_supervised(
        api_module: SlowNoResumeAPI,
        system: AgentHarness.Prompts.default(:mind)
      )

    Agent.chat_async(pid, "start")

    assert_receive {:agent_event, _id, {:tool_use, "spawn_agent", _}}, 1_000
    assert_receive {:agent_event, _id, {:tool_result, "spawn_agent", _}}, 1_000
    assert_receive {:agent_event, _id, {:text, "mind finished before the slow drone"}}, 1_000
    assert_receive {:agent_event, _id, :done}, 1_000
    assert :ok = Agent.reset(pid)

    state = :sys.get_state(pid)
    assert state.messages == []
    assert state.pending_drones == %{}
    assert state.completed_drones == []
    assert state.caller == nil

    Process.sleep(600)
    refute_receive {:agent_event, _id, _event}, 200
  end
end
