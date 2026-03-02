defmodule AgentHarness.Tools.CreateTool do
  @moduledoc """
  Meta-tool that lets the agent define new tools at runtime.

  The agent provides a name, description, input_schema, and a script.
  The script receives tool input as JSON via both stdin and the TOOL_INPUT
  environment variable. It should write its result to stdout.
  """
  @behaviour AgentHarness.Tool

  alias AgentHarness.ToolRegistry

  @impl true
  def name, do: "create_tool"

  @impl true
  def description do
    "Create a new tool that can be used in subsequent turns. " <>
      "Provide a name, description, input_schema (JSON Schema object), and a script. " <>
      "The script should start with a shebang (e.g. #!/usr/bin/env python3). " <>
      "It receives the tool input as JSON on stdin and via the TOOL_INPUT env var. " <>
      "It should write its output to stdout. Exit code 0 = success, non-zero = error. " <>
      "Max 10 dynamic tools per session."
  end

  @impl true
  def input_schema do
    %{
      "type" => "object",
      "properties" => %{
        "name" => %{
          "type" => "string",
          "description" =>
            "Tool name (lowercase, underscores, no spaces). Must not conflict with built-in tools."
        },
        "description" => %{
          "type" => "string",
          "description" => "What the tool does — shown to the model on subsequent turns."
        },
        "input_schema" => %{
          "type" => "object",
          "description" =>
            "JSON Schema describing the tool's input parameters. Must have type, properties, and required fields."
        },
        "script" => %{
          "type" => "string",
          "description" =>
            "The script contents. Must start with a shebang line (e.g. #!/usr/bin/env python3). " <>
              "Reads JSON input from stdin or TOOL_INPUT env var. Writes result to stdout."
        }
      },
      "required" => ["name", "description", "input_schema", "script"]
    }
  end

  @impl true
  def execute(%{
        "name" => name,
        "description" => description,
        "input_schema" => input_schema,
        "script" => script
      }) do
    with :ok <- validate_name(name),
         :ok <- validate_script(script),
         :ok <- validate_schema(input_schema) do
      case ToolRegistry.register(name, description, input_schema, script) do
        {:ok, ^name} ->
          {:ok, "Tool '#{name}' created successfully. It is now available for use."}

        {:error, reason} ->
          {:error, reason}
      end
    end
  end

  def execute(_input) do
    {:error, "Missing required fields: name, description, input_schema, script"}
  end

  defp validate_name(name) do
    if Regex.match?(~r/^[a-z][a-z0-9_]{0,49}$/, name) do
      :ok
    else
      {:error,
       "Invalid tool name '#{name}'. Must be lowercase, start with a letter, " <>
         "and contain only letters, digits, and underscores (max 50 chars)."}
    end
  end

  defp validate_script(script) do
    if String.starts_with?(script, "#!") do
      :ok
    else
      {:error, "Script must start with a shebang line (e.g. #!/usr/bin/env python3)"}
    end
  end

  defp validate_schema(schema) when is_map(schema) do
    if Map.has_key?(schema, "type") and Map.has_key?(schema, "properties") do
      :ok
    else
      {:error, "input_schema must have 'type' and 'properties' fields"}
    end
  end

  defp validate_schema(_), do: {:error, "input_schema must be a JSON object"}
end
