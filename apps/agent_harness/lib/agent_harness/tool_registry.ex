defmodule AgentHarness.ToolRegistry do
  @moduledoc """
  Registry of available tools. Maps tool names to their implementing modules.
  """

  alias AgentHarness.Tool
  alias AgentHarness.Tools.{ReadFile, ListFiles, EditFile}

  @tools [ReadFile, ListFiles, EditFile]

  def all_definitions do
    Enum.map(@tools, &Tool.to_api_definition/1)
  end

  def execute(name, input) do
    case Enum.find(@tools, fn t -> t.name() == name end) do
      nil -> {:error, "Unknown tool: #{name}"}
      tool -> tool.execute(input)
    end
  end

  def tools, do: @tools
end
