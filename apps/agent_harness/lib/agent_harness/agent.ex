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

  alias AgentHarness.{API, Names, ToolSet}
  alias AgentHarness.Tools.CreateTool

  @max_depth 3

  defstruct [
    :id,
    :name,
    :parent,
    :api_key,
    :model,
    :system,
    :tool_table,
    tier: :mind,
    depth: 0,
    messages: [],
    max_turns: 20,
    pending_drones: %{}
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
      model: opts[:model] || "claude-sonnet-4-20250514",
      system: opts[:system],
      max_turns: opts[:max_turns] || 20,
      tool_table: tool_table
    }

    broadcast_lifecycle(state, {:agent_started, %{id: id, name: agent_name, tier: tier, parent: parent}})
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
    {:reply, :ok, %{state | messages: []}}
  end

  @impl true
  def handle_cast({:chat_async, caller, user_message}, state) do
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

      {%{pid: pid}, pending} ->
        DynamicSupervisor.terminate_child(AgentHarness.AgentSupervisor, pid)
        state = %{state | pending_drones: pending}

        text =
          case result do
            {:ok, text} -> text
            {:error, reason} -> "[error] #{reason}"
          end

        state = append_user_message(state, "[drone_result from #{drone_name} (#{drone_id})]\n#{text}")
        {_result, state} = run_loop(state, 0, nil)
        {:noreply, state}
    end
  end

  def handle_info(_msg, state), do: {:noreply, state}

  @impl true
  def terminate(reason, state) do
    ToolSet.destroy(state.tool_table)
    broadcast_lifecycle(state, {:agent_stopped, %{id: state.id, name: state.name, reason: reason}})
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
    tools = tools_for_agent(ToolSet.all_definitions(state.tool_table), state)

    case API.chat(state.messages, tools,
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
            "content" => output
          }

          result = if status == :error, do: Map.put(result, "is_error", true), else: result
          {result, acc_state}
        end)

      state = append_tool_results(state, tool_results)
      run_loop(state, turn + 1, caller)
    end
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
    system = input["system"] || state.system
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
             model: state.model
           ) do
        {:ok, drone_pid} ->
          if async do
            %{id: drone_id, name: actual_name} = get_identity(drone_pid)
            chat_async(drone_pid, task)
            pending = Map.put(state.pending_drones, drone_id, %{name: actual_name, pid: drone_pid})
            state = %{state | pending_drones: pending}
            {:ok, "Drone '#{actual_name}' (#{drone_id}) dispatched asynchronously. It will report back when done.", state}
          else
            case chat(drone_pid, task) do
              {:ok, result} ->
                DynamicSupervisor.terminate_child(AgentHarness.AgentSupervisor, drone_pid)
                {:ok, result}

              {:error, reason} ->
                DynamicSupervisor.terminate_child(AgentHarness.AgentSupervisor, drone_pid)
                {:error, "Drone failed: #{reason}"}
            end
          end

        {:error, reason} ->
          {:error, "Failed to spawn drone: #{inspect(reason)}"}
      end
    end
  end

  # Agents at max depth cannot spawn further agents; create_tool always requires mind tier
  defp tools_for_agent(tools, %{depth: depth}) when depth >= @max_depth do
    Enum.reject(tools, &(&1["name"] in ~w(spawn_agent create_tool)))
  end

  defp tools_for_agent(tools, %{tier: :drone}) do
    Enum.reject(tools, &(&1["name"] == "create_tool"))
  end

  defp tools_for_agent(tools, _state), do: tools

  defp emit(state, caller, event) do
    if caller, do: send(caller, {:agent_event, state.id, event})
    Phoenix.PubSub.broadcast(AgentHarness.PubSub, "agent:#{state.id}", {:agent_event, event})
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
