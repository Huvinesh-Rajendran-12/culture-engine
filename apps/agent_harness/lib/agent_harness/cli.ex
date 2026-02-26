defmodule AgentHarness.CLI do
  @moduledoc """
  Interactive REPL for chatting with the agent.
  """

  def main(_args \\ []) do
    IO.puts("Agent Harness v0.1.0")
    IO.puts("Type your message and press Enter. Type 'quit' to exit.\n")

    {:ok, agent} =
      AgentHarness.Agent.start_link(
        system: "You are a helpful coding assistant with access to file tools. Use them to help the user."
      )

    loop(agent)
  end

  defp loop(agent) do
    case IO.gets("you> ") do
      :eof ->
        IO.puts("\nGoodbye!")

      input ->
        input = String.trim(input)

        cond do
          input in ["quit", "exit", "q"] ->
            IO.puts("Goodbye!")

          input == "" ->
            loop(agent)

          input == "/reset" ->
            AgentHarness.Agent.reset(agent)
            IO.puts("[conversation reset]\n")
            loop(agent)

          true ->
            AgentHarness.Agent.chat_async(agent, input)
            receive_events()
            IO.puts("")
            loop(agent)
        end
    end
  end

  defp receive_events do
    receive do
      {:agent_event, {:tool_use, name, input}} ->
        IO.puts("\n  [tool] #{name}: #{inspect(input, pretty: true, limit: 5)}")
        receive_events()

      {:agent_event, {:tool_result, name, result}} ->
        truncated = String.slice(result, 0..200)
        IO.puts("  [result] #{name}: #{truncated}")
        receive_events()

      {:agent_event, {:text, text}} ->
        IO.puts("\nagent> #{text}")

        receive_events()

      {:agent_event, {:error, reason}} ->
        IO.puts("\n[error] #{reason}")
        receive_events()

      {:agent_event, :done} ->
        :ok
    after
      120_000 ->
        IO.puts("\n[timeout] No response from agent after 120s")
    end
  end
end
