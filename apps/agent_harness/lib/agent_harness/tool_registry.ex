defmodule AgentHarness.ToolRegistry do
  @moduledoc """
  Registry of available tools. Built-in tools are seeded on init;
  dynamic tools can be registered at runtime via `register/4`.

  Built-in tools are stored as `{name, {:module, module}}`.
  Dynamic tools are stored as `{name, {:script, definition}}` where
  definition holds the description, input_schema, and script path.
  """
  use GenServer

  alias AgentHarness.{Tool, ScriptRunner}
  alias AgentHarness.Tools.{ReadFile, ListFiles, EditFile, RunCommand, SearchFiles, CreateTool, SpawnAgent, ListAgents}

  @table :tool_registry
  @max_dynamic_tools 10
  @builtin_modules [ReadFile, ListFiles, EditFile, RunCommand, SearchFiles, CreateTool, SpawnAgent, ListAgents]

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

  @doc "Returns the list of built-in tool names."
  def builtin_names do
    Enum.map(@builtin_modules, & &1.name())
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
    cond do
      name in builtin_names() ->
        {:reply, {:error, "Cannot override built-in tool: #{name}"}, state}

      dynamic_tool_count() >= @max_dynamic_tools ->
        {:reply, {:error, "Maximum dynamic tools (#{@max_dynamic_tools}) reached"}, state}

      true ->
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
    if name in builtin_names() do
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

  defp do_execute({:module, module}, input) do
    module.execute(input)
  end

  defp do_execute({:script, %{script_path: script_path}}, input) do
    ScriptRunner.run(script_path, input)
  end
end
