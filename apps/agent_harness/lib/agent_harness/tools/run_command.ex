defmodule AgentHarness.Tools.RunCommand do
  @behaviour AgentHarness.Tool

  @impl true
  def name, do: "run_command"

  @impl true
  def description do
    "Run a shell command and return its combined stdout/stderr. " <>
      "Commands are terminated after 30 seconds. " <>
      "Output is truncated to 50KB. " <>
      "Note: commands run unrestricted with the same privileges as this process."
  end

  @impl true
  def input_schema do
    %{
      "type" => "object",
      "properties" => %{
        "command" => %{
          "type" => "string",
          "description" => "The shell command to execute"
        },
        "working_directory" => %{
          "type" => "string",
          "description" => "Optional working directory for the command"
        }
      },
      "required" => ["command"]
    }
  end

  @timeout_ms 30_000
  @max_output_bytes 50_000

  @impl true
  def execute(%{"command" => command} = input) do
    opts = [stderr_to_stdout: true]

    opts =
      case Map.get(input, "working_directory") do
        nil -> opts
        "" -> opts
        dir -> Keyword.put(opts, :cd, dir)
      end

    task = Task.async(fn -> System.cmd("sh", ["-c", command], opts) end)

    case Task.yield(task, @timeout_ms) || Task.shutdown(task, :brutal_kill) do
      {:ok, {output, 0}} ->
        {:ok, truncate_output(output)}

      {:ok, {output, code}} ->
        {:ok, truncate_output("Exit code #{code}:\n#{output}")}

      nil ->
        {:error, "Command timed out after #{div(@timeout_ms, 1000)} seconds"}
    end
  rescue
    e -> {:error, "Command failed: #{Exception.message(e)}"}
  catch
    :exit, reason -> {:error, "Command exited: #{inspect(reason)}"}
  end

  defp truncate_output(output) when byte_size(output) > @max_output_bytes do
    binary_part(output, 0, @max_output_bytes) <> "\n... (output truncated)"
  end

  defp truncate_output(output), do: output
end
