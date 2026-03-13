defmodule AgentHarness.Tools.CreateTool do
  @moduledoc """
  Meta-tool that lets the agent define new tools at runtime.

  This module provides the tool definition (name, description, input_schema)
  and input validation. Execution is handled by the Agent loop, which routes
  create_tool calls to the agent's per-agent ToolSet.
  """
  @behaviour AgentHarness.Tool

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

  @doc "Validates create_tool input. Returns `:ok` or `{:error, reason}`."
  def validate(%{
        "name" => name,
        "description" => _,
        "input_schema" => schema,
        "script" => script
      })
      when is_binary(name) and is_binary(script) and is_map(schema) do
    cond do
      not Regex.match?(~r/^[a-z][a-z0-9_]{0,49}$/, name) ->
        {:error,
         "Invalid tool name '#{name}'. Must be lowercase, start with a letter, " <>
           "and contain only letters, digits, and underscores (max 50 chars)."}

      not String.starts_with?(script, "#!") ->
        {:error, "Script must start with a shebang line (e.g. #!/usr/bin/env python3)"}

      not Map.has_key?(schema, "type") or not Map.has_key?(schema, "properties") ->
        {:error, "input_schema must have 'type' and 'properties' fields"}

      true ->
        :ok
    end
  end

  def validate(_input) do
    {:error, "Missing required fields: name, description, input_schema, script"}
  end

  @impl true
  def execute(_input) do
    {:error, "create_tool must be executed within an agent context"}
  end
end
