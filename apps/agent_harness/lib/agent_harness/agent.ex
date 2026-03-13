defmodule AgentHarness.Agent do
  @moduledoc """
  The core agent loop as a GenServer.

  Each agent has an identity (id, name, tier, parent) and is registered
  in the AgentHarness.AgentRegistry for discovery. Agents are started
  under the AgentHarness.AgentSupervisor via `start_supervised/1`.

  Events are emitted as `{:agent_event, agent_id, event}` 3-tuples and
  broadcast on PubSub topic `"agent:<id>"`.
  """
  use GenServer
  require Logger

  # Agents are task-driven workers — auto-restart makes no sense because a restarted
  # agent has no messages and no caller. :temporary prevents orphan drone processes
  # from accumulating when a sync drone crashes and the supervisor restarts it before
  # the after block can terminate it.
  def child_spec(opts) do
    %{
      id: __MODULE__,
      start: {__MODULE__, :start_link, [opts]},
      restart: :temporary
    }
  end

  alias AgentHarness.{API, Names, ToolSet}
  alias AgentHarness.Tools.{CreateTool, SpawnAgent}

  # Maximum nesting depth for drone spawning (also referenced by SpawnAgent tool description)
  @max_depth 3
  def max_depth, do: @max_depth

  defstruct [
    :id,
    :name,
    :parent,
    :api_key,
    :api_module,
    :model,
    :system,
    :tool_table,
    :caller,
    tier: :mind,
    depth: 0,
    messages: [],
    max_turns: 20,
    pending_drones: %{},
    completed_drones: []
  ]

  # --- Public API ---

  @doc "Starts an agent under the DynamicSupervisor with the given opts."
  def start_supervised(opts \\ []) do
    DynamicSupervisor.start_child(AgentHarness.AgentSupervisor, {__MODULE__, opts})
  end

  def start_link(opts \\ []) do
    id = opts[:id] || short_id()
    name = {:via, Registry, {AgentHarness.AgentRegistry, id}}
    GenServer.start_link(__MODULE__, Keyword.put(opts, :id, id), name: name)
  end

  def chat(pid, message) do
    GenServer.call(pid, {:chat, message}, :infinity)
  end

  def chat_async(pid, message) do
    GenServer.cast(pid, {:chat_async, self(), message})
  end

  def get_messages(pid) do
    GenServer.call(pid, :get_messages)
  end

  def get_identity(pid) do
    GenServer.call(pid, :get_identity)
  end

  def reset(pid) do
    GenServer.call(pid, :reset)
  end

  @doc "Lists all running agents as `[{id, pid, %{name, tier, parent}}]`."
  def list_agents do
    Registry.select(AgentHarness.AgentRegistry, [
      {{:"$1", :"$2", :"$3"}, [], [{{:"$1", :"$2", :"$3"}}]}
    ])
  end

  # --- GenServer Callbacks ---

  @impl true
  def init(opts) do
    id = opts[:id] || short_id()
    agent_name = opts[:agent_name] || Names.generate()
    tier = opts[:tier] || :mind
    parent = opts[:parent]

    # Register metadata in the Registry for list_agents lookups
    Registry.update_value(AgentHarness.AgentRegistry, id, fn _ ->
      %{name: agent_name, tier: tier, parent: parent}
    end)

    tool_table = ToolSet.new()

    state = %__MODULE__{
      id: id,
      name: agent_name,
      parent: parent,
      tier: tier,
      depth: opts[:depth] || 0,
      api_key: opts[:api_key] || System.get_env("ANTHROPIC_API_KEY"),
      api_module: opts[:api_module] || API,
      model: opts[:model] || "claude-sonnet-4-20250514",
      system: opts[:system],
      max_turns: opts[:max_turns] || 20,
      tool_table: tool_table
    }

    broadcast_lifecycle(
      state,
      {:agent_started, %{id: id, name: agent_name, tier: tier, parent: parent}}
    )

    Logger.info("[agent] Started #{tier} '#{agent_name}' (#{id})")

    {:ok, state}
  end

  @impl true
  def handle_call({:chat, user_message}, _from, state) do
    state = append_user_message(state, user_message)
    {result, state} = run_loop(state, 0, nil)
    {:reply, result, state}
  end

  def handle_call(:get_messages, _from, state) do
    {:reply, state.messages, state}
  end

  def handle_call(:get_identity, _from, state) do
    identity = %{id: state.id, name: state.name, tier: state.tier, parent: state.parent}
    {:reply, identity, state}
  end

  def handle_call(:reset, _from, state) do
    state = reset_conversation(state)
    {:reply, :ok, state}
  end

  @impl true
  def handle_cast({:chat_async, caller, user_message}, state) do
    state = %{state | caller: caller}
    state = append_user_message(state, user_message)
    {result, state} = run_loop(state, 0, caller)

    # Notify parent when this drone completes
    if state.parent do
      send(state.parent, {:drone_complete, state.id, state.name, result})
    end

    {:noreply, state}
  end

  @impl true
  def handle_info({:drone_complete, drone_id, drone_name, result}, state) do
    case Map.pop(state.pending_drones, drone_id) do
      {nil, _state} ->
        {:noreply, state}

      {%{pid: _pid}, _pending} ->
        {:noreply, apply_drone_complete(state, drone_id, drone_name, result)}
    end
  end

  def handle_info({:DOWN, _ref, :process, pid, reason}, state) do
    {:noreply, apply_drone_down(state, pid, reason)}
  end

  def handle_info(_msg, state), do: {:noreply, state}

  @impl true
  def terminate(reason, state) do
    ToolSet.destroy(state.tool_table)

    broadcast_lifecycle(
      state,
      {:agent_stopped, %{id: state.id, name: state.name, reason: reason}}
    )

    Logger.info("[agent] Stopped #{state.tier} '#{state.name}' (#{state.id})")
    :ok
  end

  # --- The Agent Loop ---

  defp run_loop(state, turn, caller) when turn >= state.max_turns do
    emit(state, caller, {:error, "Max turns (#{state.max_turns}) reached"})
    emit(state, caller, :done)
    {{:error, "Max turns (#{state.max_turns}) reached"}, state}
  end

  defp run_loop(state, turn, caller) do
    state = drain_drone_events(state)
    tools = tools_for_agent(ToolSet.all_definitions(state.tool_table), state)

    case state.api_module.chat(state.messages, tools,
           api_key: state.api_key,
           model: state.model,
           system: state.system
         ) do
      {:ok, response} ->
        state = append_assistant_message(state, response)
        handle_response(state, response, turn, caller)

      {:error, reason} ->
        emit(state, caller, {:error, reason})
        emit(state, caller, :done)
        {{:error, reason}, state}
    end
  end

  defp handle_response(state, response, turn, caller) do
    content = Map.get(response, "content", [])
    tool_uses = Enum.filter(content, &(&1["type"] == "tool_use"))

    if tool_uses == [] do
      text =
        content
        |> Enum.filter(&(&1["type"] == "text"))
        |> Enum.map_join("\n", & &1["text"])

      emit(state, caller, {:text, text})
      emit(state, caller, :done)
      {{:ok, text}, state}
    else
      {tool_results, state} =
        Enum.map_reduce(tool_uses, state, fn tool_use, acc_state ->
          name = tool_use["name"]
          input = tool_use["input"]
          id = tool_use["id"]
          acc_state = drain_drone_events(acc_state)

          Logger.info("[tool_use] #{name}: #{inspect(input)}")
          emit(acc_state, caller, {:tool_use, name, input})

          {status, output, acc_state} = execute_tool(acc_state, name, input)

          case status do
            :ok ->
              Logger.info("[tool_result] #{name}: #{String.slice(output, 0..200)}")
              emit(acc_state, caller, {:tool_result, name, output})

            :error ->
              Logger.warning("[tool_error] #{name}: #{output}")
              emit(acc_state, caller, {:tool_result, name, "[error] #{output}"})
          end

          result = %{
            "type" => "tool_result",
            "tool_use_id" => id,
            "content" => String.replace_invalid(output)
          }

          result = if status == :error, do: Map.put(result, "is_error", true), else: result
          {result, acc_state}
        end)

      state = append_tool_results(state, tool_results)
      run_loop(state, turn + 1, caller)
    end
  end

  defp execute_tool(state, "list_drones", input) do
    {output, new_state} = execute_list_drones(state, input)
    {:ok, output, new_state}
  end

  defp execute_tool(state, "collect_drone_results", input) do
    {output, new_state} = execute_collect_drone_results(state, input)
    {:ok, output, new_state}
  end

  defp execute_tool(state, "cancel_drones", input) do
    {status, output, new_state} = execute_cancel_drones(state, input)
    {status, output, new_state}
  end

  defp execute_tool(state, "spawn_agent", input) do
    case execute_spawn_agent(state, input) do
      {:ok, output, new_state} -> {:ok, output, new_state}
      {status, output} -> {status, output, state}
    end
  end

  defp execute_tool(state, "create_tool", input) do
    result =
      case CreateTool.validate(input) do
        :ok ->
          ToolSet.register(
            state.tool_table,
            input["name"],
            input["description"],
            input["input_schema"],
            input["script"]
          )

        {:error, reason} ->
          {:error, reason}
      end

    {elem(result, 0), elem(result, 1), state}
  end

  defp execute_tool(state, name, input) do
    {status, output} = ToolSet.execute(state.tool_table, name, input)
    {status, output, state}
  end

  defp execute_spawn_agent(state, input) do
    task = input["task"] || ""
    drone_name = input["name"]
    system = AgentHarness.Prompts.default(:drone)
    max_turns = input["max_turns"] || 5
    async = input["async"] == true

    if task == "" do
      {:error, "spawn_agent requires a 'task' field"}
    else
      case start_supervised(
             parent: self(),
             tier: :drone,
             depth: state.depth + 1,
             agent_name: drone_name,
             system: system,
             max_turns: max_turns,
             api_key: state.api_key,
             api_module: state.api_module,
             model: state.model
           ) do
        {:ok, drone_pid} ->
          if async do
            %{id: drone_id, name: actual_name} = get_identity(drone_pid)
            Process.monitor(drone_pid)
            chat_async(drone_pid, task)

            pending =
              Map.put(state.pending_drones, drone_id, %{name: actual_name, pid: drone_pid})

            state = %{state | pending_drones: pending}
            {:ok, "Drone '#{actual_name}' (#{drone_id}) dispatched asynchronously.", state}
          else
            %{id: drone_id, name: actual_name} = get_identity(drone_pid)

            try do
              case chat(drone_pid, task) do
                {:ok, result} ->
                  {:ok, result}

                {:error, reason} ->
                  safe_reason = if is_binary(reason), do: reason, else: inspect(reason, limit: 10)

                  broadcast_lifecycle(
                    state,
                    {:drone_crashed, %{id: drone_id, name: actual_name, reason: safe_reason}}
                  )

                  Logger.warning(
                    "[agent] Drone '#{actual_name}' (#{drone_id}) failed: #{safe_reason}"
                  )

                  {:error, "Drone '#{actual_name}' (#{drone_id}) failed: #{safe_reason}"}
              end
            catch
              _kind, _reason ->
                broadcast_lifecycle(
                  state,
                  {:drone_crashed, %{id: drone_id, name: actual_name, reason: "unexpected crash"}}
                )

                Logger.error("[agent] Drone '#{actual_name}' (#{drone_id}) crashed unexpectedly")
                {:error, "Drone '#{actual_name}' (#{drone_id}) crashed unexpectedly"}
            after
              DynamicSupervisor.terminate_child(AgentHarness.AgentSupervisor, drone_pid)
            end
          end

        {:error, reason} ->
          {:error, "Failed to spawn drone: #{inspect(reason)}"}
      end
    end
  end

  defp execute_list_drones(state, input) do
    ids = requested_drone_ids(input)
    {completed, pending} = filter_drone_records(state, ids)

    completed_text =
      case completed do
        [] ->
          "No completed drone results available."

        _ ->
          results =
            Enum.map_join(completed, "\n", fn drone ->
              format_drone_status(drone)
            end)

          "Completed drones:\n#{results}"
      end

    pending_text =
      case pending do
        [] ->
          "No drones currently pending."

        _ ->
          names =
            Enum.map_join(pending, "\n", fn {id, %{name: name}} ->
              "- '#{name}' (#{id}) [pending]"
            end)

          "Pending drones:\n#{names}"
      end

    {completed_text <> "\n\n" <> pending_text, state}
  end

  defp execute_collect_drone_results(state, input) do
    ids = requested_drone_ids(input)
    {selected, remaining} = split_completed_drones(state.completed_drones, ids)

    output =
      case selected do
        [] ->
          "No completed drone results to collect."

        _ ->
          results =
            Enum.map_join(selected, "\n\n---\n\n", fn %{id: id, name: name, result: result} ->
              "Drone '#{name}' (#{id}):\n#{format_drone_result(result)}"
            end)

          "Collected drone results:\n\n#{results}"
      end

    {output, %{state | completed_drones: remaining}}
  end

  defp execute_cancel_drones(state, input) do
    ids = requested_drone_ids(input)

    {pending, completed, cancelled} =
      Enum.reduce(state.pending_drones, {state.pending_drones, state.completed_drones, []}, fn
        {drone_id, %{name: name, pid: pid}}, {pending_acc, completed_acc, cancelled_acc} ->
          if ids == :all or drone_id in ids do
            DynamicSupervisor.terminate_child(AgentHarness.AgentSupervisor, pid)
            broadcast_lifecycle(state, {:drone_cancelled, %{id: drone_id, name: name}})
            Logger.info("[agent] Drone '#{name}' (#{drone_id}) cancelled")

            completed =
              completed_acc ++
                [
                  %{
                    id: drone_id,
                    name: name,
                    status: :cancelled,
                    result: {:error, "Cancelled before completion"}
                  }
                ]

            {Map.delete(pending_acc, drone_id), completed, cancelled_acc ++ [drone_id]}
          else
            {pending_acc, completed_acc, cancelled_acc}
          end
      end)

    output =
      cond do
        cancelled == [] and pending == state.pending_drones ->
          "No matching pending drones to cancel."

        true ->
          "Cancelled drones: " <> Enum.join(cancelled, ", ")
      end

    if cancelled == [] do
      {:ok, output, state}
    else
      {:ok, output, %{state | pending_drones: pending, completed_drones: completed}}
    end
  end

  defp reset_conversation(state) do
    Enum.each(state.pending_drones, fn {_drone_id, %{pid: pid}} ->
      DynamicSupervisor.terminate_child(AgentHarness.AgentSupervisor, pid)
    end)

    %{state | messages: [], pending_drones: %{}, completed_drones: [], caller: nil}
  end

  defp format_drone_result({:ok, text}), do: text
  defp format_drone_result({:error, reason}), do: "[error] #{reason}"

  defp format_drone_status(%{id: id, name: name, status: status, result: result}) do
    preview =
      result
      |> format_drone_result()
      |> String.replace("\n", " ")
      |> String.slice(0, 120)

    "- '#{name}' (#{id}) [#{status}] #{preview}"
  end

  defp requested_drone_ids(%{"ids" => ids}) when is_list(ids), do: ids
  defp requested_drone_ids(_input), do: :all

  defp filter_drone_records(state, :all) do
    {state.completed_drones, Enum.sort_by(state.pending_drones, fn {id, _meta} -> id end)}
  end

  defp filter_drone_records(state, ids) do
    completed = Enum.filter(state.completed_drones, &(&1.id in ids))
    pending = Enum.filter(state.pending_drones, fn {id, _meta} -> id in ids end)
    {completed, pending}
  end

  defp split_completed_drones(completed_drones, :all), do: {completed_drones, []}

  defp split_completed_drones(completed_drones, ids) do
    Enum.split_with(completed_drones, &(&1.id in ids))
  end

  defp drain_drone_events(state) do
    receive do
      {:drone_complete, drone_id, drone_name, result} ->
        state
        |> apply_drone_complete(drone_id, drone_name, result)
        |> drain_drone_events()

      {:DOWN, _ref, :process, pid, reason} ->
        state
        |> apply_drone_down(pid, reason)
        |> drain_drone_events()
    after
      0 ->
        state
    end
  end

  defp apply_drone_complete(state, drone_id, drone_name, result) do
    case Map.pop(state.pending_drones, drone_id) do
      {nil, _pending} ->
        state

      {%{pid: pending_pid}, pending} ->
        DynamicSupervisor.terminate_child(AgentHarness.AgentSupervisor, pending_pid)

        completed = %{id: drone_id, name: drone_name, status: :completed, result: result}

        state = %{
          state
          | pending_drones: pending,
            completed_drones: state.completed_drones ++ [completed]
        }

        broadcast_lifecycle(state, {:drone_completed, %{id: drone_id, name: drone_name}})
        Logger.info("[agent] Drone '#{drone_name}' (#{drone_id}) completed")
        state
    end
  end

  defp apply_drone_down(state, pid, reason) do
    case Enum.find(state.pending_drones, fn {_id, %{pid: pending_pid}} -> pending_pid == pid end) do
      {drone_id, %{name: drone_name}} ->
        pending = Map.delete(state.pending_drones, drone_id)

        completed = %{
          id: drone_id,
          name: drone_name,
          status: :failed,
          result: {:error, "Drone crashed: #{inspect(reason)}"}
        }

        state = %{
          state
          | pending_drones: pending,
            completed_drones: state.completed_drones ++ [completed]
        }

        broadcast_lifecycle(
          state,
          {:drone_crashed, %{id: drone_id, name: drone_name, reason: inspect(reason)}}
        )

        Logger.warning(
          "[agent] Async drone '#{drone_name}' (#{drone_id}) crashed: #{inspect(reason)}"
        )

        state

      nil ->
        state
    end
  end

  # Build the set of tool names this agent cannot use:
  # - spawn_agent is blocked at max depth (prevents infinite nesting)
  # - create_tool is blocked for all drones (mind-only capability)
  defp tools_for_agent(tools, %{depth: depth, tier: tier}) do
    blocked =
      if(depth >= @max_depth, do: [SpawnAgent.name()], else: []) ++
        if tier == :drone, do: [CreateTool.name()], else: []

    case blocked do
      [] -> tools
      _ -> Enum.reject(tools, &(&1["name"] in blocked))
    end
  end

  defp emit(state, caller, event) do
    if caller, do: send(caller, {:agent_event, state.id, event})
    Phoenix.PubSub.broadcast(AgentHarness.PubSub, "agent:#{state.id}", {:agent_event, state.id, event})
  end

  defp broadcast_lifecycle(state, event) do
    Phoenix.PubSub.broadcast(AgentHarness.PubSub, "agent:#{state.id}", event)
    Phoenix.PubSub.broadcast(AgentHarness.PubSub, "agents", {state.id, event})
  end

  # --- Message Helpers ---

  defp append_user_message(state, text) do
    msg = %{"role" => "user", "content" => text}
    %{state | messages: state.messages ++ [msg]}
  end

  defp append_assistant_message(state, response) do
    msg = %{"role" => "assistant", "content" => Map.get(response, "content", [])}
    %{state | messages: state.messages ++ [msg]}
  end

  defp append_tool_results(state, tool_results) do
    msg = %{"role" => "user", "content" => tool_results}
    %{state | messages: state.messages ++ [msg]}
  end

  defp short_id do
    :crypto.strong_rand_bytes(4) |> Base.encode16(case: :lower)
  end
end
