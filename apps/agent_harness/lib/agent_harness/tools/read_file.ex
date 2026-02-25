defmodule AgentHarness.Tools.ReadFile do
  @behaviour AgentHarness.Tool

  @impl true
  def name, do: "read_file"

  @impl true
  def description, do: "Read the contents of a file at the given path."

  @impl true
  def input_schema do
    %{
      "type" => "object",
      "properties" => %{
        "path" => %{
          "type" => "string",
          "description" => "The path to the file to read"
        }
      },
      "required" => ["path"]
    }
  end

  @impl true
  def execute(%{"path" => path}) do
    case File.read(path) do
      {:ok, content} -> {:ok, content}
      {:error, :enoent} -> {:error, "File not found: #{path}"}
      {:error, reason} -> {:error, "Failed to read #{path}: #{reason}"}
    end
  end
end
