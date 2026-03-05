defmodule AgentHarness.ToolSet do
  @moduledoc """
  Per-agent tool isolation. Each agent gets its own ETS table for dynamic
  tools, while built-in tool definitions and execution are delegated to
  the singleton ToolRegistry.
  """

  alias AgentHarness.{ToolRegistry, ScriptRunner}

  @max_dynamic_tools 10

  @doc "Creates a new anonymous ETS table for an agent's dynamic tools."
  def new do
    :ets.new(:tool_set, [:set, :public, read_concurrency: true])
  end

  @doc "Returns all tool definitions: built-in (from ToolRegistry) + agent's dynamic tools."
  def all_definitions(table) do
    builtin = ToolRegistry.all_definitions()

    dynamic =
      :ets.tab2list(table)
      |> Enum.map(fn {_name, def_map} ->
        %{
          "name" => def_map.name,
          "description" => def_map.description,
          "input_schema" => def_map.input_schema
        }
      end)

    builtin ++ dynamic
  end

  @doc "Registers a dynamic tool in this agent's table."
  def register(table, name, description, input_schema, script) do
    cond do
      name in ToolRegistry.builtin_names() ->
        {:error, "Cannot override built-in tool: #{name}"}

      dynamic_count(table) >= @max_dynamic_tools ->
        {:error, "Maximum dynamic tools (#{@max_dynamic_tools}) reached"}

      true ->
        dir = System.tmp_dir!()
        script_path = Path.join(dir, "tool_#{name}_#{System.unique_integer([:positive])}")
        File.write!(script_path, script)
        File.chmod!(script_path, 0o755)

        entry = %{
          name: name,
          description: description,
          input_schema: input_schema,
          script_path: script_path
        }

        :ets.insert(table, {name, entry})
        {:ok, "Tool '#{name}' created successfully. It is now available for use."}
    end
  end

  @doc "Executes a tool: checks agent's dynamic table first, then falls back to built-in."
  def execute(table, name, input) do
    case :ets.lookup(table, name) do
      [{^name, %{script_path: script_path}}] -> ScriptRunner.run(script_path, input)
      [] -> ToolRegistry.execute(name, input)
    end
  end

  @doc "Destroys the per-agent ETS table and cleans up script files."
  def destroy(table) do
    :ets.tab2list(table)
    |> Enum.each(fn {_name, %{script_path: path}} -> File.rm(path) end)

    :ets.delete(table)
  rescue
    ArgumentError -> :ok
  end

  defp dynamic_count(table) do
    :ets.info(table, :size)
  end
end
