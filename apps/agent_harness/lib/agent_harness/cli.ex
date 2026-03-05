defmodule AgentHarness.CLI do
  @moduledoc """
  Interactive REPL for chatting with the agent.
  """

  def main(_args \\ []) do
    {:ok, agent} =
      AgentHarness.Agent.start_supervised(
        system: "You are a helpful coding assistant with access to file tools. Use them to help the user."
      )

    identity = AgentHarness.Agent.get_identity(agent)
    IO.puts("Agent Harness v0.1.0")
    IO.puts("Mind: #{identity.name} (#{identity.id})")
    IO.puts("Type your message and press Enter. Type 'quit' to exit.\n")

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
      {:agent_event, _id, {:tool_use, name, input}} ->
        IO.puts("\n  [tool] #{name}: #{inspect(input, pretty: true, limit: 5)}")
        receive_events()

      {:agent_event, _id, {:tool_result, name, result}} ->
        truncated = String.slice(result, 0..200)
        IO.puts("  [result] #{name}: #{truncated}")
        receive_events()

      {:agent_event, _id, {:text, text}} ->
        IO.puts("\nagent> #{text}")
        receive_events()

      {:agent_event, _id, {:error, reason}} ->
        IO.puts("\n[error] #{reason}")
        receive_events()

      {:agent_event, _id, :done} ->
        :ok
    after
      120_000 ->
        IO.puts("\n[timeout] No response from agent after 120s")
    end
  end
end
