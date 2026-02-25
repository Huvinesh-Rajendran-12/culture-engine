defmodule AgentHarness.Tools.ListFiles do
  @behaviour AgentHarness.Tool

  @impl true
  def name, do: "list_files"

  @impl true
  def description, do: "List files and directories at the given path. Directories have a trailing slash."

  @impl true
  def input_schema do
    %{
      "type" => "object",
      "properties" => %{
        "path" => %{
          "type" => "string",
          "description" => "The directory path to list"
        }
      },
      "required" => ["path"]
    }
  end

  @impl true
  def execute(%{"path" => path}) do
    case File.ls(path) do
      {:ok, entries} ->
        items =
          entries
          |> Enum.sort()
          |> Enum.map(fn entry ->
            full = Path.join(path, entry)

            if File.dir?(full) do
              entry <> "/"
            else
              entry
            end
          end)

        {:ok, Jason.encode!(items)}

      {:error, :enoent} ->
        {:error, "Directory not found: #{path}"}

      {:error, reason} ->
        {:error, "Failed to list #{path}: #{reason}"}
    end
  end
end
