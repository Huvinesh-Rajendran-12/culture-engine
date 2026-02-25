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
            case AgentHarness.Agent.chat(agent, input) do
              {:ok, response} ->
                IO.puts("\nagent> #{response}\n")

              {:error, reason} ->
                IO.puts("\n[error] #{reason}\n")
            end

            loop(agent)
        end
    end
  end
end
