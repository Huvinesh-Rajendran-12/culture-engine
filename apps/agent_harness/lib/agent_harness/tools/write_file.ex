defmodule AgentHarness.Tools.WriteFile do
  @behaviour AgentHarness.Tool

  @impl true
  def name, do: "write_file"

  @impl true
  def description do
    "Write complete contents to a file, creating parent directories if needed. " <>
      "Use this when you want to replace or create a file in one step."
  end

  @impl true
  def input_schema do
    %{
      "type" => "object",
      "properties" => %{
        "path" => %{
          "type" => "string",
          "description" => "The path to the file to write"
        },
        "content" => %{
          "type" => "string",
          "description" => "The full file contents to write"
        }
      },
      "required" => ["path", "content"]
    }
  end

  @impl true
  def execute(%{"path" => path, "content" => content}) do
    File.mkdir_p!(Path.dirname(path))
    File.write!(path, content)
    {:ok, "Wrote #{path}"}
  rescue
    e -> {:error, "Failed to write #{path}: #{Exception.message(e)}"}
  end
end
