defmodule AgentHarness.Tools.HotReload do
  @moduledoc """
  Mind-only tool that hot-reloads modified Elixir source files into the running BEAM VM.

  The BEAM supports hot code loading natively — each module can have two versions
  loaded simultaneously (current and old). This tool leverages that capability to
  let the Mind modify its own source code and load changes without restarting.

  Safety: Reloading core modules (Agent, Supervisor, API) while they are actively
  handling requests can cause process crashes. The tool warns about high-risk modules
  but does not block — the Mind is trusted to understand the consequences.
  """
  @behaviour AgentHarness.Tool

  @high_risk_modules ~w(
    AgentHarness.Agent
    AgentHarness.Supervisor
    AgentHarness.API
    AgentHarness.ToolRegistry
    AgentHarnessWeb.Endpoint
  )

  @impl true
  def name, do: "hot_reload"

  @impl true
  def description do
    "Hot-reload modified Elixir source files into the running BEAM VM. " <>
      "After editing .ex files with edit_file or write_file, call this tool to " <>
      "compile and load the changes without restarting. Accepts a list of file paths " <>
      "to recompile, or a single path. The BEAM supports two simultaneous module versions, " <>
      "so existing processes continue on the old code until they make a fully-qualified call. " <>
      "Mind-only capability."
  end

  @impl true
  def input_schema do
    %{
      "type" => "object",
      "properties" => %{
        "files" => %{
          "type" => "array",
          "items" => %{"type" => "string"},
          "description" =>
            "List of .ex file paths to recompile and hot-load. " <>
              "Each file is compiled individually. Paths should be absolute or " <>
              "relative to the project root."
        },
        "recompile_all" => %{
          "type" => "boolean",
          "description" =>
            "If true, runs a full project recompile (equivalent to `mix compile --force`). " <>
              "Ignores the 'files' parameter. Use sparingly — this reloads everything."
        }
      },
      "required" => []
    }
  end

  @impl true
  def execute(input) do
    cond do
      input["recompile_all"] == true ->
        recompile_all()

      is_list(input["files"]) and input["files"] != [] ->
        reload_files(input["files"])

      true ->
        {:error, "Provide either 'files' (list of .ex paths) or set 'recompile_all' to true."}
    end
  end

  defp reload_files(paths) do
    results =
      Enum.map(paths, fn path ->
        path = Path.expand(path)

        if String.ends_with?(path, ".ex") do
          compile_and_load(path)
        else
          {path, :error, [], "Not an Elixir source file: #{path}"}
        end
      end)

    {successes, failures} = Enum.split_with(results, fn {_, status, _, _} -> status == :ok end)

    loaded_modules = Enum.flat_map(successes, fn {_, _, modules, _} -> modules end)

    output =
      Enum.map_join(results, "\n", fn {path, status, _modules, msg} ->
        short = Path.relative_to_cwd(path)

        case status do
          :ok -> "OK  #{short}: #{msg}"
          :error -> "ERR #{short}: #{msg}"
        end
      end)

    summary = "\n---\n#{length(successes)} succeeded, #{length(failures)} failed."
    warnings = build_warnings(loaded_modules)

    {:ok, output <> summary <> warnings}
  end

  defp compile_and_load(path) do
    modules = Code.compile_file(path)

    module_names =
      modules
      |> Enum.map(fn {mod, _bytecode} -> inspect(mod) end)
      |> Enum.join(", ")

    {path, :ok, Enum.map(modules, &elem(&1, 0)), "Loaded modules: #{module_names}"}
  rescue
    e ->
      {path, :error, [], "Compilation error: #{Exception.format(:error, e)}"}
  end

  defp recompile_all do
    case IEx.Helpers.recompile() do
      :ok -> {:ok, "Full recompile succeeded. All modules reloaded."}
      :noop -> {:ok, "No changes detected. Nothing to recompile."}
      {:error, _} -> {:error, "Full recompile failed. Check source files for errors."}
    end
  rescue
    e -> {:error, "Recompile failed: #{Exception.message(e)}"}
  end

  defp build_warnings(loaded_modules) do
    risky =
      loaded_modules
      |> Enum.map(&inspect/1)
      |> Enum.filter(&(&1 in @high_risk_modules))

    case risky do
      [] ->
        ""

      modules ->
        names = Enum.join(modules, ", ")

        "\n\nWARNING: Reloaded high-risk modules: #{names}. " <>
          "Running processes still use the old code until they make a fully-qualified " <>
          "function call (e.g., Module.function()). Spawning new agents will use the " <>
          "new code immediately."
    end
  end
end
