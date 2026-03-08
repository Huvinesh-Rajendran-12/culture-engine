defmodule AgentHarness.ScriptRunner do
  @moduledoc """
  Runs a script file with JSON input passed via the TOOL_INPUT environment variable.
  Shared by ToolRegistry (built-in dynamic tools) and ToolSet (per-agent dynamic tools).
  """

  @timeout_ms 30_000
  @max_output_bytes 50_000

  @doc "Runs a script at `script_path` with `input` map. Returns `{:ok, output}` or `{:error, reason}`."
  def run(script_path, input) do
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

        collect_port_output(port, "")
      end)

    case Task.yield(task, @timeout_ms) || Task.shutdown(task, :brutal_kill) do
      {:ok, {:ok, output}} -> {:ok, output |> truncate() |> AgentHarness.Sanitize.to_valid_utf8()}
      {:ok, {:error, reason}} -> {:error, reason}
      nil -> {:error, "Tool script timed out after #{div(@timeout_ms, 1000)} seconds"}
    end
  rescue
    e -> {:error, "Tool script failed: #{Exception.message(e)}"}
  end

  defp collect_port_output(port, acc) do
    receive do
      {^port, {:data, data}} -> collect_port_output(port, acc <> data)
      {^port, {:exit_status, 0}} -> {:ok, acc}
      {^port, {:exit_status, code}} -> {:error, "Script exited with code #{code}: #{acc}"}
    after
      @timeout_ms ->
        Port.close(port)
        {:error, "Timed out reading script output"}
    end
  end

  defp truncate(output) when byte_size(output) > @max_output_bytes do
    binary_part(output, 0, @max_output_bytes) <> "\n... (output truncated)"
  end

  defp truncate(output), do: output
end
