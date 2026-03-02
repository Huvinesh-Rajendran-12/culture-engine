defmodule AgentHarness.ToolRegistry do
  @moduledoc """
  Dynamic registry of available tools. Built-in tools are seeded on init;
  the agent can register additional tools at runtime via `create_tool`.

  Built-in tools are stored as `{name, {:module, module}}`.
  Dynamic tools are stored as `{name, {:script, definition}}` where
  definition holds the description, input_schema, and script path.
  """
  use GenServer

  alias AgentHarness.Tool
  alias AgentHarness.Tools.{ReadFile, ListFiles, EditFile, RunCommand, SearchFiles, CreateTool}

  @table :tool_registry
  @max_dynamic_tools 10
  @builtin_modules [ReadFile, ListFiles, EditFile, RunCommand, SearchFiles, CreateTool]

  # --- Public API ---

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @doc "Returns API definitions for all registered tools (built-in + dynamic)."
  def all_definitions do
    :ets.tab2list(@table)
    |> Enum.map(fn {_name, entry} -> to_definition(entry) end)
  end

  @doc "Executes a tool by name."
  def execute(name, input) do
    case :ets.lookup(@table, name) do
      [{^name, entry}] -> do_execute(entry, input)
      [] -> {:error, "Unknown tool: #{name}"}
    end
  end

  @doc "Registers a dynamic script-based tool."
  def register(name, description, input_schema, script) do
    GenServer.call(__MODULE__, {:register, name, description, input_schema, script})
  end

  @doc "Unregisters a dynamic tool by name. Cannot remove built-in tools."
  def unregister(name) do
    GenServer.call(__MODULE__, {:unregister, name})
  end

  @doc "Returns list of all registered tool names."
  def tool_names do
    :ets.tab2list(@table) |> Enum.map(fn {name, _} -> name end)
  end

  @doc "Returns count of dynamic (non-built-in) tools."
  def dynamic_tool_count do
    :ets.tab2list(@table)
    |> Enum.count(fn {_name, entry} -> match?({:script, _}, entry) end)
  end

  # --- GenServer Callbacks ---

  @impl true
  def init(_opts) do
    table = :ets.new(@table, [:named_table, :set, :public, read_concurrency: true])

    for module <- @builtin_modules do
      :ets.insert(table, {module.name(), {:module, module}})
    end

    {:ok, %{table: table}}
  end

  @impl true
  def handle_call({:register, name, description, input_schema, script}, _from, state) do
    builtin_names = Enum.map(@builtin_modules, & &1.name())

    cond do
      name in builtin_names ->
        {:reply, {:error, "Cannot override built-in tool: #{name}"}, state}

      dynamic_tool_count() >= @max_dynamic_tools ->
        {:reply, {:error, "Maximum dynamic tools (#{@max_dynamic_tools}) reached"}, state}

      true ->
        # Write script to a temp file
        dir = System.tmp_dir!()
        script_path = Path.join(dir, "tool_#{name}_#{System.unique_integer([:positive])}")
        File.write!(script_path, script)
        File.chmod!(script_path, 0o755)

        entry =
          {:script,
           %{
             name: name,
             description: description,
             input_schema: input_schema,
             script_path: script_path
           }}

        :ets.insert(state.table, {name, entry})
        {:reply, {:ok, name}, state}
    end
  end

  def handle_call({:unregister, name}, _from, state) do
    builtin_names = Enum.map(@builtin_modules, & &1.name())

    if name in builtin_names do
      {:reply, {:error, "Cannot remove built-in tool: #{name}"}, state}
    else
      case :ets.lookup(state.table, name) do
        [{^name, {:script, %{script_path: path}}}] ->
          File.rm(path)
          :ets.delete(state.table, name)
          {:reply, :ok, state}

        [] ->
          {:reply, {:error, "Tool not found: #{name}"}, state}
      end
    end
  end

  # --- Internal ---

  defp to_definition({:module, module}) do
    Tool.to_api_definition(module)
  end

  defp to_definition({:script, %{name: name, description: desc, input_schema: schema}}) do
    %{
      "name" => name,
      "description" => desc,
      "input_schema" => schema
    }
  end

  @timeout_ms 30_000
  @max_output_bytes 50_000

  defp do_execute({:module, module}, input) do
    module.execute(input)
  end

  defp do_execute({:script, %{script_path: script_path}}, input) do
    json_input = Jason.encode!(input)

    task =
      Task.async(fn ->
        port =
          Port.open({:spawn_executable, script_path}, [
            :binary,
            :exit_status,
            :stderr_to_stdout,
            {:args, []},
            {:env, [{~c"TOOL_INPUT", String.to_charlist(json_input)}]}
          ])

        # Also send input on stdin
        Port.command(port, json_input)
        Port.command(port, <<>>)

        collect_port_output(port, "")
      end)

    case Task.yield(task, @timeout_ms) || Task.shutdown(task, :brutal_kill) do
      {:ok, {:ok, output}} -> {:ok, truncate(output)}
      {:ok, {:error, reason}} -> {:error, reason}
      nil -> {:error, "Tool script timed out after #{div(@timeout_ms, 1000)} seconds"}
    end
  rescue
    e -> {:error, "Tool script failed: #{Exception.message(e)}"}
  end

  defp collect_port_output(port, acc) do
    receive do
      {^port, {:data, data}} ->
        collect_port_output(port, acc <> data)

      {^port, {:exit_status, 0}} ->
        {:ok, acc}

      {^port, {:exit_status, code}} ->
        {:error, "Script exited with code #{code}: #{acc}"}
    after
      @timeout_ms ->
        Port.close(port)
        {:error, "Timed out reading script output"}
    end
  end

  defp truncate(output) when byte_size(output) > @max_output_bytes do
    binary_part(output, 0, @max_output_bytes) <> "\n... (output truncated)"
  end

  defp truncate(output), do: output
end
