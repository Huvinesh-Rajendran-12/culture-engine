defmodule Mix.Tasks.TestAgent do
  @moduledoc "Send a test message to the agent and print events."
  @shortdoc "Test the agent with a sample message"

  use Mix.Task

  @impl true
  def run(args) do
    load_dotenv()
    Mix.Task.run("app.start")

    message = Enum.join(args, " ")
    message = if message == "", do: "What is 2 + 2?", else: message

    IO.puts("Starting agent...")

    {:ok, agent} =
      AgentHarness.Agent.start_link(
        system: "You are a helpful coding assistant with access to file tools. Use them to help the user."
      )

    IO.puts("Sending: #{message}\n")
    AgentHarness.Agent.chat_async(agent, message)
    receive_events()

    IO.puts("\nDone.")
  end

  defp receive_events do
    receive do
      {:agent_event, {:text, text}} ->
        IO.puts("agent> #{text}")
        receive_events()

      {:agent_event, {:tool_use, name, input}} ->
        IO.puts("  [tool] #{name}: #{inspect(input, pretty: true, limit: 5)}")
        receive_events()

      {:agent_event, {:tool_result, name, result}} ->
        truncated = String.slice(result, 0..200)
        IO.puts("  [result] #{name}: #{truncated}")
        receive_events()

      {:agent_event, {:error, reason}} ->
        IO.puts("[error] #{reason}")
        receive_events()

      {:agent_event, :done} ->
        :ok
    after
      120_000 ->
        IO.puts("[timeout] No response after 120s")
    end
  end

  defp load_dotenv do
    case File.read(".env") do
      {:ok, content} ->
        content
        |> String.split("\n", trim: true)
        |> Enum.reject(&(String.starts_with?(&1, "#") or &1 == ""))
        |> Enum.each(fn line ->
          case String.split(line, "=", parts: 2) do
            [key, value] -> System.put_env(String.trim(key), String.trim(value))
            _ -> :ok
          end
        end)

      _ ->
        :ok
    end
  end
end
