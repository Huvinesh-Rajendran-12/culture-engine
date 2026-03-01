defmodule AgentHarness.Tools.SearchFiles do
  @behaviour AgentHarness.Tool

  @impl true
  def name, do: "search_files"

  @impl true
  def description do
    "Search for a text pattern in files recursively. Returns matching lines with file paths " <>
      "and line numbers. Supports regular expressions. Skips hidden directories, _build, deps, " <>
      "and node_modules. Files larger than 1MB are skipped."
  end

  @impl true
  def input_schema do
    %{
      "type" => "object",
      "properties" => %{
        "pattern" => %{
          "type" => "string",
          "description" => "The text pattern to search for (supports regular expressions)"
        },
        "path" => %{
          "type" => "string",
          "description" => "The directory to search in"
        },
        "file_pattern" => %{
          "type" => "string",
          "description" =>
            "Optional filename pattern to filter by (e.g. \"*.ex\", \"*.json\"). Matches basename only."
        }
      },
      "required" => ["pattern", "path"]
    }
  end

  @max_results 100
  @max_file_size 1_000_000

  @impl true
  def execute(%{"pattern" => pattern, "path" => path} = input) do
    unless File.dir?(path) do
      {:error, "Directory not found: #{path}"}
    else
      file_pattern = Map.get(input, "file_pattern")
      results = search_directory(path, pattern, file_pattern)

      case results do
        [] ->
          {:ok, "No matches found."}

        matches ->
          truncated = Enum.take(matches, @max_results)

          output =
            if length(matches) > @max_results do
              Enum.join(truncated, "\n") <>
                "\n... (#{length(matches) - @max_results} more matches truncated)"
            else
              Enum.join(truncated, "\n")
            end

          {:ok, output}
      end
    end
  end

  defp search_directory(dir, pattern, file_pattern) do
    compiled_file_regex = compile_file_pattern(file_pattern)

    dir
    |> list_files_recursive()
    |> Enum.filter(&matches_file_pattern?(&1, compiled_file_regex))
    |> Enum.flat_map(&search_file(&1, pattern))
  end

  defp list_files_recursive(dir) do
    case File.ls(dir) do
      {:ok, entries} ->
        Enum.flat_map(entries, fn entry ->
          full_path = Path.join(dir, entry)

          if String.starts_with?(entry, ".") or entry in ["_build", "deps", "node_modules"] do
            []
          else
            case File.lstat(full_path) do
              {:ok, %{type: :directory}} -> list_files_recursive(full_path)
              {:ok, %{type: :regular}} -> [full_path]
              _ -> []
            end
          end
        end)

      {:error, _} ->
        []
    end
  end

  defp compile_file_pattern(nil), do: nil
  defp compile_file_pattern(""), do: nil

  defp compile_file_pattern(glob) do
    regex_str =
      glob
      |> Regex.escape()
      |> String.replace("\\*", ".*")
      |> then(&"^#{&1}$")

    case Regex.compile(regex_str) do
      {:ok, regex} -> regex
      {:error, _} -> nil
    end
  end

  defp matches_file_pattern?(_path, nil), do: true

  defp matches_file_pattern?(path, regex) do
    Regex.match?(regex, Path.basename(path))
  end

  defp search_file(path, pattern) do
    case File.stat(path) do
      {:ok, %{size: size}} when size > @max_file_size ->
        []

      _ ->
        case File.read(path) do
          {:ok, content} ->
            if String.valid?(content) do
              search_content(content, path, pattern)
            else
              []
            end

          {:error, _} ->
            []
        end
    end
  end

  defp search_content(content, path, pattern) do
    lines =
      content
      |> String.split("\n")
      |> Enum.with_index(1)

    case Regex.compile(pattern) do
      {:ok, regex} ->
        Enum.filter(lines, fn {line, _num} -> Regex.match?(regex, line) end)

      {:error, _} ->
        Enum.filter(lines, fn {line, _num} -> String.contains?(line, pattern) end)
    end
    |> Enum.map(fn {line, num} -> "#{path}:#{num}: #{line}" end)
  end
end
