defmodule AgentHarness.Agent do
  @moduledoc """
  The core agent loop as a GenServer.

  Maintains conversation history and runs the tool loop:
    send messages → check response → execute tools or return text → repeat
  """
  use GenServer
  require Logger

  alias AgentHarness.{API, ToolRegistry}

  defstruct [
    :api_key,
    :model,
    :system,
    messages: [],
    max_turns: 20
  ]

  # --- Public API ---

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts)
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

  def reset(pid) do
    GenServer.call(pid, :reset)
  end

  # --- GenServer Callbacks ---

  @impl true
  def init(opts) do
    state = %__MODULE__{
      api_key: opts[:api_key] || System.get_env("ANTHROPIC_API_KEY"),
      model: opts[:model] || "claude-sonnet-4-20250514",
      system: opts[:system],
      max_turns: opts[:max_turns] || 20
    }

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

  def handle_call(:reset, _from, state) do
    {:reply, :ok, %{state | messages: []}}
  end

  @impl true
  def handle_cast({:chat_async, caller, user_message}, state) do
    state = append_user_message(state, user_message)
    {_result, state} = run_loop(state, 0, caller)
    {:noreply, state}
  end

  # --- The Agent Loop ---

  defp run_loop(state, turn, _caller) when turn >= state.max_turns do
    {{:error, "Max turns (#{state.max_turns}) reached"}, state}
  end

  defp run_loop(state, turn, caller) do
    tools = ToolRegistry.all_definitions()

    case API.chat(state.messages, tools,
           api_key: state.api_key,
           model: state.model,
           system: state.system
         ) do
      {:ok, response} ->
        state = append_assistant_message(state, response)
        handle_response(state, response, turn, caller)

      {:error, reason} ->
        emit(caller, {:error, reason})
        emit(caller, :done)
        {{:error, reason}, state}
    end
  end

  defp handle_response(state, response, turn, caller) do
    content = Map.get(response, "content", [])
    tool_uses = Enum.filter(content, &(&1["type"] == "tool_use"))

    if tool_uses == [] do
      # No tool calls — extract text and return
      text =
        content
        |> Enum.filter(&(&1["type"] == "text"))
        |> Enum.map_join("\n", & &1["text"])

      emit(caller, {:text, text})
      emit(caller, :done)
      {{:ok, text}, state}
    else
      # Execute each tool and collect results
      tool_results =
        Enum.map(tool_uses, fn tool_use ->
          name = tool_use["name"]
          input = tool_use["input"]
          id = tool_use["id"]

          Logger.info("[tool_use] #{name}: #{inspect(input)}")
          emit(caller, {:tool_use, name, input})

          {status, output} =
            case ToolRegistry.execute(name, input) do
              {:ok, result} ->
                Logger.info("[tool_result] #{name}: #{String.slice(result, 0..200)}")
                emit(caller, {:tool_result, name, result})
                {nil, result}

              {:error, reason} ->
                Logger.warning("[tool_error] #{name}: #{reason}")
                emit(caller, {:tool_result, name, "[error] #{reason}"})
                {"error", reason}
            end

          result = %{
            "type" => "tool_result",
            "tool_use_id" => id,
            "content" => output
          }

          if status, do: Map.put(result, "is_error", true), else: result
        end)

      state = append_tool_results(state, tool_results)

      # Always continue the loop after tool execution — the model
      # signals completion by returning a response with no tool_use blocks.
      run_loop(state, turn + 1, caller)
    end
  end

  defp emit(nil, _event), do: :ok
  defp emit(caller, event), do: send(caller, {:agent_event, event})

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
end
