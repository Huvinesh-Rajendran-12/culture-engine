defmodule AgentHarness.ScriptRunner do
  @moduledoc """
  Runs a script file with JSON input passed via the TOOL_INPUT environment variable.
  Shared by ToolRegistry (built-in dynamic tools) and ToolSet (per-agent dynamic tools).
  """

  @default_timeout_ms 120_000
  @default_max_output_bytes 200_000

  @doc """
  Runs a script at `script_path` with `input` map. Returns `{:ok, output}` or `{:error, reason}`.

  Options:
    - `timeout` — max execution time in ms (default: #{@default_timeout_ms})
    - `max_output_bytes` — truncate output beyond this size (default: #{@default_max_output_bytes})
  """
  def run(script_path, input, opts \\ []) do
    timeout = opts[:timeout] || @default_timeout_ms
    max_bytes = opts[:max_output_bytes] || @default_max_output_bytes
    json_input = Jason.encode!(input) |> String.replace(<<0>>, "")

    task =
      Task.async(fn ->
        port =
          Port.open({:spawn_executable, script_path}, [
            :binary,
            :exit_status,
            :stderr_to_stdout,
            env: [{~c"TOOL_INPUT", String.to_charlist(json_input)}]
          ])

        collect_port_output(port, "", timeout)
      end)

    case Task.yield(task, timeout) || Task.shutdown(task, :brutal_kill) do
      {:ok, {:ok, output}} -> {:ok, truncate(output, max_bytes)}
      {:ok, {:error, reason}} -> {:error, reason}
      nil -> {:error, "Tool script timed out after #{div(timeout, 1000)} seconds"}
    end
  rescue
    e -> {:error, "Tool script failed: #{Exception.message(e)}"}
  end

  defp collect_port_output(port, acc, timeout) do
    receive do
      {^port, {:data, data}} -> collect_port_output(port, acc <> data, timeout)
      {^port, {:exit_status, 0}} -> {:ok, acc}
      {^port, {:exit_status, code}} -> {:error, "Script exited with code #{code}: #{acc}"}
    after
      timeout ->
        Port.close(port)
        {:error, "Timed out reading script output"}
    end
  end

  @doc "Truncates output to `max_bytes`, appending a notice if truncated."
  def truncate(output, max_bytes) when byte_size(output) > max_bytes do
    binary_part(output, 0, max_bytes) <> "\n... (output truncated)"
  end

  def truncate(output, _max_bytes), do: output
end
