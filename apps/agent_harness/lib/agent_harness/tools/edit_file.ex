defmodule AgentHarness.Tools.EditFile do
  @behaviour AgentHarness.Tool

  @impl true
  def name, do: "edit_file"

  @impl true
  def description do
    "Edit a file by replacing old_string with new_string. If the file doesn't exist, it will be created with new_string as content. old_string and new_string must be different."
  end

  @impl true
  def input_schema do
    %{
      "type" => "object",
      "properties" => %{
        "path" => %{
          "type" => "string",
          "description" => "The path to the file to edit"
        },
        "old_string" => %{
          "type" => "string",
          "description" => "The string to search for (empty string to create new file)"
        },
        "new_string" => %{
          "type" => "string",
          "description" => "The replacement string"
        }
      },
      "required" => ["path", "old_string", "new_string"]
    }
  end

  @impl true
  def execute(%{"path" => path, "old_string" => old, "new_string" => new}) do
    cond do
      old == new ->
        {:error, "old_string and new_string must be different"}

      old == "" ->
        # Create new file
        File.mkdir_p!(Path.dirname(path))
        File.write!(path, new)
        {:ok, "Created #{path}"}

      true ->
        case File.read(path) do
          {:ok, content} ->
            if String.contains?(content, old) do
              updated = String.replace(content, old, new, global: false)
              File.write!(path, updated)
              {:ok, "Updated #{path}"}
            else
              {:error, "old_string not found in #{path}"}
            end

          {:error, :enoent} ->
            {:error, "File not found: #{path}"}

          {:error, reason} ->
            {:error, "Failed to read #{path}: #{reason}"}
        end
    end
  end
end
