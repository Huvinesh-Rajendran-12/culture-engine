defmodule AgentHarness.Tools.RunCommand do
  @behaviour AgentHarness.Tool

  @impl true
  def name, do: "run_command"

  @impl true
  def description do
    "Run a shell command and return its combined stdout/stderr. " <>
      "Commands are terminated after 120 seconds by default (set timeout to override, max 300). " <>
      "Output is truncated to 200KB. " <>
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
        },
        "timeout" => %{
          "type" => "integer",
          "description" =>
            "Optional timeout in seconds (default: 120, max: 300). " <>
              "Use higher values for long-running analysis."
        }
      },
      "required" => ["command"]
    }
  end

  @default_timeout_ms 120_000
  @max_timeout_ms 300_000
  @max_output_bytes 200_000

  @impl true
  def execute(%{"command" => command} = input) do
    timeout = resolve_timeout(input)
    max_bytes = resolve_max_output_bytes(input)
    opts = [stderr_to_stdout: true]

    opts =
      case Map.get(input, "working_directory") do
        nil -> opts
        "" -> opts
        dir -> Keyword.put(opts, :cd, dir)
      end

    task = Task.async(fn -> System.cmd("sh", ["-c", command], opts) end)

    case Task.yield(task, timeout) || Task.shutdown(task, :brutal_kill) do
      {:ok, {output, 0}} ->
        {:ok, AgentHarness.ScriptRunner.truncate(output, max_bytes)}

      {:ok, {output, code}} ->
        {:ok, AgentHarness.ScriptRunner.truncate("Exit code #{code}:\n#{output}", max_bytes)}

      nil ->
        {:error, "Command timed out after #{div(timeout, 1000)} seconds"}
    end
  rescue
    e -> {:error, "Command failed: #{Exception.message(e)}"}
  catch
    :exit, reason -> {:error, "Command exited: #{inspect(reason)}"}
  end

  defp resolve_timeout(%{"timeout" => seconds}) when is_integer(seconds) and seconds > 0 do
    min(seconds * 1000, @max_timeout_ms)
  end

  defp resolve_timeout(_input), do: @default_timeout_ms

  defp resolve_max_output_bytes(%{"max_output_bytes" => bytes})
       when is_integer(bytes) and bytes > 0,
       do: bytes

  defp resolve_max_output_bytes(_input), do: @max_output_bytes
end
